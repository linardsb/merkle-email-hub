# pyright: reportReturnType=false, reportArgumentType=false
"""Tests for inline judge adapter."""

import pytest

from app.ai.agents.evals.judges.schemas import CriterionResult, JudgeVerdict
from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, BlueprintRun, Edge
from app.ai.blueprints.protocols import NodeContext, NodeResult, NodeType, StructuredFailure

# ── Unit tests for _build_judge_input ──


class TestBuildJudgeInput:
    """Tests for _build_judge_input."""

    def test_builds_input_from_context(self) -> None:
        from app.ai.blueprints.inline_judge import _build_judge_input

        ctx = NodeContext(
            brief="Build a promo email",
            qa_failures=["dark_mode: missing meta tags"],
            iteration=1,
        )
        run = BlueprintRun()
        run.qa_failure_details = [
            StructuredFailure(
                check_name="dark_mode",
                score=0.3,
                details="Missing color-scheme meta tag",
                suggested_agent="dark_mode",
                priority=1,
            ),
        ]

        result = _build_judge_input("dark_mode", ctx, "<html>fixed</html>", run)

        assert result.agent == "dark_mode"
        assert result.trace_id.startswith("inline-")
        assert result.input_data["brief"] == "Build a promo email"
        assert result.output_data is not None
        assert result.output_data["html"] == "<html>fixed</html>"
        assert result.expected_challenges == ["dark_mode"]

    def test_empty_qa_failures(self) -> None:
        from app.ai.blueprints.inline_judge import _build_judge_input

        ctx = NodeContext(brief="test", iteration=1)
        run = BlueprintRun()

        result = _build_judge_input("scaffolder", ctx, "<html></html>", run)

        assert result.expected_challenges == []
        assert result.input_data["qa_failures"] == []


# ── Unit tests for run_inline_judge ──


