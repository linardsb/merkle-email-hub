"""Tests for audience-aware blueprint route selection."""

from __future__ import annotations

import pytest

from app.ai.blueprints.audience_context import AudienceConstraint, AudienceProfile
from app.ai.blueprints.route_advisor import is_node_relevant
from app.knowledge.ontology.types import ClientEngine, EmailClient

# -- Factories --


def _make_client(
    *,
    id: str = "gmail_web",
    name: str = "Gmail Web",
    family: str = "gmail",
    platform: str = "web",
    engine: ClientEngine = ClientEngine.BLINK,
) -> EmailClient:
    return EmailClient(id=id, name=name, family=family, platform=platform, engine=engine)


def _make_profile(
    *,
    clients: tuple[EmailClient, ...] = (),
    dark_mode_required: bool = False,
    client_ids: tuple[str, ...] = (),
    persona_names: tuple[str, ...] = ("Test User",),
    constraints: tuple[AudienceConstraint, ...] = (),
    mobile_viewports: tuple[int, ...] = (),
) -> AudienceProfile:
    return AudienceProfile(
        persona_names=persona_names,
        client_ids=client_ids or tuple(c.id for c in clients),
        clients=clients,
        constraints=constraints,
        dark_mode_required=dark_mode_required,
        mobile_viewports=mobile_viewports,
    )


# -- Tests --


class TestIsNodeRelevant:
    """Tests for is_node_relevant() relevance rules."""

    def test_no_audience_profile_always_relevant(self) -> None:
        """All nodes are relevant when no audience profile is set."""
        assert is_node_relevant("outlook_fixer", None) is True
        assert is_node_relevant("dark_mode", None) is True
        assert is_node_relevant("scaffolder", None) is True

    def test_unknown_node_always_relevant(self) -> None:
        """Nodes without relevance rules are always relevant."""
        profile = _make_profile(clients=(_make_client(),))
        assert is_node_relevant("scaffolder", profile) is True
        assert is_node_relevant("accessibility", profile) is True
        assert is_node_relevant("code_reviewer", profile) is True
        assert is_node_relevant("personalisation", profile) is True
        assert is_node_relevant("knowledge", profile) is True
        assert is_node_relevant("innovation", profile) is True

    def test_outlook_fixer_relevant_with_word_engine(self) -> None:
        """Outlook Fixer is relevant when audience includes Word engine clients."""
        outlook = _make_client(
            id="outlook_365_win",
            name="Outlook 365 (Windows)",
            family="outlook",
            platform="windows",
            engine=ClientEngine.WORD,
        )
        profile = _make_profile(clients=(outlook,))
        assert is_node_relevant("outlook_fixer", profile) is True

    def test_outlook_fixer_irrelevant_without_word_engine(self) -> None:
        """Outlook Fixer is NOT relevant for non-Word-engine audiences."""
        gmail = _make_client()  # BLINK engine
        apple = _make_client(
            id="apple_mail_macos",
            name="Apple Mail",
            family="apple",
            engine=ClientEngine.WEBKIT,
        )
        profile = _make_profile(clients=(gmail, apple))
        assert is_node_relevant("outlook_fixer", profile) is False

    def test_outlook_fixer_relevant_with_mixed_engines(self) -> None:
        """Outlook Fixer is relevant if at least one client uses Word."""
        gmail = _make_client()
        outlook = _make_client(
            id="outlook_2019_win",
            name="Outlook 2019",
            engine=ClientEngine.WORD,
        )
        profile = _make_profile(clients=(gmail, outlook))
        assert is_node_relevant("outlook_fixer", profile) is True

    def test_dark_mode_relevant_when_required(self) -> None:
        """Dark Mode is relevant when any persona requires dark mode."""
        profile = _make_profile(
            clients=(_make_client(),),
            dark_mode_required=True,
        )
        assert is_node_relevant("dark_mode", profile) is True

    def test_dark_mode_irrelevant_when_not_required(self) -> None:
        """Dark Mode is NOT relevant when no persona needs dark mode."""
        profile = _make_profile(
            clients=(_make_client(),),
            dark_mode_required=False,
        )
        assert is_node_relevant("dark_mode", profile) is False

    def test_deterministic_nodes_always_relevant(self) -> None:
        """Deterministic nodes (qa_gate, recovery_router, etc.) are always relevant."""
        profile = _make_profile(clients=(_make_client(),))
        assert is_node_relevant("qa_gate", profile) is True
        assert is_node_relevant("recovery_router", profile) is True
        assert is_node_relevant("maizzle_build", profile) is True
        assert is_node_relevant("export", profile) is True


