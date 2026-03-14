# pyright: reportReturnType=false, reportArgumentType=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportIndexIssue=false, reportUnknownArgumentType=false
"""Tests for context budget optimisation (11.22.6).

Covers: compact() methods, compact_handoff_history, summarize_trajectory,
ContextBudget defaults, remaining_budget, and engine integration.
"""

from __future__ import annotations

import json
from typing import cast

import pytest

from app.ai.agents.context_budget import (
    ECONOMY_MODE_THRESHOLD,
    ContextBudget,
    compact_handoff_history,
    summarize_trajectory,
)
from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, BlueprintRun, Edge
from app.ai.blueprints.protocols import (
    AgentHandoff,
    HandoffStatus,
    NodeContext,
    NodeResult,
    NodeType,
    StructuredFailure,
)
from app.ai.blueprints.schemas import BlueprintProgress

# ---------------------------------------------------------------------------
# Stubs (reused from test_handoff.py pattern)
# ---------------------------------------------------------------------------


class _StubAgenticNode:
    def __init__(
        self,
        name: str,
        handoff: AgentHandoff | None = None,
        html: str = "<p>ok</p>",
        usage: dict[str, int] | None = None,
    ) -> None:
        self._name = name
        self._handoff = handoff
        self._html = html
        self._usage = usage
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
            usage=self._usage,
        )


# ---------------------------------------------------------------------------
# 1. AgentHandoff.compact()
# ---------------------------------------------------------------------------


class TestAgentHandoffCompact:
    def test_compact_strips_artifact(self) -> None:
        h = AgentHandoff(
            agent_name="scaffolder",
            artifact="<div>huge html</div>",
            decisions=("Built layout",),
            warnings=("Missing logo",),
            component_refs=("header",),
            confidence=0.9,
        )
        c = h.compact()
        assert c.artifact == ""
        assert c.agent_name == "scaffolder"
        assert c.decisions == ("Built layout",)
        assert c.warnings == ("Missing logo",)
        assert c.component_refs == ("header",)
        assert c.confidence == 0.9
        assert c.status == HandoffStatus.OK

    def test_compact_preserves_status(self) -> None:
        h = AgentHandoff(status=HandoffStatus.WARNING, agent_name="dark_mode", artifact="big")
        c = h.compact()
        assert c.status == HandoffStatus.WARNING
        assert c.artifact == ""

    def test_compact_already_empty_artifact(self) -> None:
        h = AgentHandoff(agent_name="test", artifact="")
        c = h.compact()
        assert c.artifact == ""
        assert c.agent_name == "test"


# ---------------------------------------------------------------------------
# 2. StructuredFailure.compact()
# ---------------------------------------------------------------------------


class TestStructuredFailureCompact:
    def test_compact_strips_details(self) -> None:
        f = StructuredFailure(
            check_name="html_validation",
            score=0.3,
            details="Long detailed error description with HTML snippets...",
            suggested_agent="outlook_fixer",
            priority=1,
            severity="error",
        )
        c = f.compact()
        assert c.details == ""
        assert c.check_name == "html_validation"
        assert c.score == 0.3
        assert c.suggested_agent == "outlook_fixer"
        assert c.priority == 1
        assert c.severity == "error"


# ---------------------------------------------------------------------------
# 3. compact_handoff_history()
# ---------------------------------------------------------------------------


class TestCompactHandoffHistory:
    def test_empty_list(self) -> None:
        assert compact_handoff_history([]) == []

    def test_single_item_normal_mode(self) -> None:
        h = AgentHandoff(agent_name="scaffolder", artifact="<p>big</p>")
        result = compact_handoff_history([h])
        assert len(result) == 1
        assert result[0].artifact == "<p>big</p>"  # preserved

    def test_normal_mode_compacts_all_but_last(self) -> None:
        h1 = AgentHandoff(agent_name="scaffolder", artifact="<p>first</p>")
        h2 = AgentHandoff(agent_name="dark_mode", artifact="<p>second</p>")
        h3 = AgentHandoff(agent_name="content", artifact="<p>third</p>")
        result = compact_handoff_history([h1, h2, h3])
        assert len(result) == 3
        assert result[0].artifact == ""  # compacted
        assert result[1].artifact == ""  # compacted
        assert result[2].artifact == "<p>third</p>"  # last preserved

    def test_economy_mode_compacts_all(self) -> None:
        h1 = AgentHandoff(agent_name="scaffolder", artifact="<p>first</p>")
        h2 = AgentHandoff(agent_name="dark_mode", artifact="<p>second</p>")
        result = compact_handoff_history([h1, h2], economy=True)
        assert len(result) == 2
        assert result[0].artifact == ""
        assert result[1].artifact == ""


# ---------------------------------------------------------------------------
# 4. summarize_trajectory()
# ---------------------------------------------------------------------------


class TestSummarizeTrajectory:
    def test_basic_trajectory(self) -> None:
        run = BlueprintRun()
        run.progress = [
            BlueprintProgress(
                node_name="scaffolder",
                node_type="agentic",
                status="success",
                iteration=0,
                summary="ok",
                duration_ms=100.0,
            ),
            BlueprintProgress(
                node_name="qa_gate",
                node_type="deterministic",
                status="success",
                iteration=0,
                summary="passed",
                duration_ms=50.0,
            ),
        ]
        run.qa_passed = True

        result = json.loads(summarize_trajectory(run))
        assert len(result["passes"]) == 2
        assert result["qa_passed"] is True
        assert "retries" not in result

    def test_trajectory_with_retries(self) -> None:
        run = BlueprintRun()
        run.progress = [
            BlueprintProgress(
                node_name="scaffolder",
                node_type="agentic",
                status="success",
                iteration=0,
                summary="ok",
                duration_ms=100.0,
            ),
        ]
        run.iteration_counts = {"scaffolder": 2, "dark_mode": 1}
        run.qa_passed = False

        result = json.loads(summarize_trajectory(run))
        assert result["retries"] == {"scaffolder": 2}
        assert result["qa_passed"] is False


