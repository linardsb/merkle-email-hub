# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Integration tests for the visual QA feedback loop pipeline (Phase 32.8).

Tests the full data flow: VisualPrecheckNode → QAGateNode → RecoveryRouterNode,
verifying that visual defects propagate correctly through the pipeline and that
multimodal context (screenshots) reaches the fixer agent.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.visual_qa.schemas import VisualComparisonResult
from app.ai.blueprints.nodes.recovery_router_node import RecoveryRouterNode
from app.ai.blueprints.nodes.visual_comparison_node import VisualComparisonNode
from app.ai.blueprints.nodes.visual_precheck_node import VisualPrecheckNode
from app.ai.blueprints.protocols import NodeContext, StructuredFailure
from app.qa_engine.schemas import QAVisualDefect

# Minimal valid PNG (1x1 transparent)
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _make_precheck_settings(*, precheck: bool = True, top_clients: int = 3) -> MagicMock:
    s = MagicMock()
    s.blueprint.visual_qa_precheck = precheck
    s.blueprint.visual_precheck_top_clients = top_clients
    return s


def _make_comparison_settings(*, comparison: bool = True, threshold: float = 5.0) -> MagicMock:
    s = MagicMock()
    s.blueprint.visual_comparison = comparison
    s.blueprint.visual_comparison_threshold = threshold
    return s


