"""Tests for engine applying routing plan decisions."""

from __future__ import annotations

import pytest

from app.ai.blueprints.audience_context import AudienceProfile
from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType
from app.knowledge.ontology.types import ClientEngine, EmailClient


def _make_client(
    *,
    id: str = "gmail_web",
    name: str = "Gmail Web",
    engine: ClientEngine = ClientEngine.BLINK,
) -> EmailClient:
    return EmailClient(id=id, name=name, family="gmail", platform="web", engine=engine)


def _make_profile(
    *,
    clients: tuple[EmailClient, ...] = (),
    dark_mode_required: bool = False,
) -> AudienceProfile:
    return AudienceProfile(
        persona_names=("Test",),
        client_ids=tuple(c.id for c in clients),
        clients=clients,
        constraints=(),
        dark_mode_required=dark_mode_required,
        mobile_viewports=(),
    )


class _FakeNode:
    """Generic fake node for testing."""

    def __init__(self, name: str, node_type: NodeType = "agentic") -> None:
        self._name = name
        self._type: NodeType = node_type

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return self._type

    async def execute(self, context: NodeContext) -> NodeResult:
        return NodeResult(status="success", html=context.html, details=f"{self._name} done")


class _FailingNode:
    """Node that raises if called (should be skipped)."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        raise AssertionError(f"{self._name} should not be called")


class TestEngineRoutingPlan:
    """Tests for engine applying routing plan from route advisor."""

    @pytest.mark.asyncio
    async def test_personalisation_skipped_without_dynamic_content(self) -> None:
        """Personalisation node skipped when brief has no dynamic content markers."""
        definition = BlueprintDefinition(
            name="test",
            nodes={
                "scaffolder": _FakeNode("scaffolder"),
                "personalisation": _FailingNode("personalisation"),
                "qa_gate": _FakeNode("qa_gate", "deterministic"),
            },
            edges=[
                Edge(from_node="scaffolder", to_node="personalisation", condition="always"),
                Edge(from_node="personalisation", to_node="qa_gate", condition="always"),
            ],
            entry_node="scaffolder",
        )
        gmail = _make_client()
        profile = _make_profile(clients=(gmail,), dark_mode_required=True)
        engine = BlueprintEngine(definition, audience_profile=profile)
        run = await engine.run(brief="Simple newsletter", initial_html="<html>Static</html>")

        assert "personalisation" in run.skipped_nodes
        assert any(d.action == "skip" for d in run.routing_decisions)

    @pytest.mark.asyncio
    async def test_routing_decisions_in_run(self) -> None:
        """Routing decisions are stored on the BlueprintRun for API response."""
        definition = BlueprintDefinition(
            name="test",
            nodes={
                "scaffolder": _FakeNode("scaffolder"),
                "dark_mode": _FailingNode("dark_mode"),
            },
            edges=[
                Edge(from_node="scaffolder", to_node="dark_mode", condition="always"),
            ],
            entry_node="scaffolder",
        )
        gmail = _make_client()
        profile = _make_profile(clients=(gmail,), dark_mode_required=False)
        engine = BlueprintEngine(definition, audience_profile=profile)
        run = await engine.run(brief="Test", initial_html="<html></html>")

        assert len(run.routing_decisions) > 0
        dark_mode_decision = next(
            (d for d in run.routing_decisions if d.node_name == "dark_mode"), None
        )
        assert dark_mode_decision is not None
        assert dark_mode_decision.action == "skip"
        assert len(dark_mode_decision.reason) > 0

    @pytest.mark.asyncio
    async def test_relevant_node_runs_normally(self) -> None:
        """When dark_mode is relevant, it runs instead of being skipped."""
        definition = BlueprintDefinition(
            name="test",
            nodes={
                "dark_mode": _FakeNode("dark_mode"),
            },
            edges=[],
            entry_node="dark_mode",
        )
        profile = _make_profile(clients=(_make_client(),), dark_mode_required=True)
        engine = BlueprintEngine(definition, audience_profile=profile)
        run = await engine.run(brief="Test", initial_html="<html></html>")
        assert "dark_mode" not in run.skipped_nodes

    @pytest.mark.asyncio
    async def test_skip_summary_contains_reason(self) -> None:
        """Skipped node progress entry contains the routing reason."""
        definition = BlueprintDefinition(
            name="test",
            nodes={
                "outlook_fixer": _FailingNode("outlook_fixer"),
            },
            edges=[],
            entry_node="outlook_fixer",
        )
        gmail = _make_client()
        profile = _make_profile(clients=(gmail,))
        engine = BlueprintEngine(definition, audience_profile=profile)
        run = await engine.run(brief="Test", initial_html="<html></html>")

        assert run.progress[0].status == "skipped"
        assert "Word-engine" in run.progress[0].summary
