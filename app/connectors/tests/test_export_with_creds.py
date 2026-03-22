"""Tests for ESP export with real credentials (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.adobe.service import AdobeConnectorService
from app.connectors.braze.service import BrazeConnectorService
from app.connectors.sfmc.service import SFMCConnectorService
from app.connectors.taxi.service import TaxiConnectorService


def _mock_response(status: int = 200, json_data: dict[str, object] | None = None) -> httpx.Response:
    """Build a minimal httpx.Response for testing."""
    resp = httpx.Response(
        status_code=status,
        json=json_data or {},
        request=httpx.Request("POST", "http://test"),
    )
    return resp


# ── Braze ──


class TestBrazeExportWithCredentials:
    """Braze export using real API path."""

    @pytest.mark.asyncio()
    async def test_export_with_credentials_calls_api(self) -> None:
        creds = {"api_key": "test-braze-key"}
        mock_resp = _mock_response(200, {"content_block_id": "cb_123"})

        with patch(
            "app.connectors.braze.service.resilient_request",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_req:
            service = BrazeConnectorService()
            result = await service.export("<h1>Hi</h1>", "Welcome", creds)

        assert result == "cb_123"
        mock_req.assert_called_once()
        call_kwargs = mock_req.call_args
        assert "content_blocks/create" in call_kwargs.args[2]
        assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer test-braze-key"

    @pytest.mark.asyncio()
    async def test_export_without_credentials_returns_mock(self) -> None:
        service = BrazeConnectorService()
        result = await service.export("<h1>Hi</h1>", "Welcome")
        assert result == "braze_cb_welcome"


# ── SFMC ──


class TestSFMCExportWithCredentials:
    """SFMC export using real API path."""

    @pytest.mark.asyncio()
    async def test_export_with_credentials_calls_api(self) -> None:
        creds = {"client_id": "cid", "client_secret": "csec", "subdomain": "mc"}
        token_resp = _mock_response(200, {"access_token": "tok_sfmc", "expires_in": 3600})
        asset_resp = _mock_response(200, {"id": 42, "name": "Welcome"})

        # Clear token cache before test
        SFMCConnectorService._token_cache.clear()

        with (
            patch.object(
                httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_resp
            ),
            patch(
                "app.connectors.sfmc.service.resilient_request",
                new_callable=AsyncMock,
                return_value=asset_resp,
            ) as mock_req,
        ):
            service = SFMCConnectorService()
            result = await service.export("<p>Test</p>", "Welcome", creds)

        assert result == "42"
        mock_req.assert_called_once()

    @pytest.mark.asyncio()
    async def test_export_without_credentials_returns_mock(self) -> None:
        service = SFMCConnectorService()
        result = await service.export("<p>Test</p>", "Promo")
        assert result == "sfmc_ca_promo"


# ── Adobe Campaign ──


class TestAdobeExportWithCredentials:
    """Adobe Campaign export using real API path."""

    @pytest.mark.asyncio()
    async def test_export_with_credentials_calls_api(self) -> None:
        creds = {"client_id": "acid", "client_secret": "asec", "org_id": "org"}
        token_resp = _mock_response(200, {"access_token": "tok_adobe", "expires_in": 86399})
        delivery_resp = _mock_response(200, {"PKey": "PK_abc"})

        AdobeConnectorService._token_cache.clear()

        with (
            patch.object(
                httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=token_resp
            ),
            patch(
                "app.connectors.adobe.service.resilient_request",
                new_callable=AsyncMock,
                return_value=delivery_resp,
            ) as mock_req,
        ):
            service = AdobeConnectorService()
            result = await service.export("<p>Adobe</p>", "Launch", creds)

        assert result == "PK_abc"
        mock_req.assert_called_once()

    @pytest.mark.asyncio()
    async def test_export_without_credentials_returns_mock(self) -> None:
        service = AdobeConnectorService()
        result = await service.export("<p>Adobe</p>", "Launch")
        assert result == "adobe_dl_launch"


# ── Taxi ──


class TestTaxiExportWithCredentials:
    """Taxi export using real API path."""

    @pytest.mark.asyncio()
    async def test_export_with_credentials_calls_api(self) -> None:
        creds = {"api_key": "taxi-key-123"}
        mock_resp = _mock_response(200, {"id": "tpl_789", "name": "Newsletter"})

        with patch(
            "app.connectors.taxi.service.resilient_request",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_req:
            service = TaxiConnectorService()
            result = await service.export("<p>Taxi</p>", "Newsletter", creds)

        assert result == "tpl_789"
        mock_req.assert_called_once()
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["headers"]["X-API-Key"] == "taxi-key-123"

    @pytest.mark.asyncio()
    async def test_export_without_credentials_returns_mock(self) -> None:
        service = TaxiConnectorService()
        result = await service.export("<p>Taxi</p>", "Newsletter")
        assert result == "taxi_tpl_newsletter"


# ── Credential decryption failure ──


class TestCredentialDecryptionFailure:
    """Verify credential resolution error handling."""

    @pytest.mark.asyncio()
    async def test_resolve_credentials_missing_connection(self) -> None:
        from unittest.mock import MagicMock

        from app.connectors.service import ConnectorService
        from app.core.exceptions import NotFoundError

        # Mock db.execute returning no result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        service = ConnectorService(db=mock_db)
        user = MagicMock()

        with pytest.raises(NotFoundError, match="ESP connection"):
            await service._resolve_credentials(999, user)

    @pytest.mark.asyncio()
    async def test_resolve_credentials_decryption_failure(self) -> None:
        from unittest.mock import MagicMock

        from app.connectors.exceptions import ExportFailedError
        from app.connectors.service import ConnectorService

        # Mock a connection that exists but has corrupt encrypted_credentials
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.project_id = 1
        mock_conn.encrypted_credentials = "corrupt-data"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conn
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        service = ConnectorService(db=mock_db)
        user = MagicMock()

        with (
            patch("app.connectors.service.ProjectService") as mock_ps_cls,
            patch("app.connectors.service.decrypt_token", side_effect=ValueError("bad token")),
        ):
            mock_ps_cls.return_value.verify_project_access = AsyncMock()
            with pytest.raises(ExportFailedError, match="decrypt"):
                await service._resolve_credentials(1, user)
