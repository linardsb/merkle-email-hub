"""Per-service tests for AdobeConnectorService.

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

from app.connectors.adobe.service import AdobeConnectorService
from app.connectors.exceptions import ExportFailedError
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


class TestAdobeService:
    @pytest.mark.asyncio()
    async def test_happy_path_returns_external_id(self) -> None:
        lease = _lease()
        service = AdobeConnectorService(pool=_pool(lease))
        with (
            patch.object(
                httpx.AsyncClient,
                "post",
                new_callable=AsyncMock,
                return_value=_resp(200, {"access_token": "t1", "expires_in": 86399}),
            ),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=_resp(200, {"PKey": "pk_42"}),
            ) as mock_req,
        ):
            result = await service.export("<p>x</p>", "Launch")
        assert result == "pk_42"
        # Adobe payload uses 'label', not 'name'
        body = mock_req.call_args.kwargs["json"]
        assert body["label"] == "Launch"
        lease.report_success.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_token_request_uses_form_encoding(self) -> None:
        """Adobe IMS expects form-encoded credentials, not JSON."""
        lease = _lease()
        service = AdobeConnectorService(pool=_pool(lease))
        token_call = AsyncMock(return_value=_resp(200, {"access_token": "t1", "expires_in": 86399}))
        with (
            patch.object(httpx.AsyncClient, "post", token_call),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=_resp(200, {"PKey": "pk"}),
            ),
        ):
            await service.export("<p>x</p>", "Launch")
        # Verify the token request was form-encoded (`data=`, not `json=`)
        kwargs = token_call.call_args.kwargs
        assert "data" in kwargs
        assert "json" not in kwargs

    @pytest.mark.asyncio()
    async def test_401_evicts_cache_and_retries_once(self) -> None:
        lease = _lease()
        service = AdobeConnectorService(pool=_pool(lease))
        token_call = AsyncMock(return_value=_resp(200, {"access_token": "t1", "expires_in": 86399}))
        asset_call = AsyncMock(side_effect=[_resp(401), _resp(200, {"PKey": "after-retry"})])
        with (
            patch.object(httpx.AsyncClient, "post", token_call),
            patch("app.connectors._base.oauth.resilient_request", asset_call),
        ):
            result = await service.export("<p>x</p>", "Launch")
        assert result == "after-retry"
        assert token_call.await_count == 2
        assert asset_call.await_count == 2
        lease.report_success.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_429_raises_export_failed_and_blames_lease(self) -> None:
        lease = _lease()
        service = AdobeConnectorService(pool=_pool(lease))
        with (
            patch.object(
                httpx.AsyncClient,
                "post",
                new_callable=AsyncMock,
                return_value=_resp(200, {"access_token": "t1", "expires_in": 86399}),
            ),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=_resp(429),
            ),
            pytest.raises(ExportFailedError, match="Adobe Campaign API returned 429"),
        ):
            await service.export("<p>x</p>", "Launch")
        lease.report_failure.assert_awaited_once_with(429)

    @pytest.mark.asyncio()
    async def test_malformed_json_blames_lease(self) -> None:
        lease = _lease()
        service = AdobeConnectorService(pool=_pool(lease))
        bad = httpx.Response(
            status_code=200,
            content=b"<<oops>>",
            request=httpx.Request("POST", "http://test"),
        )
        with (
            patch.object(
                httpx.AsyncClient,
                "post",
                new_callable=AsyncMock,
                return_value=_resp(200, {"access_token": "t1", "expires_in": 86399}),
            ),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=bad,
            ),
            pytest.raises(ExportFailedError, match="Adobe Campaign export failed"),
        ):
            await service.export("<p>x</p>", "Launch")
        lease.report_failure.assert_awaited_once_with(0)

    @pytest.mark.asyncio()
    async def test_key_error_does_not_blame_lease(self) -> None:
        lease = _lease()
        service = AdobeConnectorService(pool=_pool(lease))
        with (
            patch.object(
                httpx.AsyncClient,
                "post",
                new_callable=AsyncMock,
                return_value=_resp(200, {"access_token": "t1", "expires_in": 86399}),
            ),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=_resp(200, {"no_pkey_field": True}),
            ),
            pytest.raises(KeyError),
        ):
            await service.export("<p>x</p>", "Launch")
        lease.report_failure.assert_not_awaited()
        lease.report_success.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_no_healthy_credentials_propagates(self) -> None:
        pool = AsyncMock(spec=CredentialPool)
        pool.get_key = AsyncMock(side_effect=NoHealthyCredentialsError("adobe_campaign"))
        service = AdobeConnectorService(pool=pool)
        with pytest.raises(NoHealthyCredentialsError):
            await service.export("<p>x</p>", "Launch")

    @pytest.mark.asyncio()
    async def test_two_instances_have_independent_caches(self) -> None:
        """No more ClassVar token cache — each instance has its own."""
        token_call = AsyncMock(return_value=_resp(200, {"access_token": "t1", "expires_in": 86399}))
        asset_call = AsyncMock(return_value=_resp(200, {"PKey": "ok"}))

        s1 = AdobeConnectorService(pool=_pool(_lease()))
        s2 = AdobeConnectorService(pool=_pool(_lease()))
        with (
            patch.object(httpx.AsyncClient, "post", token_call),
            patch("app.connectors._base.oauth.resilient_request", asset_call),
        ):
            await s1.export("<p>x</p>", "Launch")
            await s2.export("<p>x</p>", "Launch")
        # Each instance fetched the token once (no cross-instance leak)
        assert token_call.await_count == 2
