"""Iterable sync provider — bidirectional template sync via Email Templates API.

Key quirk: Upsert-based — same endpoint for create and update.
If ``templateId`` is provided, updates; otherwise creates.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sync_schemas import ESPTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class IterableSyncProvider:
    """Implements ESPSyncProvider for Iterable Email Templates.

    Credentials: ``{"api_key": "..."}``
    """

    _base_url: str

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.iterable_base_url

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {
            "Api-Key": credentials["api_key"],
            "Content-Type": "application/json",
        }

    @staticmethod
    def _map_template(item: dict[str, Any]) -> ESPTemplate:
        """Map an Iterable email template object to ESPTemplate."""
        return ESPTemplate(
            id=str(item.get("templateId", item.get("id", ""))),
            name=str(item.get("name", "")),
            html=str(item.get("html", "")),
            esp_type="iterable",
            created_at=str(item.get("createdAt", "")),
            updated_at=str(item.get("updatedAt", "")),
        )

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by fetching user info."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{self._base_url}/users/getByEmail",
                    headers=self._headers(credentials),
                    params={"email": "test@validation.check"},
                )
                # 200 or 400 (no user) both confirm valid API key;
                # 401 means invalid.
                return resp.status_code != 401
        except httpx.HTTPError:
            logger.warning("iterable.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all email templates."""
        templates: list[ESPTemplate] = []

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{self._base_url}/templates",
                headers=self._headers(credentials),
                params={"templateType": "Base", "messageMedium": "Email"},
            )
            resp.raise_for_status()
            body = resp.json()

            for item in body.get("templates", []):
                templates.append(self._map_template(item))

        return templates

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single email template by ID."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{self._base_url}/templates/email/get",
                headers=self._headers(credentials),
                params={"templateId": template_id},
            )
            resp.raise_for_status()
            item = resp.json()
        return self._map_template(item)

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new email template via upsert (no templateId = create)."""
        payload = {
            "name": name,
            "html": html,
            "messageMedium": "Email",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "POST",
                f"{self._base_url}/templates/email/upsert",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            body = resp.json()
        return self._map_template(body)

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update a template via upsert (templateId present = update)."""
        try:
            tid = int(template_id)
        except ValueError:
            msg = f"Iterable template IDs must be numeric, got: {template_id}"
            raise ValueError(msg) from None
        payload = {
            "templateId": tid,
            "html": html,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "POST",
                f"{self._base_url}/templates/email/upsert",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            body = resp.json()
        return self._map_template(body)

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a template. Returns True if successful (200)."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "DELETE",
                f"{self._base_url}/templates/{template_id}",
                headers=self._headers(credentials),
            )
            return resp.status_code == 200
