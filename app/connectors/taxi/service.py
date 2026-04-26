"""Taxi for Email connector service for exporting templates with Taxi Syntax."""

from __future__ import annotations

import json

import httpx

from app.connectors.exceptions import ExportFailedError
from app.connectors.http_resilience import resilient_request
from app.connectors.taxi.schemas import TaxiTemplate
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialLease, CredentialPool, get_credential_pool
from app.core.exceptions import AppError
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
        self._pool: CredentialPool | None = None
        if _settings.credentials.enabled and "taxi" in _settings.credentials.pools:
            self._pool = get_credential_pool("taxi")

    async def _lease_credentials(self) -> tuple[dict[str, str], CredentialLease]:
        """Get credentials from pool. Raises NoHealthyCredentialsError if exhausted."""
        if self._pool is None:
            raise AppError("_lease_credentials called without pool")
        lease = await self._pool.get_key()
        return {"api_key": lease.key}, lease

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
        Pool credentials are used when no explicit credentials are passed.
        """
        logger.info("taxi.export_started", template_name=name)

        lease: CredentialLease | None = None
        if credentials is None and self._pool is not None:
            credentials, lease = await self._lease_credentials()

        if credentials is not None:
            headers = {"X-API-Key": credentials["api_key"]}
            async with httpx.AsyncClient(timeout=15) as client:
                try:
                    resp = await resilient_request(
                        client,
                        "POST",
                        f"{self._base_url}/api/v1/templates",
                        json={"name": name, "content": html},
                        headers=headers,
                    )
                    resp.raise_for_status()
                    external_id = str(resp.json()["id"])
                except httpx.HTTPStatusError as exc:
                    if lease:
                        await lease.report_failure(exc.response.status_code)
                    raise ExportFailedError(
                        f"Taxi API returned {exc.response.status_code}"
                    ) from exc
                except (httpx.RequestError, json.JSONDecodeError) as exc:
                    if lease:
                        await lease.report_failure(0)
                    raise ExportFailedError("Taxi export failed") from exc
            if lease:
                await lease.report_success()
            logger.info("taxi.export_completed", external_id=external_id)
            return external_id

        # Mock fallback (no credentials, no pool)
        template = await self.package_template(html, name)
        _ = template
        mock_id = f"taxi_tpl_{name.lower().replace(' ', '_')}"
        logger.info("taxi.export_completed", external_id=mock_id)
        return mock_id
