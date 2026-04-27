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

## Decision: Path B (Park) — selected 2026-04-27

Rationale: Path A's shadow-mode telemetry is a sprint-sized side project (HTML c14n equality harness, token-budget cap, 2-week watch window) for code that may never become primary. Path B is reversible via `git mv prototypes/ai-pipeline app/ai/pipeline`, preserving full history. Re-import requires evaluator agent calibration baseline before primary use.

Path A is preserved below for reference but skip to Path B for execution.

### Decision gate reference

| Path | Effort | Outcome |
|---|---|---|
| **Ship — Shadow mode** | Full session + 2 weeks of telemetry | Both engines run; DAG output compared against legacy. After 2 weeks of agreement, flip primary. |
| **Park** ✅ selected | ½ session | Code moves to `prototypes/` branch. `app/ai/pipeline/`, `EvaluatorNode`, `adversarial_gate.py` removed from main. Re-imported when ready. |

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
    pipeline/                    ← from app/ai/pipeline/ (whole tree incl. tests)
    nodes/evaluator_node.py      ← from app/ai/blueprints/nodes/
    nodes/tests/test_evaluator_node.py  ← if present
    agents/evaluator/            ← from app/ai/agents/evaluator/ (service.py, prompts, criteria, tests)
    hooks/adversarial_gate.py    ← from app/ai/hooks/builtin/
  README.md  ← explains what's parked, why, and re-import steps (incl. evaluator calibration prerequisite)
```

This is **outside `app/`** so it doesn't pollute the production tree.

Test files in `app/ai/pipeline/tests/` move with the package (no separate decision). Knowledge proactive-QA test `app/knowledge/tests/test_proactive_qa.py` references `ProactiveWarningsArtifact` — see B2.5.

### B2. Remove engine evaluator-routing branches

`app/ai/blueprints/engine.py` — two evaluator branches to delete:

- **L580-601**: evaluator-revision cap + qa_failures injection
- **L713-716**: secondary "revise" verdict check
- **L112**: `evaluator_revision_count: int = 0` field on `BlueprintRun` (in-memory Pydantic — **no DB migration needed**, this is not a SQLAlchemy model)

Tests asserting evaluator routing → delete or move to `prototypes/` alongside the agent.

### B2.5. Decouple `ProactiveWarningsArtifact` and `HtmlArtifact` from `app/`

`app/ai/pipeline/artifacts.py` defines `ProactiveWarningsArtifact` (Phase 48.12) and `HtmlArtifact`, both still used by code that is **not** parked:

- `app/knowledge/tests/test_proactive_qa.py:276` imports `ProactiveWarningsArtifact` (test only — production `app/knowledge/proactive_qa.py` has no runtime pipeline import despite docstring wording).
- `app/ai/blueprints/protocols.py:16,143,164` imports `ArtifactStore` (TYPE_CHECKING) and `HtmlArtifact` (runtime).

Choose one:
1. **Drop the artifact-store seam from production code** (preferred) — rewrite `protocols.py` to drop `ArtifactStore`/`HtmlArtifact`, and replace the proactive-QA test's artifact-roundtrip assertion with a direct `ProactiveWarningInjector` call.
2. **Keep a minimal artifact stub** in `app/core/` if the seam has independent value — only justified if a non-pipeline caller uses it.

Verify after: `rg "from app.ai.pipeline" app/  # 0 results`.

### B3. Remove `PipelineConfig`

`app/core/config.py:794-806` — delete the entire `PipelineConfig` block + nested `HookConfig` (lines 786-791) + the `pipeline: PipelineConfig` field on `Settings` (line 886). Remove `PIPELINE__*` entries from `.env.example`.

### B4. Remove adversarial-gate hook registration

`app/ai/hooks/builtin/__init__.py:14,24` — drop the `adversarial_gate` import and `adversarial_gate.register(registry)` call. If the `strict` profile in `HookConfig` only existed to gate this hook (now moot since `PipelineConfig` is gone), no further cleanup needed — the profile literal dies with `HookConfig` in B3.

### B5. Documentation

`docs/phase-48-status.md` — explain that Phase 48 DAG infra is parked. Reference the prototypes/ path. Note prerequisites for re-importing (e.g., evaluator agent calibration baseline must exist).

### B6. Verification

```bash
make check
# Confirm zero refs from app/ to parked code (regex alternation, not literal pipe):
rg "from app\.ai\.pipeline|EvaluatorNode|adversarial_gate|EvaluatorAgentService|app\.ai\.agents\.evaluator" app/  # 0 results
# Confirm config gone:
rg "PIPELINE__|PipelineConfig|HookConfig" app/ .env.example  # 0 results
# Confirm engine evaluator branches gone:
rg "evaluator_revision_count|agent_name == \"evaluator\"" app/ai/blueprints/  # 0 results
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
