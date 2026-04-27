# Plan: 48.3 Typed Artifact Protocol for Inter-Agent Data Flow

## Context
Replace loose `AgentHandoff` dict-style passing with a typed artifact system. Each artifact has a schema, validation, and lifecycle. An `ArtifactStore` manages artifacts during a pipeline run. This makes data dependencies explicit and enables future DAG executor to validate artifact availability before running a node.

## Research Summary

**Current architecture:** `AgentHandoff` in `app/ai/blueprints/protocols.py:93-133` is already a frozen dataclass with `typed_payload: object | None`. Nine typed payloads exist in `app/ai/blueprints/handoff.py` (ScaffolderHandoff, DarkModeHandoff, etc.) with a `HANDOFF_PAYLOAD_TYPES` registry. `BlueprintEngine` orchestrates via state machine, calls `on_handoff` callback after each node.

**Key files:**
| File | Role |
|------|------|
| `app/ai/blueprints/protocols.py` | AgentHandoff, NodeContext, NodeResult, HandoffStatus |
| `app/ai/blueprints/handoff.py` | 9 typed payloads + registry + `format_upstream_constraints()` |
| `app/ai/blueprints/engine.py` | BlueprintEngine orchestrator (51KB) |
| `app/ai/blueprints/checkpoint.py` | CheckpointStore protocol, serialization |
| `app/ai/agents/schemas/build_plan.py` | EmailBuildPlan frozen dataclass |
| `app/qa_engine/schemas.py` | QACheckResult (Pydantic BaseModel) |
| `app/design_sync/visual_verify.py` | SectionCorrection frozen dataclass |
| `app/core/exceptions.py` | AppError hierarchy |
| `app/core/config.py` | Nested Pydantic config pattern |

**Patterns to follow:** Frozen dataclasses for immutable artifacts, `@runtime_checkable` Protocol for adapter contract, `REGISTRY` dict for dispatch, `dataclasses.replace()` for mutation, `AppError` subclass for domain exceptions.

## Test Landscape

**Existing test files (primary):**
| File | Lines | Relevance |
|------|-------|-----------|
| `app/ai/blueprints/tests/test_handoff.py` | 296 | Handoff propagation, callback pattern |
| `app/ai/blueprints/tests/test_typed_handoff.py` | 241 | Frozen payloads, upstream constraints |
| `app/ai/blueprints/tests/test_checkpoint.py` | 284 | Serialization/persistence (closest pattern) |
| `app/ai/blueprints/tests/test_engine.py` | 396 | Engine execution, stub nodes |
| `app/ai/blueprints/tests/conftest.py` | 68 | `sample_html_valid()`, `mock_provider()` |

**Test patterns:** StubAgenticNode/StubDeterministicNode inline doubles, `_make_run()` factory, `CapturingNode` for metadata inspection, AsyncMock for LLM provider, `@pytest.mark.asyncio` on all async tests. No fakeredis — use inline AsyncMock for Redis.

## Type Check Baseline

| Tool | Scope | Errors | Warnings |
|------|-------|--------|----------|
| Pyright | `app/ai/` | 202 | 384 |
| Pyright | `app/ai/blueprints/` | 37 | 81 |
| Mypy | `app/ai/` | 5 | — |

None blocking for this feature.

## Files to Create

| File | Purpose |
|------|---------|
| `app/ai/pipeline/__init__.py` | Package init |
| `app/ai/pipeline/artifacts.py` | Artifact base, concrete types, ArtifactStore, ArtifactNotFoundError |
| `app/ai/pipeline/adapters/__init__.py` | Package init + `ADAPTER_REGISTRY` |
| `app/ai/pipeline/adapters/scaffolder.py` | ScaffolderAdapter |
| `app/ai/pipeline/adapters/dark_mode.py` | DarkModeAdapter |
| `app/ai/pipeline/adapters/content.py` | ContentAdapter |
| `app/ai/pipeline/adapters/outlook_fixer.py` | OutlookFixerAdapter |
| `app/ai/pipeline/adapters/accessibility.py` | AccessibilityAdapter |
| `app/ai/pipeline/adapters/personalisation.py` | PersonalisationAdapter |
| `app/ai/pipeline/adapters/code_reviewer.py` | CodeReviewerAdapter |
| `app/ai/pipeline/adapters/knowledge.py` | KnowledgeAdapter |
| `app/ai/pipeline/adapters/innovation.py` | InnovationAdapter |
| `app/ai/pipeline/adapters/visual_qa.py` | VisualQAAdapter |
| `app/ai/pipeline/tests/__init__.py` | Test package |
| `app/ai/pipeline/tests/test_artifacts.py` | ArtifactStore unit tests |
| `app/ai/pipeline/tests/test_adapters.py` | Adapter roundtrip tests |
| `app/ai/pipeline/tests/test_bridge.py` | AgentHandoff ↔ Artifact bridge tests |

