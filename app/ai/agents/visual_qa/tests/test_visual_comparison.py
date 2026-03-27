"""Tests for VisualComparisonNode — post-build screenshot comparison."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.visual_qa.schemas import VisualComparisonResult
from app.ai.blueprints.nodes.visual_comparison_node import VisualComparisonNode
from app.ai.blueprints.protocols import NodeContext

_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _make_settings(*, comparison: bool = True, threshold: float = 5.0) -> MagicMock:
    s = MagicMock()
    s.blueprint.visual_comparison = comparison
    s.blueprint.visual_comparison_threshold = threshold
    return s


class TestVisualComparisonNode:
    @pytest.mark.asyncio()
    async def test_skipped_when_disabled(self) -> None:
        node = VisualComparisonNode()
        ctx = NodeContext(html="<p>test</p>")
        with patch(
            "app.core.config.get_settings",
            return_value=_make_settings(comparison=False),
        ):
            result = await node.execute(ctx)
        assert result.status == "skipped"
        assert "disabled" in result.details

    @pytest.mark.asyncio()
    async def test_skipped_no_original_screenshots(self) -> None:
        node = VisualComparisonNode()
        ctx = NodeContext(html="<p>test</p>", metadata={})
        with patch(
            "app.core.config.get_settings",
            return_value=_make_settings(),
        ):
            result = await node.execute(ctx)
        assert result.status == "skipped"
        assert "no original" in result.details

    @pytest.mark.asyncio()
    async def test_low_drift_advisory(self) -> None:
        node = VisualComparisonNode()
        metadata: dict[str, object] = {
            "original_screenshots": {"gmail_web": _TINY_PNG_B64},
            "precheck_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        comparison_result = VisualComparisonResult(drift_score=2.1)
        mock_service = AsyncMock()
        mock_service.compare_screenshots = AsyncMock(return_value=comparison_result)

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "success"
        assert "2.1%" in result.details

    @pytest.mark.asyncio()
    async def test_high_drift_warning(self) -> None:
        node = VisualComparisonNode()
        metadata: dict[str, object] = {
            "original_screenshots": {"gmail_web": _TINY_PNG_B64},
            "precheck_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        comparison_result = VisualComparisonResult(
            drift_score=12.5,
            semantic_description="Hero padding increased by ~8px",
        )
        mock_service = AsyncMock()
        mock_service.compare_screenshots = AsyncMock(return_value=comparison_result)

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "success"
        assert "12.5%" in result.details
        assert "Hero padding" in result.details

    @pytest.mark.asyncio()
    async def test_regression_detection(self) -> None:
        node = VisualComparisonNode()
        metadata: dict[str, object] = {
            "original_screenshots": {"gmail_web": _TINY_PNG_B64},
            "precheck_screenshots": {"gmail_web": _TINY_PNG_B64},
            "prev_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata, iteration=1)

        # Current drift = 8%, previous drift = 3% → regression
        current_result = VisualComparisonResult(drift_score=8.0)
        prev_result = VisualComparisonResult(drift_score=3.0)

        mock_service = AsyncMock()
        mock_service.compare_screenshots = AsyncMock(side_effect=[current_result, prev_result])

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "success"
        assert "REGRESSED" in result.details

    @pytest.mark.asyncio()
    async def test_odiff_failure_graceful(self) -> None:
        node = VisualComparisonNode()
        metadata: dict[str, object] = {
            "original_screenshots": {"gmail_web": _TINY_PNG_B64},
            "precheck_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                side_effect=RuntimeError("ODiff not found"),
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "skipped"
        assert "comparison failed" in result.details

    @pytest.mark.asyncio()
    async def test_result_stored_in_metadata(self) -> None:
        node = VisualComparisonNode()
        metadata: dict[str, object] = {
            "original_screenshots": {"gmail_web": _TINY_PNG_B64},
            "precheck_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        comparison_result = VisualComparisonResult(drift_score=1.5)
        mock_service = AsyncMock()
        mock_service.compare_screenshots = AsyncMock(return_value=comparison_result)

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            await node.execute(ctx)

        assert "visual_comparison" in metadata
        assert metadata["visual_comparison"]["drift_score"] == 1.5

    @pytest.mark.asyncio()
    async def test_node_metadata(self) -> None:
        node = VisualComparisonNode()
        assert node.name == "visual_comparison"
        assert node.node_type == "deterministic"
