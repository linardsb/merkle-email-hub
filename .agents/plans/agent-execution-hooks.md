# Plan: 48.13 Agent Execution Hook System with Profiles

## Context

The pipeline executor (`app/ai/pipeline/executor.py`) has no extension points between agents. Adding observability, cost tracking, or quality gates requires modifying `PipelineExecutor._run_node()` directly. A hook system decouples cross-cutting concerns from agent logic via profile-based activation (minimal/standard/strict).

## Research Summary

| File | Role | Key Lines |
|------|------|-----------|
| `app/ai/pipeline/executor.py` | `PipelineExecutor` — concurrent DAG runner | L60-156 `execute()`, L157-237 `_run_node()` |
| `app/ai/pipeline/artifacts.py` | `ArtifactStore` — typed artifact get/put/snapshot | L116-185 |
| `app/ai/pipeline/contracts.py` | `ContractValidator` — 8 built-in checks | L162-198 `validate()` |
| `app/ai/pipeline/dag.py` | `PipelineDag`, `PipelineNode` — toposort | L1-88 |
| `app/core/config.py:777-788` | `PipelineConfig(BaseModel)` — pipeline settings | Extend with hook fields |
| `app/core/exceptions.py:68-69` | `PipelineExecutionError(AppError)` — base for `HookAbortError` | L68 |
| `app/core/progress.py:37` | `ProgressTracker` — class methods `start/update/get` | progress_reporter uses this |
| `app/ai/cost_governor.py:103` | `CostGovernor` — `track_tokens()`, `check_budget()` | cost_tracker integrates |
| `app/ai/agents/evaluator/service.py` | `EvaluatorAgentService` — adversarial validation | adversarial_gate hook |

**Injection points in `_run_node()` (L157-237):**
1. Pre-agent: after semaphore acquire (L163), before `adapt_inputs` (L175)
2. Post-agent: after `adapt_outputs` (L182), before contract validation (L186)
3. Contract-failed: inside the `if not result.passed` block (L194-207)
4. On-error: exception handler (L229-237)

**Pipeline-level injection in `execute()` (L78-155):**
1. Pre-pipeline: after `_inject_proactive_warnings` (L87)
2. Pre-level: before `gather` (L103)
3. Post-level: after processing results (L134)
4. Post-pipeline: before return (L148)

**Patterns to follow:**
- `@dataclass(frozen=True, slots=True)` for all data objects
- `@runtime_checkable Protocol` for hook interface
- Nested `BaseModel` config with `PIPELINE__*` env vars
- `get_logger(__name__)` for structured logging
- DI at constructor (like `ContractValidator`)

## Test Landscape

| File | Tests | Patterns |
|------|-------|----------|
| `tests/conftest.py` | Fixtures | `MockAgentRunner`, `three_level_dag`, `pipeline_config`, `artifact_store` |
| `test_executor.py` | 16 async | `@pytest.mark.asyncio`, timing assertions, semaphore testing |
| `test_contracts.py` | 12 | `_make_contract()` factory, `_html_artifact()` factory |
| `test_artifacts.py` | 6 | put/get/snapshot, frozen immutability |
| `test_dag.py` | 14 | Topological sort, cycle detection |
| `app/core/tests/test_progress.py` | 15 | `ProgressTracker.clear()` autouse fixture |

**Mock patterns:** `MockAgentRunner` tracks `calls`, configurable `delays`/`errors`/`responses`. Tests use `time.monotonic()` for concurrency validation.

## Type Check Baseline

| Target | Pyright Errors | Mypy Errors | Notes |
|--------|---------------|-------------|-------|
| `app/ai/pipeline/` | 31 | 3 | Nearly all in test files (unused imports, private access) |
| `app/core/config.py` | 0 | 0 | Clean |
| `app/core/progress.py` | 0 | 0 | Clean |
| `app/core/exceptions.py` | 0 | 0 | Clean |

## Files to Create

