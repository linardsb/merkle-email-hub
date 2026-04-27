"""ABC for ESP connectors that authenticate via OAuth client-credentials."""

from __future__ import annotations

import json
from abc import abstractmethod
from typing import Any, ClassVar, Literal, cast

import httpx

from app.connectors._base.api_key import ApiKeyConnectorService
from app.connectors.exceptions import ExportFailedError
from app.connectors.http_resilience import resilient_request
from app.core.cache import LruWithTtl
from app.core.config import Settings
from app.core.credentials import CredentialLease, CredentialPool
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

_TOKEN_CACHE_MAXSIZE = 64
_TOKEN_CACHE_DEFAULT_TTL = 3600.0
_TOKEN_REFRESH_GRACE = 60.0


class OAuthConnectorService(ApiKeyConnectorService):
    """Shared export pipeline for OAuth client-credentials connectors.

    Per-instance LRU+TTL token cache (no class-shared state). On 401 the
    cached token is evicted and the asset call is retried once.
    """

    auth_request_encoding: ClassVar[Literal["json", "form"]] = "json"
    default_token_ttl: ClassVar[float] = _TOKEN_CACHE_DEFAULT_TTL

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        pool: CredentialPool | None = None,
    ) -> None:
        super().__init__(settings=settings, pool=pool)
        self._token_cache: LruWithTtl[str, str] = LruWithTtl(
            maxsize=_TOKEN_CACHE_MAXSIZE,
            default_ttl=self.default_token_ttl,
        )

    # ── vendor-specific hooks ────────────────────────────────────────

    @abstractmethod
    def _token_url(self) -> str: ...

    @abstractmethod
    def _asset_url(self) -> str: ...

    # ── unused ApiKey hooks ──────────────────────────────────────────

    def _endpoint(self) -> str:
        return self._asset_url()

    def _auth_header(self, api_key: str) -> dict[str, str]:
        # OAuth uses access tokens, not raw keys — handled in export().
        return {"Authorization": f"Bearer {api_key}"}

    # ── credential parsing ───────────────────────────────────────────

    def _extract_key(self, credentials: dict[str, str]) -> str:
        # OAuth credentials come as a dict with client_id/client_secret;
        # `_extract_key` is bypassed by the overridden export() flow.
        raise NotImplementedError("OAuth services use _parse_pool_credentials")

    def _parse_pool_credentials(self, raw: str) -> dict[str, str]:
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise AppError(f"Malformed {self.label} pool credential — expected JSON dict") from exc
        if (
            not isinstance(parsed, dict)
            or "client_id" not in parsed
            or "client_secret" not in parsed
        ):
            raise AppError(
                f"{self.label} pool credential must contain 'client_id' and 'client_secret' keys"
            )
        return cast(dict[str, str], parsed)

    async def _lease_credentials(  # type: ignore[override]
        self,
        credentials: dict[str, str] | None,
    ) -> tuple[dict[str, str], CredentialLease | None]:
        if credentials is not None:
            return credentials, None
        assert self._pool is not None  # noqa: S101 — caller checks this
        lease = await self._pool.get_key()
        return self._parse_pool_credentials(lease.key), lease

    # ── token lifecycle ──────────────────────────────────────────────

    def _cache_key(self, credentials: dict[str, str]) -> str:
        return f"{self.service_name}:{credentials['client_id']}"

    async def _get_access_token(self, credentials: dict[str, str]) -> str:
        key = self._cache_key(credentials)
        cached = self._token_cache.get(key)
        if cached is not None:
            return cached

        payload = {
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "grant_type": "client_credentials",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            if self.auth_request_encoding == "form":
                resp = await client.post(self._token_url(), data=payload)
            else:
                resp = await client.post(self._token_url(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            token = str(data["access_token"])
            expires_in = float(data.get("expires_in", self.default_token_ttl))
            ttl = max(expires_in - _TOKEN_REFRESH_GRACE, 1.0)
            self._token_cache.put(key, token, ttl=ttl)
            return token

    # ── export pipeline ──────────────────────────────────────────────

    async def export(
        self,
        html: str,
        name: str,
        credentials: dict[str, str] | None = None,
    ) -> str:
        logger.info(f"{self.service_name}.export_started", asset_name=name)

        if credentials is None and self._pool is None:
            mock_id = self._mock_external_id(name)
            logger.info(f"{self.service_name}.export_completed", external_id=mock_id)
            return mock_id

        creds, lease = await self._lease_credentials(credentials)

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await self._post_asset(client, creds, html=html, name=name)
                if resp.status_code == 401:
                    # Token may have rotated upstream; evict and retry once.
                    self._token_cache.pop(self._cache_key(creds))
                    resp = await self._post_asset(client, creds, html=html, name=name)
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

    async def _post_asset(
        self,
        client: httpx.AsyncClient,
        creds: dict[str, str],
        *,
        html: str,
        name: str,
    ) -> httpx.Response:
        token = await self._get_access_token(creds)
        return await resilient_request(
            client,
            "POST",
            self._asset_url(),
            json=self._build_payload(html=html, name=name),
            headers={"Authorization": f"Bearer {token}"},
        )

    @abstractmethod
    def _build_payload(self, *, html: str, name: str) -> dict[str, Any]: ...
