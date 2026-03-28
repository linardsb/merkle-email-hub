"""SendGrid sync provider — bidirectional template sync via Templates API v3.

Key quirk: Templates have **versions** — HTML lives on version objects, not template.
``create_template()`` creates a template then adds a version.
``update_template()`` creates a new version on the existing template.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sync_schemas import ESPTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SendGridSyncProvider:
    """Implements ESPSyncProvider for SendGrid Templates.

    Credentials: ``{"api_key": "SG...."}``
    """

    _base_url: str

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.sendgrid_base_url

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credentials['api_key']}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _map_template(item: dict[str, Any]) -> ESPTemplate:
        """Map a SendGrid template object to ESPTemplate.

        HTML is extracted from the first (active) version if available.
        """
        versions: list[dict[str, Any]] = item.get("versions") or []
        active = next(
            (v for v in versions if v.get("active") == 1),
            versions[0] if versions else {},
        )
        return ESPTemplate(
            id=str(item.get("id", "")),
            name=str(item.get("name", "")),
            html=str(active.get("html_content", "")),
            esp_type="sendgrid",
            created_at=str(active.get("created_at", active.get("updated_at", ""))),
            updated_at=str(active.get("updated_at", "")),
        )

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by checking API key scopes."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{self._base_url}/scopes",
                    headers=self._headers(credentials),
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            logger.warning("sendgrid.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all dynamic templates (no pagination, max 200)."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{self._base_url}/templates",
                headers=self._headers(credentials),
                params={"generations": "dynamic", "page_size": "200"},
            )
            resp.raise_for_status()
            body = resp.json()

        templates: list[ESPTemplate] = []
        for item in body.get("result", body.get("templates", [])):
            templates.append(self._map_template(item))
        return templates

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single template by ID (includes versions)."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{self._base_url}/templates/{template_id}",
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            item = resp.json()
        return self._map_template(item)

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a template then add an active version with HTML."""
        async with httpx.AsyncClient(timeout=15) as client:
            # Step 1: Create the template shell
            resp = await resilient_request(
                client,
                "POST",
                f"{self._base_url}/templates",
                json={"name": name, "generation": "dynamic"},
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            template = resp.json()
            template_id = str(template.get("id", ""))

            # Step 2: Add a version with HTML content
            version_resp = await resilient_request(
                client,
                "POST",
                f"{self._base_url}/templates/{template_id}/versions",
                json={
                    "name": name,
                    "html_content": html,
                    "subject": "{{subject}}",
                    "active": 1,
                },
                headers=self._headers(credentials),
            )
            version_resp.raise_for_status()

        # Re-fetch to get full template with versions
        return await self.get_template(template_id, credentials)

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update by creating a new active version on the template."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "POST",
                f"{self._base_url}/templates/{template_id}/versions",
                json={
                    "name": "Updated",
                    "html_content": html,
                    "subject": "{{subject}}",
                    "active": 1,
                },
                headers=self._headers(credentials),
            )
            resp.raise_for_status()

        return await self.get_template(template_id, credentials)

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a template. Returns True if successful (204)."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "DELETE",
                f"{self._base_url}/templates/{template_id}",
                headers=self._headers(credentials),
            )
            return resp.status_code == 204
