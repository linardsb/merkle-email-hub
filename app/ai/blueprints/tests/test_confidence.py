# pyright: reportReturnType=false, reportArgumentType=false
"""Tests for confidence-based routing in the blueprint engine."""

import pytest

from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, Edge
from app.ai.blueprints.protocols import AgentHandoff, NodeContext, NodeResult, NodeType


class StubAgenticNode:
    """Agentic stub with configurable handoff."""

    def __init__(self, name: str, handoff: AgentHandoff | None = None) -> None:
        self._name = name
        self._handoff = handoff
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:  # noqa: ARG002
        self.call_count += 1
        return NodeResult(
            status="success",
            html="<p>ok</p>",
            details="stub ok",
            handoff=self._handoff,
        )


class StubDeterministicNode:
    """Deterministic stub for pipeline continuation."""

    def __init__(self, name: str) -> None:
        self._name = name
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:  # noqa: ARG002
        self.call_count += 1
        return NodeResult(status="success", html="<p>gate</p>")


class TestConfidenceRouting:
    """Tests that low confidence triggers needs_review instead of continuing."""

    @pytest.mark.asyncio()
    async def test_low_confidence_triggers_needs_review(self) -> None:
        """Confidence 0.3 → run.status == 'needs_review', pipeline stops."""
        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>uncertain</p>",
            confidence=0.3,
        )
        scaffolder = StubAgenticNode("scaffolder", handoff=handoff)
        next_node = StubDeterministicNode("qa_gate")

        definition = BlueprintDefinition(
            name="low-conf",
            nodes={"scaffolder": scaffolder, "qa_gate": next_node},
            edges=[Edge(from_node="scaffolder", to_node="qa_gate", condition="always")],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        assert run.status == "needs_review"
        assert scaffolder.call_count == 1
        assert next_node.call_count == 0  # Pipeline stopped before reaching qa_gate

    @pytest.mark.asyncio()
    async def test_high_confidence_continues_normally(self) -> None:
        """Confidence 0.9 → normal flow continues to next node."""
        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>confident</p>",
            confidence=0.9,
        )
        scaffolder = StubAgenticNode("scaffolder", handoff=handoff)
        next_node = StubDeterministicNode("qa_gate")

        definition = BlueprintDefinition(
            name="high-conf",
            nodes={"scaffolder": scaffolder, "qa_gate": next_node},
            edges=[Edge(from_node="scaffolder", to_node="qa_gate", condition="always")],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        assert run.status == "completed"
        assert next_node.call_count == 1

    @pytest.mark.asyncio()
    async def test_none_confidence_continues_normally(self) -> None:
        """No confidence score → backward compatible, continues normally."""
        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>no-score</p>",
            confidence=None,
        )
        scaffolder = StubAgenticNode("scaffolder", handoff=handoff)
        next_node = StubDeterministicNode("done")

        definition = BlueprintDefinition(
            name="no-conf",
            nodes={"scaffolder": scaffolder, "done": next_node},
            edges=[Edge(from_node="scaffolder", to_node="done", condition="always")],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        assert run.status == "completed"
        assert next_node.call_count == 1

    @pytest.mark.asyncio()
    async def test_exact_threshold_continues(self) -> None:
        """Confidence exactly at threshold (0.5) → continues (threshold is strict <)."""
        handoff = AgentHandoff(
            agent_name="scaffolder",
            artifact="<p>borderline</p>",
            confidence=0.5,
        )
        scaffolder = StubAgenticNode("scaffolder", handoff=handoff)
        next_node = StubDeterministicNode("done")

        definition = BlueprintDefinition(
            name="threshold",
            nodes={"scaffolder": scaffolder, "done": next_node},
            edges=[Edge(from_node="scaffolder", to_node="done", condition="always")],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        assert run.status == "completed"
        assert next_node.call_count == 1

    @pytest.mark.asyncio()
    async def test_no_handoff_no_confidence_check(self) -> None:
        """Node without handoff → no confidence check, backward compat."""
        scaffolder = StubAgenticNode("scaffolder", handoff=None)
        next_node = StubDeterministicNode("done")

        definition = BlueprintDefinition(
            name="no-handoff",
            nodes={"scaffolder": scaffolder, "done": next_node},
            edges=[Edge(from_node="scaffolder", to_node="done", condition="always")],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        assert run.status == "completed"
        assert next_node.call_count == 1
