"""Taxi for Email connector service for exporting templates with Taxi Syntax."""

from __future__ import annotations

import httpx

from app.connectors.http_resilience import resilient_request
from app.connectors.taxi.schemas import TaxiTemplate
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TaxiConnectorService:
    """Exports compiled email HTML wrapped in Taxi Syntax for Design System export.

    When credentials are provided, uses the Taxi for Email API to create
    templates. Otherwise returns a mock ID.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.taxi_base_url

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

    async def export(self, html: str, name: str, credentials: dict[str, str] | None = None) -> str:
        """Export to Taxi for Email API.

        When credentials are provided, creates a template via the Taxi API
        with X-API-Key authentication. Otherwise returns a mock ID.
        """
        logger.info("taxi.export_started", template_name=name)

        if credentials is not None:
            headers = {"X-API-Key": credentials["api_key"]}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await resilient_request(
                    client,
                    "POST",
                    f"{self._base_url}/api/v1/templates",
                    json={"name": name, "content": html},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            external_id = str(data["id"])
            logger.info("taxi.export_completed", external_id=external_id)
            return external_id

        # Mock fallback
        template = await self.package_template(html, name)
        _ = template
        mock_id = f"taxi_tpl_{name.lower().replace(' ', '_')}"
        logger.info("taxi.export_completed", external_id=mock_id)
        return mock_id
