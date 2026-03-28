# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Unit tests for BrevoSyncProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.brevo.sync_provider import BrevoSyncProvider
from app.connectors.sync_protocol import ESPSyncProvider
from app.connectors.sync_schemas import ESPTemplate

# ── Helpers ──

CREDS = {"api_key": "xkeysib-test1234567890"}


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:  # type: ignore[type-arg]
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "http://test"),
    )


def _make_template(
    id: str = "10",
    name: str = "Welcome Email",
    html: str = "<table><tr><td>Hello</td></tr></table>",
) -> dict[str, object]:
    """Create a Brevo SMTP template object."""
    return {
        "id": int(id),
        "name": name,
        "htmlContent": html,
        "createdAt": "2026-01-01T00:00:00.000Z",
        "modifiedAt": "2026-01-15T12:00:00.000Z",
    }


# ── Protocol Conformance ──


class TestBrevoProtocol:
    def test_protocol_conformance(self) -> None:
        assert isinstance(BrevoSyncProvider(), ESPSyncProvider)

    def test_base_url_from_settings(self) -> None:
        provider = BrevoSyncProvider()
        assert "brevo" in provider._base_url


# ── Auth Headers ──


class TestBrevoHeaders:
    def test_headers_auth_format(self) -> None:
        provider = BrevoSyncProvider()
        headers = provider._headers(CREDS)
        assert headers["api-key"] == "xkeysib-test1234567890"


# ── Validate Credentials ──


class TestBrevoValidateCredentials:
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self) -> None:
        provider = BrevoSyncProvider()
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"email": "user@example.com"}),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_invalid(self) -> None:
        provider = BrevoSyncProvider()
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(401),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_credentials_missing_key(self) -> None:
        provider = BrevoSyncProvider()
        with pytest.raises(KeyError):
            await provider.validate_credentials({})


# ── List Templates ──


class TestBrevoListTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_empty(self) -> None:
        provider = BrevoSyncProvider()
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"templates": [], "count": 0}),
        ):
            result = await provider.list_templates(CREDS)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_templates_success(self) -> None:
        provider = BrevoSyncProvider()
        json_data = {
            "templates": [
                _make_template("1", "Welcome"),
                _make_template("2", "Goodbye"),
            ],
            "count": 2,
        }
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[0].esp_type == "brevo"

    @pytest.mark.asyncio
    async def test_list_templates_pagination(self) -> None:
        provider = BrevoSyncProvider()
        page1 = _mock_response(
            200,
            {"templates": [_make_template("1")], "count": 2},
        )
        page2 = _mock_response(
            200,
            {"templates": [_make_template("2")], "count": 2},
        )
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[page1, page2],
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2


# ── Get Template ──


class TestBrevoGetTemplate:
    @pytest.mark.asyncio
    async def test_get_template_success(self) -> None:
        provider = BrevoSyncProvider()
        json_data = _make_template("55", "Footer")
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.get_template("55", CREDS)
        assert tpl.id == "55"
        assert tpl.name == "Footer"
        assert isinstance(tpl, ESPTemplate)

    @pytest.mark.asyncio
    async def test_get_template_not_found(self) -> None:
        provider = BrevoSyncProvider()
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.get_template("missing", CREDS)


# ── Create Template ──


class TestBrevoCreateTemplate:
    @pytest.mark.asyncio
    async def test_create_template_success(self) -> None:
        """Create returns {id}, then fetches full template."""
        provider = BrevoSyncProvider()
        create_resp = _mock_response(201, {"id": 99})
        get_resp = _mock_response(200, _make_template("99", "New Email", "<table></table>"))
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[create_resp, get_resp],
        ):
            tpl = await provider.create_template("New Email", "<table></table>", CREDS)
        assert tpl.id == "99"
        assert tpl.name == "New Email"


# ── Update Template ──


class TestBrevoUpdateTemplate:
    @pytest.mark.asyncio
    async def test_update_template_success(self) -> None:
        """Update returns 204, then fetches full template."""
        provider = BrevoSyncProvider()
        update_resp = _mock_response(204)
        get_resp = _mock_response(200, _make_template("1", "Welcome", "<table>Updated</table>"))
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            side_effect=[update_resp, get_resp],
        ):
            tpl = await provider.update_template("1", "<table>Updated</table>", CREDS)
        assert tpl.id == "1"
        assert tpl.html == "<table>Updated</table>"

    @pytest.mark.asyncio
    async def test_update_template_not_found(self) -> None:
        provider = BrevoSyncProvider()
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.update_template("missing", "<table></table>", CREDS)


# ── Delete Template ──


class TestBrevoDeleteTemplate:
    @pytest.mark.asyncio
    async def test_delete_template_success(self) -> None:
        provider = BrevoSyncProvider()
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(204),
        ):
            result = await provider.delete_template("1", CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self) -> None:
        provider = BrevoSyncProvider()
        with patch(
            "app.connectors.brevo.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            result = await provider.delete_template("missing", CREDS)
        assert result is False