| File | Purpose |
|------|---------|
| `app/ai/hooks/__init__.py` | Public API: `HookRegistry`, `HookEvent`, `HookContext`, `HookResult`, `HookFn` |
| `app/ai/hooks/registry.py` | `HookRegistry` — register/fire with profile filtering |
| `app/ai/hooks/profiles.py` | `HookProfile` type, `PROFILE_LEVELS` ordering, `profile_includes()` |
| `app/ai/hooks/config.py` | `HookConfig(BaseModel)` nested in `PipelineConfig` |
| `app/ai/hooks/builtin/__init__.py` | `register_builtin_hooks()` auto-registration |
| `app/ai/hooks/builtin/cost_tracker.py` | `minimal` — per-agent/pipeline token accumulation |
| `app/ai/hooks/builtin/structured_logger.py` | `standard` — structured JSON event logging |
| `app/ai/hooks/builtin/progress_reporter.py` | `standard` — `ProgressTracker` updates |
| `app/ai/hooks/builtin/adversarial_gate.py` | `strict` — evaluator agent post-agent gate |
| `app/ai/hooks/builtin/pattern_extractor.py` | `strict` — recurring failure pattern detection |
| `app/ai/hooks/tests/__init__.py` | Test package |
| `app/ai/hooks/tests/conftest.py` | Hook test fixtures |
| `app/ai/hooks/tests/test_registry.py` | Registry unit tests |
| `app/ai/hooks/tests/test_profiles.py` | Profile filtering tests |
| `app/ai/hooks/tests/test_builtin.py` | Built-in hook tests |
| `app/ai/hooks/tests/test_integration.py` | Executor + hooks integration tests |

## Files to Modify

| File | Change |
|------|--------|
| `app/core/config.py:777-788` | Add `HookConfig` model, add `hooks: HookConfig` field to `PipelineConfig` |
| `app/core/exceptions.py` | Add `HookAbortError(PipelineExecutionError)` |
| `app/ai/pipeline/executor.py` | Accept `HookRegistry` in `__init__`, fire events at 8 injection points |

## Implementation Steps

### Step 1: Data types and profiles (`app/ai/hooks/profiles.py`)

```python
from __future__ import annotations
from typing import Literal

HookProfile = Literal["minimal", "standard", "strict"]

PROFILE_LEVELS: dict[HookProfile, int] = {"minimal": 0, "standard": 1, "strict": 2}

def profile_includes(active: HookProfile, required: HookProfile) -> bool:
    """Check if active profile includes hooks registered at required level."""
    return PROFILE_LEVELS[active] >= PROFILE_LEVELS[required]
```

### Step 2: Core types and registry (`app/ai/hooks/registry.py`)

```python
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Awaitable

from app.ai.hooks.profiles import HookProfile, profile_includes
from app.ai.pipeline.artifacts import ArtifactStore
from app.core.logging import get_logger

logger = get_logger(__name__)

class HookEvent(StrEnum):
    PRE_AGENT = "pre_agent"
    POST_AGENT = "post_agent"
    PRE_PIPELINE = "pre_pipeline"
    POST_PIPELINE = "post_pipeline"
    PRE_LEVEL = "pre_level"
    POST_LEVEL = "post_level"
    CONTRACT_FAILED = "contract_failed"
    ARTIFACT_STORED = "artifact_stored"

@dataclass(frozen=True, slots=True)
class HookContext:
    run_id: str
    pipeline_name: str
    event: HookEvent
    agent_name: str | None = None
    level: int | None = None
    artifacts: ArtifactStore | None = None
    node_trace: Any | None = None  # NodeTrace (avoid circular import)
    cost_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class HookResult:
    hook_name: str
    duration_ms: int
    output: Any | None = None
    error: str | None = None

# Callable type for hooks
HookFn = Callable[[HookContext], Awaitable[Any]]

@dataclass
class _RegisteredHook:
    name: str
    event: HookEvent
    fn: HookFn
    profile: HookProfile

class HookRegistry:
    def __init__(self, active_profile: HookProfile = "standard", disabled: frozenset[str] = frozenset()) -> None:
        self._hooks: list[_RegisteredHook] = []
        self._profile = active_profile
        self._disabled = disabled

    @property
    def active_profile(self) -> HookProfile:
        return self._profile

    def register(self, event: HookEvent, fn: HookFn, *, name: str, profile: HookProfile = "standard") -> None:
        if name in self._disabled:
            return
        self._hooks.append(_RegisteredHook(name=name, event=event, fn=fn, profile=profile))

    async def fire(self, event: HookEvent, context: HookContext) -> list[HookResult]:
        results: list[HookResult] = []
        for hook in self._hooks:
            if hook.event != event:
                continue
            if not profile_includes(self._profile, hook.profile):
                continue
            start = time.monotonic()
            try:
                output = await hook.fn(context)
                elapsed = int((time.monotonic() - start) * 1000)
                results.append(HookResult(hook_name=hook.name, duration_ms=elapsed, output=output))
            except Exception as exc:
                elapsed = int((time.monotonic() - start) * 1000)
                logger.warning("hooks.fire.error", extra={"hook": hook.name, "event": event, "error": str(exc)})
                results.append(HookResult(hook_name=hook.name, duration_ms=elapsed, error=f"{type(exc).__name__}: {exc}"))
                if isinstance(exc, HookAbortError):
                    raise
        return results
```