## Files to Modify

| File | Change |
|------|--------|
| `app/ai/blueprints/protocols.py` | Add `to_artifacts()` and `from_artifacts()` bridge methods on AgentHandoff |
| `app/core/exceptions.py` | Add `ArtifactNotFoundError(AppError)` |

## Implementation Steps

### Step 1: Exception + Package Structure
Create `app/ai/pipeline/` package dirs. Add `ArtifactNotFoundError` to `app/core/exceptions.py`:
```python
class ArtifactNotFoundError(AppError):
    """Requested artifact not found in store."""
    def __init__(self, name: str) -> None:
        super().__init__(f"Artifact not found: {name}")
        self.artifact_name = name
```

### Step 2: Core Artifacts Module (`app/ai/pipeline/artifacts.py`)

**Base artifact:**
```python
@dataclass(frozen=True)
class Artifact:
    name: str
    produced_by: str
    produced_at: datetime
    schema_version: str = "1"
```

**Concrete artifact types** (all frozen dataclasses inheriting Artifact):
- `HtmlArtifact` — `html: str`, `sections: tuple[str, ...] = ()`
- `BuildPlanArtifact` — `plan: EmailBuildPlan`
- `QaResultArtifact` — `results: tuple[QACheckResult, ...]`, `passed: bool`, `score: float`
- `CorrectionArtifact` — `corrections: tuple[SectionCorrection, ...]`, `applied: int`, `skipped: int`
- `DesignTokenArtifact` — `tokens: DesignTokens`
- `ScreenshotArtifact` — `screenshots: dict[str, bytes]` (use `field(default_factory=dict)`)
- `EvalArtifact` — `verdict: str`, `feedback: str`, `score: float`

**ArtifactStore class:**
```python
class ArtifactStore:
    def __init__(self) -> None:
        self._store: dict[str, Artifact] = {}

    def put(self, name: str, artifact: Artifact) -> None:
        self._store[name] = artifact

    def get(self, name: str, expected_type: type[T]) -> T:
        artifact = self._store.get(name)
        if artifact is None:
            raise ArtifactNotFoundError(name)
        if not isinstance(artifact, expected_type):
            msg = f"Expected {expected_type.__name__}, got {type(artifact).__name__}"
            raise TypeError(msg)
        return artifact

    def get_optional(self, name: str, expected_type: type[T]) -> T | None:
        artifact = self._store.get(name)
        if artifact is None:
            return None
        if not isinstance(artifact, expected_type):
            return None
        return artifact

    def has(self, name: str) -> bool:
        return name in self._store

    def names(self) -> frozenset[str]:
        return frozenset(self._store)

    def snapshot(self) -> dict[str, str]:
        return {k: type(v).__name__ for k, v in self._store.items()}
```

**Optional Redis persistence** (async methods on ArtifactStore):
- `async persist(self, run_id: str, redis: Redis) -> None` — JSON-serialize snapshot to `artifact:{run_id}`
- `async restore(cls, run_id: str, redis: Redis) -> dict[str, str]` — load snapshot (metadata only; full restore needs typed deserializers, deferred to future phase)

### Step 3: Adapter Protocol + Registry (`app/ai/pipeline/adapters/__init__.py`)

```python
@runtime_checkable
class ArtifactAdapter(Protocol):
    agent_name: str
    def input_artifacts(self) -> frozenset[str]:
        """Artifact names this agent reads.""" ...
    def output_artifacts(self) -> frozenset[str]:
        """Artifact names this agent produces.""" ...
    def adapt_inputs(self, store: ArtifactStore) -> dict[str, Any]:
        """Convert artifacts → agent kwargs.""" ...
    def adapt_outputs(self, response: Any, store: ArtifactStore) -> None:
        """Write agent outputs → artifacts.""" ...

ADAPTER_REGISTRY: dict[str, ArtifactAdapter] = {}

def register_adapter(adapter: ArtifactAdapter) -> ArtifactAdapter:
    ADAPTER_REGISTRY[adapter.agent_name] = adapter
    return adapter
```

### Step 4: Per-Agent Adapters (`app/ai/pipeline/adapters/*.py`)

Each adapter file follows the same pattern. Example for scaffolder:
```python
@dataclass(frozen=True)
class ScaffolderArtifactAdapter:
    agent_name: str = "scaffolder"

    def input_artifacts(self) -> frozenset[str]:
        return frozenset({"design_tokens"})  # optional input

    def output_artifacts(self) -> frozenset[str]:
        return frozenset({"html", "build_plan"})

    def adapt_inputs(self, store: ArtifactStore) -> dict[str, Any]:
        tokens = store.get_optional("design_tokens", DesignTokenArtifact)
        return {"design_tokens": tokens.tokens if tokens else None}

    def adapt_outputs(self, response: ScaffolderResponse, store: ArtifactStore) -> None:
        now = datetime.now(UTC)
        store.put("html", HtmlArtifact(
            name="html", produced_by="scaffolder", produced_at=now,
            html=response.html,
        ))
        if response.plan:
            store.put("build_plan", BuildPlanArtifact(
                name="build_plan", produced_by="scaffolder", produced_at=now,
                plan=response.plan,
            ))
```

