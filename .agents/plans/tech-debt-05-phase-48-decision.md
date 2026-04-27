# Tech Debt 05 — Phase 48 Decision: Ship or Park

**Source:** `TECH_DEBT_AUDIT.md`
**Scope:** ~1,500 LOC of Phase 48 DAG executor + evaluator agent + adversarial-gate hook is dormant behind disabled flags. Decide: wire it through to production, or move it out of `app/`.
**Goal:** No "tested but unused" infra in `app/`. Clear owner for the legacy `BlueprintEngine` until DAG ships.
**Estimated effort:** ½ to full session, depending on path chosen.
**Prerequisite:** None.

## Findings addressed

F008 (`EvaluatorNode` not instantiated by any blueprint) — High
F009 (`PipelineExecutor` not invoked) — High
Drift in `app/ai/hooks/builtin/adversarial_gate.py` (depends on dead pipeline) — Medium

## Decision gate (do this first)

Pick one. The plan branches.

| Path | Effort | Outcome |
|---|---|---|
| **Ship — Shadow mode** | Full session + 2 weeks of telemetry | Both engines run; DAG output compared against legacy. After 2 weeks of agreement, flip primary. |
| **Park** | ½ session | Code moves to `prototypes/` branch. `app/ai/pipeline/`, `EvaluatorNode`, `adversarial_gate.py` removed from main. Re-imported when ready. |

Default recommendation: **Park**. The DAG is well-built but undertested in production. "Behind a default-False flag" is the worst of both worlds — it adds review surface and onboarding confusion without delivering value.

## Path A — Ship (shadow mode)

### A1. Wire executor in `app/ai/blueprints/service.py:164`

```python
async def run_blueprint(self, ...):
    if settings.pipeline.enabled and settings.pipeline.shadow_mode:
        legacy_result = await self._engine.run(...)
        try:
            shadow_result = await self._executor.run(...)
            self._compare(legacy_result, shadow_result)
        except Exception:
            logger.warning("pipeline.shadow_failed", exc_info=True)
        return legacy_result
    elif settings.pipeline.enabled:
        return await self._executor.run(...)
    return await self._engine.run(...)
```

### A2. Add `PipelineConfig.shadow_mode: bool = False`

`app/core/config.py:817` — add field. Default false. Document in `.env.example`.

### A3. Wire `EvaluatorNode` into `app/ai/blueprints/definitions/campaign.py`

Behind `settings.ai.evaluator.enabled`. Add to the routing graph between scaffolder and dark_mode.

### A4. Track agreement metric

Structured event `pipeline.shadow_compare` with fields: `agree (bool)`, `legacy_html_hash`, `dag_html_hash`, `divergence_section`. Log to `traces/shadow_compare.jsonl`.

### A5. Set a sunset date

In `docs/phase-48-shadow-status.md`: declare a 2-week shadow window. After 2 weeks, if agreement >99%, flip `shadow_mode=False` and `pipeline.enabled=True` in prod. After 4 weeks of pipeline-primary, delete legacy engine (separate plan).

### A6. Verification

```bash
make check
make eval-full  # both paths run, agreement metric in traces/
```

## Path B — Park (recommended default)

### B1. Move dormant code to `prototypes/`

```
prototypes/
  ai-pipeline/
    pipeline/   ← from app/ai/pipeline/
    nodes/evaluator_node.py  ← from app/ai/blueprints/nodes/
    hooks/adversarial_gate.py  ← from app/ai/hooks/builtin/
  README.md  ← explains what's parked, why, and re-import steps
```

This is **outside `app/`** so it doesn't pollute the production tree.

### B2. Remove engine evaluator-routing branch

`app/ai/blueprints/engine.py:580-600` — delete the evaluator-revision routing logic. Remove `evaluator_revision_count` field from `BlueprintRun` model + migration. Tests that asserted evaluator routing → delete or move to `prototypes/`.

### B3. Remove `PipelineConfig`

`app/core/config.py:817` — delete the entire `PipelineConfig` block + the `PIPELINE__*` env vars. Remove from `.env.example`.

### B4. Remove `HookConfig.profile=strict` if it only triggered `adversarial_gate`

Inspect `app/ai/hooks/builtin/__init__.py` — if `adversarial_gate` was the only `strict` hook, drop the profile or rename to reflect what's left.

### B5. Documentation

`docs/phase-48-status.md` — explain that Phase 48 DAG infra is parked. Reference the prototypes/ path. Note prerequisites for re-importing (e.g., evaluator agent calibration baseline must exist).

### B6. Verification

```bash
make check
# Confirm zero refs from app/ to parked code:
rg "from app.ai.pipeline\|EvaluatorNode\|adversarial_gate" app/  # 0 results
```

## Independent of path: F015 cleanup overlap

This plan supersedes the part of Plan 01 that touches `mjml_generator.py` only if Plan 01 hasn't landed. Otherwise no overlap.

## Rollback

**Path A:** Single revert; legacy engine remains primary.
**Path B:** Move directory back from `prototypes/` to `app/`. The engine evaluator-routing deletion is a separate revert (see git history).

## Risk notes

- **Path A** doubles every blueprint run for 2 weeks. Watch token costs — set a budget cap on `_executor.run()` so an infinite loop in DAG doesn't burn quota.
- **Path A divergence handling**: define what "agreement" means before you start. HTML byte-equality is too strict (whitespace differs). DOM-equality after `lxml.etree.tostring(method="c14n")` is the right baseline.
- **Path B** is reversible but emotionally hard — "we built that". If the work was sound, the prototypes/ branch keeps it. If not, the audit is the sign to cut losses.

## Done when

- [ ] Decision documented in PR description (A or B).
- [ ] Either: shadow mode running with agreement metric (A), OR `app/ai/pipeline/` removed from `app/` (B).
- [ ] `make check` green.
- [ ] PR titled `chore(ai): Phase 48 — {ship in shadow mode | park to prototypes/} (F008 F009)`.
- [ ] Mark F008, F009 as **RESOLVED** (B) or **IN PROGRESS — shadow window** (A).
