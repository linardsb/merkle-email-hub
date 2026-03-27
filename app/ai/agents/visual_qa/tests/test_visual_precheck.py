"""Tests for VisualPrecheckNode — pre-QA VLM screenshot analysis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.blueprints.nodes.visual_precheck_node import VisualPrecheckNode
from app.ai.blueprints.protocols import NodeContext
from app.qa_engine.schemas import QAVisualDefect

# Minimal valid PNG (1x1 transparent)
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _make_settings(*, precheck: bool = True, top_clients: int = 3) -> MagicMock:
    s = MagicMock()
    s.blueprint.visual_qa_precheck = precheck
    s.blueprint.visual_precheck_top_clients = top_clients
    return s


class TestVisualPrecheckNode:
    @pytest.mark.asyncio()
    async def test_skipped_when_disabled(self) -> None:
        node = VisualPrecheckNode()
        ctx = NodeContext(html="<p>test</p>")
        with patch(
            "app.core.config.get_settings",
            return_value=_make_settings(precheck=False),
        ):
            result = await node.execute(ctx)
        assert result.status == "skipped"
        assert "disabled" in result.details

    @pytest.mark.asyncio()
    async def test_skipped_no_html(self) -> None:
        node = VisualPrecheckNode()
        ctx = NodeContext(html="")
        with patch(
            "app.core.config.get_settings",
            return_value=_make_settings(),
        ):
            result = await node.execute(ctx)
        assert result.status == "skipped"

    @pytest.mark.asyncio()
    async def test_no_defects_returns_success(self) -> None:
        node = VisualPrecheckNode()
        ctx = NodeContext(html="<p>test</p>", metadata={})

        mock_service = AsyncMock()
        mock_service.detect_defects_lightweight = AsyncMock(return_value=[])

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch.object(node, "_render_screenshots", return_value={"gmail_web": _TINY_PNG_B64}),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "success"
        assert "passed" in result.details

    @pytest.mark.asyncio()
    async def test_high_severity_defect_returns_failure(self) -> None:
        node = VisualPrecheckNode()
        ctx = NodeContext(html="<p>test</p>", metadata={})

        defect = QAVisualDefect(
            type="layout_collapse",
            severity="critical",
            client_id="outlook_2019",
            description="Hero section collapses in Outlook",
            suggested_agent="outlook_fixer",
        )
        mock_service = AsyncMock()
        mock_service.detect_defects_lightweight = AsyncMock(return_value=[defect])

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch.object(node, "_render_screenshots", return_value={"outlook_2019": _TINY_PNG_B64}),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "failed"
        assert result.structured_failures
        sf = result.structured_failures[0]
        assert sf.check_name == "visual_defect:outlook_2019"
        assert sf.suggested_agent == "outlook_fixer"
        assert sf.priority == 0

    @pytest.mark.asyncio()
    async def test_screenshots_stored_in_metadata(self) -> None:
        node = VisualPrecheckNode()
        metadata: dict[str, object] = {}
        ctx = NodeContext(html="<p>test</p>", metadata=metadata)

        mock_service = AsyncMock()
        mock_service.detect_defects_lightweight = AsyncMock(return_value=[])
        screenshots = {"gmail_web": _TINY_PNG_B64, "outlook_2019": _TINY_PNG_B64}

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch.object(node, "_render_screenshots", return_value=screenshots),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            await node.execute(ctx)

        assert metadata.get("precheck_screenshots") == screenshots

    @pytest.mark.asyncio()
    async def test_multiple_clients_multiple_defects(self) -> None:
        node = VisualPrecheckNode()
        ctx = NodeContext(html="<p>test</p>", metadata={})

        defects = [
            QAVisualDefect(
                type="layout_collapse",
                severity="critical",
                client_id="outlook_2019",
                description="Layout broken",
                suggested_agent="outlook_fixer",
            ),
            QAVisualDefect(
                type="dark_mode_inversion",
                severity="high",
                client_id="gmail_web",
                description="Dark mode inverts logo",
                suggested_agent="dark_mode",
            ),
            QAVisualDefect(
                type="minor_spacing",
                severity="low",
                client_id="apple_mail",
                description="Minor padding difference",
            ),
        ]
        mock_service = AsyncMock()
        mock_service.detect_defects_lightweight = AsyncMock(return_value=defects)

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch.object(
                node,
                "_render_screenshots",
                return_value={
                    "outlook_2019": _TINY_PNG_B64,
                    "gmail_web": _TINY_PNG_B64,
                    "apple_mail": _TINY_PNG_B64,
                },
            ),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                return_value=mock_service,
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "failed"
        # Only high/critical become structured failures
        assert len(result.structured_failures) == 2

    @pytest.mark.asyncio()
    async def test_rendering_service_failure_graceful(self) -> None:
        node = VisualPrecheckNode()
        ctx = NodeContext(html="<p>test</p>", metadata={})

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch.object(node, "_render_screenshots", side_effect=RuntimeError("render failed")),
        ):
            result = await node.execute(ctx)

        assert result.status == "skipped"
        assert "rendering failed" in result.details

    @pytest.mark.asyncio()
    async def test_vlm_failure_graceful(self) -> None:
        node = VisualPrecheckNode()
        ctx = NodeContext(html="<p>test</p>", metadata={})

        with (
            patch(
                "app.core.config.get_settings",
                return_value=_make_settings(),
            ),
            patch.object(node, "_render_screenshots", return_value={"gmail_web": _TINY_PNG_B64}),
            patch(
                "app.ai.agents.visual_qa.service.get_visual_qa_service",
                side_effect=RuntimeError("VLM down"),
            ),
        ):
            result = await node.execute(ctx)

        assert result.status == "skipped"
        assert "VLM" in result.details

    @pytest.mark.asyncio()
    async def test_node_metadata(self) -> None:
        node = VisualPrecheckNode()
        assert node.name == "visual_precheck"
        assert node.node_type == "deterministic"
