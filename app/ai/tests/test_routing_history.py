"""Tests for adaptive model tier routing (15.3)."""

from unittest.mock import AsyncMock

import pytest

from app.ai.routing import resolve_model_adaptive
from app.ai.routing_history import (
    RoutingHistoryRepository,
    resolve_adaptive_tier,
    tier_above,
    tier_below,
)

# ── Pure function tests ──


def test_tier_below_standard() -> None:
    assert tier_below("standard") == "lightweight"


def test_tier_below_lightweight_is_none() -> None:
    assert tier_below("lightweight") is None


def test_tier_above_standard() -> None:
    assert tier_above("standard") == "complex"


def test_tier_above_complex_is_none() -> None:
    assert tier_above("complex") is None


def test_tier_below_complex() -> None:
    assert tier_below("complex") == "standard"


def test_tier_above_lightweight() -> None:
    assert tier_above("lightweight") == "standard"


# ── Adaptive tier resolution tests ──


@pytest.mark.asyncio
async def test_resolve_adaptive_no_history() -> None:
    """No records → returns default tier unchanged."""
    repo = AsyncMock(spec=RoutingHistoryRepository)
    repo.get_acceptance_rate.return_value = (None, 0)

    result = await resolve_adaptive_tier("standard", "scaffolder", 1, repo)
    assert result == "standard"


@pytest.mark.asyncio
async def test_resolve_adaptive_below_min_samples() -> None:
    """5 records (< MIN_SAMPLES) → returns default tier."""
    repo = AsyncMock(spec=RoutingHistoryRepository)
    repo.get_acceptance_rate.return_value = (0.95, 5)

    result = await resolve_adaptive_tier("standard", "scaffolder", 1, repo)
    assert result == "standard"


@pytest.mark.asyncio
async def test_resolve_adaptive_downgrade() -> None:
    """Lightweight has 95% acceptance with 20 samples → downgrade from standard."""
    repo = AsyncMock(spec=RoutingHistoryRepository)

    async def mock_acceptance(
        agent_name: str,
        project_id: int | None,
        tier: str,
        limit: int = 20,
    ) -> tuple[float | None, int]:
        if tier == "lightweight":
            return 0.95, 20  # >DOWNGRADE_THRESHOLD with enough samples
        return 0.8, 15  # Current tier fine

    repo.get_acceptance_rate = AsyncMock(side_effect=mock_acceptance)

    result = await resolve_adaptive_tier("standard", "scaffolder", 1, repo)
    assert result == "lightweight"


@pytest.mark.asyncio
async def test_resolve_adaptive_upgrade() -> None:
    """Standard has 50% acceptance → upgrade to complex."""
    repo = AsyncMock(spec=RoutingHistoryRepository)

    async def mock_acceptance(
        agent_name: str,
        project_id: int | None,
        tier: str,
        limit: int = 20,
    ) -> tuple[float | None, int]:
        if tier == "lightweight":
            return None, 0  # No lightweight history
        if tier == "standard":
            return 0.5, 15  # <UPGRADE_THRESHOLD
        return 0.9, 10

    repo.get_acceptance_rate = AsyncMock(side_effect=mock_acceptance)

    result = await resolve_adaptive_tier("standard", "scaffolder", 1, repo)
    assert result == "complex"


@pytest.mark.asyncio
async def test_resolve_adaptive_no_downgrade_low_acceptance() -> None:
    """Lightweight at 60% acceptance → stays at standard (doesn't downgrade)."""
    repo = AsyncMock(spec=RoutingHistoryRepository)

    async def mock_acceptance(
        agent_name: str,
        project_id: int | None,
        tier: str,
        limit: int = 20,
    ) -> tuple[float | None, int]:
        if tier == "lightweight":
            return 0.6, 20  # Below DOWNGRADE_THRESHOLD
        return 0.8, 15  # Current tier is fine

    repo.get_acceptance_rate = AsyncMock(side_effect=mock_acceptance)

    result = await resolve_adaptive_tier("standard", "scaffolder", 1, repo)
    assert result == "standard"