Note: `HookAbortError` propagates — all other hook errors are logged and swallowed.

### Step 3: Exception (`app/core/exceptions.py`)

Add after `PipelineExecutionError` (L69):
```python
class HookAbortError(PipelineExecutionError):
    """A hook in strict mode aborted the pipeline."""

    def __init__(self, hook_name: str, reason: str) -> None:
        self.hook_name = hook_name
        self.reason = reason
        super().__init__(f"Hook '{hook_name}' aborted pipeline: {reason}")
```

### Step 4: Config (`app/core/config.py`)

Add before `PipelineConfig`:
```python
class HookConfig(BaseModel):
    """Pipeline hook execution settings."""
    profile: Literal["minimal", "standard", "strict"] = "standard"
    custom_hook_dir: str = ""
    disabled_hooks: list[str] = Field(default_factory=list)
```

Add field to `PipelineConfig`:
```python
hooks: HookConfig = Field(default_factory=HookConfig)  # PIPELINE__HOOKS__*
```

### Step 5: Built-in hooks (`app/ai/hooks/builtin/`)

**`cost_tracker.py`** (profile: `minimal`):
- Accumulates `context.cost_tokens` per agent on `POST_AGENT`
- On `POST_PIPELINE`: logs total, per-agent breakdown
- Optionally calls `CostGovernor.track_tokens()` if available
- Returns `{"agent": name, "tokens": n}` from each invocation

**`structured_logger.py`** (profile: `standard`):
- Emits structured log on every event via `get_logger()`
- Fields: `run_id`, `agent_name`, `event`, `duration_ms`, `tokens_used`, `pipeline_name`
- Registered for all 8 events

**`progress_reporter.py`** (profile: `standard`):
- `PRE_PIPELINE`: `ProgressTracker.start(run_id, "pipeline")`
- `POST_LEVEL`: `ProgressTracker.update(run_id, progress=pct)`
- `POST_PIPELINE`: `ProgressTracker.update(run_id, progress=100, status=COMPLETED)`
- Requires `level` and total level count in `metadata["total_levels"]`

**`adversarial_gate.py`** (profile: `strict`):
- `POST_AGENT`: imports `EvaluatorAgentService`, runs evaluation on agent output
- If verdict is `"reject"`: raises `HookAbortError(hook_name, reason)`
- If verdict is `"accept"`/`"revise"`: returns verdict as output
- Graceful degradation: if evaluator unavailable, log warning and continue

**`pattern_extractor.py`** (profile: `strict`):
- `POST_PIPELINE`: analyzes all `NodeTrace` entries from `metadata["traces"]`
- Identifies recurring patterns: same agent always errors, same contract always fails
- Returns structured pattern dict; does NOT write to knowledge base (deferred to 48.12)

**`__init__.py`** — `register_builtin_hooks(registry: HookRegistry)`:
- Imports all 5 built-in hooks, registers each with its event+profile
- Called from `PipelineExecutor.__init__` when hooks are enabled

### Step 6: Wire into `PipelineExecutor` (`executor.py`)

Modify `__init__` to accept optional `HookRegistry`:
```python
def __init__(self, ..., hook_registry: HookRegistry | None = None) -> None:
    ...
    self._hooks = hook_registry
```

Inject `fire()` calls at 8 points in `execute()` and `_run_node()`:

