# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Unit tests for SendGridSyncProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.sendgrid.sync_provider import SendGridSyncProvider
from app.connectors.sync_protocol import ESPSyncProvider
from app.connectors.sync_schemas import ESPTemplate

# ── Helpers ──

CREDS = {"api_key": "SG.test_key_1234567890"}


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:  # type: ignore[type-arg]
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "http://test"),
    )


def _make_template(
    id: str = "d-abc123",
    name: str = "Welcome Email",
    html: str = "<table><tr><td>Hello</td></tr></table>",
) -> dict[str, object]:
    """Create a SendGrid template object with versions."""
    return {
        "id": id,
        "name": name,
        "versions": [
            {
                "id": "ver_1",
                "name": name,
                "html_content": html,
                "active": 1,
                "updated_at": "2026-01-15T12:00:00Z",
            }
        ],
    }


# ── Protocol Conformance ──


class TestSendGridProtocol:
    def test_protocol_conformance(self) -> None:
        assert isinstance(SendGridSyncProvider(), ESPSyncProvider)

    def test_base_url_from_settings(self) -> None:
        provider = SendGridSyncProvider()
        assert "sendgrid" in provider._base_url


# ── Auth Headers ──


class TestSendGridHeaders:
    def test_headers_auth_format(self) -> None:
        provider = SendGridSyncProvider()
        headers = provider._headers(CREDS)
        assert headers["Authorization"] == "Bearer SG.test_key_1234567890"


# ── Validate Credentials ──


class TestSendGridValidateCredentials:
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self) -> None:
        provider = SendGridSyncProvider()
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"scopes": ["mail.send"]}),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_invalid(self) -> None:
        provider = SendGridSyncProvider()
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(401),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_credentials_missing_key(self) -> None:
        provider = SendGridSyncProvider()
        with pytest.raises(KeyError):
            await provider.validate_credentials({})


# ── List Templates ──


class TestSendGridListTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_empty(self) -> None:
        provider = SendGridSyncProvider()
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"result": []}),
        ):
            result = await provider.list_templates(CREDS)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_templates_success(self) -> None:
        provider = SendGridSyncProvider()
        json_data = {
            "result": [
                _make_template("d-1", "Welcome"),
                _make_template("d-2", "Goodbye"),
            ]
        }
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "d-1"
        assert result[0].esp_type == "sendgrid"

    @pytest.mark.asyncio
    async def test_map_template_active_version(self) -> None:
        """HTML is extracted from the active version."""
        template = {
            "id": "d-1",
            "name": "Test",
            "versions": [
                {"id": "v1", "html_content": "old", "active": 0, "updated_at": "2026-01-01"},
                {"id": "v2", "html_content": "new", "active": 1, "updated_at": "2026-01-02"},
            ],
        }
        result = SendGridSyncProvider._map_template(template)
        assert result.html == "new"


# ── Get Template ──


class TestSendGridGetTemplate:
    @pytest.mark.asyncio
    async def test_get_template_success(self) -> None:
        provider = SendGridSyncProvider()
        json_data = _make_template("d-55", "Footer")
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.get_template("d-55", CREDS)
        assert tpl.id == "d-55"
        assert tpl.name == "Footer"
        assert isinstance(tpl, ESPTemplate)

    @pytest.mark.asyncio
    async def test_get_template_not_found(self) -> None:
        provider = SendGridSyncProvider()
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.get_template("missing", CREDS)


# ── Create Template ──


class TestSendGridCreateTemplate:
    @pytest.mark.asyncio
    async def test_create_template_success(self) -> None:
        """Create involves two API calls: create shell + add version, then get."""
        provider = SendGridSyncProvider()
        shell_resp = _mock_response(201, {"id": "d-NEW", "name": "New Email"})
        version_resp = _mock_response(201, {"id": "ver_1"})
        get_resp = _mock_response(200, _make_template("d-NEW", "New Email", "<table></table>"))
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[shell_resp, version_resp, get_resp],
        ):
            tpl = await provider.create_template("New Email", "<table></table>", CREDS)
        assert tpl.id == "d-NEW"
        assert tpl.name == "New Email"


# ── Update Template ──


class TestSendGridUpdateTemplate:
    @pytest.mark.asyncio
    async def test_update_template_success(self) -> None:
        """Update creates new version then re-fetches."""
        provider = SendGridSyncProvider()
        version_resp = _mock_response(201, {"id": "ver_2"})
        get_resp = _mock_response(200, _make_template("d-1", "Welcome", "<table>Updated</table>"))
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[version_resp, get_resp],
        ):
            tpl = await provider.update_template("d-1", "<table>Updated</table>", CREDS)
        assert tpl.id == "d-1"
        assert tpl.html == "<table>Updated</table>"

    @pytest.mark.asyncio
    async def test_update_template_not_found(self) -> None:
        provider = SendGridSyncProvider()
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.update_template("missing", "<table></table>", CREDS)


# ── Delete Template ──


class TestSendGridDeleteTemplate:
    @pytest.mark.asyncio
    async def test_delete_template_success(self) -> None:
        provider = SendGridSyncProvider()
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(204),
        ):
            result = await provider.delete_template("d-1", CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self) -> None:
        provider = SendGridSyncProvider()
        with patch(
            "app.connectors.sendgrid.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            result = await provider.delete_template("missing", CREDS)
        assert result is False
