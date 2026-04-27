# Tech Debt 07 — Decompose `BlueprintEngine` God Functions

**Source:** `TECH_DEBT_AUDIT.md`
**Scope:** `app/ai/blueprints/engine.py` is 1416 LOC with 18 broad excepts and 8 type:ignores. Two functions own most of it: `_build_node_context` (437 LOC, 18 LAYERs) and `_execute_from` (397 LOC). Behaviour-preserving extraction.
**Goal:** Each function ≤ 80 LOC; each LAYER independently testable; engine becomes a state-machine orchestrator.
**Estimated effort:** Full session. Don't split this.
**Prerequisite:** Plan 05 landed — if Phase 48 was parked, the evaluator-revision branch in `_execute_from` (lines 580-600) is already gone, simplifying this work.

## Findings addressed

F016 (`_build_node_context` 437 LOC, 18 LAYERs) — High
F017 (`_execute_from` 397 LOC state machine) — High
Engine quality cluster: 18 broad `except Exception`, 8 `# type: ignore`

## Pre-flight

```bash
git checkout -b refactor/tech-debt-07-engine-decomp
make check
```

**Snapshot blueprint runs.** This refactor must be behaviour-preserving. Capture a baseline:
```bash
mkdir -p traces/refactor-snapshots
make eval-full > traces/refactor-snapshots/before.txt 2>&1
# also dump a few BlueprintRun JSONs:
python -c "from app.ai.blueprints.service import BlueprintService; ..." \
  > traces/refactor-snapshots/before-runs.json
```

## Part A — `_build_node_context` (F016)

### A1. Identify the LAYERs

Read `app/ai/blueprints/engine.py:738-1175`. Each LAYER is a numbered comment. Confirmed layer boundaries (from audit):
```
LAYER 7   :806   handoff context
LAYER 8   :833   QA failures
LAYER 9   :854   correction examples
LAYER 10  :930
LAYER 11  :937
LAYER 11.5:947
LAYER 12  :960
LAYER 13  :987
LAYER 14  :997
LAYER 14.5:1014
LAYER 15  :1051
LAYER 16  :1109
LAYER 17  :1125
LAYER 18  :1140  scan_for_injection on user content
```
Plus LAYERs 1-6 earlier in the function (~lines 740-805).

### A2. Extract per-LAYER methods

Each LAYER becomes a private async method on `BlueprintEngine` with the signature:
```python
async def _layer_<N>_<name>(
    self, ctx: NodeContext, run: BlueprintRun, node: Node
) -> dict[str, Any]:
    """Returns metadata to merge into ctx. Empty dict = no-op."""
```

Examples:
- `_layer_7_handoff_context` returns `{"handoff": handoff_meta}`.
- `_layer_8_qa_failures` returns `{"qa_failures": [...]}`.
- `_layer_18_injection_scan` raises on bad content; returns `{}`.

### A3. Replace `_build_node_context` body with a list-driven merge

```python
async def _build_node_context(self, run, node) -> NodeContext:
    ctx = NodeContext.empty()
    layers = [
        self._layer_1_skill_detection,
        self._layer_2_design_tokens,
        # ...
        self._layer_7_handoff_context,
        self._layer_8_qa_failures,
        # ...
        self._layer_18_injection_scan,
    ]
    for layer in layers:
        meta = await layer(ctx, run, node)
        if meta:
            ctx = ctx.merge(meta)
    return ctx
```

### A4. Make `NodeContext.merge` explicit

Currently the LAYERs mutate `ctx.metadata` in-place. Replace with a frozen `NodeContext` + `merge(other: dict) -> NodeContext` that returns a new instance. This eliminates ordering bugs from LAYER mutations.

### A5. Per-LAYER unit tests

Add `app/ai/blueprints/tests/test_node_context_layers.py`. One test per LAYER:
```python
async def test_layer_7_handoff_context_present():
    engine = BlueprintEngine(...)
    run = make_run_with_handoff(...)
    meta = await engine._layer_7_handoff_context(ctx, run, node)
    assert "handoff" in meta
    assert meta["handoff"].agent_name == "scaffolder"

async def test_layer_8_qa_failures_empty_when_no_failures():
    ...
```

## Part B — `_execute_from` (F017)

