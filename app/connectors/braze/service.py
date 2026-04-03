"""Braze connector service for exporting email templates as Content Blocks."""

from __future__ import annotations

import httpx

from app.connectors.braze.schemas import BrazeContentBlock
from app.connectors.exceptions import ExportFailedError
from app.connectors.http_resilience import resilient_request
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialLease, CredentialPool, get_credential_pool
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class BrazeConnectorService:
    """Exports compiled email HTML to Braze as Content Blocks with Liquid."""

    def __init__(self, settings: Settings | None = None) -> None:
        _settings = settings or get_settings()
        self._base_url = _settings.esp_sync.braze_base_url
        self._pool: CredentialPool | None = None
        if (
            _settings.credentials.enabled
            and isinstance(_settings.credentials.pools, dict)  # pyright: ignore[reportUnnecessaryIsInstance] — guards against MagicMock in tests
            and "braze" in _settings.credentials.pools
        ):
            self._pool = get_credential_pool("braze")

    async def _lease_credentials(self) -> tuple[dict[str, str], CredentialLease]:
        """Get credentials from pool. Raises NoHealthyCredentialsError if exhausted."""
        if self._pool is None:
            raise AppError("_lease_credentials called without pool")
        lease = await self._pool.get_key()
        return {"api_key": lease.key}, lease

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
        Pool credentials are used when no explicit credentials are passed.
        """
        logger.info("braze.export_started", block_name=name)

        lease: CredentialLease | None = None
        if credentials is None and self._pool is not None:
            credentials, lease = await self._lease_credentials()

        if credentials is not None:
            headers = {"Authorization": f"Bearer {credentials['api_key']}"}
            async with httpx.AsyncClient(timeout=15) as client:
                try:
                    resp = await resilient_request(
                        client,
                        "POST",
                        f"{self._base_url}/content_blocks/create",
                        json={"name": name, "content": html, "tags": ["email-hub"]},
                        headers=headers,
                    )
                    resp.raise_for_status()
                    external_id = str(resp.json()["content_block_id"])
                except httpx.HTTPStatusError as exc:
                    if lease:
                        await lease.report_failure(exc.response.status_code)
                    raise ExportFailedError(
                        f"Braze API returned {exc.response.status_code}"
                    ) from exc
                except Exception as exc:
                    if lease:
                        await lease.report_failure(0)
                    raise ExportFailedError("Braze export failed") from exc
            if lease:
                await lease.report_success()
            logger.info("braze.export_completed", external_id=external_id)
            return external_id

        # Mock fallback (no credentials, no pool)
        block = await self.package_content_block(html, name)
        _ = block
        mock_id = f"braze_cb_{name.lower().replace(' ', '_')}"
        logger.info("braze.export_completed", external_id=mock_id)
        return mock_id
