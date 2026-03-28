"""Brevo sync provider — bidirectional template sync via SMTP Templates API."""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sync_schemas import ESPTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BrevoSyncProvider:
    """Implements ESPSyncProvider for Brevo (formerly Sendinblue) SMTP Templates.

    Credentials: ``{"api_key": "xkeysib-..."}``
    """

    _base_url: str

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.brevo_base_url

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {
            "api-key": credentials["api_key"],
            "Content-Type": "application/json",
        }

    @staticmethod
    def _map_template(item: dict[str, Any]) -> ESPTemplate:
        """Map a Brevo SMTP template object to ESPTemplate."""
        return ESPTemplate(
            id=str(item.get("id", "")),
            name=str(item.get("name", "")),
            html=str(item.get("htmlContent", "")),
            esp_type="brevo",
            created_at=str(item.get("createdAt", "")),
            updated_at=str(item.get("modifiedAt", "")),
        )

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by fetching account info."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{self._base_url}/account",
                    headers=self._headers(credentials),
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            logger.warning("brevo.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all SMTP templates with offset pagination."""
        templates: list[ESPTemplate] = []
        offset = 0
        limit = 50

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{self._base_url}/smtp/templates",
                    headers=self._headers(credentials),
                    params={"offset": str(offset), "limit": str(limit)},
                )
                resp.raise_for_status()
                body = resp.json()

                items: list[dict[str, Any]] = body.get("templates", [])
                for item in items:
                    templates.append(self._map_template(item))

                count: int = body.get("count", 0)
                offset += len(items)
                if offset >= count or not items:
                    break

        return templates

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single SMTP template by ID."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{self._base_url}/smtp/templates/{template_id}",
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            item = resp.json()
        return self._map_template(item)

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new SMTP template."""
        payload = {
            "templateName": name,
            "htmlContent": html,
            "subject": "{{params.subject}}",
            "sender": {"name": "Default", "email": "noreply@example.com"},
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "POST",
                f"{self._base_url}/smtp/templates",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            body = resp.json()

        # Brevo returns {"id": 123} on create — fetch full template
        created_id = str(body.get("id", ""))
        return await self.get_template(created_id, credentials)

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update a template's HTML content."""
        payload = {"htmlContent": html}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "PUT",
                f"{self._base_url}/smtp/templates/{template_id}",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()

        # Brevo returns 204 on update — fetch to return full template
        return await self.get_template(template_id, credentials)

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a template. Returns True if successful (204)."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "DELETE",
                f"{self._base_url}/smtp/templates/{template_id}",
                headers=self._headers(credentials),
            )
            return resp.status_code == 204