| Point | Event | Context extras |
|-------|-------|----------------|
| `execute()` L87 after proactive warnings | `PRE_PIPELINE` | `metadata={"total_levels": len(levels)}` |
| `execute()` L97 before level starts | `PRE_LEVEL` | `level=lvl_idx` |
| `execute()` L134 after level complete | `POST_LEVEL` | `level=lvl_idx, metadata={"total_levels": ...}` |
| `execute()` L148 before return | `POST_PIPELINE` | `cost_tokens=total_tokens, metadata={"traces": traces}` |
| `_run_node()` L163 after semaphore | `PRE_AGENT` | `agent_name=node.agent_name` |
| `_run_node()` L182 after adapt_outputs | `POST_AGENT` | `agent_name, cost_tokens=tokens, node_trace=trace` |
| `_run_node()` L194 contract failed | `CONTRACT_FAILED` | `agent_name, metadata={"failures": ...}` |
| `_run_node()` L182 after put (via store wrapper) | `ARTIFACT_STORED` | Deferred — optional, add if needed |

Helper method on executor:
```python
async def _fire(self, event: HookEvent, **kwargs: Any) -> None:
    if self._hooks is None:
        return
    ctx = HookContext(run_id=self._current_run_id, pipeline_name=self._dag.name, event=event, **kwargs)
    await self._hooks.fire(event, ctx)
```

Store `run_id` as `self._current_run_id` at start of `execute()`.

### Step 7: `__init__.py` public API

```python
from app.ai.hooks.registry import HookContext, HookEvent, HookFn, HookRegistry, HookResult
from app.ai.hooks.profiles import HookProfile

__all__ = ["HookContext", "HookEvent", "HookFn", "HookProfile", "HookRegistry", "HookResult"]
```

## Tests (14 total)

### `test_registry.py` (5 tests)
1. `test_register_and_fire` — register hook, fire event, verify `HookResult` returned
2. `test_profile_filtering` — register `strict` hook, fire with `standard` profile → not called
3. `test_disabled_hook_skipped` — register with name in `disabled` set → skipped
4. `test_hook_error_captured` — hook raises `RuntimeError` → result has error, no propagation
5. `test_hook_abort_propagates` — hook raises `HookAbortError` → re-raised

### `test_profiles.py` (3 tests)
6. `test_profile_includes_same_level` — `minimal` includes `minimal`
7. `test_profile_includes_higher` — `strict` includes `minimal` and `standard`
8. `test_profile_excludes_lower` — `minimal` excludes `standard` and `strict`

### `test_builtin.py` (3 tests)
9. `test_cost_tracker_accumulates` — fire `POST_AGENT` 3x with different token counts → totals correct
10. `test_adversarial_gate_reject_aborts` — mock evaluator returns `reject` → `HookAbortError` raised
11. `test_progress_reporter_updates` — fire `PRE_PIPELINE` + `POST_LEVEL` + `POST_PIPELINE` → `ProgressTracker` entries

### `test_integration.py` (3 tests)
12. `test_executor_fires_hooks` — `PipelineExecutor` with `HookRegistry` + mock hook → verify `PRE_PIPELINE`, `PRE_AGENT`, `POST_AGENT`, `POST_PIPELINE` fired in order
13. `test_minimal_profile_cost_only` — executor with `minimal` profile → only `cost_tracker` fires
14. `test_strict_abort_stops_pipeline` — executor with `strict` profile + adversarial_gate mock rejecting → pipeline stops, `HookAbortError` raised

### Test fixtures (`conftest.py`)
```python
@pytest.fixture
def hook_registry() -> HookRegistry:
    return HookRegistry(active_profile="standard")

@pytest.fixture
def mock_hook_fn() -> AsyncMock:
    return AsyncMock(return_value=None)
```

Reuse `MockAgentRunner`, `three_level_dag`, `pipeline_config`, `artifact_store` from `app/ai/pipeline/tests/conftest.py`.

## Security Checklist

No new endpoints. No user input reaches hook system (pipeline-internal only). `HookAbortError` message does not leak internal types. Cost governor integration uses existing auth-gated paths.

## Verification

- [ ] `make check` passes
- [ ] `make types` — pyright errors ≤ 31 for `app/ai/pipeline/`, 0 for new `app/ai/hooks/`
- [ ] `minimal` profile: only cost_tracker runs
- [ ] `standard` profile: cost + logging + progress
- [ ] `strict` profile: all hooks including adversarial gate
- [ ] Custom hook registered → fires on correct event
- [ ] Disabled hook → skipped
- [ ] `HookAbortError` in strict mode → pipeline stops
- [ ] Cost tracker accumulates correctly across 3-agent DAG
- [ ] 14 tests pass
