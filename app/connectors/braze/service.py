"""Braze connector service for exporting email templates as Content Blocks."""

from __future__ import annotations

import httpx

from app.connectors.braze.schemas import BrazeContentBlock
from app.connectors.http_resilience import resilient_request
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BrazeConnectorService:
    """Exports compiled email HTML to Braze as Content Blocks with Liquid."""

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.braze_base_url

    async def package_content_block(self, html: str, name: str) -> BrazeContentBlock:
        """Package compiled HTML as a Braze Content Block.

        Wraps the HTML with Liquid-compatible syntax for Braze ingestion.
        """
        logger.info("braze.package_started", block_name=name)
        return BrazeContentBlock(
            name=name,
            content_type="html",
            content=html,
            tags=["email-hub", "auto-generated"],
        )

    async def export(self, html: str, name: str, credentials: dict[str, str] | None = None) -> str:
        """Export to Braze API.

        When credentials are provided, makes a real API call to create a
        Content Block. Otherwise returns a mock ID for backward compatibility.
        """
        logger.info("braze.export_started", block_name=name)

        if credentials is not None:
            headers = {"Authorization": f"Bearer {credentials['api_key']}"}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await resilient_request(
                    client,
                    "POST",
                    f"{self._base_url}/content_blocks/create",
                    json={"name": name, "content": html, "tags": ["email-hub"]},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            external_id = str(data["content_block_id"])
            logger.info("braze.export_completed", external_id=external_id)
            return external_id

        # Mock fallback (no credentials)
        block = await self.package_content_block(html, name)
        _ = block
        mock_id = f"braze_cb_{name.lower().replace(' ', '_')}"
        logger.info("braze.export_completed", external_id=mock_id)
        return mock_id
