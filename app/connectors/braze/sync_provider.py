"""Braze sync provider — bidirectional template sync via Content Blocks API."""

from __future__ import annotations

import httpx

from app.connectors.sync_schemas import ESPTemplate
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BrazeSyncProvider:
    """Implements ESPSyncProvider for Braze Content Blocks.

    Credentials: ``{"api_key": "..."}``
    """

    def __init__(self) -> None:
        self._base_url = get_settings().esp_sync.braze_base_url

    def _headers(self, credentials: dict[str, str]) -> dict[str, str]:
        return {"Authorization": f"Bearer {credentials['api_key']}"}

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """Validate by listing content blocks (lightweight call)."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/content_blocks/list",
                    headers=self._headers(credentials),
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            logger.warning("braze.sync.validate_failed", exc_info=True)
            return False

    async def list_templates(self, credentials: dict[str, str]) -> list[ESPTemplate]:
        """List all Braze content blocks."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}/content_blocks/list",
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            ESPTemplate(
                id=cb["content_block_id"],
                name=cb["name"],
                html=cb.get("content", ""),
                esp_type="braze",
                created_at=cb.get("created_at", ""),
                updated_at=cb.get("updated_at", ""),
            )
            for cb in data.get("content_blocks", [])
        ]

    async def get_template(self, template_id: str, credentials: dict[str, str]) -> ESPTemplate:
        """Get a single content block by ID."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._base_url}/content_blocks/info",
                params={"content_block_id": template_id},
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            cb = resp.json()
        return ESPTemplate(
            id=cb["content_block_id"],
            name=cb["name"],
            html=cb.get("content", ""),
            esp_type="braze",
            created_at=cb.get("created_at", ""),
            updated_at=cb.get("updated_at", ""),
        )

    async def create_template(
        self, name: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Create a new content block in Braze."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}/content_blocks/create",
                json={"name": name, "content": html, "tags": ["email-hub"]},
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            cb = resp.json()
        return ESPTemplate(
            id=cb["content_block_id"],
            name=cb.get("name", name),
            html=cb.get("content", html),
            esp_type="braze",
            created_at=cb.get("created_at", ""),
            updated_at=cb.get("updated_at", ""),
        )

    async def update_template(
        self, template_id: str, html: str, credentials: dict[str, str]
    ) -> ESPTemplate:
        """Update a content block's HTML."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}/content_blocks/update",
                json={"content_block_id": template_id, "content": html},
                headers=self._headers(credentials),
            )
            resp.raise_for_status()
            cb = resp.json()
        return ESPTemplate(
            id=cb["content_block_id"],
            name=cb.get("name", ""),
            html=cb.get("content", html),
            esp_type="braze",
            created_at=cb.get("created_at", ""),
            updated_at=cb.get("updated_at", ""),
        )

    async def delete_template(self, template_id: str, credentials: dict[str, str]) -> bool:
        """Delete a content block."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"{self._base_url}/content_blocks/{template_id}",
                headers=self._headers(credentials),
            )
            return resp.status_code == 200