class TestRecoveryRouterAudienceFiltering:
    """Tests for recovery router filtering by audience relevance."""

    @pytest.mark.asyncio
    async def test_router_skips_irrelevant_fixer(self) -> None:
        """Recovery router falls back when primary target is audience-irrelevant."""
        from app.ai.blueprints.nodes.recovery_router_node import RecoveryRouterNode
        from app.ai.blueprints.protocols import NodeContext

        apple = _make_client(
            id="apple_mail_macos",
            engine=ClientEngine.WEBKIT,
        )
        profile = _make_profile(clients=(apple,))

        context = NodeContext(
            html="<html></html>",
            qa_failures=["fallback: No MSO conditional comments found"],
            metadata={"audience_profile": profile},
        )
        node = RecoveryRouterNode()
        result = await node.execute(context)
        assert "route_to:outlook_fixer" not in result.details

    @pytest.mark.asyncio
    async def test_router_routes_relevant_fixer(self) -> None:
        """Recovery router routes to fixer when it IS audience-relevant."""
        from app.ai.blueprints.nodes.recovery_router_node import RecoveryRouterNode
        from app.ai.blueprints.protocols import NodeContext

        outlook = _make_client(
            id="outlook_365_win",
            engine=ClientEngine.WORD,
        )
        profile = _make_profile(clients=(outlook,))

        context = NodeContext(
            html="<html></html>",
            qa_failures=["fallback: No MSO conditional comments found"],
            metadata={"audience_profile": profile},
        )
        node = RecoveryRouterNode()
        result = await node.execute(context)
        assert "route_to:outlook_fixer" in result.details

    @pytest.mark.asyncio
    async def test_router_no_audience_profile_routes_normally(self) -> None:
        """Without audience profile, router routes to primary target as before."""
        from app.ai.blueprints.nodes.recovery_router_node import RecoveryRouterNode
        from app.ai.blueprints.protocols import NodeContext

        context = NodeContext(
            html="<html></html>",
            qa_failures=["dark_mode: Missing color-scheme meta"],
            metadata={},
        )
        node = RecoveryRouterNode()
        result = await node.execute(context)
        assert "route_to:dark_mode" in result.details

    @pytest.mark.asyncio
    async def test_router_falls_to_scaffolder_when_all_filtered(self) -> None:
        """Falls back to scaffolder when the relevant fixer is filtered out."""
        from app.ai.blueprints.nodes.recovery_router_node import RecoveryRouterNode
        from app.ai.blueprints.protocols import NodeContext

        gmail = _make_client()
        profile = _make_profile(clients=(gmail,), dark_mode_required=False)

        context = NodeContext(
            html="<html></html>",
            qa_failures=["dark_mode: Missing color-scheme meta"],
            metadata={"audience_profile": profile},
        )
        node = RecoveryRouterNode()
        result = await node.execute(context)
        assert "route_to:scaffolder" in result.details


class TestEngineNodeSkipping:
    """Tests for engine-level node skipping based on audience."""

    @pytest.mark.asyncio
    async def test_engine_skips_irrelevant_node(self) -> None:
        """Engine skips agentic nodes that are irrelevant for the audience."""
        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
        from app.ai.blueprints.protocols import NodeContext, NodeResult

        class FakeDarkMode:
            name = "dark_mode"
            node_type = "agentic"

            async def execute(self, _ctx: NodeContext) -> NodeResult:
                raise AssertionError("Should not be called when skipped")

        class FakeQAGate:
            name = "qa_gate"
            node_type = "deterministic"

            async def execute(self, ctx: NodeContext) -> NodeResult:
                return NodeResult(status="success", html=ctx.html, details="All checks passed")

        definition = BlueprintDefinition(
            name="test",
            nodes={"dark_mode": FakeDarkMode(), "qa_gate": FakeQAGate()},
            edges=[Edge(from_node="dark_mode", to_node="qa_gate", condition="always")],
            entry_node="dark_mode",
        )

        gmail = _make_client()
        profile = _make_profile(clients=(gmail,), dark_mode_required=False)

        engine = BlueprintEngine(definition, audience_profile=profile)
        run = await engine.run(brief="Test brief", initial_html="<html></html>")

        assert "dark_mode" in run.skipped_nodes
        assert run.progress[0].node_name == "dark_mode"
        assert run.progress[0].status == "skipped"
        assert run.progress[1].node_name == "qa_gate"
        assert run.progress[1].status == "success"

    @pytest.mark.asyncio
    async def test_engine_runs_relevant_node(self) -> None:
        """Engine runs agentic nodes that ARE relevant for the audience."""
        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
        from app.ai.blueprints.protocols import NodeContext, NodeResult

        class FakeDarkMode:
            name = "dark_mode"
            node_type = "agentic"

            async def execute(self, _ctx: NodeContext) -> NodeResult:
                return NodeResult(status="success", html="<html>dark</html>")

        class FakeQAGate:
            name = "qa_gate"
            node_type = "deterministic"

            async def execute(self, ctx: NodeContext) -> NodeResult:
                return NodeResult(status="success", html=ctx.html)

        definition = BlueprintDefinition(
            name="test",
            nodes={"dark_mode": FakeDarkMode(), "qa_gate": FakeQAGate()},
            edges=[Edge(from_node="dark_mode", to_node="qa_gate", condition="always")],
            entry_node="dark_mode",
        )

        profile = _make_profile(clients=(_make_client(),), dark_mode_required=True)
        engine = BlueprintEngine(definition, audience_profile=profile)
        run = await engine.run(brief="Test brief", initial_html="<html></html>")

        assert run.skipped_nodes == []
        assert run.progress[0].node_name == "dark_mode"
        assert run.progress[0].status == "success"

    @pytest.mark.asyncio
    async def test_engine_no_audience_skips_nothing(self) -> None:
        """Without audience profile, no nodes are skipped."""
        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine
        from app.ai.blueprints.protocols import NodeContext, NodeResult

        class FakeDarkMode:
            name = "dark_mode"
            node_type = "agentic"

            async def execute(self, _ctx: NodeContext) -> NodeResult:
                return NodeResult(status="success", html="<html>dark</html>")

        definition = BlueprintDefinition(
            name="test",
            nodes={"dark_mode": FakeDarkMode()},
            edges=[],
            entry_node="dark_mode",
        )

        engine = BlueprintEngine(definition, audience_profile=None)
        run = await engine.run(brief="Test brief")
        assert run.skipped_nodes == []
        assert run.progress[0].status == "success"

    @pytest.mark.asyncio
    async def test_engine_skips_entry_node_proceeds_to_next(self) -> None:
        """When entry node is skipped, engine proceeds to the next node via edges."""
        from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
        from app.ai.blueprints.protocols import NodeContext, NodeResult

        class FakeOutlookFixer:
            name = "outlook_fixer"
            node_type = "agentic"

            async def execute(self, _ctx: NodeContext) -> NodeResult:
                raise AssertionError("Should not be called when skipped")

        class FakeScaffolder:
            name = "scaffolder"
            node_type = "agentic"

            async def execute(self, _ctx: NodeContext) -> NodeResult:
                return NodeResult(status="success", html="<html>scaffolded</html>")

        definition = BlueprintDefinition(
            name="test",
            nodes={
                "outlook_fixer": FakeOutlookFixer(),
                "scaffolder": FakeScaffolder(),
            },
            edges=[Edge(from_node="outlook_fixer", to_node="scaffolder", condition="always")],
            entry_node="outlook_fixer",
        )

        # Gmail-only audience — no Word engine → outlook_fixer irrelevant
        gmail = _make_client()
        profile = _make_profile(clients=(gmail,))

        engine = BlueprintEngine(definition, audience_profile=profile)
        run = await engine.run(brief="Test brief", initial_html="<html></html>")

        assert "outlook_fixer" in run.skipped_nodes
        assert run.progress[0].status == "skipped"
        assert run.progress[1].node_name == "scaffolder"
        assert run.progress[1].status == "success"
        assert run.html == "<html>scaffolded</html>"


