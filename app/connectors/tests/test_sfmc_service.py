"""Per-service tests for SFMCConnectorService.

Coverage: 200 happy path, 401 → token cache evicted + retried once,
429 → ExportFailedError, malformed JSON → ExportFailedError +
lease.report_failure(0), KeyError on response → ExportFailedError +
lease NOT blamed (F023), NoHealthyCredentialsError propagates.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.exceptions import ExportFailedError
from app.connectors.sfmc.service import SFMCConnectorService
from app.core.credentials import CredentialLease, CredentialPool
from app.core.exceptions import NoHealthyCredentialsError


def _resp(status: int = 200, body: dict[str, object] | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=body or {},
        request=httpx.Request("POST", "http://test"),
    )


def _lease(creds: dict[str, str] | None = None) -> AsyncMock:
    lease = AsyncMock(spec=CredentialLease)
    lease.key = json.dumps(creds or {"client_id": "cid", "client_secret": "csec"})
    lease.report_success = AsyncMock()
    lease.report_failure = AsyncMock()
    return lease


def _pool(lease: AsyncMock) -> AsyncMock:
    pool = AsyncMock(spec=CredentialPool)
    pool.get_key = AsyncMock(return_value=lease)
    return pool


class TestSFMCService:
    @pytest.mark.asyncio()
    async def test_happy_path_returns_external_id(self) -> None:
        lease = _lease()
        service = SFMCConnectorService(pool=_pool(lease))
        with (
            patch.object(
                httpx.AsyncClient,
                "post",
                new_callable=AsyncMock,
                return_value=_resp(200, {"access_token": "t1", "expires_in": 3600}),
            ),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=_resp(200, {"id": 42}),
            ),
        ):
            result = await service.export("<p>x</p>", "Promo")
        assert result == "42"
        lease.report_success.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_401_evicts_cache_and_retries_once(self) -> None:
        lease = _lease()
        service = SFMCConnectorService(pool=_pool(lease))
        # Token endpoint returns the same token twice (we evict + refetch).
        token_call = AsyncMock(return_value=_resp(200, {"access_token": "t1", "expires_in": 3600}))
        # Asset endpoint: first 401, then 200.
        asset_call = AsyncMock(side_effect=[_resp(401), _resp(200, {"id": "after-retry"})])
        with (
            patch.object(httpx.AsyncClient, "post", token_call),
            patch("app.connectors._base.oauth.resilient_request", asset_call),
        ):
            result = await service.export("<p>x</p>", "Promo")
        assert result == "after-retry"
        # Token was fetched twice (cache evicted between)
        assert token_call.await_count == 2
        # Asset was called twice (initial + retry)
        assert asset_call.await_count == 2
        lease.report_success.assert_awaited_once()
        lease.report_failure.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_429_raises_export_failed_and_blames_lease(self) -> None:
        lease = _lease()
        service = SFMCConnectorService(pool=_pool(lease))
        with (
            patch.object(
                httpx.AsyncClient,
                "post",
                new_callable=AsyncMock,
                return_value=_resp(200, {"access_token": "t1", "expires_in": 3600}),
            ),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=_resp(429),
            ),
            pytest.raises(ExportFailedError, match="SFMC API returned 429"),
        ):
            await service.export("<p>x</p>", "Promo")
        lease.report_failure.assert_awaited_once_with(429)

    @pytest.mark.asyncio()
    async def test_malformed_json_response_blames_lease(self) -> None:
        lease = _lease()
        service = SFMCConnectorService(pool=_pool(lease))
        bad = httpx.Response(
            status_code=200,
            content=b"oops",
            request=httpx.Request("POST", "http://test"),
        )
        with (
            patch.object(
                httpx.AsyncClient,
                "post",
                new_callable=AsyncMock,
                return_value=_resp(200, {"access_token": "t1", "expires_in": 3600}),
            ),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=bad,
            ),
            pytest.raises(ExportFailedError, match="SFMC export failed"),
        ):
            await service.export("<p>x</p>", "Promo")
        lease.report_failure.assert_awaited_once_with(0)

    @pytest.mark.asyncio()
    async def test_key_error_on_response_does_not_blame_lease(self) -> None:
        lease = _lease()
        service = SFMCConnectorService(pool=_pool(lease))
        with (
            patch.object(
                httpx.AsyncClient,
                "post",
                new_callable=AsyncMock,
                return_value=_resp(200, {"access_token": "t1", "expires_in": 3600}),
            ),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=_resp(200, {"missing_id": True}),
            ),
            pytest.raises(KeyError),
        ):
            await service.export("<p>x</p>", "Promo")
        lease.report_failure.assert_not_awaited()
        lease.report_success.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_no_healthy_credentials_propagates(self) -> None:
        pool = AsyncMock(spec=CredentialPool)
        pool.get_key = AsyncMock(side_effect=NoHealthyCredentialsError("sfmc"))
        service = SFMCConnectorService(pool=pool)
        with pytest.raises(NoHealthyCredentialsError):
            await service.export("<p>x</p>", "Promo")

    @pytest.mark.asyncio()
    async def test_malformed_pool_credential_raises(self) -> None:
        from app.core.exceptions import AppError

        bad_lease = AsyncMock(spec=CredentialLease)
        bad_lease.key = "not-json"
        bad_lease.report_success = AsyncMock()
        bad_lease.report_failure = AsyncMock()
        service = SFMCConnectorService(pool=_pool(bad_lease))
        with pytest.raises(AppError, match="Malformed SFMC pool credential"):
            await service.export("<p>x</p>", "Promo")

    @pytest.mark.asyncio()
    async def test_token_cached_across_calls_in_instance(self) -> None:
        lease = _lease()
        service = SFMCConnectorService(pool=_pool(lease))
        token_call = AsyncMock(return_value=_resp(200, {"access_token": "t1", "expires_in": 3600}))
        asset_call = AsyncMock(return_value=_resp(200, {"id": "ok"}))
        with (
            patch.object(httpx.AsyncClient, "post", token_call),
            patch("app.connectors._base.oauth.resilient_request", asset_call),
        ):
            await service.export("<p>x</p>", "Call1")
            await service.export("<p>y</p>", "Call2")
        # Token endpoint hit only once; second export reuses cached token.
        assert token_call.await_count == 1
        assert asset_call.await_count == 2
