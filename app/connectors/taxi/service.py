"""Taxi for Email connector service for exporting templates with Taxi Syntax."""

from __future__ import annotations

from app.connectors.taxi.schemas import TaxiTemplate
from app.core.logging import get_logger

logger = get_logger(__name__)


class TaxiConnectorService:
    """Exports compiled email HTML wrapped in Taxi Syntax for Design System export.

    In production, this would use the Taxi for Email API to create/update templates
    with Taxi Syntax markup (editable regions, module system, design tokens).
    """

    async def package_template(self, html: str, name: str) -> TaxiTemplate:
        """Package compiled HTML with Taxi Syntax wrapping.

        Adds Taxi editable region markers and module structure comments.
        """
        logger.info("taxi.package_started", template_name=name)
        taxi_wrapped = (
            f'<!-- taxi:template name="{name}" version="1.0" -->\n{html}\n<!-- /taxi:template -->'
        )
        return TaxiTemplate(
            name=name,
            content_type="html",
            content=taxi_wrapped,
        )

    async def export(self, html: str, name: str) -> str:
        """Export to Taxi for Email API (placeholder — returns mock ID).

        In production, this would:
        1. Authenticate via Taxi API key
        2. POST to /api/v1/templates to create a template
        3. Return the Taxi template ID
        """
        logger.info("taxi.export_started", template_name=name)
        template = await self.package_template(html, name)
        _ = template
        mock_id = f"taxi_tpl_{name.lower().replace(' ', '_')}"
        logger.info("taxi.export_completed", external_id=mock_id)
        return mock_id
