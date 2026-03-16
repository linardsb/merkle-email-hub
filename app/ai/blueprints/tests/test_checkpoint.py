"""Tests for checkpoint storage layer (14.1) and engine integration (14.2)."""

import json
from unittest.mock import AsyncMock

import pytest

from app.ai.blueprints.checkpoint import (
    _checkpoint_to_dict,
    _dict_to_checkpoint,
    restore_run,
    serialize_run,
)
from app.ai.blueprints.engine import BlueprintDefinition, BlueprintEngine, BlueprintRun, Edge
from app.ai.blueprints.protocols import (
    AgentHandoff,
    NodeContext,
    NodeResult,
    NodeType,
    StructuredFailure,
)
from app.ai.blueprints.route_advisor import RoutingAction, RoutingDecision
from app.ai.blueprints.schemas import BlueprintProgress

# ── Fixtures ──


def _make_run() -> BlueprintRun:
    """Create a BlueprintRun with representative state."""
    run = BlueprintRun(
        run_id="test123",
        status="running",
        html="<html><body>test</body></html>",
        progress=[
            BlueprintProgress(
                node_name="scaffolder",
                node_type="agentic",
                status="success",
                iteration=0,
                summary="Generated HTML",
                duration_ms=1234.5,
            )
        ],
        iteration_counts={"scaffolder": 1},
        qa_failures=["dark_mode"],
        qa_failure_details=[
            StructuredFailure(
                check_name="dark_mode",
                score=0.3,
                details="Missing prefers-color-scheme",
                suggested_agent="dark_mode",
                priority=1,
                severity="error",
            )
        ],
        qa_passed=False,
        model_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        skipped_nodes=["personalisation"],
        routing_decisions=(
            RoutingDecision(
                node_name="personalisation",
                action=RoutingAction.SKIP,
                reason="No personalisation syntax detected",
            ),
        ),
    )
    run._handoff_history = [
        AgentHandoff(
            agent_name="scaffolder",
            decisions=("Used hero template",),
            warnings=(),
            component_refs=("components/hero",),
            confidence=0.85,
        )
    ]
    return run


# ── Round-trip tests ──


class TestSerializeRestoreRoundTrip:
    """serialize_run → restore_run round-trip preserves all state."""

    def test_round_trip_preserves_scalar_fields(self) -> None:
        run = _make_run()
        data = serialize_run(run, node_name="scaffolder", node_index=0, blueprint_name="campaign")

        assert data.run_id == "test123"
        assert data.blueprint_name == "campaign"
        assert data.node_name == "scaffolder"
        assert data.node_index == 0
        assert data.status == "running"
        assert data.html == "<html><body>test</body></html>"
        assert data.qa_passed is False

    def test_round_trip_preserves_collections(self) -> None:
        run = _make_run()
        data = serialize_run(run, node_name="scaffolder", node_index=0, blueprint_name="campaign")
        restored = restore_run(data)

        assert restored.run_id == run.run_id
        assert restored.status == run.status
        assert restored.html == run.html
        assert len(restored.progress) == 1
        assert restored.progress[0].node_name == "scaffolder"
        assert restored.iteration_counts == {"scaffolder": 1}
        assert restored.qa_failures == ["dark_mode"]
        assert restored.qa_passed is False
        assert restored.model_usage == run.model_usage
        assert restored.skipped_nodes == ["personalisation"]

    def test_round_trip_preserves_qa_failure_details(self) -> None:
        run = _make_run()
        data = serialize_run(run, node_name="scaffolder", node_index=0, blueprint_name="campaign")
        restored = restore_run(data)

        assert len(restored.qa_failure_details) == 1
        f = restored.qa_failure_details[0]
        assert f.check_name == "dark_mode"
        assert f.score == 0.3
        assert f.suggested_agent == "dark_mode"

    def test_round_trip_preserves_routing_decisions(self) -> None:
        run = _make_run()
        data = serialize_run(run, node_name="scaffolder", node_index=0, blueprint_name="campaign")
        restored = restore_run(data)

        assert len(restored.routing_decisions) == 1
        rd = restored.routing_decisions[0]
        assert rd.node_name == "personalisation"
        assert rd.action == RoutingAction.SKIP

    def test_round_trip_preserves_handoff_history(self) -> None:
        run = _make_run()
        data = serialize_run(run, node_name="scaffolder", node_index=0, blueprint_name="campaign")
        restored = restore_run(data)

        assert len(restored._handoff_history) == 1
        h = restored._handoff_history[0]
        assert h.agent_name == "scaffolder"
        assert h.confidence == 0.85
        assert "components/hero" in h.component_refs


