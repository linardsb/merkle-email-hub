"""Adobe Campaign sync provider — bidirectional template sync via Delivery API."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping, Sequence
from typing import ClassVar

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sync_schemas import ESPTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AdobeSyncProvider:
    """Implements ESPSyncProvider for Adobe Campaign Standard.

    Credentials: ``{"client_id": "...", "client_secret": "...", "org_id": "..."}``

    Auth flow: IMS OAuth → POST /ims/token/v3 → Bearer on Delivery API.
    """

    _base_url: str
    _token_cache: ClassVar[dict[str, tuple[str, float]]] = {}

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.adobe_base_url

    @staticmethod
    def _cache_key(credentials: dict[str, str]) -> str:
        return hashlib.sha256(credentials["client_id"].encode()).hexdigest()[:16]

    async def _get_access_token(self, credentials: dict[str, str]) -> str:
        """Exchange credentials via Adobe IMS for an access token, with caching."""
        key = self._cache_key(credentials)
        cached = self._token_cache.get(key)
        if cached:
            token, expiry = cached
            if time.time() < expiry - 60:
                return token

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self._base_url}/ims/token/v3",
                data={
                    "client_id": credentials["client_id"],
                    "client_secret": credentials["client_secret"],
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            token = str(data["access_token"])
            expires_in = int(data.get("expires_in", 86399))
            self._token_cache[key] = (token, time.time() + expires_in)
            return token

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    async def _call_with_auth(
        self,
        credentials: dict[str, str],
        method: str,
        url: str,
        params: Mapping[
            str, str | int | float | bool | None | Sequence[str | int | float | bool | None]
        ]
        | None = None,
        json: object | None = None,
    ) -> httpx.Response:
        """Make an API call; on 401 evict cache, re-auth, retry once."""
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await resilient_request(
                client, method, url, headers=self._headers(token), params=params, json=json
            )
            if resp.status_code == 401:
                key = self._cache_key(credentials)
                self._token_cache.pop(key, None)
                token = await self._get_access_token(credentials)
                resp = await resilient_request(
                    client, method, url, headers=self._headers(token), params=params, json=json
                )
            return resp

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by performing IMS token exchange."""
        try:
            await self._get_access_token(credentials)
            return True
        except httpx.HTTPError:
            logger.warning("adobe.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all Adobe Campaign deliveries."""
        resp = await self._call_with_auth(
            credentials,
            "GET",
            f"{self._base_url}/profileAndServicesExt/delivery",
            params={"_lineStart": 0, "_lineCount": 1000},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            ESPTemplate(
                id=str(d["PKey"]),
                name=d["label"],
                html=d.get("content", ""),
                esp_type="adobe_campaign",
                created_at=d.get("created_at", ""),
                updated_at=d.get("updated_at", ""),
            )
            for d in data.get("content", [])
        ]

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single delivery by PKey."""
        resp = await self._call_with_auth(
            credentials,
            "GET",
            f"{self._base_url}/profileAndServicesExt/delivery/{template_id}",
        )
        resp.raise_for_status()
        d = resp.json()
        return ESPTemplate(
            id=str(d["PKey"]),
            name=d["label"],
            html=d.get("content", ""),
            esp_type="adobe_campaign",
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new delivery in Adobe Campaign."""
        resp = await self._call_with_auth(
            credentials,
            "POST",
            f"{self._base_url}/profileAndServicesExt/delivery",
            json={"label": name, "content": html},
        )
        resp.raise_for_status()
        d = resp.json()
        return ESPTemplate(
            id=str(d["PKey"]),
            name=d.get("label", name),
            html=d.get("content", html),
            esp_type="adobe_campaign",
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update a delivery's HTML content."""
        resp = await self._call_with_auth(
            credentials,
            "PATCH",
            f"{self._base_url}/profileAndServicesExt/delivery/{template_id}",
            json={"content": html},
        )
        resp.raise_for_status()
        d = resp.json()
        return ESPTemplate(
            id=str(d["PKey"]),
            name=d.get("label", ""),
            html=d.get("content", html),
            esp_type="adobe_campaign",
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a delivery from Adobe Campaign."""
        resp = await self._call_with_auth(
            credentials,
            "DELETE",
            f"{self._base_url}/profileAndServicesExt/delivery/{template_id}",
        )
        return resp.status_code == 200
