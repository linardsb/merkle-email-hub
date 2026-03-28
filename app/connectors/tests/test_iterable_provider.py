# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Unit tests for IterableSyncProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.connectors.iterable.sync_provider import IterableSyncProvider
from app.connectors.sync_protocol import ESPSyncProvider
from app.connectors.sync_schemas import ESPTemplate

# ── Helpers ──

CREDS = {"api_key": "iter_test_key_1234567890"}


def _mock_response(status_code: int = 200, json_data: dict | list | None = None) -> httpx.Response:  # type: ignore[type-arg]
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "http://test"),
    )


def _make_template(
    id: str = "100",
    name: str = "Welcome Email",
    html: str = "<table><tr><td>Hello</td></tr></table>",
) -> dict[str, object]:
    """Create an Iterable email template object."""
    return {
        "templateId": int(id),
        "name": name,
        "html": html,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-15T12:00:00Z",
    }


# ── Protocol Conformance ──


class TestIterableProtocol:
    def test_protocol_conformance(self) -> None:
        assert isinstance(IterableSyncProvider(), ESPSyncProvider)

    def test_base_url_from_settings(self) -> None:
        provider = IterableSyncProvider()
        assert "iterable" in provider._base_url


# ── Auth Headers ──


class TestIterableHeaders:
    def test_headers_auth_format(self) -> None:
        provider = IterableSyncProvider()
        headers = provider._headers(CREDS)
        assert headers["Api-Key"] == "iter_test_key_1234567890"


# ── Validate Credentials ──


class TestIterableValidateCredentials:
    @pytest.mark.asyncio
    async def test_validate_credentials_success(self) -> None:
        provider = IterableSyncProvider()
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"user": {}}),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_bad_email_still_valid(self) -> None:
        """400 (no such user) still means API key is valid."""
        provider = IterableSyncProvider()
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(400, {"msg": "No user"}),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_invalid(self) -> None:
        provider = IterableSyncProvider()
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(401),
        ):
            result = await provider.validate_credentials(CREDS)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_credentials_missing_key(self) -> None:
        provider = IterableSyncProvider()
        with pytest.raises(KeyError):
            await provider.validate_credentials({})


# ── List Templates ──


class TestIterableListTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_empty(self) -> None:
        provider = IterableSyncProvider()
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, {"templates": []}),
        ):
            result = await provider.list_templates(CREDS)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_templates_success(self) -> None:
        provider = IterableSyncProvider()
        json_data = {
            "templates": [
                _make_template("100", "Welcome"),
                _make_template("200", "Goodbye"),
            ]
        }
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            result = await provider.list_templates(CREDS)
        assert len(result) == 2
        assert result[0].id == "100"
        assert result[0].esp_type == "iterable"


# ── Get Template ──


class TestIterableGetTemplate:
    @pytest.mark.asyncio
    async def test_get_template_success(self) -> None:
        provider = IterableSyncProvider()
        json_data = _make_template("55", "Footer")
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ):
            tpl = await provider.get_template("55", CREDS)
        assert tpl.id == "55"
        assert tpl.name == "Footer"
        assert isinstance(tpl, ESPTemplate)

    @pytest.mark.asyncio
    async def test_get_template_not_found(self) -> None:
        provider = IterableSyncProvider()
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.get_template("missing", CREDS)


# ── Create Template (upsert without templateId) ──


class TestIterableCreateTemplate:
    @pytest.mark.asyncio
    async def test_create_template_success(self) -> None:
        provider = IterableSyncProvider()
        json_data = _make_template("999", "New Email", "<table></table>")
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ) as mock_req:
            tpl = await provider.create_template("New Email", "<table></table>", CREDS)

        assert tpl.name == "New Email"
        call_kwargs = mock_req.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        # Upsert create should NOT include templateId
        assert "templateId" not in payload
        assert payload["name"] == "New Email"


# ── Update Template (upsert with templateId) ──


class TestIterableUpdateTemplate:
    @pytest.mark.asyncio
    async def test_update_template_success(self) -> None:
        provider = IterableSyncProvider()
        json_data = _make_template("100", "Welcome", "<table>Updated</table>")
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200, json_data),
        ) as mock_req:
            tpl = await provider.update_template("100", "<table>Updated</table>", CREDS)
        assert tpl.id == "100"
        assert tpl.html == "<table>Updated</table>"
        # Upsert update should include templateId
        call_kwargs = mock_req.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["templateId"] == 100

    @pytest.mark.asyncio
    async def test_update_template_not_found(self) -> None:
        provider = IterableSyncProvider()
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.update_template("999", "<table></table>", CREDS)

    @pytest.mark.asyncio
    async def test_update_template_non_numeric_id_raises(self) -> None:
        provider = IterableSyncProvider()
        with pytest.raises(ValueError, match="numeric"):
            await provider.update_template("abc", "<table></table>", CREDS)


# ── Delete Template ──


class TestIterableDeleteTemplate:
    @pytest.mark.asyncio
    async def test_delete_template_success(self) -> None:
        provider = IterableSyncProvider()
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(200),
        ):
            result = await provider.delete_template("100", CREDS)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self) -> None:
        provider = IterableSyncProvider()
        with patch(
            "app.connectors.iterable.sync_provider.resilient_request",
            new_callable=AsyncMock,
            return_value=_mock_response(404),
        ):
            result = await provider.delete_template("missing", CREDS)
        assert result is False
