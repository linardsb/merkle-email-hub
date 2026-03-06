"""Tests for blueprint daily cost cap enforcement."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
from app.ai.blueprints.protocols import NodeContext, NodeResult


class _StubNode:
    """Stub node that returns configurable token usage."""

    node_type = "agentic"

    def __init__(self, usage_tokens: int = 100, html: str = "<p>ok</p>") -> None:
        self._usage = {
            "prompt_tokens": usage_tokens,
            "completion_tokens": 0,
            "total_tokens": usage_tokens,
        }
        self._html = html

    async def execute(self, context: NodeContext) -> NodeResult:  # noqa: ARG002
        return NodeResult(status="success", html=self._html, usage=self._usage)


class _DeterministicNode:
    """Stub deterministic node (no tokens)."""

    node_type = "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:  # noqa: ARG002
        return NodeResult(status="success")


def _simple_blueprint(usage_tokens: int = 100) -> BlueprintDefinition:
    """Two-node blueprint: agent -> terminal."""
    return BlueprintDefinition(
        name="test",
        nodes={
            "agent": _StubNode(usage_tokens=usage_tokens),  # type: ignore[dict-item]
            "finish": _DeterministicNode(),  # type: ignore[dict-item]
        },
        edges=[Edge(from_node="agent", to_node="finish", condition="success")],
        entry_node="agent",
    )


def _multi_node_blueprint(usage_per_node: int = 200) -> BlueprintDefinition:
    """Three agent nodes in sequence."""
    return BlueprintDefinition(
        name="test_multi",
        nodes={
            "a1": _StubNode(usage_tokens=usage_per_node),  # type: ignore[dict-item]
            "a2": _StubNode(usage_tokens=usage_per_node),  # type: ignore[dict-item]
            "a3": _StubNode(usage_tokens=usage_per_node),  # type: ignore[dict-item]
        },
        edges=[
            Edge(from_node="a1", to_node="a2", condition="success"),
            Edge(from_node="a2", to_node="a3", condition="success"),
        ],
        entry_node="a1",
    )


@pytest.mark.asyncio
async def test_blueprint_runs_within_cap() -> None:
    engine = BlueprintEngine(_simple_blueprint(usage_tokens=100))

    mock_tracker = AsyncMock()
    mock_tracker.check_budget = AsyncMock(return_value=500_000)
    mock_tracker.record_usage = AsyncMock()

    with (
        patch("app.core.quota.BlueprintCostTracker", return_value=mock_tracker),
        patch("app.core.config.get_settings") as mock_settings,
    ):
        mock_settings.return_value.blueprint.daily_token_cap = 500_000
        result = await engine.run("test brief", user_id=1)

    assert result.status == "completed"
    mock_tracker.record_usage.assert_called_once_with(1, 100)


@pytest.mark.asyncio
async def test_blueprint_stops_at_cap() -> None:
    engine = BlueprintEngine(_multi_node_blueprint(usage_per_node=200))

    mock_tracker = AsyncMock()
    # First node: budget remaining; second node: budget exhausted
    mock_tracker.check_budget = AsyncMock(side_effect=[1000, 0])
    mock_tracker.record_usage = AsyncMock()

    with (
        patch("app.core.quota.BlueprintCostTracker", return_value=mock_tracker),
        patch("app.core.config.get_settings") as mock_settings,
    ):
        mock_settings.return_value.blueprint.daily_token_cap = 500
        result = await engine.run("test brief", user_id=1)

    assert result.status == "cost_cap_exceeded"
    # Only first node's usage recorded (second node budget was 0, so break before record)
    assert mock_tracker.record_usage.call_count == 1


@pytest.mark.asyncio
async def test_no_tracking_without_user_id() -> None:
    engine = BlueprintEngine(_simple_blueprint(usage_tokens=100))

    with patch("app.core.quota.BlueprintCostTracker") as mock_cls:
        result = await engine.run("test brief", user_id=None)

    assert result.status == "completed"
    # Tracker never instantiated
    mock_cls.assert_not_called()


@pytest.mark.asyncio
async def test_token_usage_accumulated() -> None:
    engine = BlueprintEngine(_multi_node_blueprint(usage_per_node=150))

    mock_tracker = AsyncMock()
    mock_tracker.check_budget = AsyncMock(return_value=999_999)
    mock_tracker.record_usage = AsyncMock()

    with (
        patch("app.core.quota.BlueprintCostTracker", return_value=mock_tracker),
        patch("app.core.config.get_settings") as mock_settings,
    ):
        mock_settings.return_value.blueprint.daily_token_cap = 500_000
        result = await engine.run("test brief", user_id=1)

    assert result.status == "completed"
    # All 3 nodes recorded usage
    assert mock_tracker.record_usage.call_count == 3
    assert result.model_usage["total_tokens"] == 450
