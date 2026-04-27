"""ABC for ESP connectors that authenticate with a bearer-style API key."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx

from app.connectors.exceptions import ExportFailedError
from app.connectors.http_resilience import resilient_request
from app.core.config import Settings, get_settings
from app.core.credentials import CredentialLease, CredentialPool, get_credential_pool
from app.core.logging import get_logger

logger = get_logger(__name__)


class ApiKeyConnectorService(ABC):
    """Shared export pipeline for connectors backed by a single API key.

    Subclasses declare the vendor-specific endpoint shape, payload, auth
    header, and response parsing. Construction, pool lookup, lease
    lifecycle, and exception handling live here.
    """

    service_name: ClassVar[str]
    label: ClassVar[str]

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        pool: CredentialPool | None = None,
    ) -> None:
        _settings = settings or get_settings()
        self._base_url = self._resolve_base_url(_settings)
        if pool is not None:
            self._pool: CredentialPool | None = pool
        elif _settings.credentials.enabled and self.service_name in _settings.credentials.pools:
            self._pool = get_credential_pool(self.service_name)
        else:
            self._pool = None

    # ── vendor-specific hooks ────────────────────────────────────────

    @abstractmethod
    def _resolve_base_url(self, settings: Settings) -> str: ...

    @abstractmethod
    def _endpoint(self) -> str: ...

    @abstractmethod
    def _auth_header(self, api_key: str) -> dict[str, str]: ...

    @abstractmethod
    def _build_payload(self, *, html: str, name: str) -> dict[str, Any]: ...

    @abstractmethod
    def _external_id_from_response(self, body: dict[str, Any]) -> str: ...

    @abstractmethod
    def _mock_external_id(self, name: str) -> str: ...

    def _extract_key(self, credentials: dict[str, str]) -> str:
        """Default: API key under the `api_key` field. Override for variants."""
        return credentials["api_key"]

    # ── shared export pipeline ───────────────────────────────────────

    async def _lease_credentials(
        self,
        credentials: dict[str, str] | None,
    ) -> tuple[str, CredentialLease | None]:
        """Caller-supplied credentials win; otherwise pull from the pool.

        `NoHealthyCredentialsError` propagates so the orchestrator wraps it.
        """
        if credentials is not None:
            return self._extract_key(credentials), None
        assert self._pool is not None  # noqa: S101 — caller checks this
        lease = await self._pool.get_key()
        return lease.key, lease

    async def export(
        self,
        html: str,
        name: str,
        credentials: dict[str, str] | None = None,
    ) -> str:
        """Export compiled HTML to the vendor.

        Returns a deterministic mock id when no credentials and no pool are
        available — preserves the legacy preview path.
        """
        logger.info(f"{self.service_name}.export_started", asset_name=name)

        if credentials is None and self._pool is None:
            mock_id = self._mock_external_id(name)
            logger.info(f"{self.service_name}.export_completed", external_id=mock_id)
            return mock_id

        api_key, lease = await self._lease_credentials(credentials)
        headers = self._auth_header(api_key)

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await resilient_request(
                    client,
                    "POST",
                    self._endpoint(),
                    json=self._build_payload(html=html, name=name),
                    headers=headers,
                )
                resp.raise_for_status()
                external_id = str(self._external_id_from_response(resp.json()))
            except httpx.HTTPStatusError as exc:
                if lease:
                    await lease.report_failure(exc.response.status_code)
                raise ExportFailedError(
                    f"{self.label} API returned {exc.response.status_code}"
                ) from exc
            except (httpx.RequestError, json.JSONDecodeError) as exc:
                if lease:
                    await lease.report_failure(0)
                raise ExportFailedError(f"{self.label} export failed") from exc

        if lease:
            await lease.report_success()
        logger.info(f"{self.service_name}.export_completed", external_id=external_id)
        return external_id
