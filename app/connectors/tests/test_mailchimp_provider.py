# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Unit tests for MailchimpSyncProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.mailchimp.sync_provider import MailchimpSyncProvider
from app.connectors.sync_protocol import ESPSyncProvider
from app.connectors.sync_schemas import ESPTemplate

# ── Helpers ──

CREDS = {"api_key": "abc123def456-us21"}


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:  # type: ignore[type-arg]
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "http://test"),
    )


def _make_template(
    id: str = "12345",
    name: str = "Welcome Email",
    html: str = "<table><tr><td>Hello</td></tr></table>",
) -> dict[str, object]:
    """Create a Mailchimp template object."""
    return {
        "id": id,
        "name": name,
        "html": html,
        "date_created": "2026-01-01T00:00:00+00:00",
        "date_edited": "2026-01-15T12:00:00+00:00",
    }


# ── Protocol Conformance ──


class TestMailchimpProtocol:
    def test_protocol_conformance(self) -> None:
        assert isinstance(MailchimpSyncProvider(), ESPSyncProvider)

    def test_base_url_from_settings(self) -> None:
        provider = MailchimpSyncProvider()
        assert "mailchimp" in provider._base_url


# ── Auth Headers ──


class TestMailchimpHeaders:
    def test_headers_auth_format(self) -> None:
        provider = MailchimpSyncProvider()
        headers = provider._headers(CREDS)
        assert headers["Authorization"] == "Bearer abc123def456-us21"

    def test_extract_dc(self) -> None:
        assert MailchimpSyncProvider._extract_dc("abc-us21") == "us21"
        assert MailchimpSyncProvider._extract_dc("nodc") == "us1"


# ── Validate Credentials ──


class TestMailchimpValidateCredentials:
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self) -> None:
        provider = MailchimpSyncProvider()
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"account_id": "abc"}),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_invalid(self) -> None:
        provider = MailchimpSyncProvider()
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(401),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_credentials_missing_key(self) -> None:
        provider = MailchimpSyncProvider()
        with pytest.raises(KeyError):
            await provider.validate_credentials({})


# ── List Templates ──


class TestMailchimpListTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_empty(self) -> None:
        provider = MailchimpSyncProvider()
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"templates": [], "total_items": 0}),
        ):
            result = await provider.list_templates(CREDS)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_templates_success(self) -> None:
        provider = MailchimpSyncProvider()
        json_data = {
            "templates": [
                _make_template("1", "Welcome"),
                _make_template("2", "Goodbye"),
            ],
            "total_items": 2,
        }
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[0].name == "Welcome"
        assert result[0].esp_type == "mailchimp"

    @pytest.mark.asyncio
    async def test_list_templates_pagination(self) -> None:
        provider = MailchimpSyncProvider()
        page1 = _mock_response(
            200,
            {"templates": [_make_template("1")], "total_items": 2},
        )
        page2 = _mock_response(
            200,
            {"templates": [_make_template("2")], "total_items": 2},
        )
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[page1, page2],
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "2"


# ── Get Template ──


class TestMailchimpGetTemplate:
    @pytest.mark.asyncio
    async def test_get_template_success(self) -> None:
        provider = MailchimpSyncProvider()
        json_data = _make_template("55", "Footer")
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.get_template("55", CREDS)
        assert tpl.id == "55"
        assert tpl.name == "Footer"
        assert isinstance(tpl, ESPTemplate)

    @pytest.mark.asyncio
    async def test_get_template_not_found(self) -> None:
        provider = MailchimpSyncProvider()
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.get_template("missing", CREDS)


# ── Create Template ──


class TestMailchimpCreateTemplate:
    @pytest.mark.asyncio
    async def test_create_template_success(self) -> None:
        provider = MailchimpSyncProvider()
        json_data = _make_template("NEW", "New Email", "<table></table>")
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ) as mock_req:
            tpl = await provider.create_template("New Email", "<table></table>", CREDS)

        assert tpl.id == "NEW"
        assert tpl.name == "New Email"
        call_kwargs = mock_req.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["name"] == "New Email"
        assert payload["html"] == "<table></table>"


# ── Update Template ──


class TestMailchimpUpdateTemplate:
    @pytest.mark.asyncio
    async def test_update_template_success(self) -> None:
        provider = MailchimpSyncProvider()
        json_data = _make_template("1", "Welcome", "<table>Updated</table>")
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.update_template("1", "<table>Updated</table>", CREDS)
        assert tpl.id == "1"
        assert tpl.html == "<table>Updated</table>"

    @pytest.mark.asyncio
    async def test_update_template_not_found(self) -> None:
        provider = MailchimpSyncProvider()
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.update_template("missing", "<table></table>", CREDS)


# ── Delete Template ──


class TestMailchimpDeleteTemplate:
    @pytest.mark.asyncio
    async def test_delete_template_success(self) -> None:
        provider = MailchimpSyncProvider()
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(204),
        ):
            result = await provider.delete_template("1", CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self) -> None:
        provider = MailchimpSyncProvider()
        with patch(
            "app.connectors.mailchimp.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            result = await provider.delete_template("missing", CREDS)
        assert result is False