@pytest.mark.asyncio
async def test_resolve_adaptive_no_upgrade_acceptable_rate() -> None:
    """Standard at 80% acceptance → stays at standard (above UPGRADE_THRESHOLD)."""
    repo = AsyncMock(spec=RoutingHistoryRepository)

    async def mock_acceptance(
        agent_name: str,
        project_id: int | None,
        tier: str,
        limit: int = 20,
    ) -> tuple[float | None, int]:
        if tier == "lightweight":
            return 0.7, 20  # Below DOWNGRADE_THRESHOLD
        return 0.8, 15  # Above UPGRADE_THRESHOLD

    repo.get_acceptance_rate = AsyncMock(side_effect=mock_acceptance)

    result = await resolve_adaptive_tier("standard", "scaffolder", 1, repo)
    assert result == "standard"


# ── resolve_model_adaptive tests ──


@pytest.mark.asyncio
async def test_resolve_model_adaptive_disabled() -> None:
    """routing_repo=None → uses static tier."""
    model, effective_tier = await resolve_model_adaptive("standard", "scaffolder", 1, None)
    assert effective_tier == "standard"
    assert isinstance(model, str)


@pytest.mark.asyncio
async def test_resolve_model_adaptive_with_repo() -> None:
    """With routing repo, calls resolve_adaptive_tier."""
    repo = AsyncMock(spec=RoutingHistoryRepository)
    repo.get_acceptance_rate.return_value = (None, 0)

    model, effective_tier = await resolve_model_adaptive("standard", "scaffolder", 1, repo)
    assert effective_tier == "standard"
    assert isinstance(model, str)


# ── Engine integration tests ──


@pytest.mark.asyncio
async def test_engine_records_routing_history() -> None:
    """BlueprintEngine with routing_history_repo records entries after agentic node."""
    from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
    from app.ai.blueprints.protocols import NodeContext, NodeResult

    class _FakeNode:
        name = "scaffolder"
        node_type = "agentic"
        model_tier = "standard"

        async def execute(self, context: NodeContext) -> NodeResult:
            return NodeResult(status="success", html="<html>done</html>")

    definition = BlueprintDefinition(
        name="test",
        nodes={"scaffolder": _FakeNode()},  # type: ignore[dict-item]
        edges=[],
        entry_node="scaffolder",
    )
    repo = AsyncMock(spec=RoutingHistoryRepository)
    repo.get_acceptance_rate.return_value = (None, 0)

    engine = BlueprintEngine(
        definition,
        project_id=1,
        routing_history_repo=repo,
    )
    run = await engine.run(brief="test brief")

    assert run.status == "completed"
    repo.record.assert_called_once_with(
        agent_name="scaffolder",
        project_id=1,
        tier_used="standard",
        accepted=True,
    )


@pytest.mark.asyncio
async def test_engine_no_routing_history_when_disabled() -> None:
    """Engine with routing_history_repo=None doesn't crash."""
    from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
    from app.ai.blueprints.protocols import NodeContext, NodeResult

    class _FakeNode:
        name = "scaffolder"
        node_type = "agentic"
        model_tier = "standard"

        async def execute(self, context: NodeContext) -> NodeResult:
            return NodeResult(status="success", html="<html>done</html>")

    definition = BlueprintDefinition(
        name="test",
        nodes={"scaffolder": _FakeNode()},  # type: ignore[dict-item]
        edges=[],
        entry_node="scaffolder",
    )

    engine = BlueprintEngine(definition, project_id=1)
    run = await engine.run(brief="test brief")
    assert run.status == "completed"


# ── Capability-aware routing tests ──


def test_resolve_model_by_capabilities_no_match() -> None:
    """No match returns None, caller falls back to tier-based."""
    import app.ai.capability_registry as mod
    from app.ai.capability_registry import CapabilityRegistry, ModelCapability
    from app.ai.routing import resolve_model_by_capabilities

    old = mod._registry
    mod._registry = CapabilityRegistry()
    try:
        result = resolve_model_by_capabilities(
            requirements={ModelCapability.EXTENDED_THINKING},
        )
        assert result is None
    finally:
        mod._registry = old
