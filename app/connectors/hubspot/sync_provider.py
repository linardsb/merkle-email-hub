"""HubSpot sync provider — bidirectional template sync via Marketing Email API."""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sync_schemas import ESPTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class HubSpotSyncProvider:
    """Implements ESPSyncProvider for HubSpot Marketing Emails.

    Credentials: ``{"access_token": "pat-..."}``
    """

    _base_url: str

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.hubspot_base_url

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credentials['access_token']}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _map_template(item: dict[str, Any]) -> ESPTemplate:
        """Map a HubSpot marketing email object to ESPTemplate."""
        content: dict[str, Any] = item.get("content") or {}
        return ESPTemplate(
            id=str(item.get("id", "")),
            name=str(item.get("name", "")),
            html=str(content.get("html", "")),
            esp_type="hubspot",
            created_at=str(item.get("createdAt", "")),
            updated_at=str(item.get("updatedAt", "")),
        )

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by fetching account details."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{self._base_url}/account-info/v3/details",
                    headers=self._headers(credentials),
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            logger.warning("hubspot.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all HubSpot marketing emails with cursor pagination."""
        templates: list[ESPTemplate] = []
        params: dict[str, str] = {}

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{self._base_url}/marketing/v3/emails/",
                    headers=self._headers(credentials),
                    params=params or None,
                )
                resp.raise_for_status()
                body = resp.json()

                for item in body.get("results", []):
                    templates.append(self._map_template(item))

                paging: dict[str, Any] = body.get("paging") or {}
                next_page: dict[str, Any] = paging.get("next") or {}
                after: str | None = next_page.get("after")
                if after is None:
                    break
                params = {"after": str(after)}

        return templates

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single marketing email by ID."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{self._base_url}/marketing/v3/emails/{template_id}",
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            item = resp.json()
        return self._map_template(item)

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new marketing email in HubSpot."""
        payload = {
            "name": name,
            "content": {"html": html},
            "type": "REGULAR",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "POST",
                f"{self._base_url}/marketing/v3/emails/",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            item = resp.json()
        return self._map_template(item)

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update a marketing email's HTML."""
        payload = {"content": {"html": html}}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "PATCH",
                f"{self._base_url}/marketing/v3/emails/{template_id}",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            item = resp.json()
        return self._map_template(item)

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a marketing email (soft delete to trash). Returns True if successful."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "DELETE",
                f"{self._base_url}/marketing/v3/emails/{template_id}",
                headers=self._headers(credentials),
            )
            return resp.status_code == 204
