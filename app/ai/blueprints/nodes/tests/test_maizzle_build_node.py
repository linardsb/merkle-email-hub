# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Tests for MaizzleBuildNode with consolidated sidecar CSS pipeline."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.ai.blueprints.nodes.maizzle_build_node import MaizzleBuildNode
from app.ai.blueprints.protocols import NodeContext


@pytest.fixture
def node() -> MaizzleBuildNode:
    return MaizzleBuildNode()


@contextmanager
def _patch_httpx(
    html: str = "<html><body>compiled</body></html>",
    optimization: dict[str, object] | None = None,
) -> Generator[MagicMock]:
    response_data: dict[str, object] = {"html": html}
    if optimization is not None:
        response_data["optimization"] = optimization

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", MagicMock(return_value=mock_cm)):
        yield mock_client


class TestMaizzleBuildNodeConsolidatedPipeline:
    @pytest.mark.asyncio
    async def test_passes_target_clients_to_sidecar(self, node: MaizzleBuildNode) -> None:
        ctx = NodeContext(
            html="<html><head><style>.h{color:red}</style></head><body>Hi</body></html>",
            metadata={"target_clients": ["gmail_web"]},
        )
        with _patch_httpx(
            optimization={
                "removed_properties": [],
                "conversions": [],
                "warnings": [],
                "original_css_size": 50,
                "optimized_css_size": 40,
            }
        ) as mock:
            result = await node.execute(ctx)
        assert result.status == "success"
        payload = mock.post.call_args.kwargs.get("json") or mock.post.call_args[1]["json"]
        assert payload["target_clients"] == ["gmail_web"]

    @pytest.mark.asyncio
    async def test_skips_target_clients_when_preoptimized(self, node: MaizzleBuildNode) -> None:
        from app.ai.templates.precompiler import CSS_PREOPTIMIZED_MARKER

        html = CSS_PREOPTIMIZED_MARKER + "<html><body>Hi</body></html>"
        ctx = NodeContext(html=html, metadata={"target_clients": ["gmail_web"]})
        with _patch_httpx() as mock:
            result = await node.execute(ctx)
        assert result.status == "success"
        payload = mock.post.call_args.kwargs.get("json") or mock.post.call_args[1]["json"]
        assert "target_clients" not in payload
        assert CSS_PREOPTIMIZED_MARKER not in payload["source"]

    @pytest.mark.asyncio
    async def test_omits_target_clients_when_not_in_metadata(self, node: MaizzleBuildNode) -> None:
        ctx = NodeContext(html="<html><body>test</body></html>")
        with _patch_httpx() as mock:
            result = await node.execute(ctx)
        assert result.status == "success"
        payload = mock.post.call_args.kwargs.get("json") or mock.post.call_args[1]["json"]
        assert "target_clients" not in payload

    @pytest.mark.asyncio
    async def test_handles_response_without_optimization(self, node: MaizzleBuildNode) -> None:
        ctx = NodeContext(html="<html><body>test</body></html>")
        with _patch_httpx():
            result = await node.execute(ctx)
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_fails_on_empty_html(self, node: MaizzleBuildNode) -> None:
        result = await node.execute(NodeContext(html=""))
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_fails_on_sidecar_connect_error(self, node: MaizzleBuildNode) -> None:
        ctx = NodeContext(html="<html><body>test</body></html>")
        mock_cm = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with patch("httpx.AsyncClient", MagicMock(return_value=mock_cm)):
            result = await node.execute(ctx)
        assert result.status == "failed"
        assert "unavailable" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_fails_on_sidecar_http_error(self, node: MaizzleBuildNode) -> None:
        ctx = NodeContext(html="<html><body>test</body></html>")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with patch("httpx.AsyncClient", MagicMock(return_value=mock_cm)):
            result = await node.execute(ctx)
        assert result.status == "failed"
        assert "500" in (result.error or "")
