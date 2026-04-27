# Tech Debt 07 — Decompose `BlueprintEngine` God Functions

**Source:** `TECH_DEBT_AUDIT.md`
**Scope:** `app/ai/blueprints/engine.py` is 1382 LOC with 18 broad excepts and 8 type:ignores. Two functions own most of it: `_build_node_context` (≈437 LOC, 18 LAYERs) and `_execute_from` (≈397 LOC). Behaviour-preserving extraction.
**Goal:** Each function ≤ 80 LOC; each LAYER independently testable; engine becomes a state-machine orchestrator.
**Estimated effort:** Full session. Don't split this.
**Prerequisite:** Plan 05 (tech-debt-05) decided **Path B — Park** on 2026-04-27. The evaluator branch and revision routing are being moved to `prototypes/`, not kept in `engine.py`. Verified absent: `grep EvaluatorNode|revision_count|MAX_REVISIONS app/ai/blueprints/engine.py` returns nothing. This plan therefore has **no Phase 48 conditional** — the simpler "no evaluator branch" code path is the only path.

## Findings addressed

F016 (`_build_node_context` 437 LOC, 18 LAYERs) — High
F017 (`_execute_from` 397 LOC state machine) — High
Engine quality cluster: 18 broad `except Exception`, 8 `# type: ignore`

## Pre-flight

```bash
git checkout -b refactor/tech-debt-07-engine-decomp
make check
```

**Snapshot blueprint runs.** Refactor must be behaviour-preserving. Use `eval-golden` as the deterministic baseline (no LLM, repeatable diff). `eval-full` is end-of-PR sanity only — its output is non-deterministic across runs (LLM stochasticity, timestamps), so a clean diff is not expected; use it to confirm pass-rate didn't regress, not byte-equality.

**Cost note:** `eval-full` is a developer/CI tool that runs synthetic test fixtures through the agents and judges them with an LLM. It is **not** invoked per email build — production-build evals only happen if `EVAL__PRODUCTION_SAMPLE_RATE > 0` (default `0.0`, off). For this refactor, `eval-full` is a single before/after baseline (≈$2-5 in LLM spend total, depending on provider). It is not a permanent recurring cost.

```bash
mkdir -p traces/refactor-snapshots
make eval-golden > traces/refactor-snapshots/before-golden.txt 2>&1
make eval-full   > traces/refactor-snapshots/before-full.txt 2>&1   # for pass-rate comparison only
```

### Audit external `NodeContext` mutators (do this first!)

```bash
rg "context\.metadata\[\"[^\"]+\"\]\s*=|ctx\.metadata\[\"[^\"]+\"\]\s*=" app/ -n
rg "(context|ctx)\.(html|brief|node_rules|iteration|build_plan|qa_failures|multimodal_context)\s*=\s*[^=]" app/ -n | grep -v engine.py
```

Known external `metadata` writers (must keep working):
- `app/ai/blueprints/nodes/visual_comparison_node.py:120,122` (production — visual_comparison + prev_screenshots)
- `app/ai/blueprints/nodes/visual_precheck_node.py:74,110` (production — precheck_screenshots + visual_precheck_failures)
- `app/ai/tests/test_recovery_outcomes.py:154-156,186` (fixture)
- `app/ai/agents/tests/test_recovery_router.py:43,45,47` (fixture)

Known external **top-level field** writers (must keep working):
- `app/ai/blueprints/nodes/scaffolder_node.py:213` — `context.build_plan = plan`
- `app/ai/blueprints/nodes/dark_mode_node.py:235` — `context.build_plan = merge_dark_mode(...)`
- `app/ai/blueprints/nodes/accessibility_node.py:267` — `context.build_plan = merge_accessibility(...)`
- `app/ai/blueprints/nodes/personalisation_node.py:279` — `context.build_plan = merge_personalisation(...)`
- `app/ai/tests/test_agent_multimodal.py:379,421` — `context.multimodal_context = …`

These are the **plan-accumulation pattern** for structured output mode: each agent node enriches `EmailBuildPlan` (or `multimodal_context`) and writes it back to context for the next agent. They are not LAYER ordering bugs — they are explicit handoff slots between agents.

