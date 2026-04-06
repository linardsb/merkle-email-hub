# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Tests for EvaluatorNode — accept, revise, disabled passthrough."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.agents.evaluator.schemas import EvalIssue, EvaluatorResponse, EvalVerdict
from app.ai.blueprints.nodes.evaluator_node import EvaluatorNode
from app.ai.blueprints.protocols import NodeContext


@pytest.fixture
def evaluator_node() -> EvaluatorNode:
    return EvaluatorNode()


@pytest.fixture
def context_with_brief() -> NodeContext:
    return NodeContext(
        html='<table role="presentation"><tr><td>Test</td></tr></table>',
        brief="Create a promotional email",
        metadata={
            "brief": "Create a promotional email",
            "upstream_agent": "scaffolder",
        },
    )


@pytest.mark.asyncio
async def test_node_accept_passes_through(
    evaluator_node: EvaluatorNode,
    context_with_brief: NodeContext,
) -> None:
    """Evaluator accepts -> NodeResult(status='success')."""
    mock_response = EvaluatorResponse(
        verdict=EvalVerdict(
            verdict="accept",
            score=0.9,
            issues=[],
            feedback="Looks good",
        ),
        model="test:model",
        confidence=0.9,
        skills_loaded=["scaffolder"],
    )

    mock_service = AsyncMock()
    mock_service.evaluate.return_value = mock_response

    with (
        patch("app.ai.blueprints.nodes.evaluator_node.get_settings") as mock_settings,
        patch(
            "app.ai.blueprints.nodes.evaluator_node.get_evaluator_service",
            return_value=mock_service,
        ),
    ):
        mock_settings.return_value.ai.evaluator.enabled = True
        result = await evaluator_node.execute(context_with_brief)

    assert result.status == "success"
    assert result.html == context_with_brief.html
    assert "accepted" in result.details.lower()


@pytest.mark.asyncio
async def test_node_revise_triggers_handoff(
    evaluator_node: EvaluatorNode,
    context_with_brief: NodeContext,
) -> None:
    """Evaluator revises -> NodeResult with handoff + feedback."""
    mock_response = EvaluatorResponse(
        verdict=EvalVerdict(
            verdict="revise",
            score=0.5,
            issues=[
                EvalIssue(
                    severity="major",
                    category="layout",
                    description="Needs table-based layout",
                )
            ],
            feedback="Fix the layout structure",
        ),
        model="test:model",
        confidence=0.5,
        skills_loaded=["scaffolder"],
    )

    mock_service = AsyncMock()
    mock_service.evaluate.return_value = mock_response

    with (
        patch("app.ai.blueprints.nodes.evaluator_node.get_settings") as mock_settings,
        patch(
            "app.ai.blueprints.nodes.evaluator_node.get_evaluator_service",
            return_value=mock_service,
        ),
    ):
        mock_settings.return_value.ai.evaluator.enabled = True
        result = await evaluator_node.execute(context_with_brief)

    assert result.status == "failed"
    assert result.handoff is not None
    assert result.handoff.agent_name == "evaluator"
    assert "Fix the layout structure" in result.handoff.decisions[0]
    assert len(result.handoff.warnings) == 1


@pytest.mark.asyncio
async def test_node_disabled_skips(
    evaluator_node: EvaluatorNode,
    context_with_brief: NodeContext,
) -> None:
    """AI__EVALUATOR__ENABLED=false -> passthrough."""
    with patch("app.ai.blueprints.nodes.evaluator_node.get_settings") as mock_settings:
        mock_settings.return_value.ai.evaluator.enabled = False
        result = await evaluator_node.execute(context_with_brief)

    assert result.status == "success"
    assert result.html == context_with_brief.html
    assert "disabled" in result.details.lower()
