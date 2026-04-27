# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Per-LAYER unit tests for the ``_build_node_context`` pipeline.

Each LAYER is exercised in isolation with a minimal engine + stub node.
Tests cover: default no-op behaviour, the gating condition, and the dict
keys the layer is contracted to produce.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import patch

import pytest

from app.ai.blueprints.engine import (
    BlueprintDefinition,
    BlueprintEngine,
    BlueprintRun,
)
from app.ai.blueprints.protocols import (
    AgentHandoff,
    HandoffStatus,
    NodeContext,
    NodeType,
    StructuredFailure,
)


class _StubNode:
    """Minimal node stand-in for layer unit tests."""

    def __init__(self, name: str, node_type: NodeType = "agentic") -> None:
        self._name = name
        self._node_type = node_type

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return self._node_type


def _make_engine(**kwargs: object) -> BlueprintEngine:
    """Construct a BlueprintEngine with an empty blueprint, overrideable kwargs."""
    definition = BlueprintDefinition(name="test", nodes={}, edges=[], entry_node="entry")
    return BlueprintEngine(definition, **cast(dict[str, object], kwargs))  # type: ignore[arg-type]


@pytest.mark.asyncio
class TestLayer01AgentBudget:
    async def test_emits_agent_name_and_budget(self) -> None:
        engine = _make_engine()
        node = _StubNode("scaffolder_node")
        out = await engine._layer_01_agent_budget(NodeContext(), BlueprintRun(), node)
        assert out["agent_name"] == "scaffolder"
        assert "agent_budget" in out
        assert "client_id" not in out

    async def test_includes_client_id_when_set(self) -> None:
        engine = _make_engine(client_id="acme")
        out = await engine._layer_01_agent_budget(
            NodeContext(), BlueprintRun(), _StubNode("scaffolder_node")
        )
        assert out["client_id"] == "acme"


@pytest.mark.asyncio
class TestLayer02UpstreamHandoff:
    async def test_no_handoff_returns_empty(self) -> None:
        engine = _make_engine()
        out = await engine._layer_02_upstream_handoff(
            NodeContext(), BlueprintRun(), _StubNode("scaffolder_node")
        )
        assert out == {}

    async def test_emits_handoff_for_agentic_node(self) -> None:
        engine = _make_engine()
        run = BlueprintRun()
        run._last_handoff = AgentHandoff(
            status=HandoffStatus.OK,
            agent_name="scaffolder",
            learnings=("learnt-x",),
        )
        out = await engine._layer_02_upstream_handoff(
            NodeContext(), run, _StubNode("dark_mode_node", node_type="agentic")
        )
        assert "upstream_handoff" in out
        assert out["upstream_learnings"] == ("learnt-x",)

    async def test_skips_constraints_for_deterministic(self) -> None:
        engine = _make_engine()
        run = BlueprintRun()
        run._last_handoff = AgentHandoff(status=HandoffStatus.OK, agent_name="scaffolder")
        out = await engine._layer_02_upstream_handoff(
            NodeContext(), run, _StubNode("qa_gate", node_type="deterministic")
        )
        assert "upstream_handoff" in out
        assert "upstream_constraints" not in out


@pytest.mark.asyncio
class TestLayer03HandoffHistory:
    async def test_empty_history_noop(self) -> None:
        engine = _make_engine()
        out = await engine._layer_03_handoff_history(
            NodeContext(), BlueprintRun(), _StubNode("scaffolder_node")
        )
        assert out == {}

    async def test_emits_compacted_history(self) -> None:
        engine = _make_engine()
        run = BlueprintRun()
        run._handoff_history = [AgentHandoff(agent_name=f"agent_{i}") for i in range(5)]
        out = await engine._layer_03_handoff_history(
            NodeContext(), run, _StubNode("scaffolder_node")
        )
        assert "handoff_history" in out


@pytest.mark.asyncio
class TestLayer04QAFailureDetails:
    async def test_no_failures_returns_empty(self) -> None:
        engine = _make_engine()
        out = await engine._layer_04_qa_failure_details(
            NodeContext(), BlueprintRun(), _StubNode("scaffolder_node")
        )
        assert out == {}

    async def test_emits_qa_failure_details(self) -> None:
        engine = _make_engine()
        run = BlueprintRun()
        run.qa_failure_details = [
            StructuredFailure(
                check_name="contrast",
                score=0.3,
                details="low contrast",
                suggested_agent="accessibility",
                priority=1,
            )
        ]
        out = await engine._layer_04_qa_failure_details(NodeContext(), run, _StubNode("scaff"))
        assert "qa_failure_details" in out
        assert "previous_qa_failure_details" not in out