class TestRunInlineJudge:
    """Tests for run_inline_judge (mocked LLM calls)."""

    @pytest.mark.asyncio()
    async def test_returns_none_for_unknown_agent(self) -> None:
        from app.ai.blueprints.inline_judge import run_inline_judge

        ctx = NodeContext(brief="test", iteration=1)
        run = BlueprintRun()

        result = await run_inline_judge("nonexistent_agent", ctx, "<html></html>", run)

        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_on_provider_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Judge returns None (failure-safe) when LLM call fails."""
        from app.ai.blueprints import inline_judge

        class FakeProvider:
            async def complete(self, *args: object, **kwargs: object) -> None:
                raise RuntimeError("Provider unavailable")

        class FakeRegistry:
            def get_llm(self, name: str) -> FakeProvider:
                return FakeProvider()

        monkeypatch.setattr(inline_judge, "get_registry", lambda: FakeRegistry())

        ctx = NodeContext(brief="test", iteration=1)
        run = BlueprintRun()

        result = await inline_judge.run_inline_judge("scaffolder", ctx, "<html></html>", run)

        assert result is None


# ── Engine integration tests ──


class StubAgenticNode:
    """Agentic stub with configurable results per call."""

    def __init__(self, name: str, results: list[NodeResult] | None = None) -> None:
        self._name = name
        self._results = results or [
            NodeResult(status="success", html="<p>ok</p>", details="stub ok")
        ]
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        idx = min(self.call_count, len(self._results) - 1)
        self.call_count += 1
        return self._results[idx]


class StubQAGateNode:
    """QA gate stub: fails first call, passes subsequent."""

    def __init__(self, fail_count: int = 1) -> None:
        self._fail_count = fail_count
        self.call_count = 0

    @property
    def name(self) -> str:
        return "qa_gate"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        self.call_count += 1
        if self.call_count <= self._fail_count:
            return NodeResult(
                status="failed",
                html=context.html,
                details="dark_mode: missing meta",
                structured_failures=(
                    StructuredFailure(
                        check_name="dark_mode",
                        score=0.3,
                        details="Missing color-scheme",
                        suggested_agent="dark_mode",
                        priority=1,
                    ),
                ),
            )
        return NodeResult(status="success", html=context.html, details="all checks pass")


class StubRecoveryRouterToAgent:
    """Recovery router that routes back to the same agentic node."""

    def __init__(self, target_node: str) -> None:
        self._target = target_node

    @property
    def name(self) -> str:
        return "recovery_router"

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        return NodeResult(
            status="failed",
            html=context.html,
            details=f"route_to:{self._target}",
        )


def _build_retry_blueprint(
    agent_results: list[NodeResult],
) -> tuple[BlueprintDefinition, StubAgenticNode, StubQAGateNode]:
    """Build a blueprint: dark_mode_node → qa_gate → recovery_router → dark_mode_node (retry).

    The agent runs first (iteration 0), QA fails, recovery routes back to
    the same agent (iteration 1) — triggering the inline judge.
    """
    qa_gate = StubQAGateNode(fail_count=1)
    recovery_router = StubRecoveryRouterToAgent("dark_mode_node")
    agent = StubAgenticNode("dark_mode_node", agent_results)

    definition = BlueprintDefinition(
        name="retry-test",
        nodes={
            "dark_mode_node": agent,
            "qa_gate": qa_gate,
            "recovery_router": recovery_router,
        },
        edges=[
            Edge(from_node="dark_mode_node", to_node="qa_gate", condition="success"),
            Edge(from_node="qa_gate", to_node="recovery_router", condition="qa_fail"),
            Edge(
                from_node="recovery_router",
                to_node="dark_mode_node",
                condition="route_to",
                route_value="dark_mode_node",
            ),
        ],
        entry_node="dark_mode_node",
    )
    return definition, agent, qa_gate


class TestInlineJudgeIntegration:
    """Tests for inline judge integration in the engine loop."""

    @pytest.mark.asyncio()
    async def test_judge_on_retry_rejects_bad_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When judge fails a retry, run status becomes needs_review."""
        failing_verdict = JudgeVerdict(
            trace_id="inline-test",
            agent="dark_mode",
            overall_pass=False,
            criteria_results=[
                CriterionResult(criterion="color_scheme", passed=False, reasoning="bad")
            ],
        )

        async def mock_run_inline_judge(
            agent_name: str, context: object, html_output: str, run: object
        ) -> JudgeVerdict:
            return failing_verdict

        # Patch the inline judge at the engine module level (lazy import target)
        import app.ai.blueprints.inline_judge as ij_mod

        monkeypatch.setattr(ij_mod, "run_inline_judge", mock_run_inline_judge)

        agent_results = [
            NodeResult(status="success", html="<p>initial</p>", details="first pass"),
            NodeResult(status="success", html="<p>fixed</p>", details="fix attempt"),
        ]
        definition, _agent, _qa_gate = _build_retry_blueprint(agent_results)

        engine = BlueprintEngine(definition, judge_on_retry=True)
        run = await engine.run(brief="test email")

        assert run.status == "needs_review"
        assert run.judge_verdict is not None
        assert run.judge_verdict.overall_pass is False

    @pytest.mark.asyncio()
    async def test_judge_on_retry_approves_good_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When judge approves a retry, it proceeds to QA gate normally."""
        passing_verdict = JudgeVerdict(
            trace_id="inline-test",
            agent="dark_mode",
            overall_pass=True,
            criteria_results=[
                CriterionResult(criterion="color_scheme", passed=True, reasoning="good")
            ],
        )

        async def mock_run_inline_judge(
            agent_name: str, context: object, html_output: str, run: object
        ) -> JudgeVerdict:
            return passing_verdict

        import app.ai.blueprints.inline_judge as ij_mod

        monkeypatch.setattr(ij_mod, "run_inline_judge", mock_run_inline_judge)

        agent_results = [
            NodeResult(status="success", html="<p>initial</p>", details="first pass"),
            NodeResult(status="success", html="<p>fixed</p>", details="fix attempt"),
        ]
        definition, _agent, qa_gate = _build_retry_blueprint(agent_results)
        # Make QA gate pass on second call (after the judge-approved retry)
        qa_gate._fail_count = 1

        engine = BlueprintEngine(definition, judge_on_retry=True)
        run = await engine.run(brief="test email")

        # Judge approved, then QA gate ran again — it passes the second time
        assert run.judge_verdict is not None
        assert run.judge_verdict.overall_pass is True
        assert qa_gate.call_count == 2  # Called once (fail), then after fixer (pass)

    @pytest.mark.asyncio()
    async def test_judge_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When judge_on_retry=False (default), no judge is called."""
        judge_called = False

        async def mock_run_inline_judge(
            agent_name: str, context: object, html_output: str, run: object
        ) -> None:
            nonlocal judge_called
            judge_called = True
            return None

        import app.ai.blueprints.inline_judge as ij_mod

        monkeypatch.setattr(ij_mod, "run_inline_judge", mock_run_inline_judge)

        agent_results = [
            NodeResult(status="success", html="<p>initial</p>", details="first pass"),
            NodeResult(status="success", html="<p>fixed</p>", details="fix attempt"),
        ]
        definition, _agent, qa_gate = _build_retry_blueprint(agent_results)
        qa_gate._fail_count = 1

        engine = BlueprintEngine(definition)  # judge_on_retry defaults to False
        await engine.run(brief="test email")

        assert not judge_called

    @pytest.mark.asyncio()
    async def test_judge_failure_safe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When judge call fails (returns None), pipeline continues normally."""

        async def mock_run_inline_judge(
            agent_name: str, context: object, html_output: str, run: object
        ) -> None:
            return None  # Simulates failure-safe return

        import app.ai.blueprints.inline_judge as ij_mod

        monkeypatch.setattr(ij_mod, "run_inline_judge", mock_run_inline_judge)

        agent_results = [
            NodeResult(status="success", html="<p>initial</p>", details="first pass"),
            NodeResult(status="success", html="<p>fixed</p>", details="fix attempt"),
        ]
        definition, _agent, qa_gate = _build_retry_blueprint(agent_results)
        qa_gate._fail_count = 1

        engine = BlueprintEngine(definition, judge_on_retry=True)
        run = await engine.run(brief="test email")

        # Judge returned None → pipeline continued to QA gate
        assert run.judge_verdict is None
        assert qa_gate.call_count == 2