class TestHasMatchingFailure:
    """Direct tests for _has_matching_failure helper."""

    def test_dark_mode_pattern_matches_qa_failure(self) -> None:
        from app.ai.blueprints.nodes.recovery_router_node import _has_matching_failure

        assert _has_matching_failure("dark_mode", ["dark_mode: Missing meta"], None) is True

    def test_outlook_fixer_matches_mso_failure(self) -> None:
        from app.ai.blueprints.nodes.recovery_router_node import _has_matching_failure

        assert (
            _has_matching_failure("outlook_fixer", ["fallback: No MSO conditionals"], None) is True
        )

    def test_no_match_returns_false(self) -> None:
        from app.ai.blueprints.nodes.recovery_router_node import _has_matching_failure

        assert _has_matching_failure("dark_mode", ["accessibility: Missing lang"], None) is False

    def test_matches_upstream_handoff_warnings(self) -> None:
        from app.ai.blueprints.nodes.recovery_router_node import _has_matching_failure
        from app.ai.blueprints.protocols import AgentHandoff

        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<html></html>",
            decisions=(),
            warnings=("Outlook MSO conditionals missing",),
            component_refs=(),
        )
        assert _has_matching_failure("outlook_fixer", [], handoff) is True

    def test_unknown_candidate_returns_false(self) -> None:
        from app.ai.blueprints.nodes.recovery_router_node import _has_matching_failure

        assert _has_matching_failure("unknown_node", ["dark_mode: fail"], None) is False


class TestSkippedNodesInResponse:
    """Tests for skipped_nodes field in API response."""

    def test_skipped_nodes_default_empty(self) -> None:
        from app.ai.blueprints.schemas import BlueprintRunResponse

        resp = BlueprintRunResponse(
            run_id="test",
            blueprint_name="campaign",
            status="completed",
            html="",
            progress=[],
            qa_passed=True,
            model_usage={},
            handoff_history=[],
        )
        assert resp.skipped_nodes == []

    def test_skipped_nodes_populated(self) -> None:
        from app.ai.blueprints.schemas import BlueprintRunResponse

        resp = BlueprintRunResponse(
            run_id="test",
            blueprint_name="campaign",
            status="completed",
            html="",
            progress=[],
            qa_passed=True,
            model_usage={},
            handoff_history=[],
            skipped_nodes=["outlook_fixer", "dark_mode"],
        )
        assert resp.skipped_nodes == ["outlook_fixer", "dark_mode"]