All 10 adapters: scaffolder, dark_mode, content, outlook_fixer, accessibility, personalisation, code_reviewer, knowledge, innovation, visual_qa. Register each at module level via `register_adapter()`.

**Adapter input/output mapping:**

| Agent | Reads | Produces |
|-------|-------|----------|
| scaffolder | design_tokens? | html, build_plan |
| dark_mode | html | html |
| content | html | html |
| outlook_fixer | html, qa_results? | html |
| accessibility | html | html |
| personalisation | html | html |
| code_reviewer | html | qa_results |
| knowledge | — | — (advisory) |
| innovation | html? | html |
| visual_qa | html, screenshots? | corrections, html |

### Step 5: Bridge Methods on AgentHandoff (`app/ai/blueprints/protocols.py`)

Add two bridge methods to `AgentHandoff`:
```python
def to_artifacts(self, store: ArtifactStore) -> None:
    """Deprecated: bridge handoff → artifact store."""
    now = datetime.now(UTC)
    if self.artifact:
        store.put("html", HtmlArtifact(
            name="html", produced_by=self.agent_name,
            produced_at=now, html=self.artifact,
        ))

@classmethod
def from_artifact_store(cls, store: ArtifactStore, agent_name: str) -> AgentHandoff:
    """Deprecated: bridge artifact store → handoff."""
    html_art = store.get_optional("html", HtmlArtifact)
    return cls(
        agent_name=agent_name,
        artifact=html_art.html if html_art else "",
    )
```

Import `TYPE_CHECKING` guarded imports for artifact types.

### Step 6: Tests (`app/ai/pipeline/tests/`)

**test_artifacts.py** (~12 tests):
1. `test_put_and_get` — store HtmlArtifact, retrieve with type check
2. `test_get_wrong_type_raises` — store HtmlArtifact, get as BuildPlanArtifact → TypeError
3. `test_get_missing_raises` — get nonexistent → ArtifactNotFoundError
4. `test_get_optional_missing` — returns None
5. `test_get_optional_wrong_type` — returns None
6. `test_has` — true/false
7. `test_names` — returns frozenset of stored names
8. `test_snapshot` — returns `{name: type_name}` dict
9. `test_frozen_artifacts` — cannot mutate fields
10. `test_overwrite` — put same name twice, latest wins
11. `test_persist_snapshot` — AsyncMock Redis, verify set called with JSON
12. `test_restore_snapshot` — AsyncMock Redis, verify get returns deserialized

**test_adapters.py** (~4 tests):
1. `test_scaffolder_adapter_roundtrip` — adapt_outputs → store → adapt_inputs reads
2. `test_code_reviewer_adapter_reads_html` — store html, adapt_inputs extracts it
3. `test_adapter_registry_populated` — all 10 agents registered
4. `test_adapter_protocol_compliance` — isinstance checks on all adapters

**test_bridge.py** (~2 tests):
1. `test_handoff_to_artifacts` — AgentHandoff.to_artifacts() populates store
2. `test_from_artifact_store` — round-trip store → AgentHandoff

## Preflight Warnings

- `AgentHandoff` is frozen — bridge methods must be pure (no mutation). `to_artifacts()` writes to external store, `from_artifact_store()` is classmethod. Both safe.
- `typed_payload: object | None` field already exists — artifacts complement rather than replace payloads during migration.
- 9 agent response types have varying signatures — adapters must handle optional fields gracefully.
- `QACheckResult` is Pydantic BaseModel (not dataclass) — `QaResultArtifact.results` stores as tuple, no serialization issues.

## Security Checklist

No new endpoints introduced. All new code is internal pipeline infrastructure:
- [ ] No user input reaches artifact names (internal string constants only)
- [ ] No `eval()` or dynamic deserialization of artifact data
- [ ] Redis persistence uses `run_id` scoped keys (no user-controlled key names)
- [ ] Frozen dataclasses prevent mutation after creation

## Verification

- [ ] `make check` passes
- [ ] `make types` — pyright errors ≤ 202 for `app/ai/`, mypy errors ≤ 5
- [ ] 18 new tests pass (`test_artifacts.py` 12 + `test_adapters.py` 4 + `test_bridge.py` 2)
- [ ] All existing `app/ai/blueprints/tests/` tests still pass (no breaking changes)
- [ ] `ArtifactStore.snapshot()` roundtrips correctly
- [ ] Bridge methods are backward compatible (existing AgentHandoff usage unchanged)
