# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Unit tests for HubSpotSyncProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.hubspot.sync_provider import HubSpotSyncProvider
from app.connectors.sync_protocol import ESPSyncProvider
from app.connectors.sync_schemas import ESPTemplate

# ── Helpers ──

CREDS = {"access_token": "pat-na1-test-1234567890"}


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:  # type: ignore[type-arg]
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "http://test"),
    )


def _make_hubspot_email(
    id: str = "100",
    name: str = "Welcome Email",
    html: str = "<table><tr><td>Hello</td></tr></table>",
) -> dict[str, object]:
    """Create a HubSpot marketing email object."""
    return {
        "id": id,
        "name": name,
        "content": {"html": html},
        "type": "REGULAR",
        "createdAt": "2026-01-01T00:00:00.000Z",
        "updatedAt": "2026-01-15T12:00:00.000Z",
    }


# ── Protocol Conformance ──


class TestHubSpotProtocol:
    def test_protocol_conformance(self) -> None:
        assert isinstance(HubSpotSyncProvider(), ESPSyncProvider)

    def test_base_url_from_settings(self) -> None:
        provider = HubSpotSyncProvider()
        assert "hubspot" in provider._base_url


# ── Auth Headers ──


class TestHubSpotHeaders:
    def test_headers_bearer_format(self) -> None:
        provider = HubSpotSyncProvider()
        headers = provider._headers(CREDS)
        assert headers["Authorization"] == "Bearer pat-na1-test-1234567890"


# ── Validate Credentials ──


class TestHubSpotValidateCredentials:
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self) -> None:
        provider = HubSpotSyncProvider()
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"portalId": 12345}),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_invalid(self) -> None:
        provider = HubSpotSyncProvider()
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(401),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is False


# ── List Templates ──


class TestHubSpotListTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_empty(self) -> None:
        provider = HubSpotSyncProvider()
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"results": [], "paging": {}}),
        ):
            result = await provider.list_templates(CREDS)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_templates_with_items(self) -> None:
        provider = HubSpotSyncProvider()
        json_data = {
            "results": [
                _make_hubspot_email("100", "Welcome"),
                _make_hubspot_email("101", "Goodbye"),
            ],
            "paging": {},
        }
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "100"
        assert result[0].name == "Welcome"
        assert result[0].esp_type == "hubspot"
        assert result[1].id == "101"

    @pytest.mark.asyncio
    async def test_list_templates_pagination(self) -> None:
        provider = HubSpotSyncProvider()
        page1 = _mock_response(
            200,
            {
                "results": [_make_hubspot_email("100")],
                "paging": {"next": {"after": "cursor_abc"}},
            },
        )
        page2 = _mock_response(
            200,
            {
                "results": [_make_hubspot_email("101")],
                "paging": {},
            },
        )
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[page1, page2],
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "100"
        assert result[1].id == "101"


# ── Get Template ──


class TestHubSpotGetTemplate:
    @pytest.mark.asyncio
    async def test_get_template(self) -> None:
        provider = HubSpotSyncProvider()
        json_data = _make_hubspot_email("200", "Footer")
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.get_template("200", CREDS)
        assert tpl.id == "200"
        assert tpl.name == "Footer"
        assert isinstance(tpl, ESPTemplate)


# ── Create Template ──


class TestHubSpotCreateTemplate:
    @pytest.mark.asyncio
    async def test_create_template(self) -> None:
        provider = HubSpotSyncProvider()
        json_data = _make_hubspot_email("300", "New Email", "<table></table>")
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(201, json_data),
        ) as mock_req:
            tpl = await provider.create_template("New Email", "<table></table>", CREDS)

        assert tpl.id == "300"
        assert tpl.name == "New Email"
        # Verify payload structure
        call_kwargs = mock_req.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["type"] == "REGULAR"
        assert payload["content"]["html"] == "<table></table>"

    @pytest.mark.asyncio
    async def test_create_template_content_structure(self) -> None:
        """Verify HTML is nested under content.html (not top-level)."""
        provider = HubSpotSyncProvider()
        json_data = _make_hubspot_email("301", "Test")
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(201, json_data),
        ) as mock_req:
            await provider.create_template("Test", "<table>Hi</table>", CREDS)

        call_kwargs = mock_req.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "html" not in payload  # Not top-level
        assert payload["content"]["html"] == "<table>Hi</table>"  # Nested


# ── Update Template ──


class TestHubSpotUpdateTemplate:
    @pytest.mark.asyncio
    async def test_update_template(self) -> None:
        provider = HubSpotSyncProvider()
        json_data = _make_hubspot_email("100", "Welcome", "<table>Updated</table>")
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.update_template("100", "<table>Updated</table>", CREDS)
        assert tpl.id == "100"
        assert tpl.html == "<table>Updated</table>"


# ── Delete Template ──


class TestHubSpotDeleteTemplate:
    @pytest.mark.asyncio
    async def test_delete_template_success(self) -> None:
        provider = HubSpotSyncProvider()
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(204),
        ):
            result = await provider.delete_template("100", CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self) -> None:
        provider = HubSpotSyncProvider()
        with patch(
            "app.connectors.hubspot.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            result = await provider.delete_template("999", CREDS)
        assert result is False