class TestCheckpointDataSerialization:
    """_checkpoint_to_dict ↔ _dict_to_checkpoint round-trip."""

    def test_dict_round_trip(self) -> None:
        run = _make_run()
        data = serialize_run(run, node_name="scaffolder", node_index=0, blueprint_name="campaign")
        d = _checkpoint_to_dict(data)
        restored = _dict_to_checkpoint(d)

        assert restored.run_id == data.run_id
        assert restored.node_name == data.node_name
        assert restored.created_at == data.created_at

    def test_dict_is_json_serializable(self) -> None:
        """Verify the dict can be serialized to JSON (required for JSONB)."""
        run = _make_run()
        data = serialize_run(run, node_name="scaffolder", node_index=0, blueprint_name="campaign")
        d = _checkpoint_to_dict(data)
        serialized = json.dumps(d)
        assert isinstance(serialized, str)


class TestCheckpointDataFrozen:
    """CheckpointData is immutable."""

    def test_frozen(self) -> None:
        run = _make_run()
        data = serialize_run(run, node_name="scaffolder", node_index=0, blueprint_name="campaign")
        with pytest.raises(AttributeError):
            data.run_id = "changed"  # type: ignore[misc]


class TestEmptyRunRoundTrip:
    """Round-trip with a fresh/empty BlueprintRun."""

    def test_empty_run(self) -> None:
        run = BlueprintRun()
        data = serialize_run(run, node_name="entry", node_index=0, blueprint_name="test")
        restored = restore_run(data)

        assert restored.status == "running"
        assert restored.html == ""
        assert restored.progress == []
        assert restored.iteration_counts == {}
        assert restored.qa_failures == []
        assert restored.qa_passed is None
        assert restored._handoff_history == []


# ── Engine integration tests (14.2) ──


class _StubNode:
    """Minimal node for engine tests."""

    def __init__(self, name: str, html: str = "<p>done</p>") -> None:
        self._name = name
        self._html = html

    @property
    def name(self) -> str:
        return self._name

    @property
    def node_type(self) -> NodeType:
        return "deterministic"

    async def execute(self, context: NodeContext) -> NodeResult:
        return NodeResult(status="success", html=self._html)


def _two_node_definition() -> BlueprintDefinition:
    """Two-node blueprint: entry → finish."""
    return BlueprintDefinition(
        name="test_bp",
        nodes={
            "entry": _StubNode("entry", "<p>step1</p>"),
            "finish": _StubNode("finish", "<p>final</p>"),
        },
        edges=[Edge(from_node="entry", to_node="finish", condition="success")],
        entry_node="entry",
    )


class TestEngineCheckpointIntegration:
    """Verify engine calls checkpoint store after each node."""

    @pytest.mark.asyncio
    async def test_checkpoint_saved_after_each_node(self) -> None:
        mock_store = AsyncMock()
        mock_store.save = AsyncMock()

        engine = BlueprintEngine(_two_node_definition(), checkpoint_store=mock_store)
        run = await engine.run(brief="test")

        assert run.status == "completed"
        # Two nodes executed → two checkpoint saves
        assert mock_store.save.call_count == 2

    @pytest.mark.asyncio
    async def test_checkpoint_contains_correct_node_info(self) -> None:
        mock_store = AsyncMock()
        mock_store.save = AsyncMock()

        engine = BlueprintEngine(_two_node_definition(), checkpoint_store=mock_store)
        await engine.run(brief="test")

        # First checkpoint: entry node at index 0
        first_call = mock_store.save.call_args_list[0]
        data = first_call[0][0]
        assert data.node_name == "entry"
        assert data.node_index == 0
        assert data.blueprint_name == "test_bp"

        # Second checkpoint: finish node at index 1
        second_call = mock_store.save.call_args_list[1]
        data2 = second_call[0][0]
        assert data2.node_name == "finish"
        assert data2.node_index == 1

    @pytest.mark.asyncio
    async def test_checkpoint_failure_does_not_crash_pipeline(self) -> None:
        """Store.save() raising should not abort the run."""
        failing_store = AsyncMock()
        failing_store.save = AsyncMock(side_effect=RuntimeError("DB gone"))

        engine = BlueprintEngine(_two_node_definition(), checkpoint_store=failing_store)
        run = await engine.run(brief="test")

        # Pipeline completes despite checkpoint failures
        assert run.status == "completed"
        assert len(run.progress) == 2

    @pytest.mark.asyncio
    async def test_no_checkpoint_when_store_is_none(self) -> None:
        """No errors when checkpoint_store is not provided."""
        engine = BlueprintEngine(_two_node_definition(), checkpoint_store=None)
        run = await engine.run(brief="test")
        assert run.status == "completed"
