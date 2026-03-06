# pyright: reportReturnType=false, reportArgumentType=false
"""Tests for the BlueprintEngine state machine."""

import pytest

from app.ai.blueprints.engine import (
    MAX_SELF_CORRECTION_ROUNDS,
    BlueprintDefinition,
    BlueprintEngine,
    Edge,
)
from app.ai.blueprints.exceptions import BlueprintEscalatedError, BlueprintNodeError
from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType

# ── Stub nodes ──


class StubNode:
    """Configurable stub node for engine tests."""

    def __init__(
        self,
        name: str,
        node_type: NodeType = "deterministic",
        result: NodeResult | None = None,
    ) -> None:
        self._name = name
        self._node_type = node_type
        self._result = result or NodeResult(status="success", html="<p>ok</p>", details="stub ok")
        self.call_count = 0
        self.last_context: NodeContext | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return self._node_type

    async def execute(self, context: NodeContext) -> NodeResult:
        self.call_count += 1
        self.last_context = context
        return self._result


class FailThenPassNode:
    """Agentic node that fails N times, then passes."""

    def __init__(self, name: str, fail_count: int = 1) -> None:
        self._name = name
        self._fail_count = fail_count
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, _context: NodeContext) -> NodeResult:
        self.call_count += 1
        if self.call_count <= self._fail_count:
            return NodeResult(status="failed", details="not ready yet")
        return NodeResult(status="success", html="<p>fixed</p>", details="ok")


# ── Tests ──


