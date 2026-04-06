"""Tests for PipelineExecutor — concurrent DAG execution."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.pipeline.artifacts import ArtifactStore, HtmlArtifact
from app.ai.pipeline.contracts import (
    Assertion,
    ContractResult,
    ContractValidator,
)
from app.ai.pipeline.dag import PipelineDag, PipelineNode
from app.ai.pipeline.executor import PipelineExecutor, PipelineResult
from app.ai.pipeline.registry import get_pipeline_registry
from app.core.config import PipelineConfig

from .conftest import MockAgentRunner

# ── Helpers ──


def _single_node_dag() -> PipelineDag:
    return PipelineDag(
        name="single",
        description="Single node",
        nodes={"n1": PipelineNode("agent_a", "standard", inputs=(), outputs=("html",))},
    )


def _two_level_dag() -> PipelineDag:
    """Level 0: [root], Level 1: [left, right]."""
    return PipelineDag(
        name="two-level",
        description="Two level DAG",
        nodes={
            "root": PipelineNode("agent_root", "complex", inputs=(), outputs=("html",)),
            "left": PipelineNode(
                "agent_left", "standard", inputs=("html",), outputs=("left_html",)
            ),
            "right": PipelineNode(
                "agent_right", "standard", inputs=("html",), outputs=("right_html",)
            ),
        },
    )


# ── Tests ──


@pytest.mark.asyncio
async def test_execute_single_node_dag(
    mock_runner: MockAgentRunner,
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """1-node DAG executes, result has 1 trace."""
    dag = _single_node_dag()
    executor = PipelineExecutor(dag, artifact_store, pipeline_config, mock_runner)

    result = await executor.execute("run-1")

    assert len(result.trace) == 1
    assert result.trace[0].agent_name == "agent_a"
    assert result.trace[0].error is None
    assert result.nodes_executed == 1
    assert len(mock_runner.calls) == 1


@pytest.mark.asyncio
async def test_execute_three_level_dag(
    three_level_dag: PipelineDag,
    mock_runner: MockAgentRunner,
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """3-level DAG: correct order, 4 traces."""
    executor = PipelineExecutor(three_level_dag, artifact_store, pipeline_config, mock_runner)

    result = await executor.execute("run-2")

    assert len(result.trace) == 4
    assert result.nodes_executed == 4
    # Level 0 runs first (agent_a), then level 1 (agent_b, agent_c), then level 2 (agent_d)
    agents_called = [name for name, _ in mock_runner.calls]
    a_idx = agents_called.index("agent_a")
    d_idx = agents_called.index("agent_d")
    assert a_idx < d_idx


@pytest.mark.asyncio
async def test_concurrent_execution_same_level(
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """Level 1 nodes run concurrently (timing check with delays)."""
    dag = _two_level_dag()
    runner = MockAgentRunner()
    # Root completes instantly, both children take 0.1s each
    runner.delays["agent_left"] = 0.1
    runner.delays["agent_right"] = 0.1

    executor = PipelineExecutor(dag, artifact_store, pipeline_config, runner)

    start = time.monotonic()
    result = await executor.execute("run-timing")
    elapsed = time.monotonic() - start

    assert result.nodes_executed == 3
    # If sequential, would take ~0.2s for level 1. Concurrent should be ~0.1s.
    assert elapsed < 0.25


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency(
    artifact_store: ArtifactStore,
) -> None:
    """max_concurrent_agents=1 forces serial execution within a level."""
    dag = _two_level_dag()
    config = PipelineConfig(enabled=True, max_concurrent_agents=1)
    runner = MockAgentRunner()
    runner.delays["agent_left"] = 0.05
    runner.delays["agent_right"] = 0.05

    executor = PipelineExecutor(dag, artifact_store, config, runner)

    start = time.monotonic()
    await executor.execute("run-sem")
    elapsed = time.monotonic() - start

    # With semaphore=1, level 1 nodes run serially: ~0.1s minimum
    assert elapsed >= 0.09


@pytest.mark.asyncio
async def test_artifact_flow_between_levels(
    pipeline_config: PipelineConfig,
) -> None:
    """Level 0 output available as level 1 input via adapter."""
    dag = _two_level_dag()
    store = ArtifactStore()
    runner = MockAgentRunner()

    # Register a mock adapter for agent_root that writes html artifact
    from app.ai.pipeline.adapters import ADAPTER_REGISTRY

    original = dict(ADAPTER_REGISTRY)
    try:

        class _RootAdapter:
            @property
            def agent_name(self) -> str:
                return "agent_root"

            def input_artifacts(self) -> frozenset[str]:
                return frozenset()

            def output_artifacts(self) -> frozenset[str]:
                return frozenset({"html"})

            def adapt_inputs(self, store: ArtifactStore) -> dict[str, object]:
                return {}

            def adapt_outputs(self, response: object, store: ArtifactStore) -> None:
                store.put(
                    "html",
                    HtmlArtifact(
                        name="html",
                        produced_by="agent_root",
                        produced_at=datetime.now(UTC),
                        html="<table><tr><td>root output</td></tr></table>",
                    ),
                )

        class _LeftAdapter:
            @property
            def agent_name(self) -> str:
                return "agent_left"

            def input_artifacts(self) -> frozenset[str]:
                return frozenset({"html"})

            def output_artifacts(self) -> frozenset[str]:
                return frozenset({"left_html"})

            def adapt_inputs(self, store: ArtifactStore) -> dict[str, object]:
                art = store.get_optional("html", HtmlArtifact)
                return {"html": art.html if art else ""}

            def adapt_outputs(self, response: object, store: ArtifactStore) -> None:
                pass

        ADAPTER_REGISTRY["agent_root"] = _RootAdapter()
        ADAPTER_REGISTRY["agent_left"] = _LeftAdapter()

        executor = PipelineExecutor(dag, store, pipeline_config, runner)
        await executor.execute("run-flow")

        # Verify agent_left received html from agent_root
        left_call = next((c for c in runner.calls if c[0] == "agent_left"), None)
        assert left_call is not None
        assert left_call[1].get("html") == "<table><tr><td>root output</td></tr></table>"
    finally:
        ADAPTER_REGISTRY.clear()
        ADAPTER_REGISTRY.update(original)


@pytest.mark.asyncio
async def test_node_failure_continues_level(
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """One node fails, others at same level still complete."""
    dag = _two_level_dag()
    runner = MockAgentRunner()
    runner.errors["agent_left"] = ValueError("boom")

    executor = PipelineExecutor(dag, artifact_store, pipeline_config, runner)
    result = await executor.execute("run-fail")

    # Both level 1 nodes processed, one with error
    level1_traces = [t for t in result.trace if t.agent_name in ("agent_left", "agent_right")]
    assert len(level1_traces) == 2
    right_trace = next(t for t in level1_traces if t.agent_name == "agent_right")
    assert right_trace.error is None


@pytest.mark.asyncio
async def test_node_failure_recorded_in_trace(
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """Failed node has error field in NodeTrace."""
    dag = _single_node_dag()
    runner = MockAgentRunner()
    runner.errors["agent_a"] = RuntimeError("agent crashed")

    executor = PipelineExecutor(dag, artifact_store, pipeline_config, runner)
    result = await executor.execute("run-err")

    assert result.trace[0].error is not None
    assert "agent crashed" in result.trace[0].error


@pytest.mark.asyncio
async def test_contract_validation_passes(
    mock_runner: MockAgentRunner,
    artifact_store: ArtifactStore,
) -> None:
    """Node with contract, validator returns passed=True."""
    dag = PipelineDag(
        name="with-contract",
        description="Contract test",
        nodes={
            "n1": PipelineNode(
                "agent_a", "standard", inputs=(), outputs=("html",), contract="html_valid"
            )
        },
    )
    config = PipelineConfig(enabled=True)

    validator = ContractValidator()
    # Put a valid HTML artifact so contract check has content
    artifact_store.put(
        "html",
        HtmlArtifact(
            name="html",
            produced_by="test",
            produced_at=datetime.now(UTC),
            html="<html><body><table><tr><td>valid</td></tr></table></body></html>",
        ),
    )

    executor = PipelineExecutor(dag, artifact_store, config, mock_runner, validator)

    with patch.object(
        validator,
        "validate",
        return_value=ContractResult(passed=True, failures=(), duration_ms=1),
    ):
        result = await executor.execute("run-contract")

    assert result.trace[0].contract_passed is True


@pytest.mark.asyncio
async def test_contract_validation_fails_warning(
    mock_runner: MockAgentRunner,
    artifact_store: ArtifactStore,
) -> None:
    """Contract fails but non-strict: warning logged, continues."""
    dag = PipelineDag(
        name="contract-warn",
        description="Contract warning test",
        nodes={
            "n1": PipelineNode(
                "agent_a", "standard", inputs=(), outputs=("html",), contract="html_valid"
            )
        },
    )
    config = PipelineConfig(enabled=True, contract_strict=False)

    validator = AsyncMock(spec=ContractValidator)
    from app.ai.pipeline.contracts import AssertionFailure

    validator.validate.return_value = ContractResult(
        passed=False,
        failures=(
            AssertionFailure(
                assertion=Assertion(check="html_valid", operator="==", threshold=True),
                actual_value=False,
                message="HTML invalid",
            ),
        ),
        duration_ms=1,
    )

    executor = PipelineExecutor(dag, artifact_store, config, mock_runner, validator)
    result = await executor.execute("run-warn")

    assert result.trace[0].contract_passed is False
    assert result.trace[0].error is None  # No fatal error — just warning


@pytest.mark.asyncio
async def test_contract_strict_fails_fast(
    mock_runner: MockAgentRunner,
    artifact_store: ArtifactStore,
) -> None:
    """contract_strict=True: contract failure raises PipelineExecutionError."""
    dag = PipelineDag(
        name="contract-strict",
        description="Strict contract test",
        nodes={
            "n1": PipelineNode(
                "agent_a", "standard", inputs=(), outputs=("html",), contract="html_valid"
            )
        },
    )
    config = PipelineConfig(enabled=True, contract_strict=True)

    validator = AsyncMock(spec=ContractValidator)
    from app.ai.pipeline.contracts import AssertionFailure

    validator.validate.return_value = ContractResult(
        passed=False,
        failures=(
            AssertionFailure(
                assertion=Assertion(check="html_valid", operator="==", threshold=True),
                actual_value=False,
                message="HTML invalid",
            ),
        ),
        duration_ms=1,
    )

    executor = PipelineExecutor(dag, artifact_store, config, mock_runner, validator)

    # PipelineExecutionError propagates through gather as BaseException
    result = await executor.execute("run-strict")
    # The error is caught by gather(return_exceptions=True) and recorded in trace
    assert any(t.error and "Contract" in t.error for t in result.trace)


@pytest.mark.asyncio
async def test_resume_skips_completed_levels(
    mock_runner: MockAgentRunner,
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """completed_levels=1 skips first level."""
    dag = _two_level_dag()
    executor = PipelineExecutor(dag, artifact_store, pipeline_config, mock_runner)

    await executor.execute("run-resume", completed_levels=1)

    # Only level 1 nodes (left, right) should run, not root
    agents_called = {name for name, _ in mock_runner.calls}
    assert "agent_root" not in agents_called
    assert "agent_left" in agents_called
    assert "agent_right" in agents_called


@pytest.mark.asyncio
async def test_pipeline_result_fields(
    mock_runner: MockAgentRunner,
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """Result has correct levels_executed, nodes_executed, cost_tokens."""
    dag = _two_level_dag()
    executor = PipelineExecutor(dag, artifact_store, pipeline_config, mock_runner)

    result = await executor.execute("run-fields")

    assert isinstance(result, PipelineResult)
    assert result.levels_executed == 2
    assert result.nodes_executed == 3
    assert result.total_duration_ms >= 0


@pytest.mark.asyncio
async def test_tokens_accumulated(
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """Tokens from all nodes summed in cost_tokens."""
    dag = _two_level_dag()
    runner = MockAgentRunner()

    # Each _StubResponse has tokens_used=100, 3 nodes = 300
    executor = PipelineExecutor(dag, artifact_store, pipeline_config, runner)
    result = await executor.execute("run-tokens")

    assert result.cost_tokens == 300


@pytest.mark.asyncio
async def test_no_adapter_graceful(
    mock_runner: MockAgentRunner,
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """Node without registered adapter runs with empty inputs."""
    dag = _single_node_dag()

    # Ensure no adapter registered for agent_a
    from app.ai.pipeline.adapters import ADAPTER_REGISTRY

    original = ADAPTER_REGISTRY.pop("agent_a", None)
    try:
        executor = PipelineExecutor(dag, artifact_store, pipeline_config, mock_runner)
        result = await executor.execute("run-no-adapter")

        assert result.trace[0].error is None
        # Runner called with empty inputs
        assert mock_runner.calls[0][1] == {}
    finally:
        if original is not None:
            ADAPTER_REGISTRY["agent_a"] = original


@pytest.mark.asyncio
async def test_full_build_template_topology() -> None:
    """Load real full-build.yaml, verify 2 levels, 7 nodes."""
    registry = get_pipeline_registry()
    dag = registry.get("full-build")

    levels = dag.topological_levels()
    assert len(levels) == 2
    assert len(dag.nodes) == 7
    assert levels[0] == ["scaffolder"]
    assert len(levels[1]) == 6


@pytest.mark.asyncio
async def test_merge_html_outputs_no_conflict(
    mock_runner: MockAgentRunner,
    pipeline_config: PipelineConfig,
    artifact_store: ArtifactStore,
) -> None:
    """Default template: each agent writes distinct artifacts, no merge needed."""
    # Two nodes at same level with different output artifact names — no conflict
    dag = PipelineDag(
        name="no-conflict",
        description="No merge conflict",
        nodes={
            "a": PipelineNode("agent_a", "standard", inputs=(), outputs=("left_html",)),
            "b": PipelineNode("agent_b", "standard", inputs=(), outputs=("right_html",)),
        },
    )
    executor = PipelineExecutor(dag, artifact_store, pipeline_config, mock_runner)
    result = await executor.execute("run-merge")

    # Both nodes succeed, no merge issues
    assert all(t.error is None for t in result.trace)
    assert result.nodes_executed == 2
