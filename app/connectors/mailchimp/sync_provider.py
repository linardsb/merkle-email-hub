"""Mailchimp sync provider — bidirectional template sync via Templates API."""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sync_schemas import ESPTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MailchimpSyncProvider:
    """Implements ESPSyncProvider for Mailchimp Templates.

    Credentials: ``{"api_key": "...-us21"}``
    The datacenter is extracted from the API key suffix.
    """

    _base_url: str

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.mailchimp_base_url

    @staticmethod
    def _extract_dc(api_key: str) -> str:
        """Extract datacenter from Mailchimp API key (e.g. 'abc-us21' -> 'us21')."""
        import re

        parts = api_key.rsplit("-", 1)
        if len(parts) == 2:
            dc = parts[1]
            if re.fullmatch(r"[a-zA-Z0-9]+", dc):
                return dc
        return "us1"

    def _resolve_base_url(self, credentials: dict[str, str]) -> str:
        """Resolve the base URL, replacing datacenter placeholder if needed."""
        base = self._base_url
        if "{dc}" in base:
            dc = self._extract_dc(credentials["api_key"])
            return base.replace("{dc}", dc)
        return base

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credentials['api_key']}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _map_template(item: dict[str, Any]) -> ESPTemplate:
        """Map a Mailchimp template object to ESPTemplate."""
        return ESPTemplate(
            id=str(item.get("id", "")),
            name=str(item.get("name", "")),
            html=str(item.get("html", "")),
            esp_type="mailchimp",
            created_at=str(item.get("date_created", "")),
            updated_at=str(item.get("date_edited", "")),
        )

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by pinging the root API endpoint."""
        try:
            base = self._resolve_base_url(credentials)
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await resilient_request(
                    client,
                    "GET",
                    base,
                    headers=self._headers(credentials),
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            logger.warning("mailchimp.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all Mailchimp templates with offset pagination."""
        templates: list[ESPTemplate] = []
        base = self._resolve_base_url(credentials)
        offset = 0
        count = 100

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{base}/templates",
                    headers=self._headers(credentials),
                    params={"offset": str(offset), "count": str(count)},
                )
                resp.raise_for_status()
                body = resp.json()

                items: list[dict[str, Any]] = body.get("templates", [])
                for item in items:
                    templates.append(self._map_template(item))

                total_items: int = body.get("total_items", 0)
                offset += len(items)
                if offset >= total_items or not items:
                    break

        return templates

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single template by ID."""
        base = self._resolve_base_url(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{base}/templates/{template_id}",
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            item = resp.json()
        return self._map_template(item)

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new template in Mailchimp."""
        base = self._resolve_base_url(credentials)
        payload = {"name": name, "html": html}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "POST",
                f"{base}/templates",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            item = resp.json()
        return self._map_template(item)

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update a template's HTML."""
        base = self._resolve_base_url(credentials)
        payload = {"html": html}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "PATCH",
                f"{base}/templates/{template_id}",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            item = resp.json()
        return self._map_template(item)

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a template. Returns True if successful (204)."""
        base = self._resolve_base_url(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "DELETE",
                f"{base}/templates/{template_id}",
                headers=self._headers(credentials),
            )
            return resp.status_code == 204
