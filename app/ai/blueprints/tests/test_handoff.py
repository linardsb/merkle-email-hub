# pyright: reportReturnType=false, reportArgumentType=false
"""Tests for AgentHandoff propagation through the blueprint engine."""

import pytest

from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
from app.ai.blueprints.protocols import AgentHandoff, NodeContext, NodeResult, NodeType


class StubAgenticNode:
    """Agentic stub that emits a configurable handoff."""

    def __init__(
        self,
        name: str,
        handoff: AgentHandoff | None = None,
        html: str = "<p>ok</p>",
    ) -> None:
        self._name = name
        self._handoff = handoff
        self._html = html
        self.last_context: NodeContext | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        self.last_context = context
        return NodeResult(
            status="success",
            html=self._html,
            details="stub ok",
            handoff=self._handoff,
        )


class StubDeterministicNode:
    """Deterministic stub that passes through HTML."""

    def __init__(self, name: str) -> None:
        self._name = name
        self.last_context: NodeContext | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        self.last_context = context
        return NodeResult(status="success", html=context.html, details="pass-through")


class TestHandoffPropagation:
    """Tests that AgentHandoff flows through the engine correctly."""

    @pytest.mark.asyncio()
    async def test_agentic_node_handoff_propagated_to_next_node(self) -> None:
        """Handoff from node A is visible in node B's context metadata."""
        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>gen</p>",
            decisions=("Generated 10 chars",),
            warnings=("Missing logo",),
            component_refs=("header",),
            confidence=0.85,
        )
        node_a = StubAgenticNode("scaffolder", handoff=handoff, html="<p>gen</p>")
        node_b = StubAgenticNode("dark_mode", html="<p>dm</p>")

        definition = BlueprintDefinition(
            name="handoff-test",
            nodes={"scaffolder": node_a, "dark_mode": node_b},
            edges=[Edge(from_node="scaffolder", to_node="dark_mode", condition="always")],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        await engine.run(brief="test")

        assert node_b.last_context is not None
        upstream = node_b.last_context.metadata.get("upstream_handoff")
        assert isinstance(upstream, AgentHandoff)
        assert upstream.agent_name == "scaffolder"
        assert upstream.warnings == ("Missing logo",)
        assert upstream.confidence == 0.85

    @pytest.mark.asyncio()
    async def test_deterministic_node_does_not_clear_handoff(self) -> None:
        """A deterministic node between two agentic nodes preserves _last_handoff."""
        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>gen</p>",
            confidence=0.9,
        )
        node_a = StubAgenticNode("scaffolder", handoff=handoff, html="<p>gen</p>")
        node_mid = StubDeterministicNode("gate")
        node_b = StubAgenticNode("dark_mode", html="<p>dm</p>")

        definition = BlueprintDefinition(
            name="preserve-test",
            nodes={"scaffolder": node_a, "gate": node_mid, "dark_mode": node_b},
            edges=[
                Edge(from_node="scaffolder", to_node="gate", condition="always"),
                Edge(from_node="gate", to_node="dark_mode", condition="always"),
            ],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        # Handoff should still be available after deterministic node
        assert node_b.last_context is not None
        upstream = node_b.last_context.metadata.get("upstream_handoff")
        assert isinstance(upstream, AgentHandoff)
        assert upstream.agent_name == "scaffolder"

        # Run also exposes last handoff (from dark_mode, which has no handoff → still scaffolder's)
        assert run._last_handoff is not None
        assert run._last_handoff.agent_name == "scaffolder"

    @pytest.mark.asyncio()
    async def test_handoff_appears_in_run_after_completion(self) -> None:
        """BlueprintRun._last_handoff is set after the run completes."""
        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>done</p>",
            decisions=("Built layout",),
            confidence=0.95,
        )
        node = StubAgenticNode("scaffolder", handoff=handoff)

        definition = BlueprintDefinition(
            name="run-handoff",
            nodes={"scaffolder": node},
            edges=[],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        assert run._last_handoff is not None
        assert run._last_handoff.agent_name == "scaffolder"
        assert run._last_handoff.confidence == 0.95

    @pytest.mark.asyncio()
    async def test_no_handoff_backward_compatible(self) -> None:
        """Nodes that don't emit handoff work exactly as before."""
        node = StubAgenticNode("scaffolder", handoff=None, html="<p>legacy</p>")

        definition = BlueprintDefinition(
            name="compat-test",
            nodes={"scaffolder": node},
            edges=[],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        assert run.status == "completed"
        assert run.html == "<p>legacy</p>"
        assert run._last_handoff is None

    @pytest.mark.asyncio()
    async def test_handoff_history_accumulates_across_nodes(self) -> None:
        """Each agentic node's handoff is appended to _handoff_history."""
        handoff_a = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>scaffold</p>",
            decisions=("Built layout",),
            confidence=0.9,
        )
        handoff_b = AgentHandoff(
            agent_name="dark_mode",
            artifact="<p>dark</p>",
            decisions=("Added dark mode",),
            confidence=0.85,
        )
        node_a = StubAgenticNode("scaffolder", handoff=handoff_a, html="<p>scaffold</p>")
        node_b = StubAgenticNode("dark_mode", handoff=handoff_b, html="<p>dark</p>")

        definition = BlueprintDefinition(
            name="history-test",
            nodes={"scaffolder": node_a, "dark_mode": node_b},
            edges=[Edge(from_node="scaffolder", to_node="dark_mode", condition="always")],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        assert len(run._handoff_history) == 2
        assert run._handoff_history[0].agent_name == "scaffolder"
        assert run._handoff_history[1].agent_name == "dark_mode"
        assert run._last_handoff == handoff_b

    @pytest.mark.asyncio()
    async def test_handoff_history_injected_into_context(self) -> None:
        """Downstream nodes receive full handoff_history in context metadata."""
        handoff_a = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>scaffold</p>",
            decisions=("Built layout",),
            confidence=0.9,
        )
        node_a = StubAgenticNode("scaffolder", handoff=handoff_a, html="<p>scaffold</p>")
        node_b = StubAgenticNode("dark_mode", html="<p>dark</p>")

        definition = BlueprintDefinition(
            name="ctx-history-test",
            nodes={"scaffolder": node_a, "dark_mode": node_b},
            edges=[Edge(from_node="scaffolder", to_node="dark_mode", condition="always")],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        await engine.run(brief="test")

        assert node_b.last_context is not None
        history = node_b.last_context.metadata.get("handoff_history")
        assert isinstance(history, list)
        assert len(history) == 1
        assert history[0].agent_name == "scaffolder"

    @pytest.mark.asyncio()
    async def test_on_handoff_callback_fires(self) -> None:
        """The on_handoff memory callback is invoked for each agentic handoff."""
        recorded: list[tuple[AgentHandoff, str, int | None]] = []

        async def mock_callback(handoff: AgentHandoff, run_id: str, project_id: int | None) -> None:
            recorded.append((handoff, run_id, project_id))

        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>gen</p>",
            confidence=0.9,
        )
        node = StubAgenticNode("scaffolder", handoff=handoff)

        definition = BlueprintDefinition(
            name="callback-test",
            nodes={"scaffolder": node},
            edges=[],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition, on_handoff=mock_callback, project_id=42)
        run = await engine.run(brief="test")

        assert len(recorded) == 1
        assert recorded[0][0].agent_name == "scaffolder"
        assert recorded[0][1] == run.run_id
        assert recorded[0][2] == 42

    @pytest.mark.asyncio()
    async def test_on_handoff_callback_failure_does_not_crash(self) -> None:
        """A failing on_handoff callback is swallowed — engine continues."""

        async def failing_callback(
            handoff: AgentHandoff, run_id: str, project_id: int | None
        ) -> None:
            raise RuntimeError("memory write failed")

        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>gen</p>",
            confidence=0.9,
        )
        node = StubAgenticNode("scaffolder", handoff=handoff)

        definition = BlueprintDefinition(
            name="fail-callback-test",
            nodes={"scaffolder": node},
            edges=[],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition, on_handoff=failing_callback)
        run = await engine.run(brief="test")

        assert run.status == "completed"
        assert run._last_handoff is not None