### Constraint that drops out of the audit

`@dataclass(frozen=True)` is all-or-nothing — can't selectively freeze fields without an ugly `__setattr__` override or splitting the dataclass into two. Given:

1. `build_plan` and `multimodal_context` legitimately need post-construction mutation by agent nodes.
2. `metadata` legitimately needs in-place writes by visual nodes.
3. The actual LAYER-ordering bug surface is the fields *set during `_build_node_context`*: `html`, `brief`, `node_rules`, `iteration`, `qa_failures` — verified to have **zero external writers**.

**Decision: enforce LAYER purity by contract, not by `frozen=True`.** Specifically:
- `NodeContext` stays a mutable `@dataclass` (no `frozen=True`).
- LAYER methods get the type signature `_layer_N(...) -> dict[str, Any]` — they never receive a writable handle to `ctx` for mutation purposes.
- The entry function `_build_node_context` constructs the initial `NodeContext` once with LAYER-set fields, then iterates layers, then applies returned dicts via `merge_metadata`.
- Runtime guarantee comes from a **layer-ordering-invariance test**: shuffle the layer list, run `_build_node_context`, assert the resulting `metadata` is equivalent to the canonical order (modulo last-write-wins keys, which must be explicitly listed).
- Code-review checklist: "no `ctx.x = y` inside any `_layer_N` body" + ruff/grep CI guard if cheap.

## Execution order (each step ends with `make check` green)

The original plan listed Parts A/B/C without sequencing. The order below is chosen so the codebase compiles, tests pass, and behaviour is unchanged after every step. Do not re-order.

The original A4 (frozen `NodeContext` + functional `merge() -> NodeContext`) is replaced with a contract-based equivalent (LAYER methods return `dict[str, Any]`, entry function applies via `merge_metadata`, ordering-invariance test). See "Constraint that drops out of the audit" above for rationale.

### Step 1 — Part C: Hoist late imports (lowest risk, do first)

Files: `app/ai/blueprints/engine.py:808` (`_get_settings_ce2`), `:770` (`format_upstream_constraints`), `:811` (`correction_examples`), `:1140-1175` (`scan_for_injection`).

Move all to module top. Verify: `make check`.

This is purely mechanical, lets you confirm import cycles are clean before you start moving code, and reduces noise in subsequent diffs.

### Step 2 — Part A1-A3: Extract LAYERs as pure dict-returning methods

**Keep `NodeContext` mutable**. Don't freeze the dataclass. The extraction is what gives us testability — freezing is optional and addressed in Step 5.

#### A1. Identify the LAYERs

Read `app/ai/blueprints/engine.py:704-1141`. Layer boundaries (from audit):
```
LAYER 1-6 :740-805  (early setup)
LAYER 7   :806      handoff context
LAYER 8   :833      QA failures
LAYER 9   :854      correction examples
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
LAYER 18  :1140      scan_for_injection on user content
```

#### A2. Extract per-LAYER methods (pure, dict-returning)

Each LAYER becomes a private async method on `BlueprintEngine`:
```python
async def _layer_<N>_<name>(
    self, ctx: NodeContext, run: BlueprintRun, node: Node
) -> dict[str, Any]:
    """Returns metadata to merge into ctx.metadata. Empty dict = no-op.

    Read-only view of `ctx`. Must not mutate `ctx` or its fields.
    """
```

Examples:
- `_layer_7_handoff_context` returns `{"upstream_handoff": …, "upstream_constraints": …}`.
- `_layer_8_qa_failures` returns `{"qa_failure_details": …}`.
- `_layer_18_injection_scan` raises on bad content; returns `{}`.

**LAYERs 1-6 also become individual `_layer_N` methods** (consistent with 7-18). They seed top-level fields (`html`, `brief`, `iteration`, `node_rules`), so the entry function constructs the initial `NodeContext` from their combined output via `dataclasses.replace` *before* the metadata-merge loop begins. Concretely, each LAYER 1-6 returns a `dict` with reserved keys (`_html`, `_brief`, `_node_rules`, etc.) plus optional metadata. The entry function partitions reserved-keys-vs-metadata once, applies reserved keys via `replace`, then enters the loop for LAYERs 7-18.

