"""SFMC sync provider — bidirectional template sync via Content Builder Asset API."""

from __future__ import annotations

import httpx

from app.connectors.sync_schemas import ESPTemplate
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SFMCSyncProvider:
    """Implements ESPSyncProvider for Salesforce Marketing Cloud.

    Credentials: ``{"client_id": "...", "client_secret": "...", "subdomain": "..."}``

    Auth flow: OAuth2 client_credentials → POST /v2/token → Bearer on Asset API.
    """

    def __init__(self) -> None:
        self._base_url = get_settings().esp_sync.sfmc_base_url

    async def _get_access_token(self, credentials: dict[str, str]) -> str:
        """Exchange client credentials for an access token."""
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
            return str(resp.json()["access_token"])

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by performing token exchange."""
        try:
            await self._get_access_token(credentials)
            return True
        except httpx.HTTPError:
            logger.warning("sfmc.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all SFMC content assets."""
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}/asset/v1/content/assets",
                headers=self._headers(token),
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            ESPTemplate(
                id=str(asset["id"]),
                name=asset["name"],
                html=asset.get("content", ""),
                esp_type="sfmc",
                created_at=asset.get("created_at", ""),
                updated_at=asset.get("updated_at", ""),
            )
            for asset in data.get("items", [])
        ]

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single SFMC asset."""
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._base_url}/asset/v1/content/assets/{template_id}",
                headers=self._headers(token),
            )
            resp.raise_for_status()
            asset = resp.json()
        return ESPTemplate(
            id=str(asset["id"]),
            name=asset["name"],
            html=asset.get("content", ""),
            esp_type="sfmc",
            created_at=asset.get("created_at", ""),
            updated_at=asset.get("updated_at", ""),
        )

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new content asset in SFMC."""
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}/asset/v1/content/assets",
                json={"name": name, "content": html},
                headers=self._headers(token),
            )
            resp.raise_for_status()
            asset = resp.json()
        return ESPTemplate(
            id=str(asset["id"]),
            name=asset.get("name", name),
            html=asset.get("content", html),
            esp_type="sfmc",
            created_at=asset.get("created_at", ""),
            updated_at=asset.get("updated_at", ""),
        )

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update an SFMC asset's HTML."""
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.patch(
                f"{self._base_url}/asset/v1/content/assets/{template_id}",
                json={"content": html},
                headers=self._headers(token),
            )
            resp.raise_for_status()
            asset = resp.json()
        return ESPTemplate(
            id=str(asset["id"]),
            name=asset.get("name", ""),
            html=asset.get("content", html),
            esp_type="sfmc",
            created_at=asset.get("created_at", ""),
            updated_at=asset.get("updated_at", ""),
        )

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete an SFMC asset."""
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"{self._base_url}/asset/v1/content/assets/{template_id}",
                headers=self._headers(token),
            )
            return resp.status_code == 200
