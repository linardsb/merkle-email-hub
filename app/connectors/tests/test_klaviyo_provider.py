# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Unit tests for KlaviyoSyncProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.klaviyo.sync_provider import KlaviyoSyncProvider
from app.connectors.sync_protocol import ESPSyncProvider
from app.connectors.sync_schemas import ESPTemplate

# ── Helpers ──

CREDS = {"api_key": "pk_test_1234567890"}


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:  # type: ignore[type-arg]
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "http://test"),
    )


def _make_klaviyo_template(
    id: str = "TMPL_1",
    name: str = "Welcome Email",
    html: str = "<table><tr><td>Hello</td></tr></table>",
) -> dict[str, object]:
    """Create a Klaviyo JSON:API template resource."""
    return {
        "type": "template",
        "id": id,
        "attributes": {
            "name": name,
            "html": html,
            "created": "2026-01-01T00:00:00+00:00",
            "updated": "2026-01-15T12:00:00+00:00",
        },
    }


# ── Protocol Conformance ──


class TestKlaviyoProtocol:
    def test_protocol_conformance(self) -> None:
        assert isinstance(KlaviyoSyncProvider(), ESPSyncProvider)

    def test_base_url_from_settings(self) -> None:
        provider = KlaviyoSyncProvider()
        assert "klaviyo" in provider._base_url


# ── Auth Headers ──


class TestKlaviyoHeaders:
    def test_headers_auth_format(self) -> None:
        provider = KlaviyoSyncProvider()
        headers = provider._headers(CREDS)
        assert headers["Authorization"] == "Klaviyo-API-Key pk_test_1234567890"

    def test_headers_include_revision(self) -> None:
        provider = KlaviyoSyncProvider()
        headers = provider._headers(CREDS)
        assert headers["revision"] == "2025-07-15"


# ── Validate Credentials ──


class TestKlaviyoValidateCredentials:
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self) -> None:
        provider = KlaviyoSyncProvider()
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"data": [{"id": "acct_1"}]}),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_invalid(self) -> None:
        provider = KlaviyoSyncProvider()
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(401),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is False


# ── List Templates ──


class TestKlaviyoListTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_empty(self) -> None:
        provider = KlaviyoSyncProvider()
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"data": [], "links": {}}),
        ):
            result = await provider.list_templates(CREDS)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_templates_with_items(self) -> None:
        provider = KlaviyoSyncProvider()
        json_data = {
            "data": [
                _make_klaviyo_template("TMPL_1", "Welcome"),
                _make_klaviyo_template("TMPL_2", "Goodbye"),
            ],
            "links": {},
        }
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "TMPL_1"
        assert result[0].name == "Welcome"
        assert result[0].esp_type == "klaviyo"
        assert result[1].id == "TMPL_2"

    @pytest.mark.asyncio
    async def test_list_templates_pagination(self) -> None:
        provider = KlaviyoSyncProvider()
        page1 = _mock_response(
            200,
            {
                "data": [_make_klaviyo_template("TMPL_1")],
                "links": {"next": "http://test/api/templates/?page[cursor]=abc"},
            },
        )
        page2 = _mock_response(
            200,
            {
                "data": [_make_klaviyo_template("TMPL_2")],
                "links": {},
            },
        )
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[page1, page2],
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "TMPL_1"
        assert result[1].id == "TMPL_2"


# ── Get Template ──


class TestKlaviyoGetTemplate:
    @pytest.mark.asyncio
    async def test_get_template(self) -> None:
        provider = KlaviyoSyncProvider()
        json_data = {"data": _make_klaviyo_template("TMPL_5", "Footer")}
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.get_template("TMPL_5", CREDS)
        assert tpl.id == "TMPL_5"
        assert tpl.name == "Footer"
        assert isinstance(tpl, ESPTemplate)


# ── Create Template ──


class TestKlaviyoCreateTemplate:
    @pytest.mark.asyncio
    async def test_create_template(self) -> None:
        provider = KlaviyoSyncProvider()
        json_data = {"data": _make_klaviyo_template("TMPL_NEW", "New Email", "<table></table>")}
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(201, json_data),
        ) as mock_req:
            tpl = await provider.create_template("New Email", "<table></table>", CREDS)

        assert tpl.id == "TMPL_NEW"
        assert tpl.name == "New Email"
        # Verify JSON:API payload structure
        call_kwargs = mock_req.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["data"]["type"] == "template"
        assert payload["data"]["attributes"]["name"] == "New Email"
        assert payload["data"]["attributes"]["html"] == "<table></table>"


# ── Update Template ──


class TestKlaviyoUpdateTemplate:
    @pytest.mark.asyncio
    async def test_update_template(self) -> None:
        provider = KlaviyoSyncProvider()
        json_data = {"data": _make_klaviyo_template("TMPL_1", "Welcome", "<table>Updated</table>")}
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.update_template("TMPL_1", "<table>Updated</table>", CREDS)
        assert tpl.id == "TMPL_1"
        assert tpl.html == "<table>Updated</table>"


# ── Delete Template ──


class TestKlaviyoDeleteTemplate:
    @pytest.mark.asyncio
    async def test_delete_template_success(self) -> None:
        provider = KlaviyoSyncProvider()
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(204),
        ):
            result = await provider.delete_template("TMPL_1", CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self) -> None:
        provider = KlaviyoSyncProvider()
        with patch(
            "app.connectors.klaviyo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            result = await provider.delete_template("TMPL_MISSING", CREDS)
        assert result is False
