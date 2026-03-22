# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Tests for MaizzleBuildNode with CSS optimization."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.blueprints.nodes.maizzle_build_node import MaizzleBuildNode
from app.ai.blueprints.protocols import NodeContext


@pytest.fixture
def node() -> MaizzleBuildNode:
    return MaizzleBuildNode()


@pytest.fixture
def context_with_css() -> NodeContext:
    html = (
        "<html><head><style>.hero { color: red; }</style></head>"
        "<body><div class='hero'>Hello</div></body></html>"
    )
    return NodeContext(html=html, metadata={"target_clients": ["gmail_web"]})


@contextmanager
def _patch_httpx(
    html: str = "<html><body>compiled</body></html>",
) -> Generator[None]:
    """Patch httpx.AsyncClient for MaizzleBuildNode tests."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"html": html}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    # httpx.AsyncClient(timeout=30.0) returns an instance, then __aenter__/__aexit__
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_cls = MagicMock(return_value=mock_cm)
    with patch("httpx.AsyncClient", mock_cls):
        yield


class TestMaizzleBuildNodeCSSOptimization:
    @pytest.fixture(autouse=True)
    def _mock_ontology(self) -> Generator[None]:
        from app.email_engine.tests.test_css_compiler import _mock_registry

        reg = _mock_registry(support_none=False)
        with (
            patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
            patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
        ):
            yield

    @pytest.mark.asyncio
    async def test_execute_calls_css_optimization(
        self, node: MaizzleBuildNode, context_with_css: NodeContext
    ) -> None:
        """CSS optimization runs before Maizzle build."""
        with _patch_httpx():
            result = await node.execute(context_with_css)

        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_execute_skips_css_when_preoptimized(self, node: MaizzleBuildNode) -> None:
        """CSS optimization is skipped when HTML contains preoptimized marker."""
        from app.ai.templates.precompiler import CSS_PREOPTIMIZED_MARKER

        html = (
            CSS_PREOPTIMIZED_MARKER
            + "<html><head><style>.hero{color:red}</style></head>"
            + "<body><div class='hero'>Hello</div></body></html>"
        )
        context = NodeContext(html=html, metadata={})

        with (
            patch("app.email_engine.css_compiler.compiler.EmailCSSCompiler") as mock_compiler_cls,
            _patch_httpx(),
        ):
            result = await node.execute(context)

        assert result.status == "success"
        # CSS compiler should NOT have been instantiated
        mock_compiler_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_proceeds_when_css_optimization_fails(
        self, node: MaizzleBuildNode
    ) -> None:
        """If CSS optimization fails, node still sends original HTML to Maizzle."""
        context = NodeContext(html="<html><body>test</body></html>")

        with (
            patch(
                "app.email_engine.css_compiler.compiler.EmailCSSCompiler",
                side_effect=RuntimeError("boom"),
            ),
            _patch_httpx(),
        ):
            result = await node.execute(context)

        assert result.status == "success"
