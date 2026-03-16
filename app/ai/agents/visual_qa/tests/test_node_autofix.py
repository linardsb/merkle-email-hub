"""Tests for VisualQANode auto-fix orchestration (Phase 17.4)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.blueprints.nodes.visual_qa_node import VisualQANode
from app.ai.blueprints.protocols import NodeContext

MINIMAL_HTML = "<html><body><table><tr><td>Test</td></tr></table></body></html>"
FIXED_HTML = "<html><body><table><tr><td>Fixed</td></tr></table></body></html>"
# Tiny 1x1 red PNG base64
TINY_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="


def _make_context(html: str = MINIMAL_HTML) -> NodeContext:
    return NodeContext(
        html=html,
        brief="Test email",
        metadata={
            "screenshots": {"gmail_web": TINY_PNG, "outlook_2019": TINY_PNG},
            "baseline_diffs": [],
        },
        iteration=0,
    )


def _make_mock_decisions(
    *,
    defects: tuple[MagicMock, ...] = (),
    auto_fixable: bool = False,
    score: float = 1.0,
) -> MagicMock:
    mock = MagicMock()
    mock.defects = defects
    mock.auto_fixable = auto_fixable
    mock.overall_rendering_score = score
    mock.critical_clients = ()
    mock.confidence = 0.8
    mock.summary = "Test"
    return mock


@pytest.mark.asyncio
async def test_autofix_disabled_skips_correction() -> None:
    """When autofix is disabled, node is advisory-only (original behavior)."""
    node = VisualQANode()
    context = _make_context()

    mock_decisions = _make_mock_decisions(defects=(MagicMock(),), auto_fixable=True, score=0.6)

    with (
        patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock_settings,
        patch("app.ai.blueprints.nodes.visual_qa_node.get_registry") as mock_reg,
        patch("app.ai.blueprints.nodes.visual_qa_node.get_visual_qa_service") as mock_svc,
        patch("app.ai.blueprints.nodes.visual_qa_node.resolve_model", return_value="gpt-4o"),
    ):
        mock_settings.return_value.ai.visual_qa_enabled = True
        mock_settings.return_value.ai.visual_qa_model = ""
        mock_settings.return_value.ai.visual_qa_autofix_enabled = False

        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_response.usage = None
        mock_provider.complete = AsyncMock(return_value=mock_response)
        mock_reg.return_value.get_llm.return_value = mock_provider

        mock_svc.return_value.parse_decisions.return_value = mock_decisions
        mock_svc.return_value.enrich_with_ontology.return_value = mock_decisions

        result = await node.execute(context)

    assert result.html == MINIMAL_HTML
    assert "auto-fixed" not in (result.details or "")


@pytest.mark.asyncio
async def test_autofix_accepted_when_score_improves() -> None:
    """Auto-fix accepted when re-analysis shows improved score."""
    node = VisualQANode()
    context = _make_context()

    mock_defect = MagicMock()
    mock_defect.region = "header"
    mock_defect.severity = "warning"
    mock_defect.description = "Broken"
    mock_defect.suggested_fix = "Fix it"
    mock_defect.css_property = "display: flex"
    mock_defect.affected_clients = ("outlook_2019",)

    mock_decisions = _make_mock_decisions(defects=(mock_defect,), auto_fixable=True, score=0.6)

    with (
        patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock_settings,
        patch("app.ai.blueprints.nodes.visual_qa_node.get_registry") as mock_reg,
        patch("app.ai.blueprints.nodes.visual_qa_node.get_visual_qa_service") as mock_svc,
        patch("app.ai.blueprints.nodes.visual_qa_node.resolve_model", return_value="gpt-4o"),
        patch(
            "app.ai.agents.visual_qa.correction.correct_visual_defects",
            return_value=(FIXED_HTML, ["header:display: flex"]),
        ),
    ):
        mock_settings.return_value.ai.visual_qa_enabled = True
        mock_settings.return_value.ai.visual_qa_model = ""
        mock_settings.return_value.ai.visual_qa_autofix_enabled = True

        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_response.usage = None
        mock_provider.complete = AsyncMock(return_value=mock_response)
        mock_reg.return_value.get_llm.return_value = mock_provider

        mock_svc.return_value.parse_decisions.return_value = mock_decisions
        mock_svc.return_value.enrich_with_ontology.return_value = mock_decisions

        with patch.object(node, "_verify_fix", return_value=0.9):
            result = await node.execute(context)

    assert result.html == FIXED_HTML
    assert "auto-fixed" in (result.details or "")


@pytest.mark.asyncio
async def test_autofix_rejected_when_score_regresses() -> None:
    """Auto-fix rejected when re-analysis shows worse or equal score."""
    node = VisualQANode()
    context = _make_context()

    mock_defect = MagicMock()
    mock_defect.region = "header"
    mock_defect.severity = "warning"
    mock_defect.description = "Broken"
    mock_defect.suggested_fix = "Fix it"
    mock_defect.css_property = "display: flex"
    mock_defect.affected_clients = ("outlook_2019",)

    mock_decisions = _make_mock_decisions(defects=(mock_defect,), auto_fixable=True, score=0.6)

    with (
        patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock_settings,
        patch("app.ai.blueprints.nodes.visual_qa_node.get_registry") as mock_reg,
        patch("app.ai.blueprints.nodes.visual_qa_node.get_visual_qa_service") as mock_svc,
        patch("app.ai.blueprints.nodes.visual_qa_node.resolve_model", return_value="gpt-4o"),
        patch(
            "app.ai.agents.visual_qa.correction.correct_visual_defects",
            return_value=(FIXED_HTML, ["header:display: flex"]),
        ),
    ):
        mock_settings.return_value.ai.visual_qa_enabled = True
        mock_settings.return_value.ai.visual_qa_model = ""
        mock_settings.return_value.ai.visual_qa_autofix_enabled = True

        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_response.usage = None
        mock_provider.complete = AsyncMock(return_value=mock_response)
        mock_reg.return_value.get_llm.return_value = mock_provider

        mock_svc.return_value.parse_decisions.return_value = mock_decisions
        mock_svc.return_value.enrich_with_ontology.return_value = mock_decisions

        # Verification returns worse score
        with patch.object(node, "_verify_fix", return_value=0.5):
            result = await node.execute(context)

    assert result.html == MINIMAL_HTML
    assert "auto-fixed" not in (result.details or "")


@pytest.mark.asyncio
async def test_autofix_skipped_when_no_defects() -> None:
    """No defects -> no correction attempted (zero cost)."""
    node = VisualQANode()
    context = _make_context()

    mock_decisions = _make_mock_decisions(defects=(), auto_fixable=False, score=1.0)

    with (
        patch("app.ai.blueprints.nodes.visual_qa_node.get_settings") as mock_settings,
        patch("app.ai.blueprints.nodes.visual_qa_node.get_registry") as mock_reg,
        patch("app.ai.blueprints.nodes.visual_qa_node.get_visual_qa_service") as mock_svc,
        patch("app.ai.blueprints.nodes.visual_qa_node.resolve_model", return_value="gpt-4o"),
    ):
        mock_settings.return_value.ai.visual_qa_enabled = True
        mock_settings.return_value.ai.visual_qa_model = ""
        mock_settings.return_value.ai.visual_qa_autofix_enabled = True

        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "{}"
        mock_response.usage = None
        mock_provider.complete = AsyncMock(return_value=mock_response)
        mock_reg.return_value.get_llm.return_value = mock_provider

        mock_svc.return_value.parse_decisions.return_value = mock_decisions
        mock_svc.return_value.enrich_with_ontology.return_value = mock_decisions

        result = await node.execute(context)

    assert result.html == MINIMAL_HTML
    assert result.status == "success"


@pytest.mark.asyncio
async def test_verify_fix_failure_returns_none() -> None:
    """Verification failure (renderer crash) -> returns None -> fix rejected."""
    node = VisualQANode()

    with patch(
        "app.ai.blueprints.nodes.visual_qa_node.LocalRenderingProvider",
        side_effect=RuntimeError("Playwright not installed"),
    ):
        score = await node._verify_fix(
            FIXED_HTML,
            {"gmail_web": TINY_PNG},
            AsyncMock(),
            "gpt-4o",
            "system",
            MagicMock(),
        )

    assert score is None
