"""Tests for the recovery router with structured failure routing."""

import pytest

from app.ai.blueprints.nodes.recovery_router_node import (
    CHECK_PRIORITY,
    CHECK_TO_AGENT,
    RecoveryRouterNode,
    _fingerprint,
)
from app.ai.blueprints.protocols import AgentHandoff, NodeContext, StructuredFailure


def _make_failure(
    check_name: str = "html_validation",
    score: float = 0.5,
    details: str = "some issue",
    suggested_agent: str | None = None,
    priority: int | None = None,
) -> StructuredFailure:
    return StructuredFailure(
        check_name=check_name,
        score=score,
        details=details,
        suggested_agent=suggested_agent or CHECK_TO_AGENT.get(check_name, "scaffolder"),
        priority=priority or CHECK_PRIORITY.get(check_name, 99),
    )


def _make_context(
    qa_failures: list[str] | None = None,
    structured: list[StructuredFailure] | None = None,
    previous_structured: list[StructuredFailure] | None = None,
    handoff_history: list[AgentHandoff] | None = None,
    iteration: int = 1,
) -> NodeContext:
    ctx = NodeContext(
        html="<html><body>test</body></html>",
        qa_failures=qa_failures or [],
        iteration=iteration,
    )
    if structured is not None:
        ctx.metadata["qa_failure_details"] = structured
    if previous_structured is not None:
        ctx.metadata["previous_qa_failure_details"] = previous_structured
    if handoff_history is not None:
        ctx.metadata["handoff_history"] = handoff_history
    return ctx


@pytest.fixture
def router() -> RecoveryRouterNode:
    return RecoveryRouterNode()


class TestStructuredRouting:
    """Tests for priority-based structured failure routing."""

    @pytest.mark.anyio
    async def test_routes_to_highest_priority(self, router: RecoveryRouterNode) -> None:
        """Feed 3 failures with different priorities → routes to highest-priority agent."""
        failures = [
            _make_failure("html_validation", priority=11),  # scaffolder
            _make_failure("fallback", priority=1),  # outlook_fixer
            _make_failure("dark_mode", priority=3),  # dark_mode
        ]
        # Sort by priority like QA gate does
        failures.sort(key=lambda f: f.priority)

        ctx = _make_context(structured=failures)
        result = await router.execute(ctx)

        assert "route_to:outlook_fixer" in result.details

    @pytest.mark.anyio
    async def test_all_11_checks_map_correctly(self, router: RecoveryRouterNode) -> None:
        """Each check_name in CHECK_TO_AGENT routes to the expected agent."""
        for check_name, expected_agent in CHECK_TO_AGENT.items():
            failure = _make_failure(check_name)
            ctx = _make_context(structured=[failure])
            result = await router.execute(ctx)
            assert f"route_to:{expected_agent}" in result.details, (
                f"{check_name} should route to {expected_agent}, got {result.details}"
            )

    @pytest.mark.anyio
    async def test_unknown_check_defaults_to_scaffolder(self, router: RecoveryRouterNode) -> None:
        """Unknown check names default to scaffolder."""
        failure = _make_failure("unknown_check", suggested_agent="scaffolder", priority=99)
        ctx = _make_context(structured=[failure])
        result = await router.execute(ctx)
        assert "route_to:scaffolder" in result.details


class TestCycleDetection:
    """Tests for fingerprint-based cycle detection."""

    @pytest.mark.anyio
    async def test_cycle_detected_escalates_to_scaffolder(self, router: RecoveryRouterNode) -> None:
        """Same (check_name, details_hash) appears twice → escalates to scaffolder."""
        failure = _make_failure("dark_mode", details="Missing prefers-color-scheme")
        history = [AgentHandoff(agent_name="dark_mode")]

        ctx = _make_context(
            structured=[failure],
            previous_structured=[failure],  # Same failure from previous iteration
            handoff_history=history,
        )
        result = await router.execute(ctx)
        assert "route_to:scaffolder" in result.details

    @pytest.mark.anyio
    async def test_different_details_allows_retry(self, router: RecoveryRouterNode) -> None:
        """Same check_name but different details → not a cycle, allows retry."""
        current = _make_failure("dark_mode", details="Missing color-scheme meta tag")
        previous = _make_failure("dark_mode", details="No prefers-color-scheme media query")
        history = [AgentHandoff(agent_name="dark_mode")]

        ctx = _make_context(
            structured=[current],
            previous_structured=[previous],
            handoff_history=history,
        )
        result = await router.execute(ctx)
        assert "route_to:dark_mode" in result.details

    @pytest.mark.anyio
    async def test_no_previous_failures_no_cycle(self, router: RecoveryRouterNode) -> None:
        """First iteration with failures — no cycle detection triggered."""
        failure = _make_failure("fallback", details="No MSO conditional comments")
        history = [AgentHandoff(agent_name="outlook_fixer")]

        ctx = _make_context(
            structured=[failure],
            previous_structured=[],
            handoff_history=history,
        )
        result = await router.execute(ctx)
        # No previous fingerprints → no repeated set → no cycle
        assert "route_to:outlook_fixer" in result.details


class TestLegacyFallback:
    """Tests for backward-compatible string-based routing."""

    @pytest.mark.anyio
    async def test_legacy_routing_dark_mode(self, router: RecoveryRouterNode) -> None:
        """No structured failures → uses string-based routing."""
        ctx = _make_context(
            qa_failures=["dark_mode: Missing color-scheme meta (score=0.30)"],
        )
        result = await router.execute(ctx)
        assert "route_to:dark_mode" in result.details

    @pytest.mark.anyio
    async def test_legacy_routing_outlook(self, router: RecoveryRouterNode) -> None:
        ctx = _make_context(
            qa_failures=["fallback: No MSO conditional comments (score=0.00)"],
        )
        result = await router.execute(ctx)
        assert "route_to:outlook_fixer" in result.details

    @pytest.mark.anyio
    async def test_legacy_routing_accessibility(self, router: RecoveryRouterNode) -> None:
        ctx = _make_context(
            qa_failures=["accessibility: Missing lang attribute (score=0.50)"],
        )
        result = await router.execute(ctx)
        assert "route_to:accessibility" in result.details

    @pytest.mark.anyio
    async def test_legacy_fallback_to_scaffolder(self, router: RecoveryRouterNode) -> None:
        ctx = _make_context(
            qa_failures=["some_unknown: random issue (score=0.50)"],
        )
        result = await router.execute(ctx)
        assert "route_to:scaffolder" in result.details

    @pytest.mark.anyio
    async def test_no_failures_routes_to_scaffolder(self, router: RecoveryRouterNode) -> None:
        ctx = _make_context()
        result = await router.execute(ctx)
        assert "route_to:scaffolder" in result.details


class TestFingerprint:
    """Tests for failure fingerprinting."""

    def test_same_failure_same_fingerprint(self) -> None:
        f1 = _make_failure("dark_mode", details="Missing meta tag")
        f2 = _make_failure("dark_mode", details="Missing meta tag")
        assert _fingerprint(f1) == _fingerprint(f2)

    def test_different_details_different_fingerprint(self) -> None:
        f1 = _make_failure("dark_mode", details="Missing meta tag")
        f2 = _make_failure("dark_mode", details="No media query")
        assert _fingerprint(f1) != _fingerprint(f2)

    def test_different_check_different_fingerprint(self) -> None:
        f1 = _make_failure("dark_mode", details="issue")
        f2 = _make_failure("fallback", details="issue")
        assert _fingerprint(f1) != _fingerprint(f2)
