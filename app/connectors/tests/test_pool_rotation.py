"""Tests for ESP connector credential pool rotation (Phase 46.3)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.connectors.braze.service import BrazeConnectorService
from app.connectors.exceptions import ExportFailedError
from app.connectors.sfmc.service import SFMCConnectorService
from app.connectors.taxi.service import TaxiConnectorService
from app.core.credentials import CredentialLease, CredentialPool
from app.core.exceptions import NoHealthyCredentialsError


def _mock_response(status: int = 200, json_data: dict[str, object] | None = None) -> httpx.Response:
    """Build a minimal httpx.Response for testing."""
    return httpx.Response(
        status_code=status,
        json=json_data or {},
        request=httpx.Request("POST", "http://test"),
    )


def _make_lease(key: str = "test-key-1") -> AsyncMock:
    """Create a mock CredentialLease."""
    lease = AsyncMock(spec=CredentialLease)
    lease.key = key
    lease.key_hash = "abc123"
    lease.report_success = AsyncMock()
    lease.report_failure = AsyncMock()
    return lease


def _make_pool(lease: AsyncMock | None = None) -> AsyncMock:
    """Create a mock CredentialPool with a default lease."""
    pool = AsyncMock(spec=CredentialPool)
    pool.get_key = AsyncMock(return_value=lease or _make_lease())
    return pool


class TestBrazePoolRotation:
    """Braze connector uses pool when no explicit credentials are passed."""

    @pytest.mark.asyncio()
    async def test_export_uses_pool_when_no_credentials(self) -> None:
        lease = _make_lease("pool-braze-key")
        pool = _make_pool(lease)
        service = BrazeConnectorService()
        service._pool = pool

        mock_resp = _mock_response(200, {"content_block_id": "cb_pool"})
        with patch(
            "app.connectors._base.api_key.resilient_request",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_req:
            result = await service.export("<h1>Hi</h1>", "Test", credentials=None)

        assert result == "cb_pool"
        pool.get_key.assert_called_once()
        lease.report_success.assert_called_once()
        # Verify pool key was used in Authorization header
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer pool-braze-key"

    @pytest.mark.asyncio()
    async def test_export_falls_back_to_passed_credentials(self) -> None:
        pool = _make_pool()
        service = BrazeConnectorService()
        service._pool = pool

        explicit_creds = {"api_key": "explicit-key"}
        mock_resp = _mock_response(200, {"content_block_id": "cb_explicit"})
        with patch(
            "app.connectors._base.api_key.resilient_request",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_req:
            result = await service.export("<h1>Hi</h1>", "Test", credentials=explicit_creds)

        assert result == "cb_explicit"
        pool.get_key.assert_not_called()
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer explicit-key"

    @pytest.mark.asyncio()
    async def test_export_no_pool_no_credentials_returns_mock(self) -> None:
        service = BrazeConnectorService()
        assert service._pool is None
        result = await service.export("<h1>Hi</h1>", "Welcome")
        assert result == "braze_cb_welcome"


class TestSFMCPoolRotation:
    """SFMC connector uses pool with JSON-decoded credentials."""

    @pytest.mark.asyncio()
    async def test_export_uses_pool_with_json_credentials(self) -> None:
        creds_json = json.dumps({"client_id": "pool_cid", "client_secret": "pool_csec"})
        lease = _make_lease(creds_json)
        pool = _make_pool(lease)

        service = SFMCConnectorService()
        service._pool = pool

        token_resp = _mock_response(200, {"access_token": "tok_pool", "expires_in": 3600})
        asset_resp = _mock_response(200, {"id": 99, "name": "Pool"})

        with (
            patch.object(
                httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_resp
            ),
            patch(
                "app.connectors._base.oauth.resilient_request",
                new_callable=AsyncMock,
                return_value=asset_resp,
            ),
        ):
            result = await service.export("<p>Pool</p>", "PoolTest", credentials=None)

        assert result == "99"
        pool.get_key.assert_called_once()
        lease.report_success.assert_called_once()


class TestPoolReportsFailure:
    """Pool lease reports failure on HTTP errors."""

    @pytest.mark.asyncio()
    async def test_export_pool_reports_failure_on_http_error(self) -> None:
        lease = _make_lease("fail-key")
        pool = _make_pool(lease)

        service = TaxiConnectorService()
        service._pool = pool

        error_resp = _mock_response(429, {"error": "rate limited"})
        with (
            patch(
                "app.connectors._base.api_key.resilient_request",
                new_callable=AsyncMock,
                return_value=error_resp,
            ),
            pytest.raises(ExportFailedError, match="Taxi API returned 429"),
        ):
            await service.export("<p>Rate</p>", "RateTest", credentials=None)

        pool.get_key.assert_called_once()
        lease.report_failure.assert_called_once_with(429)
        lease.report_success.assert_not_called()

    @pytest.mark.asyncio()
    async def test_export_pool_reports_failure_on_transport_error(self) -> None:
        lease = _make_lease("timeout-key")
        pool = _make_pool(lease)

        service = BrazeConnectorService()
        service._pool = pool

        with (
            patch(
                "app.connectors._base.api_key.resilient_request",
                new_callable=AsyncMock,
                side_effect=httpx.ConnectError("connection refused"),
            ),
            pytest.raises(ExportFailedError, match="Braze export failed"),
        ):
            await service.export("<h1>Hi</h1>", "Test", credentials=None)

        pool.get_key.assert_called_once()
        lease.report_failure.assert_called_once_with(0)
        lease.report_success.assert_not_called()


class TestConnectorServicePoolError:
    """ConnectorService catches NoHealthyCredentialsError from provider."""

    @pytest.mark.asyncio()
    async def test_connector_service_catches_no_healthy_credentials(self) -> None:
        from app.connectors.exceptions import ExportFailedError
        from app.connectors.service import ConnectorService

        mock_db = AsyncMock()
        service = ConnectorService(db=mock_db)

        # Mock provider that raises NoHealthyCredentialsError
        mock_provider = AsyncMock()
        mock_provider.export = AsyncMock(
            side_effect=NoHealthyCredentialsError("All keys on cooldown for braze")
        )
        service._providers["braze"] = mock_provider

        # Mock _resolve_html and gate checks
        mock_user = MagicMock()
        mock_user.role = "admin"

        mock_request = MagicMock()
        mock_request.connector_type = "braze"
        mock_request.build_id = None
        mock_request.template_version_id = 1
        mock_request.content_block_name = "Test"
        mock_request.connection_id = None
        mock_request.skip_qa_gate = True
        mock_request.skip_approval = True

        with (
            patch.object(
                service, "_resolve_html", new_callable=AsyncMock, return_value="<h1>Hi</h1>"
            ),
            patch.object(service, "_resolve_project_id", new_callable=AsyncMock, return_value=None),
            patch("app.connectors.service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.export.qa_gate_mode = "skip"
            mock_settings.return_value.rendering.gate_mode = "skip"
            with pytest.raises(ExportFailedError, match="All API keys exhausted"):
                await service.export(mock_request, mock_user)