### B1. Identify branches

`app/ai/blueprints/engine.py:270-666`. Branches:
- Cost cap check (early exit)
- Evaluator revision routing (`:580-600`) — **may already be deleted by Plan 05**
- Confidence-based routing
- Recovery (retry on failure)
- Checkpoint persistence
- Node result handling (success/failure/handoff/abort)

### B2. Extract handlers

```python
async def _handle_node_result(
    self, run, node, result: NodeResult
) -> ExecutionDecision:
    """Returns: continue, retry, abort, route_to(other_node)."""

async def _apply_evaluator_verdict(...)  # only if Phase 48 shipped (Plan 05 Path A)

async def _persist_checkpoint_if_enabled(self, run, node) -> None:
    if not settings.blueprint.checkpoints_enabled:
        return
    ...

async def _enforce_cost_cap(self, run) -> bool:
    """Returns True if cap exceeded; caller breaks."""
```

### B3. Replace `_execute_from` body with a thin loop

```python
async def _execute_from(self, run, start_node):
    current = start_node
    while current:
        if await self._enforce_cost_cap(run):
            break

        try:
            result = await self._run_node(run, current)
        except Exception as exc:
            decision = await self._handle_node_failure(run, current, exc)
        else:
            decision = await self._handle_node_result(run, current, result)

        await self._persist_checkpoint_if_enabled(run, current)
        current = self._next_node(current, decision)
```

### B4. Narrow exception handlers

Address the 18 broad `except Exception` clusters in this file. Each one should narrow to:
- `(httpx.HTTPError, anthropic.APIError, asyncio.TimeoutError)` for LLM calls
- `ValidationError` for schema failures
- Nothing else gets swallowed — let `KeyboardInterrupt`, `SystemExit`, programming errors propagate.

For each, audit:
```bash
rg "except Exception" app/ai/blueprints/engine.py -n
```

## Part C — Late imports

`app/ai/blueprints/engine.py:808` (`_get_settings_ce2`), `:770` (`format_upstream_constraints`), `:811` (`correction_examples`), `:1140-1175` (`scan_for_injection`). Hoist all to module top. The "import-on-demand" perf concern is negligible at engine instantiation cost. (F021 in app/ai audit.)

## Verification

```bash
make check
make test app/ai/blueprints/ -v

# Behaviour-preserving check: replay snapshot
make eval-full > traces/refactor-snapshots/after.txt 2>&1
diff traces/refactor-snapshots/before.txt traces/refactor-snapshots/after.txt
# Differences should be limited to timestamps and JSON ordering.

# Specific behaviours:
pytest app/ai/blueprints/tests/test_node_context_layers.py -v
pytest app/ai/blueprints/tests/test_engine_state_machine.py -v
```

## Rollback

Single PR revert. The extraction is purely additive in the layer functions; the parent function bodies become small. If any LAYER misbehaves, the per-LAYER unit test catches it before merge.

## Risk notes

- **LAYER ordering is critical.** The current in-place mutation pattern means `LAYER 8` may read state set by `LAYER 7`. After the refactor, the merge order in the list is the only ordering guarantee — verify the list matches the original execution order.
- **Frozen `NodeContext`** is a contract change. Any code that mutates `ctx.metadata` directly elsewhere will break — find via `rg "ctx\.metadata\[" app/ai/`.
- **Test fixture coverage**: the engine has many integration tests. They should pass without modification *if* the refactor is behaviour-preserving. If they fail, you've changed semantics.
- **Phase 48 dependency**: if Plan 05 chose Ship (Path A), the evaluator branch stays. If Park (B), delete it as part of this plan.

## Done when

- [ ] Each LAYER ≤ 30 LOC in its own method.
- [ ] `_build_node_context` ≤ 30 LOC (just the merge loop).
- [ ] `_execute_from` ≤ 60 LOC (just the state-machine loop).
- [ ] Per-LAYER unit tests exist.
- [ ] Engine integration tests pass without modification.
- [ ] `eval-full` output diff vs baseline is empty (modulo timestamps).
- [ ] PR titled `refactor(ai/blueprints): decompose engine god-functions (F016 F017)`.
- [ ] Mark F016, F017 as **RESOLVED**.
