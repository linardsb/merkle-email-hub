"""Tests for Maizzle passthrough flag propagation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.email_engine.schemas import BuildResponse, PreviewResponse
from app.email_engine.service import EmailEngineService


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _mock_httpx_response(*, passthrough: bool, html: str = "<html></html>") -> MagicMock:
    """Create a mock httpx response with the given passthrough flag."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "html": html,
        "build_time_ms": 42,
        "passthrough": passthrough,
        "optimization": {"removed_properties": [], "conversions": [], "warnings": []},
    }
    return resp


class TestPassthroughPropagation:
    """Verify passthrough flag flows from sidecar response to Python schemas."""

    @pytest.mark.asyncio
    async def test_call_builder_returns_passthrough_true(self, mock_db: AsyncMock) -> None:
        service = EmailEngineService(mock_db)
        mock_resp = _mock_httpx_response(passthrough=True)

        with patch("app.email_engine.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            _html, _opt, passthrough = await service._call_builder("src", None, False)
            assert passthrough is True

    @pytest.mark.asyncio
    async def test_call_builder_returns_passthrough_false(self, mock_db: AsyncMock) -> None:
        service = EmailEngineService(mock_db)
        mock_resp = _mock_httpx_response(passthrough=False)

        with patch("app.email_engine.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            _html, _opt, passthrough = await service._call_builder("src", None, False)
            assert passthrough is False

    @pytest.mark.asyncio
    async def test_call_builder_missing_passthrough_defaults_false(
        self, mock_db: AsyncMock
    ) -> None:
        service = EmailEngineService(mock_db)
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"html": "<html></html>", "build_time_ms": 10}

        with patch("app.email_engine.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            _html, _opt, passthrough = await service._call_builder("src", None, False)
            assert passthrough is False

    def test_preview_response_schema_has_passthrough(self) -> None:
        resp = PreviewResponse(compiled_html="<html></html>", build_time_ms=10.0, passthrough=True)
        assert resp.passthrough is True

    def test_preview_response_schema_defaults_false(self) -> None:
        resp = PreviewResponse(compiled_html="<html></html>", build_time_ms=10.0)
        assert resp.passthrough is False

    def test_build_response_schema_has_passthrough(self) -> None:
        resp = BuildResponse(
            id=1,
            project_id=1,
            template_name="test",
            status="success",
            is_production=False,
            passthrough=True,
            created_at="2026-01-01T00:00:00Z",
        )
        assert resp.passthrough is True

    def test_build_response_schema_defaults_false(self) -> None:
        resp = BuildResponse(
            id=1,
            project_id=1,
            template_name="test",
            status="success",
            is_production=False,
            created_at="2026-01-01T00:00:00Z",
        )
        assert resp.passthrough is False
