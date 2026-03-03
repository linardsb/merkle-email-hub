"""Adobe Campaign connector service for exporting email templates as delivery fragments."""

from __future__ import annotations

from app.connectors.adobe.schemas import AdobeDeliveryFragment
from app.core.logging import get_logger

logger = get_logger(__name__)


class AdobeConnectorService:
    """Exports compiled email HTML to Adobe Campaign as delivery content fragments.

    In production, this would use Adobe Campaign Standard REST API with
    Adobe IMS OAuth (JWT or OAuth Server-to-Server) for authentication.
    """

    async def package_delivery_fragment(self, html: str, name: str) -> AdobeDeliveryFragment:
        """Package compiled HTML as an Adobe Campaign delivery fragment."""
        logger.info("adobe.package_started", delivery_name=name)
        return AdobeDeliveryFragment(
            name=name,
            content_type="html",
            content=html,
            label=name,
        )

    async def export(self, html: str, name: str) -> str:
        """Export to Adobe Campaign API (placeholder — returns mock ID).

        In production, this would:
        1. Authenticate via Adobe IMS OAuth (Server-to-Server)
        2. POST to /profileAndServicesExt/delivery to create a delivery
        3. Set HTML content via PATCH /profileAndServicesExt/delivery/{id}/content
        4. Return the Adobe Campaign delivery PKey
        """
        logger.info("adobe.export_started", delivery_name=name)
        fragment = await self.package_delivery_fragment(html, name)
        _ = fragment
        mock_id = f"adobe_dl_{name.lower().replace(' ', '_')}"
        logger.info("adobe.export_completed", external_id=mock_id)
        return mock_id