class TestLinearExecution:
    """Tests for simple linear graph execution (no loops)."""

    @pytest.mark.asyncio()
    async def test_three_node_linear(self) -> None:
        node_a = StubNode("a", result=NodeResult(status="success", html="<p>a</p>", details="a ok"))
        node_b = StubNode("b", result=NodeResult(status="success", html="<p>b</p>", details="b ok"))
        node_c = StubNode("c", result=NodeResult(status="success", html="<p>c</p>", details="c ok"))

        definition = BlueprintDefinition(
            name="linear",
            nodes={"a": node_a, "b": node_b, "c": node_c},
            edges=[
                Edge(from_node="a", to_node="b", condition="always"),
                Edge(from_node="b", to_node="c", condition="always"),
            ],
            entry_node="a",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test brief")

        assert run.status == "completed"
        assert run.html == "<p>c</p>"
        assert len(run.progress) == 3
        assert [p.node_name for p in run.progress] == ["a", "b", "c"]
        assert all(p.status == "success" for p in run.progress)

    @pytest.mark.asyncio()
    async def test_single_node(self) -> None:
        node = StubNode("solo", result=NodeResult(status="success", html="<p>solo</p>"))

        definition = BlueprintDefinition(
            name="solo",
            nodes={"solo": node},
            edges=[],
            entry_node="solo",
        )

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        assert run.html == "<p>solo</p>"
        assert len(run.progress) == 1


class TestSelfCorrection:
    """Tests for QA fail → recovery → fix → QA pass loop."""

    @pytest.mark.asyncio()
    async def test_qa_fail_triggers_recovery(self) -> None:
        scaffolder = StubNode(
            "scaffolder", "agentic", NodeResult(status="success", html="<p>gen</p>")
        )
        qa_gate = StubNode(
            "qa_gate", result=NodeResult(status="failed", details="dark_mode: missing meta")
        )
        recovery = StubNode(
            "recovery_router",
            result=NodeResult(status="success", html="<p>gen</p>", details="route_to:scaffolder"),
        )
        # Second scaffolder call succeeds (reuse same stub — it always returns success)

        definition = BlueprintDefinition(
            name="correction",
            nodes={"scaffolder": scaffolder, "qa_gate": qa_gate, "recovery_router": recovery},
            edges=[
                Edge(from_node="scaffolder", to_node="qa_gate", condition="always"),
                Edge(from_node="qa_gate", to_node="recovery_router", condition="qa_fail"),
                Edge(
                    from_node="recovery_router",
                    to_node="scaffolder",
                    condition="route_to",
                    route_value="scaffolder",
                ),
            ],
            entry_node="scaffolder",
        )

        engine = BlueprintEngine(definition)
        # Will loop: scaffolder → qa_gate(fail) → recovery → scaffolder → qa_gate(fail) → recovery → scaffolder(escalated)
        with pytest.raises(BlueprintEscalatedError):
            await engine.run(brief="test")

        # scaffolder should have been called MAX_SELF_CORRECTION_ROUNDS times before escalation
        assert scaffolder.call_count == MAX_SELF_CORRECTION_ROUNDS


class TestEscalation:
    """Tests for escalation when max self-correction rounds exhausted."""

    @pytest.mark.asyncio()
    async def test_escalation_raises(self) -> None:
        always_fail = StubNode(
            "fixer",
            "agentic",
            NodeResult(status="success", html="<p>bad</p>"),
        )
        qa_gate = StubNode(
            "qa_gate",
            result=NodeResult(status="failed", details="html_validation: broken"),
        )
        recovery = StubNode(
            "recovery_router",
            result=NodeResult(status="success", details="route_to:fixer"),
        )

        definition = BlueprintDefinition(
            name="escalate",
            nodes={"fixer": always_fail, "qa_gate": qa_gate, "recovery_router": recovery},
            edges=[
                Edge(from_node="fixer", to_node="qa_gate", condition="always"),
                Edge(from_node="qa_gate", to_node="recovery_router", condition="qa_fail"),
                Edge(
                    from_node="recovery_router",
                    to_node="fixer",
                    condition="route_to",
                    route_value="fixer",
                ),
            ],
            entry_node="fixer",
        )

        engine = BlueprintEngine(definition)
        with pytest.raises(BlueprintEscalatedError) as exc_info:
            await engine.run(brief="test")

        assert exc_info.value.node_name == "fixer"
        assert exc_info.value.iterations == MAX_SELF_CORRECTION_ROUNDS


class TestProgressAnchor:
    """Tests for the compact progress summary injected into retry context."""

    @pytest.mark.asyncio()
    async def test_progress_anchor_in_retry_context(self) -> None:
        call_count = 0
        captured_contexts: list[NodeContext] = []

        class TrackingNode:
            @property
            def name(self) -> str:
                return "tracker"

            @property
            def node_type(self) -> NodeType:
                return "agentic"

            async def execute(self, context: NodeContext) -> NodeResult:
                nonlocal call_count
                call_count += 1
                captured_contexts.append(context)
                return NodeResult(status="success", html="<p>ok</p>")

        qa_gate_calls = 0

        class FailOnceQA:
            @property
            def name(self) -> str:
                return "qa_gate"

            @property
            def node_type(self) -> NodeType:
                return "deterministic"

            async def execute(self, context: NodeContext) -> NodeResult:
                nonlocal qa_gate_calls
                qa_gate_calls += 1
                if qa_gate_calls == 1:
                    return NodeResult(status="failed", details="check_a: issue")
                return NodeResult(status="success", html=context.html, details="all passed")

        recovery = StubNode(
            "recovery_router",
            result=NodeResult(status="success", details="route_to:tracker"),
        )

        tracker = TrackingNode()
        qa = FailOnceQA()

        definition = BlueprintDefinition(
            name="anchor-test",
            nodes={"tracker": tracker, "qa_gate": qa, "recovery_router": recovery},
            edges=[
                Edge(from_node="tracker", to_node="qa_gate", condition="always"),
                Edge(from_node="qa_gate", to_node="recovery_router", condition="qa_fail"),
                Edge(from_node="qa_gate", to_node="done_stub", condition="success"),
                Edge(
                    from_node="recovery_router",
                    to_node="tracker",
                    condition="route_to",
                    route_value="tracker",
                ),
            ],
            entry_node="tracker",
        )
        # Add a terminal node so success can resolve
        terminal = StubNode("done_stub")
        definition.nodes["done_stub"] = terminal

        engine = BlueprintEngine(definition)
        await engine.run(brief="test")

        # Second call (retry) should have progress_anchor in metadata
        assert len(captured_contexts) == 2
        assert captured_contexts[0].iteration == 0
        assert captured_contexts[1].iteration == 1
        assert "PROGRESS" in str(captured_contexts[1].metadata.get("progress_anchor", ""))


class TestEdgeResolution:
    """Tests for edge resolution with metadata-based routing."""

    @pytest.mark.asyncio()
    async def test_route_to_dark_mode(self) -> None:
        scaffolder = StubNode(
            "scaffolder", "agentic", NodeResult(status="success", html="<p>gen</p>")
        )
        recovery = StubNode(
            "recovery_router", result=NodeResult(status="success", details="route_to:dark_mode")
        )
        dark_mode = StubNode("dark_mode", "agentic", NodeResult(status="success", html="<p>dm</p>"))

        # After dark_mode, QA passes
        qa_calls = 0

        class PassSecondQA:
            @property
            def name(self) -> str:
                return "qa_gate"

            @property
            def node_type(self) -> NodeType:
                return "deterministic"

            async def execute(self, context: NodeContext) -> NodeResult:
                nonlocal qa_calls
                qa_calls += 1
                if qa_calls == 1:
                    return NodeResult(status="failed", details="dark_mode: no meta")
                return NodeResult(status="success", html=context.html, details="all passed")

        build = StubNode("maizzle_build", result=NodeResult(status="success", html="<p>built</p>"))

        qa = PassSecondQA()

        definition = BlueprintDefinition(
            name="routing-test",
            nodes={
                "scaffolder": scaffolder,
                "qa_gate": qa,
                "recovery_router": recovery,
                "dark_mode": dark_mode,
                "maizzle_build": build,
            },
            edges=[
                Edge(from_node="scaffolder", to_node="qa_gate", condition="always"),
                Edge(from_node="qa_gate", to_node="maizzle_build", condition="success"),
                Edge(from_node="qa_gate", to_node="recovery_router", condition="qa_fail"),
                Edge(
                    from_node="recovery_router",
                    to_node="dark_mode",
                    condition="route_to",
                    route_value="dark_mode",
                ),
                Edge(
                    from_node="recovery_router",
                    to_node="scaffolder",
                    condition="route_to",
                    route_value="scaffolder",
                ),
                Edge(from_node="dark_mode", to_node="qa_gate", condition="always"),
                Edge(from_node="maizzle_build", to_node="done", condition="always"),
            ],
            entry_node="scaffolder",
        )
        done = StubNode("done")
        definition.nodes["done"] = done

        engine = BlueprintEngine(definition)
        run = await engine.run(brief="test")

        # Path: scaffolder → qa(fail) → recovery → dark_mode → qa(pass) → build → done
        names = [p.node_name for p in run.progress]
        assert names == [
            "scaffolder",
            "qa_gate",
            "recovery_router",
            "dark_mode",
            "qa_gate",
            "maizzle_build",
            "done",
        ]
        assert dark_mode.call_count == 1


class TestNodeError:
    """Tests for node execution errors."""

    @pytest.mark.asyncio()
    async def test_node_exception_wraps_in_blueprint_node_error(self) -> None:
        class CrashNode:
            @property
            def name(self) -> str:
                return "crasher"

            @property
            def node_type(self) -> NodeType:
                return "deterministic"

            async def execute(self, context: NodeContext) -> NodeResult:  # noqa: ARG002
                msg = "Something went wrong"
                raise RuntimeError(msg)

        definition = BlueprintDefinition(
            name="crash",
            nodes={"crasher": CrashNode()},
            edges=[],
            entry_node="crasher",
        )

        engine = BlueprintEngine(definition)
        with pytest.raises(BlueprintNodeError, match=r"crasher.*execution failed"):
            await engine.run(brief="test")
