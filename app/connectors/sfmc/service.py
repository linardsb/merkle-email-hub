"""SFMC connector service for exporting email templates as Content Areas."""

from __future__ import annotations

import hashlib
import time
from typing import ClassVar

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.sfmc.schemas import SFMCContentArea
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SFMCConnectorService:
    """Exports compiled email HTML to SFMC Content Builder as Content Areas.

    When credentials are provided, uses OAuth 2.0 client credentials flow
    to create Content Areas via the SFMC Asset API.
    """

    _token_cache: ClassVar[dict[str, tuple[str, float]]] = {}

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.sfmc_base_url

    @staticmethod
    def _cache_key(credentials: dict[str, str]) -> str:
        return hashlib.sha256(credentials["client_id"].encode()).hexdigest()[:16]

    async def _get_access_token(self, credentials: dict[str, str]) -> str:
        """Exchange client credentials for an access token, with caching."""
        key = self._cache_key(credentials)
        cached = self._token_cache.get(key)
        if cached:
            token, expiry = cached
            if time.time() < expiry - 60:
                return token

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self._base_url}/v2/token",
                json={
                    "client_id": credentials["client_id"],
                    "client_secret": credentials["client_secret"],
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            token = str(data["access_token"])
            expires_in = int(data.get("expires_in", 3600))
            self._token_cache[key] = (token, time.time() + expires_in)
            return token

    async def package_content_area(self, html: str, name: str) -> SFMCContentArea:
        """Package compiled HTML as an SFMC Content Area."""
        logger.info("sfmc.package_started", content_area_name=name)
        return SFMCContentArea(
            name=name,
            content_type="html",
            content=html,
        )

    async def export(self, html: str, name: str, credentials: dict[str, str] | None = None) -> str:
        """Export to SFMC API.

        When credentials are provided, authenticates via OAuth 2.0 and creates
        a Content Area via the Asset API. Otherwise returns a mock ID.
        """
        logger.info("sfmc.export_started", content_area_name=name)

        if credentials is not None:
            token = await self._get_access_token(credentials)
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await resilient_request(
                    client,
                    "POST",
                    f"{self._base_url}/asset/v1/content/assets",
                    json={"name": name, "content": html},
                    headers=headers,
                )
                # On 401, evict cache and retry once
                if resp.status_code == 401:
                    self._token_cache.pop(self._cache_key(credentials), None)
                    token = await self._get_access_token(credentials)
                    headers = {"Authorization": f"Bearer {token}"}
                    resp = await resilient_request(
                        client,
                        "POST",
                        f"{self._base_url}/asset/v1/content/assets",
                        json={"name": name, "content": html},
                        headers=headers,
                    )
                resp.raise_for_status()
                data = resp.json()
            external_id = str(data["id"])
            logger.info("sfmc.export_completed", external_id=external_id)
            return external_id

        # Mock fallback
        content_area = await self.package_content_area(html, name)
        _ = content_area
        mock_id = f"sfmc_ca_{name.lower().replace(' ', '_')}"
        logger.info("sfmc.export_completed", external_id=mock_id)
        return mock_id
