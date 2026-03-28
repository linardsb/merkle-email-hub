"""ActiveCampaign sync provider — bidirectional template sync via Messages API."""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sync_schemas import ESPTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ActiveCampaignSyncProvider:
    """Implements ESPSyncProvider for ActiveCampaign personal email templates.

    Credentials: ``{"api_key": "...", "account": "mycompany"}``
    Base URL: ``https://{account}.api-us1.com/api/3``
    """

    _base_url: str

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.activecampaign_base_url

    def _resolve_base_url(self, credentials: dict[str, str]) -> str:
        """Resolve the base URL, replacing account placeholder if needed."""
        import re

        base = self._base_url
        if "{account}" in base:
            account = credentials["account"]
            if not re.fullmatch(r"[a-zA-Z0-9_-]+", account):
                msg = "Invalid ActiveCampaign account name: contains disallowed characters"
                raise ValueError(msg)
            return base.replace("{account}", account)
        return base

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {
            "Api-Token": credentials["api_key"],
            "Content-Type": "application/json",
        }

    @staticmethod
    def _map_template(item: dict[str, Any]) -> ESPTemplate:
        """Map an ActiveCampaign message object to ESPTemplate."""
        return ESPTemplate(
            id=str(item.get("id", "")),
            name=str(item.get("name", item.get("subject", ""))),
            html=str(item.get("message", "")),
            esp_type="activecampaign",
            created_at=str(item.get("cdate", "")),
            updated_at=str(item.get("mdate", "")),
        )

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by fetching account info."""
        try:
            base = self._resolve_base_url(credentials)
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{base}/users/me",
                    headers=self._headers(credentials),
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            logger.warning("activecampaign.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all personal email templates with offset pagination."""
        templates: list[ESPTemplate] = []
        base = self._resolve_base_url(credentials)
        offset = 0
        limit = 100

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await resilient_request(
                    client,
                    "GET",
                    f"{base}/messages",
                    headers=self._headers(credentials),
                    params={"offset": str(offset), "limit": str(limit)},
                )
                resp.raise_for_status()
                body = resp.json()

                items: list[dict[str, Any]] = body.get("messages", [])
                for item in items:
                    templates.append(self._map_template(item))

                meta: dict[str, Any] = body.get("meta") or {}
                total: int = int(meta.get("total", 0))
                offset += len(items)
                if offset >= total or not items:
                    break

        return templates

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single template by ID."""
        base = self._resolve_base_url(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "GET",
                f"{base}/messages/{template_id}",
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            body = resp.json()
        return self._map_template(body.get("message", {}))

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new personal email template."""
        base = self._resolve_base_url(credentials)
        payload = {"message": {"name": name, "message": html}}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "POST",
                f"{base}/messages",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            body = resp.json()
        return self._map_template(body.get("message", {}))

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update a template's HTML."""
        base = self._resolve_base_url(credentials)
        payload = {"message": {"message": html}}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "PUT",
                f"{base}/messages/{template_id}",
                json=payload,
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            body = resp.json()
        return self._map_template(body.get("message", {}))

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a template. Returns True if successful (200)."""
        base = self._resolve_base_url(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await resilient_request(
                client,
                "DELETE",
                f"{base}/messages/{template_id}",
                headers=self._headers(credentials),
            )
            return resp.status_code == 200
