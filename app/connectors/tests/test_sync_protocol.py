# pyright: reportUnknownMemberType=false
"""Protocol conformance tests for ESP sync providers."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.adobe.sync_provider import AdobeSyncProvider
from app.connectors.braze.sync_provider import BrazeSyncProvider
from app.connectors.sfmc.sync_provider import SFMCSyncProvider
from app.connectors.sync_protocol import ESPSyncProvider
from app.connectors.sync_schemas import ESPTemplate
from app.connectors.taxi.sync_provider import TaxiSyncProvider

# ── Protocol Conformance ──

PROTOCOL_METHODS = [
    "validate_credentials",
    "list_templates",
    "get_template",
    "create_template",
    "update_template",
    "delete_template",
]


class TestSyncProtocolConformance:
    """All 4 sync providers satisfy ESPSyncProvider protocol."""

    def test_braze_is_esp_sync_provider(self) -> None:
        assert isinstance(BrazeSyncProvider(), ESPSyncProvider)

    def test_sfmc_is_esp_sync_provider(self) -> None:
        assert isinstance(SFMCSyncProvider(), ESPSyncProvider)

    def test_adobe_is_esp_sync_provider(self) -> None:
        assert isinstance(AdobeSyncProvider(), ESPSyncProvider)

    def test_taxi_is_esp_sync_provider(self) -> None:
        assert isinstance(TaxiSyncProvider(), ESPSyncProvider)

    @pytest.mark.parametrize("method", PROTOCOL_METHODS)
    def test_braze_has_protocol_method(self, method: str) -> None:
        assert hasattr(BrazeSyncProvider, method)
        assert inspect.iscoroutinefunction(getattr(BrazeSyncProvider, method))

    @pytest.mark.parametrize("method", PROTOCOL_METHODS)
    def test_sfmc_has_protocol_method(self, method: str) -> None:
        assert hasattr(SFMCSyncProvider, method)
        assert inspect.iscoroutinefunction(getattr(SFMCSyncProvider, method))

    @pytest.mark.parametrize("method", PROTOCOL_METHODS)
    def test_adobe_has_protocol_method(self, method: str) -> None:
        assert hasattr(AdobeSyncProvider, method)
        assert inspect.iscoroutinefunction(getattr(AdobeSyncProvider, method))

    @pytest.mark.parametrize("method", PROTOCOL_METHODS)
    def test_taxi_has_protocol_method(self, method: str) -> None:
        assert hasattr(TaxiSyncProvider, method)
        assert inspect.iscoroutinefunction(getattr(TaxiSyncProvider, method))


# ── Provider Initialization ──


class TestProviderInit:
    """Providers initialize base URL from settings."""

    def test_braze_base_url_from_settings(self) -> None:
        provider = BrazeSyncProvider()
        assert provider._base_url.endswith("/braze") or "braze" in provider._base_url

    def test_sfmc_base_url_from_settings(self) -> None:
        provider = SFMCSyncProvider()
        assert provider._base_url.endswith("/sfmc") or "sfmc" in provider._base_url

    def test_adobe_base_url_from_settings(self) -> None:
        provider = AdobeSyncProvider()
        assert provider._base_url.endswith("/adobe") or "adobe" in provider._base_url

    def test_taxi_base_url_from_settings(self) -> None:
        provider = TaxiSyncProvider()
        assert provider._base_url.endswith("/taxi") or "taxi" in provider._base_url


# ── Provider Auth Patterns ──


class TestProviderAuth:
    """Braze/Taxi use API key headers; SFMC/Adobe use OAuth."""

    def test_braze_uses_bearer_header(self) -> None:
        provider = BrazeSyncProvider()
        headers = provider._headers({"api_key": "test-key-1234"})
        assert headers["Authorization"] == "Bearer test-key-1234"

    def test_taxi_uses_api_key_header(self) -> None:
        provider = TaxiSyncProvider()
        headers = provider._headers({"api_key": "test-key-5678"})
        assert headers["X-API-Key"] == "test-key-5678"


# ── Braze Provider ──


def _make_esp_template(
    id: str = "tpl_1",
    name: str = "Test Template",
    html: str = "<div>Hello</div>",
    esp_type: str = "braze",
) -> ESPTemplate:
    return ESPTemplate(
        id=id,
        name=name,
        html=html,
        esp_type=esp_type,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:  # type: ignore[type-arg]
    """Create a mock httpx.Response."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "http://test"),
    )
    return resp


class TestBrazeProvider:
    """Unit tests for BrazeSyncProvider using mocked resilient_request."""

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self) -> None:
        provider = BrazeSyncProvider()
        with patch(
            "app.connectors.braze.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"content_blocks": []}),
        ):
            result = await provider.validate_credentials({"api_key": "valid"})
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_failure(self) -> None:
        provider = BrazeSyncProvider()
        with patch(
            "app.connectors.braze.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(401),
        ):
            result = await provider.validate_credentials({"api_key": "invalid"})
        assert result is False

    @pytest.mark.asyncio
    async def test_list_templates(self) -> None:
        provider = BrazeSyncProvider()
        json_data = {
            "content_blocks": [
                {
                    "content_block_id": "cb_1",
                    "name": "Welcome",
                    "content": "<p>Hi</p>",
                    "created_at": "2026-01-01",
                    "updated_at": "2026-01-01",
                }
            ]
        }
        with patch(
            "app.connectors.braze.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            templates = await provider.list_templates({"api_key": "test"})
        assert len(templates) == 1
        assert templates[0].id == "cb_1"
        assert templates[0].name == "Welcome"
        assert templates[0].esp_type == "braze"

    @pytest.mark.asyncio
    async def test_get_template(self) -> None:
        provider = BrazeSyncProvider()
        json_data = {
            "content_block_id": "cb_2",
            "name": "Footer",
            "content": "<footer>End</footer>",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        with patch(
            "app.connectors.braze.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.get_template("cb_2", {"api_key": "test"})
        assert tpl.id == "cb_2"
        assert tpl.html == "<footer>End</footer>"

    @pytest.mark.asyncio
    async def test_create_template(self) -> None:
        provider = BrazeSyncProvider()
        json_data = {
            "content_block_id": "cb_new",
            "name": "New Block",
            "content": "<div>New</div>",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        with patch(
            "app.connectors.braze.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.create_template("New Block", "<div>New</div>", {"api_key": "test"})
        assert tpl.id == "cb_new"
        assert tpl.name == "New Block"

    @pytest.mark.asyncio
    async def test_delete_template_success(self) -> None:
        provider = BrazeSyncProvider()
        with patch(
            "app.connectors.braze.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200),
        ):
            result = await provider.delete_template("cb_1", {"api_key": "test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self) -> None:
        provider = BrazeSyncProvider()
        with patch(
            "app.connectors.braze.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            result = await provider.delete_template("cb_missing", {"api_key": "test"})
        assert result is False
