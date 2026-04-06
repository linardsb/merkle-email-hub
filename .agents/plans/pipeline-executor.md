# Plan: Pipeline Executor with Topological Ordering (48.2)

## Context

The current `BlueprintEngine` runs agents sequentially via a state machine. With 7 agents in the `full-build` template, this means ~7x single-agent latency. The DAG infrastructure (48.1) already provides `topological_levels()` which groups nodes by execution level — same-level nodes are independent and can run concurrently via `asyncio.gather()`, reducing wall-clock time to ~3x (3 levels in full-build).

## Research Summary

### Existing Infrastructure (All from 48.1/48.3/48.5)

| Component | File | API |
|-----------|------|-----|
| `PipelineDag` | `app/ai/pipeline/dag.py` | `topological_levels() -> list[list[str]]` (Kahn's algorithm) |
| `PipelineNode` | `dag.py:19` | `agent_name`, `tier`, `inputs`, `outputs`, `contract` (frozen dataclass) |
| `ArtifactStore` | `artifacts.py:116` | `put()`, `get()`, `get_optional()`, `has()`, `names()`, `persist()`, `restore()` |
| `ArtifactAdapter` | `adapters/__init__.py:17` | `adapt_inputs(store)`, `adapt_outputs(response, store)`, `ADAPTER_REGISTRY` |
| `ContractValidator` | `contracts.py:162` | `async validate(contract, html, metadata) -> ContractResult` |
| `PipelineRegistry` | `registry.py` | `get(name) -> PipelineDag`, `list_all()` |
| `PipelineConfig` | `config.py:747` | `default_template`, `custom_dir`, `contract_retry`, `contract_strict` |
| `load_contract` | `contracts.py:200` | `load_contract(Path) -> Contract` (lru_cache) |

### Adapter Registry (10 agents registered)

All in `app/ai/pipeline/adapters/`: scaffolder, dark_mode, content, outlook_fixer, accessibility, personalisation, code_reviewer, knowledge, innovation, visual_qa. Each frozen dataclass with `adapt_inputs(store) -> dict[str, object]` and `adapt_outputs(response, store) -> None`.

### full-build.yaml Topology (2 levels, 7 nodes)

```
Level 0: [scaffolder]       — outputs: html, build_plan (contract: html_valid)
Level 1: [accessibility, code_reviewer, content, dark_mode, personalisation, visual_qa]
```

Note: Level 1 agents output different artifact names (`dark_mode_html`, `a11y_html`, etc.), NOT overwriting the shared `html`. Only code_reviewer outputs `qa_results`, visual_qa outputs `visual_qa_results` + `corrections`.

### Concurrency Patterns in Codebase

| File | Pattern |
|------|---------|
| `image_importer.py:21` | `_SEMAPHORE = asyncio.Semaphore(8)` + `gather(*tasks, return_exceptions=True)` |
| `qa_sweep.py:91` | `sem = asyncio.Semaphore(5)` + `gather` |
| `knowledge/summarizer.py:144` | `Semaphore(settings.knowledge.multi_rep_max_concurrency)` |
| `design_sync/assets.py:20` | `_DOWNLOAD_SEMAPHORE = asyncio.Semaphore(10)` |

Consistent pattern: module-level or config-driven semaphore + `asyncio.gather(*tasks, return_exceptions=True)`.

### Agent Service Resolution

Each agent has `get_{agent}_service() -> {Agent}Service` singleton factory in `app/ai/agents/{agent}/service.py`. Services expose `async complete(request) -> response`. The adapters bridge `ArtifactStore ↔ agent request/response`.

### Blueprint Engine Integration Point

`BlueprintEngine` in `engine.py:1` is the sequential state machine. It uses `BlueprintRun` mutable state, edge-based routing, and `_execute_from()` loop. The pipeline executor is a *parallel alternative*, not a replacement — feature-flagged via `PIPELINE__ENABLED`.

## Test Landscape

### Existing Pipeline Tests (62 tests in 6 files)

| File | Tests | Patterns |
|------|-------|----------|
| `tests/test_dag.py` | 14 | Topology verification, cycle detection, immutability |
| `tests/test_registry.py` | 14 | YAML loading, singleton lifecycle, custom dirs |
| `tests/test_artifacts.py` | 14 | Store CRUD, type checking, Redis persistence (AsyncMock) |
| `tests/test_contracts.py` | 12 | Contract validation, check registry, operator evaluation |
| `tests/test_adapters.py` | 4 | Per-agent adapt_inputs/adapt_outputs roundtrip |
| `tests/test_bridge.py` | 4 | AgentHandoff ↔ ArtifactStore conversion |

### Key Fixtures (`tests/conftest.py`)

- `_reset_registry()` — autouse, resets PipelineRegistry before/after each test
- `three_level_nodes()` — 4-node DAG: `A → [B, C] → D` with html/styled_html/qa_results/final
- `three_level_dag()` — Pre-built PipelineDag from above

### Blueprint Test Patterns (`app/ai/blueprints/tests/conftest.py`)

- `sample_html_valid` — Full email HTML (passes 11 QA checks)
- `StubNode` — Configurable result, tracks `call_count` + `last_context`
- `FailThenPassNode` — Fails N times then passes (self-correction tests)
- Provider mock: `AsyncMock()` returning `CompletionResponse`

### Async Test Pattern

```python
@pytest.mark.asyncio
async def test_example() -> None:
    redis = AsyncMock()
    # ...
```

## Type Check Baseline

| Target | Pyright Errors | Mypy Errors |
|--------|---------------|-------------|
| `app/ai/pipeline/` | 31 errors, 12 warnings | 3 errors |
| `app/ai/blueprints/engine.py` | 2 errors, 21 warnings | — |

Most pyright errors are `reportUnknownVariableType` in registry/conftest and `reportUnusedImport` in test_adapters (side-effect imports). New code must not increase these counts.

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `app/ai/pipeline/executor.py` | `PipelineExecutor`, `PipelineResult`, `NodeTrace`, `_merge_html_outputs()` |
| `app/ai/pipeline/tests/test_executor.py` | 16 tests for executor |

### Modified Files

| File | Change |
|------|--------|
| `app/core/config.py:747` | Add `enabled`, `max_concurrent_agents`, `merge_strategy` to `PipelineConfig` |
| `app/core/exceptions.py` | Add `PipelineExecutionError` to hierarchy |
| `app/ai/pipeline/tests/conftest.py` | Add executor fixtures (`mock_agent_service`, `make_executor`) |

## Implementation Steps

### Step 1: Extend `PipelineConfig` (`config.py:747`)

Add 3 fields to existing `PipelineConfig`:

```python
class PipelineConfig(BaseModel):
    """Pipeline DAG template settings."""
    default_template: str = "full-build"
    custom_dir: str = ""
    contract_retry: bool = True
    contract_strict: bool = False
    # New fields (48.2):
    enabled: bool = False  # PIPELINE__ENABLED
    max_concurrent_agents: int = 5  # PIPELINE__MAX_CONCURRENT_AGENTS
    merge_strategy: Literal["sequential", "diff3"] = "sequential"  # PIPELINE__MERGE_STRATEGY
```

### Step 2: Add `PipelineExecutionError` (`exceptions.py`)

```python
class PipelineExecutionError(AppError):
    """Pipeline executor encountered a fatal error."""
    status_code = 500
```

### Step 3: Create `executor.py`

```python
# app/ai/pipeline/executor.py
"""Concurrent pipeline executor with topological ordering."""

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.ai.pipeline.adapters import ADAPTER_REGISTRY, ArtifactAdapter
from app.ai.pipeline.artifacts import ArtifactStore, HtmlArtifact
from app.ai.pipeline.contracts import ContractValidator, load_contract
from app.ai.pipeline.dag import PipelineDag, PipelineNode
from app.core.config import PipelineConfig
from app.core.exceptions import PipelineExecutionError
from app.core.logging import get_logger

logger = get_logger(__name__)

CONTRACT_DEF_DIR = Path(__file__).parent / "contract_defs"


@dataclass(frozen=True, slots=True)
class NodeTrace:
    """Execution trace for a single pipeline node."""
    agent_name: str
    duration_ms: int
    tokens_used: int = 0
    contract_passed: bool | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Outcome of a complete pipeline execution."""
    artifacts: dict[str, str]  # name → type snapshot
    trace: tuple[NodeTrace, ...]
    total_duration_ms: int
    levels_executed: int
    nodes_executed: int
    cost_tokens: int


# Protocol for agent service resolution (avoids hard dependency on all agents)
from typing import Protocol, runtime_checkable

@runtime_checkable
class AgentRunner(Protocol):
    """Callable that runs an agent with adapted inputs and returns a response."""
    async def __call__(self, agent_name: str, inputs: dict[str, object]) -> object: ...


class PipelineExecutor:
    """Executes a PipelineDag with concurrent same-level agent invocation."""

    def __init__(
        self,
        dag: PipelineDag,
        store: ArtifactStore,
        settings: PipelineConfig,
        agent_runner: AgentRunner,
        contract_validator: ContractValidator | None = None,
    ) -> None:
        self._dag = dag
        self._store = store
        self._settings = settings
        self._runner = agent_runner
        self._validator = contract_validator or ContractValidator()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_agents)

    async def execute(self, run_id: str, completed_levels: int = 0) -> PipelineResult:
        """Run all DAG levels, executing same-level nodes concurrently."""
        start = time.monotonic()
        levels = self._dag.topological_levels()
        traces: list[NodeTrace] = []
        nodes_executed = 0
        total_tokens = 0

        for lvl_idx, node_ids in enumerate(levels):
            if lvl_idx < completed_levels:
                logger.info("pipeline.level.skipped", extra={"run_id": run_id, "level": lvl_idx})
                continue

            logger.info(
                "pipeline.level.start",
                extra={"run_id": run_id, "level": lvl_idx, "nodes": node_ids},
            )

            # Run all nodes at this level concurrently
            tasks = [self._run_node(node_id, run_id) for node_id in node_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            level_traces: list[NodeTrace] = []
            for node_id, result in zip(node_ids, results, strict=True):
                if isinstance(result, BaseException):
                    trace = NodeTrace(
                        agent_name=self._dag.nodes[node_id].agent_name,
                        duration_ms=0,
                        error=str(result),
                    )
                    level_traces.append(trace)
                    logger.error(
                        "pipeline.node.failed",
                        extra={"run_id": run_id, "node": node_id, "error": str(result)},
                    )
                else:
                    level_traces.append(result)
                    total_tokens += result.tokens_used

            traces.extend(level_traces)
            nodes_executed += len(node_ids)

            # Merge HTML outputs if multiple nodes at this level produce HTML variants
            self._merge_html_outputs(node_ids)

            logger.info(
                "pipeline.level.complete",
                extra={
                    "run_id": run_id,
                    "level": lvl_idx,
                    "errors": sum(1 for t in level_traces if t.error),
                },
            )

            # Fail-fast on strict mode if any node failed
            if self._settings.contract_strict and any(t.error for t in level_traces):
                break

        elapsed = int((time.monotonic() - start) * 1000)
        return PipelineResult(
            artifacts=self._store.snapshot(),
            trace=tuple(traces),
            total_duration_ms=elapsed,
            levels_executed=min(len(levels), len(levels) - completed_levels),
            nodes_executed=nodes_executed,
            cost_tokens=total_tokens,
        )

    async def _run_node(self, node_id: str, run_id: str) -> NodeTrace:
        """Execute a single node: adapt inputs → run agent → adapt outputs → validate contract."""
        node = self._dag.nodes[node_id]
        adapter = ADAPTER_REGISTRY.get(node.agent_name)
        start = time.monotonic()

        async with self._semaphore:
            logger.info(
                "pipeline.node.start",
                extra={"run_id": run_id, "node": node_id, "agent": node.agent_name},
            )

            try:
                # Adapt inputs from artifact store
                inputs = adapter.adapt_inputs(self._store) if adapter else {}

                # Run agent via injected runner
                response = await self._runner(node.agent_name, inputs)

                # Adapt outputs back to artifact store
                if adapter:
                    adapter.adapt_outputs(response, self._store)

                # Validate contract if present
                contract_passed: bool | None = None
                if node.contract:
                    contract_path = CONTRACT_DEF_DIR / f"{node.contract}.yaml"
                    if contract_path.exists():
                        contract = load_contract(contract_path)
                        html_artifact = self._store.get_optional("html", HtmlArtifact)
                        html = html_artifact.html if html_artifact else ""
                        result = await self._validator.validate(contract, html)
                        contract_passed = result.passed
                        if not result.passed:
                            logger.warning(
                                "pipeline.contract.failed",
                                extra={
                                    "run_id": run_id,
                                    "node": node_id,
                                    "contract": node.contract,
                                    "failures": [f.message for f in result.failures],
                                },
                            )
                            if self._settings.contract_strict:
                                raise PipelineExecutionError(
                                    f"Contract '{node.contract}' failed for node '{node_id}'"
                                )

                elapsed = int((time.monotonic() - start) * 1000)
                tokens = getattr(response, "tokens_used", 0) or 0

                logger.info(
                    "pipeline.node.complete",
                    extra={
                        "run_id": run_id,
                        "node": node_id,
                        "duration_ms": elapsed,
                        "contract_passed": contract_passed,
                    },
                )

                return NodeTrace(
                    agent_name=node.agent_name,
                    duration_ms=elapsed,
                    tokens_used=tokens,
                    contract_passed=contract_passed,
                )

            except PipelineExecutionError:
                raise
            except Exception as exc:
                elapsed = int((time.monotonic() - start) * 1000)
                return NodeTrace(
                    agent_name=node.agent_name,
                    duration_ms=elapsed,
                    error=f"{type(exc).__name__}: {exc}",
                )

    def _merge_html_outputs(self, node_ids: list[str]) -> None:
        """Merge HTML-producing outputs from parallel nodes.

        Strategy: deterministic sequential merge in alphabetical agent order.
        Each agent's adapter writes to its own artifact name (e.g. dark_mode_html),
        so no conflict for the default full-build template. This method handles
        the edge case where multiple nodes write to the same artifact name.
        """
        if self._settings.merge_strategy != "sequential":
            return  # diff3 deferred to future phase

        # Check if multiple nodes produced artifacts with the same name
        # In the current template design, each agent writes distinct artifact names,
        # so this is a safety net for custom templates.
        html_producers: list[str] = []
        for node_id in sorted(node_ids):  # alphabetical for determinism
            node = self._dag.nodes[node_id]
            if "html" in node.outputs and node_id != node_ids[0]:
                html_producers.append(node_id)

        if len(html_producers) > 1:
            logger.warning(
                "pipeline.merge.multiple_html_producers",
                extra={"producers": html_producers, "strategy": "last-writer-wins"},
            )
```

### Step 4: Add fixtures to `tests/conftest.py`

Extend existing conftest with executor helpers:

```python
# Add to app/ai/pipeline/tests/conftest.py
from unittest.mock import AsyncMock
from app.ai.pipeline.artifacts import ArtifactStore
from app.core.config import PipelineConfig


class MockAgentRunner:
    """Configurable mock agent runner for executor tests."""
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.responses: dict[str, object] = {}
        self.delays: dict[str, float] = {}
        self.errors: dict[str, Exception] = {}

    async def __call__(self, agent_name: str, inputs: dict[str, object]) -> object:
        self.calls.append((agent_name, inputs))
        if agent_name in self.errors:
            raise self.errors[agent_name]
        if agent_name in self.delays:
            await asyncio.sleep(self.delays[agent_name])
        return self.responses.get(agent_name, _StubResponse())

class _StubResponse:
    html: str = "<html><body><table><tr><td>stub</td></tr></table></body></html>"
    tokens_used: int = 100


@pytest.fixture
def mock_runner() -> MockAgentRunner:
    return MockAgentRunner()

@pytest.fixture
def pipeline_config() -> PipelineConfig:
    return PipelineConfig(enabled=True, max_concurrent_agents=5)

@pytest.fixture
def artifact_store() -> ArtifactStore:
    return ArtifactStore()
```

### Step 5: Create `test_executor.py` (16 tests)

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_execute_single_node_dag` | 1-node DAG executes, result has 1 trace |
| 2 | `test_execute_three_level_dag` | 3-level DAG: correct order, 4 traces |
| 3 | `test_concurrent_execution_same_level` | Level 1 nodes run concurrently (timing check with delays) |
| 4 | `test_semaphore_caps_concurrency` | `max_concurrent_agents=2` limits parallel execution |
| 5 | `test_artifact_flow_between_levels` | Level 0 output available as level 1 input via adapter |
| 6 | `test_node_failure_continues_level` | One node fails, others at same level still complete |
| 7 | `test_node_failure_recorded_in_trace` | Failed node has `error` field in `NodeTrace` |
| 8 | `test_contract_validation_passes` | Node with contract, validator returns passed=True |
| 9 | `test_contract_validation_fails_warning` | Contract fails but non-strict: warning logged, continues |
| 10 | `test_contract_strict_fails_fast` | `contract_strict=True`: contract failure raises `PipelineExecutionError` |
| 11 | `test_resume_skips_completed_levels` | `completed_levels=1` skips first level |
| 12 | `test_pipeline_result_fields` | Result has correct `levels_executed`, `nodes_executed`, `cost_tokens` |
| 13 | `test_tokens_accumulated` | Tokens from all nodes summed in `cost_tokens` |
| 14 | `test_no_adapter_graceful` | Node without registered adapter runs with empty inputs |
| 15 | `test_full_build_template_topology` | Load real `full-build.yaml`, verify 2 levels, 7 nodes |
| 16 | `test_merge_html_outputs_no_conflict` | Default template: each agent writes distinct artifacts, no merge needed |

## Preflight Warnings

- `test_adapters.py` uses side-effect imports (`import app.ai.pipeline.adapters.scaffolder`) to register adapters — new tests must do the same or pre-populate `ADAPTER_REGISTRY`.
- `conftest.py` resets `PipelineRegistry` singleton before/after each test — executor tests should follow this pattern.
- `ArtifactStore` is purely in-memory; Redis persistence is metadata-only (snapshot). Full artifact serialization is deferred.

## Security Checklist

No new endpoints in this task. The executor is an internal service class:
- [x] No user input reaches executor directly (called from blueprint engine)
- [x] Agent runner is injected (no direct import of agent services in executor)
- [x] Contract validation uses existing `sanitize_html_xss` check
- [x] No secrets or API keys handled in executor

## Verification

- [ ] `make check` passes
- [ ] `uv run pytest app/ai/pipeline/tests/test_executor.py -v` — 16 tests pass
- [ ] Pyright errors for `app/ai/pipeline/` ≤ 31 (baseline)
- [ ] Mypy errors for `app/ai/pipeline/` ≤ 3 (baseline)
- [ ] Concurrent timing test proves level 1 nodes run in parallel
- [ ] Failed node doesn't block siblings at same level