class TestPrecheckToQAGatePipeline:
    """Tests that precheck defects flow correctly into the QA gate merge."""

    @pytest.mark.asyncio()
    async def test_precheck_defects_stored_for_qa_gate(self) -> None:
        """Precheck stores failure dicts in metadata for QAGateNode to merge."""
        node = VisualPrecheckNode()
        metadata: dict[str, object] = {}
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        defect = QAVisualDefect(
            type="layout_collapse",
            severity="high",
            client_id="outlook_2019",
            description="Hero section collapses",
            suggested_agent="outlook_fixer",
        )
        mock_service = AsyncMock()
        mock_service.detect_defects_lightweight = AsyncMock(return_value=[defect])

        with (
            patch("app.core.config.get_settings", return_value=_make_precheck_settings()),
            patch.object(node, "_render_screenshots", return_value={"outlook_2019": _TINY_PNG_B64}),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "failed"

        # Verify metadata contains serialized failures for QA gate
        assert "visual_precheck_failures" in metadata
        raw = metadata["visual_precheck_failures"]
        assert isinstance(raw, list)
        assert len(raw) == 1
        first: dict[str, object] = raw[0]
        assert first["check_name"] == "visual_defect:outlook_2019"
        assert first["suggested_agent"] == "outlook_fixer"

    @pytest.mark.asyncio()
    async def test_precheck_screenshots_available_for_recovery(self) -> None:
        """Precheck stores screenshots so recovery router can inject them."""
        node = VisualPrecheckNode()
        metadata: dict[str, object] = {}
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        mock_service = AsyncMock()
        mock_service.detect_defects_lightweight = AsyncMock(return_value=[])
        expected_screenshots = {"gmail_web": _TINY_PNG_B64, "outlook_2019": _TINY_PNG_B64}

        with (
            patch("app.core.config.get_settings", return_value=_make_precheck_settings()),
            patch.object(node, "_render_screenshots", return_value=expected_screenshots),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            await node.execute(ctx)

        # Screenshots must be in metadata for recovery router
        assert metadata.get("precheck_screenshots") == expected_screenshots


class TestRecoveryRouterVisualContext:
    """Tests that recovery router injects multimodal context for visual defects."""

    @pytest.mark.asyncio()
    async def test_fixer_receives_screenshot_via_override(self) -> None:
        """When routing a visual defect, screenshots are injected as multimodal override."""
        node = RecoveryRouterNode()

        structured = [
            StructuredFailure(
                check_name="visual_defect:gmail_web",
                score=0.3,
                details="Dark mode inverts logo",
                suggested_agent="dark_mode",
                priority=0,
                severity="high",
            )
        ]
        metadata: dict[str, object] = {
            "qa_failure_details": structured,
            "precheck_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        result = await node.execute(ctx)

        assert "route_to:dark_mode" in result.details
        # Screenshot should be injected as multimodal override
        assert "multimodal_context_override" in metadata

    @pytest.mark.asyncio()
    async def test_non_visual_failure_no_screenshot_injection(self) -> None:
        """Standard QA failures (non-visual) don't get multimodal context."""
        node = RecoveryRouterNode()

        structured = [
            StructuredFailure(
                check_name="css_support",
                score=0.2,
                details="Unsupported CSS property",
                suggested_agent="scaffolder",
                priority=1,
                severity="high",
            )
        ]
        metadata: dict[str, object] = {
            "qa_failure_details": structured,
            "precheck_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        result = await node.execute(ctx)

        assert "route_to:scaffolder" in result.details
        # No multimodal override for non-visual failures
        assert "multimodal_context_override" not in metadata


class TestComparisonThresholds:
    """Tests that comparison drift scores are correctly stored for BuildResponse."""

    @pytest.mark.asyncio()
    async def test_below_threshold_no_regression_flag(self) -> None:
        node = VisualComparisonNode()
        metadata: dict[str, object] = {
            "original_screenshots": {"gmail_web": _TINY_PNG_B64},
            "precheck_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        mock_service = AsyncMock()
        mock_service.compare_screenshots = AsyncMock(
            return_value=VisualComparisonResult(drift_score=3.0)
        )

        with (
            patch("app.core.config.get_settings", return_value=_make_comparison_settings()),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "success"
        stored = metadata.get("visual_comparison")
        assert isinstance(stored, dict)
        assert stored["drift_score"] == 3.0
        assert stored["regressed"] is False

    @pytest.mark.asyncio()
    async def test_above_threshold_includes_description(self) -> None:
        node = VisualComparisonNode()
        metadata: dict[str, object] = {
            "original_screenshots": {"gmail_web": _TINY_PNG_B64},
            "precheck_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        mock_service = AsyncMock()
        mock_service.compare_screenshots = AsyncMock(
            return_value=VisualComparisonResult(
                drift_score=8.5,
                semantic_description="CTA button shifted 12px right",
            )
        )

        with (
            patch("app.core.config.get_settings", return_value=_make_comparison_settings()),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "success"
        assert "8.5%" in result.details
        assert "CTA button" in result.details


class TestFeatureGatesOff:
    """Tests that the pipeline integration is unaffected when visual gates are off.

    Note: individual node gate-off behaviour is tested in
    test_visual_precheck.py::test_skipped_when_disabled and
    test_visual_comparison.py::test_skipped_when_disabled.
    This class tests that disabling gates has no side effects on shared metadata.
    """

    @pytest.mark.asyncio()
    async def test_precheck_gate_off_leaves_metadata_clean(self) -> None:
        """Disabled precheck must not write precheck_screenshots or failures to metadata."""
        node = VisualPrecheckNode()
        metadata: dict[str, object] = {}
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        with patch(
            "app.core.config.get_settings",
            return_value=_make_precheck_settings(precheck=False),
        ):
            await node.execute(ctx)

        assert "precheck_screenshots" not in metadata
        assert "visual_precheck_failures" not in metadata

    @pytest.mark.asyncio()
    async def test_comparison_gate_off_leaves_metadata_clean(self) -> None:
        """Disabled comparison must not write visual_comparison to metadata."""
        node = VisualComparisonNode()
        metadata: dict[str, object] = {
            "original_screenshots": {"gmail_web": _TINY_PNG_B64},
        }
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        with patch(
            "app.core.config.get_settings",
            return_value=_make_comparison_settings(comparison=False),
        ):
            await node.execute(ctx)

        assert "visual_comparison" not in metadata