#### A3. Add `NodeContext.merge_metadata(meta: dict) -> None` and rewrite `_build_node_context`

Add to `NodeContext` (still mutable):
```python
def merge_metadata(self, meta: Mapping[str, object]) -> None:
    """Merge new metadata in place. Last-write-wins per key."""
    self.metadata.update(meta)
```

Rewrite the entry function as a list-driven loop (≤30 LOC). The layer order is held as **instance attributes** (not local tuples) so the Step 4 invariance test can patch them:

```python
RESERVED_FIELD_KEYS = ("_html", "_brief", "_node_rules", "_iteration", "_qa_failures")

class BlueprintEngine:
    def __init__(self, ...):
        ...
        self._SEED_LAYERS = (
            self._layer_1_..., ..., self._layer_6_...,
        )
        self._METADATA_LAYERS = (
            self._layer_7_handoff_context,
            self._layer_8_qa_failures,
            # ... through LAYER 18, in original execution order
        )

    async def _build_node_context(self, node, run, brief, iteration) -> NodeContext:
        ctx = NodeContext()
        for layer in self._SEED_LAYERS + self._METADATA_LAYERS:
            out = await layer(ctx, run, node)
            if not out:
                continue
            field_updates = {k.lstrip("_"): out.pop(k) for k in RESERVED_FIELD_KEYS if k in out}
            if field_updates:
                ctx = dataclasses.replace(ctx, **field_updates)
            if out:
                ctx.merge_metadata(out)
        return ctx
```

**LAYER ordering is critical.** The current in-place mutation pattern means later LAYERs may read state set by earlier ones. The list order is the only ordering guarantee — verify it matches the original execution order line-by-line. Step 4's invariance test catches violations.

#### A5. Per-LAYER unit tests

Add `app/ai/blueprints/tests/test_node_context_layers.py`. One test per LAYER:
```python
async def test_layer_7_handoff_context_present():
    engine = BlueprintEngine(...)
    run = make_run_with_handoff(...)
    meta = await engine._layer_7_handoff_context(NodeContext(), run, node)
    assert "upstream_handoff" in meta

async def test_layer_8_qa_failures_empty_when_no_failures():
    ...
```

Verification gate after Step 2:
```bash
make check
pytest app/ai/blueprints/tests/test_node_context_layers.py -v
diff traces/refactor-snapshots/before.txt <(make eval-full)  # modulo timestamps
```

### Step 3 — Part B: Decompose `_execute_from`

Independent of Step 2; can be done after A1-A3 lands cleanly.

#### B1. Identify branches

`app/ai/blueprints/engine.py:269-643`. Branches:
- Cost cap check (early exit)
- Evaluator revision routing (`:580-600`) — **may already be deleted by Plan 05**
- Confidence-based routing
- Recovery (retry on failure)
- Checkpoint persistence
- Node result handling (success/failure/handoff/abort)

#### B2. Extract handlers

```python
async def _enforce_cost_cap(self, run) -> bool:
    """Returns True if cap exceeded; caller breaks."""

async def _handle_node_result(
    self, run, node, result: NodeResult
) -> ExecutionDecision:
    """Returns: continue, retry, abort, route_to(other_node)."""

async def _persist_checkpoint_if_enabled(self, run, node) -> None:
    if not settings.blueprint.checkpoints_enabled:
        return
    ...

```

(No `_apply_evaluator_verdict` — Plan 05 Park removed the evaluator branch; do not re-introduce.)

Define `ExecutionDecision` as a frozen dataclass in `protocols.py`:
```python
@dataclass(frozen=True)
class ExecutionDecision:
    action: Literal["continue", "retry", "abort", "route"]
    next_node: str | None = None
    reason: str = ""
```

