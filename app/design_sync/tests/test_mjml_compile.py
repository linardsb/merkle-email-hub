"""Tests for MJML compilation via Maizzle sidecar."""

from __future__ import annotations

from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.design_sync.converter_service import (
    DesignConverterService,
    MjmlCompileResult,
    MjmlError,
)
from app.design_sync.exceptions import MjmlCompileError

VALID_MJML = (
    "<mjml><mj-body><mj-section><mj-column>"
    "<mj-text>Hello</mj-text>"
    "</mj-column></mj-section></mj-body></mjml>"
)

MOCK_SETTINGS_PATH = "app.design_sync.converter_service.get_settings"
MOCK_HTTPX_PATH = "app.design_sync.converter_service.httpx.AsyncClient"


def _mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.maizzle_builder_url = "http://localhost:3001"
    return settings


def _mock_httpx_response(
    *,
    html: str = "<html><body><table></table></body></html>",
    errors: list[dict[str, Any]] | None = None,
    build_time_ms: float = 42.0,
    optimization: dict[str, Any] | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    data: dict[str, Any] = {
        "html": html,
        "errors": errors or [],
        "build_time_ms": build_time_ms,
    }
    if optimization is not None:
        data["optimization"] = optimization
    resp.json.return_value = data
    return resp


def _patch_httpx(mock_resp: MagicMock) -> AbstractContextManager[AsyncMock]:
    """Return a context manager that mocks httpx.AsyncClient for the sidecar call."""
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp

    patcher = patch(MOCK_HTTPX_PATH)

    class _Ctx(AbstractContextManager[AsyncMock]):
        def __enter__(self) -> AsyncMock:
            mock_cls = patcher.__enter__()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            return mock_client

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            patcher.__exit__(exc_type, exc_val, exc_tb)

    return _Ctx()


class TestCompileMjmlSuccess:
    @pytest.mark.asyncio
    async def test_returns_compile_result(self) -> None:
        resp = _mock_httpx_response(html="<html><table>OK</table></html>")
        with patch(MOCK_SETTINGS_PATH, return_value=_mock_settings()), _patch_httpx(resp) as client:
            service = DesignConverterService()
            result = await service.compile_mjml(VALID_MJML)

        assert isinstance(result, MjmlCompileResult)
        assert "<table>OK</table>" in result.html
        assert result.errors == []
        assert result.build_time_ms == 42.0
        assert result.optimization is None
        client.post.assert_called_once()
        call_kwargs = client.post.call_args
        assert "/compile-mjml" in call_kwargs.args[0]

    @pytest.mark.asyncio
    async def test_parses_mjml_errors(self) -> None:
        errors = [
            {"line": 5, "message": "Unknown element mj-bad", "tagName": "mj-bad"},
            {"line": 10, "message": "Missing attr", "tagName": "mj-text"},
        ]
        resp = _mock_httpx_response(errors=errors)
        with patch(MOCK_SETTINGS_PATH, return_value=_mock_settings()), _patch_httpx(resp):
            service = DesignConverterService()
            result = await service.compile_mjml(VALID_MJML)

        assert len(result.errors) == 2
        assert isinstance(result.errors[0], MjmlError)
        assert result.errors[0].line == 5
        assert result.errors[0].message == "Unknown element mj-bad"
        assert result.errors[0].tag_name == "mj-bad"

    @pytest.mark.asyncio
    async def test_passes_target_clients_in_payload(self) -> None:
        resp = _mock_httpx_response()
        with patch(MOCK_SETTINGS_PATH, return_value=_mock_settings()), _patch_httpx(resp) as client:
            service = DesignConverterService()
            await service.compile_mjml(VALID_MJML, target_clients=["gmail_web", "outlook_2021"])

        payload = client.post.call_args.kwargs["json"]
        assert payload["target_clients"] == ["gmail_web", "outlook_2021"]

    @pytest.mark.asyncio
    async def test_omits_target_clients_when_none(self) -> None:
        resp = _mock_httpx_response()
        with patch(MOCK_SETTINGS_PATH, return_value=_mock_settings()), _patch_httpx(resp) as client:
            service = DesignConverterService()
            await service.compile_mjml(VALID_MJML)

        payload = client.post.call_args.kwargs["json"]
        assert "target_clients" not in payload

    @pytest.mark.asyncio
    async def test_includes_optimization_when_present(self) -> None:
        opt = {"removed_properties": ["flex"], "conversions": [], "warnings": []}
        resp = _mock_httpx_response(optimization=opt)
        with patch(MOCK_SETTINGS_PATH, return_value=_mock_settings()), _patch_httpx(resp):
            service = DesignConverterService()
            result = await service.compile_mjml(VALID_MJML, target_clients=["gmail_web"])

        assert result.optimization is not None
        assert result.optimization["removed_properties"] == ["flex"]


class TestCompileMjmlErrors:
    @pytest.mark.asyncio
    async def test_connect_error_raises_mjml_compile_error(self) -> None:
        with (
            patch(MOCK_SETTINGS_PATH, return_value=_mock_settings()),
            patch(MOCK_HTTPX_PATH) as mock_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            service = DesignConverterService()
            with pytest.raises(MjmlCompileError, match="Cannot connect"):
                await service.compile_mjml(VALID_MJML)

    @pytest.mark.asyncio
    async def test_http_500_raises_mjml_compile_error(self) -> None:
        with (
            patch(MOCK_SETTINGS_PATH, return_value=_mock_settings()),
            patch(MOCK_HTTPX_PATH) as mock_cls,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.request = MagicMock()
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=mock_response
            )
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            service = DesignConverterService()
            with pytest.raises(MjmlCompileError, match="MJML compilation failed"):
                await service.compile_mjml(VALID_MJML)

    @pytest.mark.asyncio
    async def test_invalid_json_response_raises_mjml_compile_error(self) -> None:
        with (
            patch(MOCK_SETTINGS_PATH, return_value=_mock_settings()),
            patch(MOCK_HTTPX_PATH) as mock_cls,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            service = DesignConverterService()
            with pytest.raises(MjmlCompileError, match="Invalid response"):
                await service.compile_mjml(VALID_MJML)
