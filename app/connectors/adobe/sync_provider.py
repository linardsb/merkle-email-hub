"""Adobe Campaign sync provider — bidirectional template sync via Delivery API."""

from __future__ import annotations

import httpx

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

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.adobe_base_url  # type: ignore[attr-defined]

    async def _get_access_token(self, credentials: dict[str, str]) -> str:
        """Exchange credentials via Adobe IMS for an access token."""
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
            return str(resp.json()["access_token"])

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

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
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}/profileAndServicesExt/delivery",
                headers=self._headers(token),
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
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._base_url}/profileAndServicesExt/delivery/{template_id}",
                headers=self._headers(token),
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
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}/profileAndServicesExt/delivery",
                json={"label": name, "content": html},
                headers=self._headers(token),
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
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.patch(
                f"{self._base_url}/profileAndServicesExt/delivery/{template_id}",
                json={"content": html},
                headers=self._headers(token),
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
        token = await self._get_access_token(credentials)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"{self._base_url}/profileAndServicesExt/delivery/{template_id}",
                headers=self._headers(token),
            )
            return resp.status_code == 200
