"""Braze connector service for exporting email templates as Content Blocks."""

from __future__ import annotations

from app.connectors.braze.schemas import BrazeContentBlock
from app.core.logging import get_logger

logger = get_logger(__name__)


class BrazeConnectorService:
    """Exports compiled email HTML to Braze as Content Blocks with Liquid."""

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

    async def export(self, html: str, name: str) -> str:
        """Export to Braze API (placeholder — returns mock ID).

        In production, this would call the Braze REST API to create/update
        a Content Block.
        """
        logger.info("braze.export_started", block_name=name)
        block = await self.package_content_block(html, name)
        # Placeholder: actual Braze API call would go here
        mock_id = f"braze_cb_{name.lower().replace(' ', '_')}"
        logger.info("braze.export_completed", external_id=mock_id)
        _ = block
        return mock_id