# ---------------------------------------------------------------------------
# 5. ContextBudget defaults
# ---------------------------------------------------------------------------


class TestContextBudget:
    def test_defaults(self) -> None:
        b = ContextBudget()
        assert b.system_prompt_max == 4000
        assert b.skill_docs_max == 2000
        assert b.handoff_summary_max == 1000
        assert b.user_message_max == 4000
        assert b.total_max == 12000

    def test_frozen(self) -> None:
        b = ContextBudget()
        with pytest.raises(AttributeError):
            b.total_max = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6. BlueprintRun.remaining_budget
# ---------------------------------------------------------------------------


class TestRemainingBudget:
    def test_full_budget(self) -> None:
        run = BlueprintRun(token_budget=100_000)
        assert run.remaining_budget == 1.0

    def test_half_used(self) -> None:
        run = BlueprintRun(token_budget=100_000)
        run.model_usage["total_tokens"] = 50_000
        assert run.remaining_budget == pytest.approx(0.5)

    def test_fully_exhausted(self) -> None:
        run = BlueprintRun(token_budget=100_000)
        run.model_usage["total_tokens"] = 100_000
        assert run.remaining_budget == 0.0

    def test_over_budget_clamps_to_zero(self) -> None:
        run = BlueprintRun(token_budget=100_000)
        run.model_usage["total_tokens"] = 150_000
        assert run.remaining_budget == 0.0

    def test_zero_budget(self) -> None:
        run = BlueprintRun(token_budget=0)
        assert run.remaining_budget == 0.0


# ---------------------------------------------------------------------------
# 7. Engine integration — handoff compaction in normal mode
# ---------------------------------------------------------------------------


class TestEngineContextCompaction:
    @pytest.mark.asyncio()
    async def test_normal_mode_compacts_history_except_last(self) -> None:
        """With plenty of budget, all-but-last handoffs are compacted."""
        h1 = AgentHandoff(agent_name="scaffolder", artifact="<p>big1</p>", confidence=0.9)
        h2 = AgentHandoff(agent_name="dark_mode", artifact="<p>big2</p>", confidence=0.8)
        node_a = _StubAgenticNode("scaffolder", handoff=h1, html="<p>a</p>")
        node_b = _StubAgenticNode("dark_mode", handoff=h2, html="<p>b</p>")
        node_c = _StubAgenticNode("content", html="<p>c</p>")

        defn = BlueprintDefinition(
            name="compact-test",
            nodes={"scaffolder": node_a, "dark_mode": node_b, "content": node_c},
            edges=[
                Edge(from_node="scaffolder", to_node="dark_mode", condition="always"),
                Edge(from_node="dark_mode", to_node="content", condition="always"),
            ],
            entry_node="scaffolder",
        )
        engine = BlueprintEngine(defn)
        await engine.run(brief="test")

        assert node_c.last_context is not None
        history = cast(list[AgentHandoff], node_c.last_context.metadata["handoff_history"])
        assert len(history) == 2
        # First is compacted (no artifact), second preserved
        assert history[0].artifact == ""
        assert history[1].artifact == "<p>big2</p>"

        # upstream_handoff is latest, not compacted in normal mode
        upstream = cast(AgentHandoff, node_c.last_context.metadata["upstream_handoff"])
        assert upstream.artifact == "<p>big2</p>"

    @pytest.mark.asyncio()
    async def test_economy_mode_compacts_all(self) -> None:
        """When budget is low, all handoffs are compacted including upstream."""
        h = AgentHandoff(agent_name="scaffolder", artifact="<p>big</p>", confidence=0.9)
        # Use high token usage to trigger economy mode
        node_a = _StubAgenticNode(
            "scaffolder",
            handoff=h,
            html="<p>a</p>",
            usage={"prompt_tokens": 200_000, "completion_tokens": 200_000, "total_tokens": 400_000},
        )
        node_b = _StubAgenticNode("dark_mode", html="<p>b</p>")

        defn = BlueprintDefinition(
            name="economy-test",
            nodes={"scaffolder": node_a, "dark_mode": node_b},
            edges=[Edge(from_node="scaffolder", to_node="dark_mode", condition="always")],
            entry_node="scaffolder",
        )
        engine = BlueprintEngine(defn)
        run = await engine.run(brief="test")

        # Verify economy mode was triggered
        assert run.remaining_budget < ECONOMY_MODE_THRESHOLD

        assert node_b.last_context is not None
        # upstream_handoff compacted in economy mode
        upstream = cast(AgentHandoff, node_b.last_context.metadata["upstream_handoff"])
        assert upstream.artifact == ""

        # economy_mode flag set
        assert node_b.last_context.metadata.get("economy_mode") is True

        # trajectory_summary present
        assert "trajectory_summary" in node_b.last_context.metadata
        summary = json.loads(cast(str, node_b.last_context.metadata["trajectory_summary"]))
        assert summary["passes"][0]["node"] == "scaffolder"