@pytest.mark.asyncio
class TestLayer05Economy:
    async def test_normal_budget_noop(self) -> None:
        engine = _make_engine()
        run = BlueprintRun(token_budget=500_000)
        run.model_usage["total_tokens"] = 100  # ~99.98% remaining
        out = await engine._layer_05_economy(NodeContext(), run, _StubNode("scaff"))
        assert out == {}

    async def test_low_budget_emits_economy_flag(self) -> None:
        engine = _make_engine()
        run = BlueprintRun(token_budget=100)
        run.model_usage["total_tokens"] = 99  # 1% remaining → economy
        out = await engine._layer_05_economy(NodeContext(), run, _StubNode("scaff"))
        assert out["economy_mode"] is True
        assert "trajectory_summary" in out


@pytest.mark.asyncio
class TestLayer06ProgressAnchor:
    async def test_first_iteration_noop(self) -> None:
        engine = _make_engine()
        ctx = NodeContext(iteration=0)
        out = await engine._layer_06_progress_anchor(
            ctx, BlueprintRun(), _StubNode("scaffolder_node", node_type="agentic")
        )
        assert out == {}

    async def test_retry_emits_anchor(self) -> None:
        engine = _make_engine()
        ctx = NodeContext(iteration=1)
        out = await engine._layer_06_progress_anchor(
            ctx, BlueprintRun(), _StubNode("scaffolder_node", node_type="agentic")
        )
        assert "progress_anchor" in out


@pytest.mark.asyncio
class TestLayer13RecoveryRepo:
    async def test_no_repo_noop(self) -> None:
        engine = _make_engine()
        out = await engine._layer_13_recovery_repo(
            NodeContext(), BlueprintRun(), _StubNode("scaff")
        )
        assert out == {}


@pytest.mark.asyncio
class TestLayer15AudienceContext:
    async def test_no_profile_noop(self) -> None:
        engine = _make_engine()
        out = await engine._layer_15_audience_context(
            NodeContext(), BlueprintRun(), _StubNode("scaffolder_node")
        )
        assert out == {}


@pytest.mark.asyncio
class TestLayer18CompetitiveContext:
    async def test_non_innovation_noop(self) -> None:
        engine = _make_engine()
        out = await engine._layer_18_competitive_context(
            NodeContext(brief="hi"), BlueprintRun(), _StubNode("scaffolder_node")
        )
        assert out == {}

    async def test_innovation_no_trigger_noop(self) -> None:
        engine = _make_engine()
        # Brief has no competitive trigger keywords
        with patch(
            "app.ai.blueprints.competitor_context.should_fetch_competitive_context",
            return_value=False,
        ):
            out = await engine._layer_18_competitive_context(
                NodeContext(brief="plain brief"),
                BlueprintRun(),
                _StubNode("innovation"),
            )
        assert out == {}


@pytest.mark.asyncio
class TestLayer19ClientLookupTools:
    async def test_deterministic_node_noop(self) -> None:
        engine = _make_engine()
        out = await engine._layer_19_client_lookup_tools(
            NodeContext(), BlueprintRun(), _StubNode("qa_gate", node_type="deterministic")
        )
        assert out == {}

    async def test_agentic_node_emits_tools(self) -> None:
        engine = _make_engine()
        out = await engine._layer_19_client_lookup_tools(
            NodeContext(), BlueprintRun(), _StubNode("scaffolder_node")
        )
        assert "client_lookup_tool" in out
        assert "client_lookup_batch_tool" in out


@pytest.mark.asyncio
class TestLayer24DesignSystem:
    async def test_no_design_system_noop(self) -> None:
        engine = _make_engine()
        out = await engine._layer_24_design_system(
            NodeContext(), BlueprintRun(), _StubNode("scaff")
        )
        assert out == {}


@pytest.mark.asyncio
class TestLayer25InjectionScan:
    async def test_disabled_noop(self) -> None:
        from app.core.config import get_settings as _get_settings

        engine = _make_engine()
        # Default config has prompt_guard_enabled=False
        if _get_settings().security.prompt_guard_enabled:
            pytest.skip("prompt_guard enabled in current settings")
        out = await engine._layer_25_injection_scan(
            NodeContext(brief="x", html="<p>y</p>"),
            BlueprintRun(),
            _StubNode("scaff"),
        )
        assert out == {}


@pytest.mark.asyncio
class TestBuildNodeContextLoop:
    """Smoke tests on the loop-driven _build_node_context entry function."""

    async def test_seed_fields_propagate(self) -> None:
        engine = _make_engine()
        run = BlueprintRun(html="<p>seed</p>")
        run.qa_failures = ["html_validation: missing title"]
        node = _StubNode("scaffolder_node")
        ctx = await engine._build_node_context(node, run, brief="brief", iteration=2)
        assert ctx.html == "<p>seed</p>"
        assert ctx.brief == "brief"
        assert ctx.iteration == 2
        assert ctx.qa_failures == ["html_validation: missing title"]

    async def test_metadata_layers_contribute(self) -> None:
        engine = _make_engine(client_id="acme")
        node = _StubNode("scaffolder_node")
        ctx = await engine._build_node_context(node, BlueprintRun(), brief="b", iteration=0)
        assert ctx.metadata["agent_name"] == "scaffolder"
        assert ctx.metadata["client_id"] == "acme"
        assert "client_lookup_tool" in ctx.metadata
