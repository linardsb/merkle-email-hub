# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Unit tests for ActiveCampaignSyncProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.activecampaign.sync_provider import ActiveCampaignSyncProvider
from app.connectors.sync_protocol import ESPSyncProvider
from app.connectors.sync_schemas import ESPTemplate

# ── Helpers ──

CREDS = {"api_key": "ac_test_key_1234", "account": "mycompany"}


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:  # type: ignore[type-arg]
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "http://test"),
    )


def _make_template(
    id: str = "42",
    name: str = "Welcome Email",
    html: str = "<table><tr><td>Hello</td></tr></table>",
) -> dict[str, object]:
    """Create an ActiveCampaign message object."""
    return {
        "id": id,
        "name": name,
        "message": html,
        "cdate": "2026-01-01T00:00:00-06:00",
        "mdate": "2026-01-15T12:00:00-06:00",
    }


# ── Protocol Conformance ──


class TestActiveCampaignProtocol:
    def test_protocol_conformance(self) -> None:
        assert isinstance(ActiveCampaignSyncProvider(), ESPSyncProvider)

    def test_base_url_from_settings(self) -> None:
        provider = ActiveCampaignSyncProvider()
        assert "activecampaign" in provider._base_url


# ── Auth Headers ──


class TestActiveCampaignHeaders:
    def test_headers_auth_format(self) -> None:
        provider = ActiveCampaignSyncProvider()
        headers = provider._headers(CREDS)
        assert headers["Api-Token"] == "ac_test_key_1234"


# ── Validate Credentials ──


class TestActiveCampaignValidateCredentials:
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self) -> None:
        provider = ActiveCampaignSyncProvider()
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"user": {"id": 1}}),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_invalid(self) -> None:
        provider = ActiveCampaignSyncProvider()
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(401),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_credentials_missing_key(self) -> None:
        provider = ActiveCampaignSyncProvider()
        with pytest.raises(KeyError):
            await provider.validate_credentials({})

    @pytest.mark.asyncio
    async def test_validate_credentials_malicious_account_rejected(self) -> None:
        """Account names with path traversal chars are rejected when URL has placeholder."""
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.esp_sync.activecampaign_base_url = "https://{account}.api-us1.com/api/3"
        provider = ActiveCampaignSyncProvider(settings=mock_settings)
        bad_creds = {"api_key": "key", "account": "evil.com/api#"}
        with pytest.raises(ValueError, match="disallowed"):
            await provider.validate_credentials(bad_creds)


# ── List Templates ──


class TestActiveCampaignListTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_empty(self) -> None:
        provider = ActiveCampaignSyncProvider()
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"messages": [], "meta": {"total": 0}}),
        ):
            result = await provider.list_templates(CREDS)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_templates_success(self) -> None:
        provider = ActiveCampaignSyncProvider()
        json_data = {
            "messages": [
                _make_template("1", "Welcome"),
                _make_template("2", "Goodbye"),
            ],
            "meta": {"total": 2},
        }
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[0].esp_type == "activecampaign"

    @pytest.mark.asyncio
    async def test_list_templates_pagination(self) -> None:
        provider = ActiveCampaignSyncProvider()
        page1 = _mock_response(
            200,
            {"messages": [_make_template("1")], "meta": {"total": 2}},
        )
        page2 = _mock_response(
            200,
            {"messages": [_make_template("2")], "meta": {"total": 2}},
        )
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[page1, page2],
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2


# ── Get Template ──


class TestActiveCampaignGetTemplate:
    @pytest.mark.asyncio
    async def test_get_template_success(self) -> None:
        provider = ActiveCampaignSyncProvider()
        json_data = {"message": _make_template("55", "Footer")}
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.get_template("55", CREDS)
        assert tpl.id == "55"
        assert tpl.name == "Footer"
        assert isinstance(tpl, ESPTemplate)

    @pytest.mark.asyncio
    async def test_get_template_not_found(self) -> None:
        provider = ActiveCampaignSyncProvider()
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.get_template("missing", CREDS)


# ── Create Template ──


class TestActiveCampaignCreateTemplate:
    @pytest.mark.asyncio
    async def test_create_template_success(self) -> None:
        provider = ActiveCampaignSyncProvider()
        json_data = {"message": _make_template("NEW", "New Email", "<table></table>")}
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(201, json_data),
        ) as mock_req:
            tpl = await provider.create_template("New Email", "<table></table>", CREDS)

        assert tpl.id == "NEW"
        call_kwargs = mock_req.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["message"]["name"] == "New Email"
        assert payload["message"]["message"] == "<table></table>"


# ── Update Template ──


class TestActiveCampaignUpdateTemplate:
    @pytest.mark.asyncio
    async def test_update_template_success(self) -> None:
        provider = ActiveCampaignSyncProvider()
        json_data = {"message": _make_template("1", "Welcome", "<table>Updated</table>")}
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.update_template("1", "<table>Updated</table>", CREDS)
        assert tpl.id == "1"
        assert tpl.html == "<table>Updated</table>"

    @pytest.mark.asyncio
    async def test_update_template_not_found(self) -> None:
        provider = ActiveCampaignSyncProvider()
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.update_template("missing", "<table></table>", CREDS)


# ── Delete Template ──


class TestActiveCampaignDeleteTemplate:
    @pytest.mark.asyncio
    async def test_delete_template_success(self) -> None:
        provider = ActiveCampaignSyncProvider()
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200),
        ):
            result = await provider.delete_template("1", CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self) -> None:
        provider = ActiveCampaignSyncProvider()
        with patch(
            "app.connectors.activecampaign.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            result = await provider.delete_template("missing", CREDS)
        assert result is False
