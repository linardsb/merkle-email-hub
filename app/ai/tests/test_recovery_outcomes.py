"""Tests for failure-outcome ledger — adaptive recovery routing."""

from unittest.mock import AsyncMock

import pytest

from app.ai.recovery_outcomes import (
    MIN_OUTCOME_SAMPLES,
    POOR_RESOLUTION_THRESHOLD,
    RecoveryOutcomeRepository,
    select_best_fixer,
)

# ── select_best_fixer tests ──


@pytest.mark.asyncio
async def test_select_best_fixer_no_history() -> None:
    """No records → returns default agent unchanged."""
    repo = AsyncMock(spec=RecoveryOutcomeRepository)
    repo.get_resolution_rate.return_value = (None, 0)

    result = await select_best_fixer("html_validation", "scaffolder", None, repo)
    assert result == "scaffolder"


@pytest.mark.asyncio
async def test_select_best_fixer_below_min_samples() -> None:
    """Too few samples → returns default agent."""
    repo = AsyncMock(spec=RecoveryOutcomeRepository)
    repo.get_resolution_rate.return_value = (0.1, MIN_OUTCOME_SAMPLES - 1)

    result = await select_best_fixer("html_validation", "scaffolder", None, repo)
    assert result == "scaffolder"


@pytest.mark.asyncio
async def test_select_best_fixer_good_performer() -> None:
    """Default agent performs well → keep it."""
    repo = AsyncMock(spec=RecoveryOutcomeRepository)
    repo.get_resolution_rate.return_value = (0.8, 15)

    result = await select_best_fixer("html_validation", "scaffolder", None, repo)
    assert result == "scaffolder"


@pytest.mark.asyncio
async def test_select_best_fixer_skips_poor_performer() -> None:
    """Default agent is poor → reroutes to first acceptable alternative."""
    repo = AsyncMock(spec=RecoveryOutcomeRepository)

    async def mock_rate(
        check_name: str,
        agent_name: str,
        project_id: int | None,
        limit: int = 20,
    ) -> tuple[float | None, int]:
        if agent_name == "scaffolder":
            return 0.1, 15  # poor
        if agent_name == "code_reviewer":
            return 0.7, 10  # acceptable
        return None, 0

    repo.get_resolution_rate = AsyncMock(side_effect=mock_rate)

    result = await select_best_fixer("html_validation", "scaffolder", None, repo)
    assert result == "code_reviewer"


@pytest.mark.asyncio
async def test_select_best_fixer_all_poor_returns_default() -> None:
    """All candidates poor or no data → falls back to default."""
    repo = AsyncMock(spec=RecoveryOutcomeRepository)

    async def mock_rate(
        check_name: str,
        agent_name: str,
        project_id: int | None,
        limit: int = 20,
    ) -> tuple[float | None, int]:
        if agent_name == "scaffolder":
            return 0.1, 15  # poor
        return None, 0  # no data for alternatives

    repo.get_resolution_rate = AsyncMock(side_effect=mock_rate)

    result = await select_best_fixer("html_validation", "scaffolder", None, repo)
    assert result == "scaffolder"


@pytest.mark.asyncio
async def test_select_best_fixer_threshold_boundary() -> None:
    """Agent at exactly the threshold → kept (>= comparison)."""
    repo = AsyncMock(spec=RecoveryOutcomeRepository)
    repo.get_resolution_rate.return_value = (POOR_RESOLUTION_THRESHOLD, MIN_OUTCOME_SAMPLES)

    result = await select_best_fixer("dark_mode", "dark_mode", None, repo)
    assert result == "dark_mode"


@pytest.mark.asyncio
async def test_select_best_fixer_project_scoped() -> None:
    """Project ID is passed through to repo calls."""
    repo = AsyncMock(spec=RecoveryOutcomeRepository)
    repo.get_resolution_rate.return_value = (0.9, 20)

    await select_best_fixer("css_support", "code_reviewer", 42, repo)
    repo.get_resolution_rate.assert_called_once_with("css_support", "code_reviewer", 42)


# ── Recovery router integration test ──


@pytest.mark.asyncio
async def test_recovery_router_uses_ledger() -> None:
    """Recovery router queries ledger via metadata when available."""

    from app.ai.blueprints.nodes.recovery_router_node import RecoveryRouterNode
    from app.ai.blueprints.protocols import NodeContext, StructuredFailure

    failures = [
        StructuredFailure(
            check_name="html_validation",
            score=0.3,
            details="Missing doctype",
            suggested_agent="scaffolder",
            priority=1,
        ),
    ]

    # Mock repo that reroutes away from scaffolder
    mock_repo = AsyncMock(spec=RecoveryOutcomeRepository)

    async def mock_rate(
        check_name: str,
        agent_name: str,
        project_id: int | None,
        limit: int = 20,
    ) -> tuple[float | None, int]:
        if agent_name == "scaffolder":
            return 0.1, 15  # poor
        if agent_name == "code_reviewer":
            return 0.8, 12  # good
        return None, 0

    mock_repo.get_resolution_rate = AsyncMock(side_effect=mock_rate)

    context = NodeContext(
        html="<html></html>",
        brief="Test brief",
        iteration=0,
        qa_failures=["html_validation: Missing doctype"],
    )
    context.metadata["qa_failure_details"] = failures
    context.metadata["recovery_outcome_repo"] = mock_repo
    context.metadata["project_id"] = None

    node = RecoveryRouterNode()
    result = await node.execute(context)

    assert "route_to:code_reviewer" in result.details


@pytest.mark.asyncio
async def test_recovery_router_without_ledger_uses_static() -> None:
    """Without ledger repo, recovery router uses static CHECK_TO_AGENT mapping."""
    from app.ai.blueprints.nodes.recovery_router_node import RecoveryRouterNode
    from app.ai.blueprints.protocols import NodeContext, StructuredFailure

    failures = [
        StructuredFailure(
            check_name="dark_mode",
            score=0.2,
            details="No dark mode support",
            suggested_agent="dark_mode",
            priority=1,
        ),
    ]

    context = NodeContext(
        html="<html></html>",
        brief="Test brief",
        iteration=0,
        qa_failures=["dark_mode: No dark mode support"],
    )
    context.metadata["qa_failure_details"] = failures

    node = RecoveryRouterNode()
    result = await node.execute(context)

    assert "route_to:dark_mode" in result.details
