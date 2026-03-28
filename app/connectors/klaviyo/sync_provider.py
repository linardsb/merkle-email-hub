"""Klaviyo sync provider — bidirectional template sync via Templates API (JSON:API)."""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sync_schemas import ESPTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_API_REVISION = "2025-07-15"


class KlaviyoSyncProvider:
    """Implements ESPSyncProvider for Klaviyo Templates.

    Credentials: ``{"api_key": "pk_..."}``
    """

    _base_url: str

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.klaviyo_base_url

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {
            "Authorization": f"Klaviyo-API-Key {credentials['api_key']}",
            "revision": _API_REVISION,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _map_template(item: dict[str, Any]) -> ESPTemplate:
        """Map a Klaviyo JSON:API template resource to ESPTemplate."""
        attrs: dict[str, Any] = item.get("attributes") or {}
        return ESPTemplate(
            id=str(item.get("id", "")),
            name=str(attrs.get("name", "")),
            html=str(attrs.get("html", "")),
            esp_type="klaviyo",
            created_at=str(attrs.get("created", "")),
            updated_at=str(attrs.get("updated", "")),
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
                    f"{self._base_url}/api/accounts/",
                    headers=self._headers(credentials),
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            logger.warning("klaviyo.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all Klaviyo email templates with cursor pagination."""
        templates: list[ESPTemplate] = []
        url: str | None = f"{self._base_url}/api/templates/"

        async with httpx.AsyncClient(timeout=30) as client:
            while url is not None:
                resp = await resilient_request(
                    client,
                    "GET",
                    url,
                    headers=self._headers(credentials),
                )
                resp.raise_for_status()
                body = resp.json()

                for item in body.get("data", []):
                    templates.append(self._map_template(item))

                links: dict[str, Any] = body.get("links") or {}
                next_url: str | None = links.get("next")
                url = str(next_url) if next_url is not None else None

        return templates

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single template by ID."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{self._base_url}/api/templates/{template_id}/",
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            body = resp.json()
        return self._map_template(body.get("data", {}))

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new template in Klaviyo."""
        payload = {
            "data": {
                "type": "template",
                "attributes": {
                    "name": name,
                    "html": html,
                },
            }
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "POST",
                f"{self._base_url}/api/templates/",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            body = resp.json()
        return self._map_template(body.get("data", {}))

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update a template's HTML."""
        payload = {
            "data": {
                "type": "template",
                "id": template_id,
                "attributes": {
                    "html": html,
                },
            }
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "PATCH",
                f"{self._base_url}/api/templates/{template_id}/",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            body = resp.json()
        return self._map_template(body.get("data", {}))

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a template. Returns True if successful (204)."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "DELETE",
                f"{self._base_url}/api/templates/{template_id}/",
                headers=self._headers(credentials),
            )
            return resp.status_code == 204