**`_resolve_next_node` (currently `engine.py:673`) is absorbed.** Its current responsibility — pick the next node id given current node + result — splits into two pieces:
- The *decision logic* (when to retry vs continue vs route to recovery) moves into `_handle_node_result`, which inspects `result.status`, confidence, handoff, etc., and returns an `ExecutionDecision`.
- The *graph-walk lookup* (given "continue", what's the next node id?) becomes a thin `_next_node(current: str, decision: ExecutionDecision) -> str | None` helper — pure dict lookup against the blueprint definition, no branching logic.

This splits a function that today both decides *what* to do and *where* to go. Tests for `_handle_node_result` mock the result/run state; tests for `_next_node` are pure data tests against fixture blueprints.

#### B3. Replace `_execute_from` body with a thin loop (≤60 LOC)

```python
async def _execute_from(self, run, start_node, brief, plan, cost_tracker, user_id):
    current = start_node
    while current:
        if await self._enforce_cost_cap(run):
            break
        try:
            result = await self._run_node(run, current, brief, plan, cost_tracker, user_id)
        except (httpx.HTTPError, anthropic.APIError, asyncio.TimeoutError) as exc:
            decision = await self._handle_node_failure(run, current, exc)
        else:
            decision = await self._handle_node_result(run, current, result)
        await self._persist_checkpoint_if_enabled(run, current)
        current = self._next_node(current, decision)
    return run
```

#### B4. Audit exception handlers (re-raise discipline, not type narrowing)

The real hazard with the 18 broad excepts is **silent swallowing**, not type breadth. Type narrowing (`except (httpx.HTTPError, anthropic.APIError, ...)` etc.) is brittle when SDKs introduce new exception classes and trades one churn cost for another. Instead, audit each handler for whether it logs+propagates or logs+swallows:

```bash
rg -A 8 "except Exception" app/ai/blueprints/engine.py
```

For each handler, classify:
- **Logs and re-raises** (body ends with `raise` / `raise Foo(...) from exc`): leave as `except Exception` — that's a perfectly fine logging hook.
- **Logs and swallows** (body has no `raise`): this is the actual bug class. Either:
  - narrow the type to the specific known-safe-to-swallow exception (e.g. `redis.RedisError` for checkpoint persistence, `httpx.HTTPError` for telemetry emission), OR
  - document why swallowing is intentional in a one-line comment naming the failure mode (e.g. `# scan_for_injection failure-safe: do not crash pipeline if pattern compile fails`).
- **Catches `Exception` to convert to a pipeline-domain exception** (e.g. `raise BlueprintExecutionError(...) from exc`): leave as is — that's a translation boundary, not a swallow.

Add per-handler unit tests in `app/ai/blueprints/tests/test_engine_state_machine.py` covering the four `ExecutionDecision.action` values.

Programming errors (`KeyboardInterrupt`, `SystemExit`, `AssertionError`) must propagate. If any handler catches `BaseException` instead of `Exception`, that's a separate bug — fix it.

Verification gate after Step 3:
```bash
make check
pytest app/ai/blueprints/tests/test_engine_state_machine.py -v
diff traces/refactor-snapshots/before.txt <(make eval-full)
```

### Step 4 — Layer-ordering-invariance test

This is the runtime guarantee that replaces `frozen=True`. Add to `test_node_context_layers.py`:

```python
async def test_layer_ordering_invariance():
    """Layers must be order-independent except for explicitly declared last-write-wins keys."""
    engine = BlueprintEngine(...)
    run, node = make_full_fixture(...)

    canonical = await engine._build_node_context(node, run, brief, iteration=0)

    # Shuffle the metadata-layer order a few times; outcome metadata must match.
    # (Seed layers are NOT shuffled — their reserved-key writes are inherently order-sensitive.)
    for _ in range(5):
        shuffled = tuple(random.sample(engine._METADATA_LAYERS, len(engine._METADATA_LAYERS)))
        with patch.object(engine, "_METADATA_LAYERS", shuffled):
            ctx = await engine._build_node_context(node, run, brief, iteration=0)
        assert ctx.metadata == canonical.metadata, (
            "Layer mutation observed — a layer is reading state set by another layer. "
            "If this is intentional, declare the dependency explicitly."
        )
```

If the test fails, you have a real ordering bug — a layer is depending on metadata produced by an earlier layer. Either:
- Refactor so the dependent layer reads from `run` / `node` directly, not `ctx.metadata`, OR
- Document the dependency in a comment and add the offending key to a `_ORDER_DEPENDENT_KEYS` exclusion the test ignores.

This catches real bugs that `frozen=True` would also have caught at runtime, without breaking agent-node mutation patterns.

Verification gate: `make check` + the new test passing.

## Verification (final)

```bash
make check
pytest app/ai/blueprints/ -v
make eval-golden > traces/refactor-snapshots/after-golden.txt 2>&1
diff traces/refactor-snapshots/before-golden.txt traces/refactor-snapshots/after-golden.txt
# eval-golden is deterministic — diff should be empty modulo timestamps.

make eval-full > traces/refactor-snapshots/after-full.txt 2>&1
# eval-full has LLM noise — compare pass-rate, not byte-equality:
grep -E "pass.*rate|passed|failed" traces/refactor-snapshots/{before,after}-full.txt
```

## Rollback

Single PR, one logical commit per step (Step 1 / Step 2 / Step 3 / Step 4). Each commit is independently revertable, and the four step boundaries are the natural bisect cut points if a regression slips through.

The whole PR is one revert because the layer signatures, `ExecutionDecision`, and `merge_metadata` are mutually load-bearing — partial revert leaves the engine in an inconsistent state. If a LAYER misbehaves in production, fix forward (the per-LAYER unit tests should have caught it before merge, so a runtime failure points to a missing test fixture, not an architectural problem).

## Risk notes

- **LAYER ordering is critical.** Verify the merge-list matches the original execution order line-by-line — write the list down beside the original function body before deleting anything. The Step 4 invariance test is the runtime backstop.
- **Layer purity is contract-based, not runtime-enforced.** `NodeContext` stays mutable (because agent nodes legitimately reassign `build_plan` / `multimodal_context`, and visual nodes legitimately mutate `metadata`). Purity comes from: (a) the `_layer_N(...) -> dict[str, Any]` signature, (b) Step 4's ordering-invariance test, (c) a grep guard for `ctx.x = ` inside layer bodies.
- **Plan-accumulation pattern is preserved.** `scaffolder_node`, `dark_mode_node`, `accessibility_node`, `personalisation_node` all reassign `context.build_plan` after agent execution — this is structured-output handoff, not a bug. Do not refactor.
- **Visual nodes write metadata mid-pipeline.** `visual_comparison_node.py` and `visual_precheck_node.py` are not LAYERs — they're downstream consumers that publish results for later nodes. Their writes are part of the engine's contract; do not refactor them away.
- **Test fixture coverage**: blueprint integration tests should pass without modification *if* the refactor is behaviour-preserving. If they fail, semantics changed.
- **Phase 48 / evaluator branch**: removed by Plan 05 Park (2026-04-27). Do not reintroduce `EvaluatorNode`, `_apply_evaluator_verdict`, or revision-counter logic in this plan.
- **Pyright baseline**: 0 errors, 21 warnings on `engine.py + protocols.py` before this work. Any new errors are regressions.

## Done when

- [ ] Each LAYER ≤ 30 LOC in its own method.
- [ ] `_build_node_context` ≤ 30 LOC (just the merge loop).
- [ ] `_execute_from` ≤ 60 LOC (just the state-machine loop).
- [ ] Per-LAYER unit tests exist (`test_node_context_layers.py`).
- [ ] Layer-ordering-invariance test passes (Step 4).
- [ ] State-machine handler tests exist (`test_engine_state_machine.py`).
- [ ] Engine integration tests pass without modification.
- [ ] `eval-full` output diff vs baseline is empty (modulo timestamps).
- [ ] Late imports hoisted to module top (Step 1).
- [ ] No `ctx.x = y` writes inside any `_layer_N` body (grep audit clean).
- [ ] PR titled `refactor(ai/blueprints): decompose engine god-functions (F016 F017)`.
- [ ] Mark F016, F017 as **RESOLVED**.
