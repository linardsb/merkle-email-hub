# Plan: Agent Learning System — Failure-Outcome Ledger, Correction Few-Shot, Judge Aggregation, Confidence Calibration

## Context

Agents in the blueprint pipeline currently operate without learning from historical outcomes. The recovery router uses static `CHECK_TO_AGENT` mappings regardless of past resolution success rates. Self-correction prompts are generic with no examples of prior successful fixes. Judge verdicts are computed per-run but never aggregated to improve prompts. Confidence scores are stored but never validated against reality.

This plan adds 4 learning capabilities that close the feedback loop, ordered by impact:

1. **Failure-Outcome Ledger** — adaptive recovery routing based on historical fix success rates
2. **Correction Few-Shot Injection** — inject examples of prior successful corrections into retry prompts
3. **Judge Verdict Aggregation → Prompt Patching** — auto-detect chronic criterion failures and inject targeted instructions
4. **Confidence Calibration** — per-agent calibrated confidence thresholds based on actual outcomes

All features are off by default via `BlueprintConfig` flags. All persistence is fire-and-forget. No new API endpoints.

---

## Feature 1: Failure-Outcome Ledger (Highest Priority)

### Purpose

Replace static `CHECK_TO_AGENT` routing in `recovery_router_node.py` with data-driven fixer selection. If `scaffolder` consistently fails to fix `html_validation` issues, route to the next best agent automatically.

### Reference Pattern

Mirrors `app/ai/routing_history.py` exactly: SQLAlchemy model + Repository + adaptive logic function.

### New Files

#### `app/ai/recovery_outcomes.py` (~100 lines)

**Model:**
```python
class RecoveryOutcomeEntry(Base):
    __tablename__ = "recovery_outcomes"

    id: Mapped[int] (PK, autoincrement)
    check_name: Mapped[str] (String(64), index)        # e.g. "html_validation"
    agent_routed: Mapped[str] (String(64), index)       # e.g. "scaffolder"
    failure_fingerprint: Mapped[str | None] (String(128))  # MD5 hash from _fingerprint()
    resolved: Mapped[bool]                               # did QA pass after this fixer?
    iterations_needed: Mapped[int] (default=1)
    run_id: Mapped[str] (String(36))
    project_id: Mapped[int | None] (index)
    created_at: Mapped[datetime] (server_default=now())

    __table_args__ = (Index("ix_recovery_outcome_check_agent", "check_name", "agent_routed"),)
```

**Repository:**
```python
class RecoveryOutcomeRepository:
    def __init__(self, db: AsyncSession) -> None

    async def record(self, check_name, agent_routed, failure_fingerprint,
                     resolved, iterations_needed, run_id, project_id) -> None

    async def get_resolution_rate(self, check_name, agent_name, project_id,
                                  limit=20) -> tuple[float | None, int]
        # Returns (resolution_rate, sample_count). None if no history.
```

**Adaptive Selection:**
```python
MIN_OUTCOME_SAMPLES = 8
POOR_RESOLUTION_THRESHOLD = 0.30  # below this → skip agent

async def select_best_fixer(
    check_name: str,
    default_agent: str,            # from static CHECK_TO_AGENT
    project_id: int | None,
    repo: RecoveryOutcomeRepository,
) -> str:
    # 1. Get resolution rate for default_agent on this check_name
    # 2. If rate >= POOR_RESOLUTION_THRESHOLD or insufficient samples → return default_agent
    # 3. Otherwise, iterate _FIXER_PRIORITY candidates, pick first with rate > threshold
    # 4. If no candidate has data → return default_agent (static map fallback)
```

#### `alembic/versions/XX_add_recovery_outcomes.py` (~30 lines)

Standard migration following `routing_history` pattern.

### Modified Files

#### `app/core/config.py` — `BlueprintConfig` (line 411)

```python
recovery_ledger_enabled: bool = False
```

#### `app/ai/blueprints/service.py` — `_build_engine()` (line ~40)

Wire `RecoveryOutcomeRepository` into engine (same pattern as `routing_history_repo`):
```python
recovery_outcome_repo = None
if settings.blueprint.recovery_ledger_enabled and db is not None:
    from app.ai.recovery_outcomes import RecoveryOutcomeRepository
    recovery_outcome_repo = RecoveryOutcomeRepository(db)
```
Pass to `BlueprintEngine(recovery_outcome_repo=recovery_outcome_repo)`.

#### `app/ai/blueprints/engine.py`

**`__init__()` (line 126):** Accept `recovery_outcome_repo` parameter, store as `self._recovery_outcome_repo`.

**`_execute_from()` (line ~440, after QA gate tracking):** Record outcome fire-and-forget:
```python
if self._recovery_outcome_repo is not None and current_node_name == "qa_gate":
    try:
        await self._record_recovery_outcome(run, result)
    except Exception:
        logger.debug("blueprint.recovery_outcome_record_failed", ...)
```

**New method `_record_recovery_outcome(run, result)` (~25 lines):**
- Find the last agentic handoff before this QA gate
- Cross-reference with `run.previous_qa_failure_details` to identify which checks that fixer targeted
- For each targeted check: record `(check_name, agent_routed, fingerprint, resolved, iterations, run_id, project_id)`
- `resolved = True` if the check is no longer in `run.qa_failure_details`

**`_build_node_context()` (~line 650):** Inject repo into context metadata for recovery router:
```python
if self._recovery_outcome_repo is not None:
    context.metadata["recovery_outcome_repo"] = self._recovery_outcome_repo
    context.metadata["project_id"] = self._project_id
```

#### `app/ai/blueprints/nodes/recovery_router_node.py` — `execute()` (line 135)

Before `target = structured[0].suggested_agent` (line 154), add adaptive lookup:
```python
recovery_outcome_repo = context.metadata.get("recovery_outcome_repo")
if recovery_outcome_repo is not None:
    from app.ai.recovery_outcomes import select_best_fixer
    target = await select_best_fixer(
        check_name=structured[0].check_name,
        default_agent=structured[0].suggested_agent,
        project_id=context.metadata.get("project_id"),
        repo=recovery_outcome_repo,
    )
else:
    target = structured[0].suggested_agent
```

### Tests

**`app/ai/tests/test_recovery_outcomes.py`** (~120 lines):
- `test_record_and_get_resolution_rate`: Round-trip DB test
- `test_select_best_fixer_no_history`: Returns default agent
- `test_select_best_fixer_below_min_samples`: Returns default agent
- `test_select_best_fixer_skips_poor_performer`: Low resolution rate → picks alternate
- `test_select_best_fixer_below_threshold_all`: All poor → returns default
- `test_engine_records_recovery_outcome`: Engine integration with StubNodes
- `test_recovery_router_uses_ledger`: Mock repo injected via metadata, overrides static map

---

## Feature 2: Correction Few-Shot Injection

### Purpose

When a self-correction round succeeds (fixer runs → QA passes), store a compact correction example. On future correction rounds, recall 1-2 relevant examples and inject as few-shot context.

### New Files

#### `app/ai/blueprints/correction_examples.py` (~90 lines)

```python
async def store_correction_example(
    agent_name: str,
    check_name: str,
    failure_description: str,
    correction_summary: str,   # from handoff.decisions
    project_id: int | None,
    run_id: str,
) -> None:
    """Store a successful correction as procedural memory. Fire-and-forget.

    Uses existing MemoryService with:
    - memory_type="procedural"
    - metadata.source="correction_example"
    - content: "FAILURE: {failure_desc}\nCORRECTION: {correction_summary}\nAGENT: {agent_name}"
    """

async def recall_correction_examples(
    agent_name: str,
    qa_failures: list[str],
    project_id: int | None,
    limit: int = 2,
) -> list[str]:
    """Recall 1-2 correction examples relevant to current failures.

    Query: memory_type="procedural", similarity search on failure descriptions.
    Filter: metadata.source == "correction_example"
    """

def format_correction_examples(examples: list[str]) -> str:
    """Format as '## Prior Successful Corrections' context block."""
```

### Modified Files

#### `app/core/config.py` — `BlueprintConfig`

```python
correction_examples_enabled: bool = False
```

#### `app/ai/blueprints/engine.py`

**Store on success** — In `_execute_from()`, after `run.qa_passed = True` (line 430), add fire-and-forget block (~15 lines):
```python
# Store correction example if this was a recovery pass (fixer ran before)
if (settings.blueprint.correction_examples_enabled
    and run._handoff_history
    and any(run.iteration_counts.get(h.agent_name + "_node", 0) > 0
            for h in run._handoff_history)):
    try:
        await self._store_correction_example(run)
    except Exception:
        logger.debug("blueprint.correction_example_store_failed", ...)
```

New private method `_store_correction_example(run)` (~20 lines):
- Last handoff = fixer that succeeded
- `failure_description` from `run.previous_qa_failure_details`
- `correction_summary` from `handoff.decisions`
- Call `store_correction_example()`

**Recall on retry** — In `_build_node_context()`, new context layer:
```python
# Correction examples (agentic + iteration > 0 + feature enabled)
if (node.node_type == "agentic" and iteration > 0
    and settings.blueprint.correction_examples_enabled):
    from app.ai.blueprints.correction_examples import (
        recall_correction_examples, format_correction_examples,
    )
    examples = await recall_correction_examples(
        agent_name=agent_name, qa_failures=run.qa_failures,
        project_id=self._project_id,
    )
    if examples:
        context.metadata["correction_examples"] = format_correction_examples(examples)
```

### Tests

**`app/ai/blueprints/tests/test_correction_examples.py`** (~80 lines):
- `test_store_correction_example`: Mock MemoryService, verify store called with correct params
- `test_recall_returns_empty_when_no_matches`
- `test_recall_filters_by_source`
- `test_format_correction_examples_output`
- `test_engine_injects_on_retry`: Engine test with iteration > 0

---

## Feature 3: Judge Verdict Aggregation → Prompt Patching

### Purpose

Aggregate inline judge verdicts over time. When a criterion has <70% pass rate, auto-generate a targeted instruction and inject it into the agent's context.

### New Files

#### `app/ai/blueprints/judge_aggregator.py` (~110 lines)

```python
@dataclass
class PromptPatch:
    agent_name: str
    criterion: str
    pass_rate: float
    instruction: str       # e.g. "IMPORTANT: Your output frequently fails '{criterion}'. {reasoning}."
    sample_count: int

PASS_RATE_THRESHOLD = 0.70
MIN_VERDICT_SAMPLES = 5

async def persist_judge_verdict(
    verdict: JudgeVerdict,
    project_id: int | None,
    run_id: str,
) -> None:
    """Store each CriterionResult as a semantic memory entry. Fire-and-forget.

    metadata: {"source": "judge_verdict", "agent": ..., "criterion": ..., "passed": ..., "run_id": ...}
    """

async def aggregate_verdicts(
    agent_name: str,
    project_id: int | None,
    lookback_limit: int = 50,
) -> list[PromptPatch]:
    """Query recent judge verdicts for this agent.

    Uses raw SQL on memory_entries where metadata_json->>'source' = 'judge_verdict'.
    Groups by criterion, computes pass rates.
    Returns PromptPatch for criteria below PASS_RATE_THRESHOLD with >= MIN_VERDICT_SAMPLES.
    """

def format_prompt_patches(patches: list[PromptPatch]) -> str:
    """Format as '## Quality Focus Areas' context block."""
```

### Modified Files

#### `app/core/config.py` — `BlueprintConfig`

```python
judge_aggregation_enabled: bool = False
```

#### `app/ai/blueprints/engine.py`

**Persist verdicts** — After inline judge section (~line 395), when `verdict is not None`:
```python
if settings.blueprint.judge_aggregation_enabled:
    from app.ai.blueprints.judge_aggregator import persist_judge_verdict
    try:
        await persist_judge_verdict(verdict, self._project_id, run.run_id)
    except Exception:
        logger.debug("blueprint.judge_verdict_persist_failed", ...)
```

**Inject patches** — In `_build_node_context()`, new context layer:
```python
# Judge-derived prompt patches (agentic + aggregation enabled)
if (node.node_type == "agentic"
    and settings.blueprint.judge_aggregation_enabled):
    from app.ai.blueprints.judge_aggregator import aggregate_verdicts, format_prompt_patches
    patches = await aggregate_verdicts(agent_name, self._project_id)
    if patches:
        context.metadata["prompt_patches"] = format_prompt_patches(patches)
```

### Tests

**`app/ai/blueprints/tests/test_judge_aggregator.py`** (~90 lines):
- `test_persist_judge_verdict`: Verify memory entries created per criterion
- `test_aggregate_identifies_failing_criteria`: Mixed pass/fail → patches for <70%
- `test_aggregate_ignores_small_samples`: <5 samples → no patches
- `test_aggregate_no_verdicts`: Empty memory → empty list
- `test_format_prompt_patches_output`

---

## Feature 4: Confidence Calibration

### Purpose

Track whether confidence scores correlate with actual QA outcomes. Apply per-agent calibration discounts to the `CONFIDENCE_REVIEW_THRESHOLD`.

### Design Decision

No new DB table. Derives calibration from existing handoff memory + outcome data already stored. Calibration computed once at engine init, cached for the run.

### New Files

#### `app/ai/confidence_calibration.py` (~80 lines)

```python
DEFAULT_DISCOUNT = 1.0
MIN_CALIBRATION_SAMPLES = 10

@dataclass
class CalibrationResult:
    agent_name: str
    discount: float              # multiply confidence by this (0.5 = halve it)
    sample_count: int
    effective_threshold: float   # adjusted CONFIDENCE_REVIEW_THRESHOLD

async def compute_calibration(
    agent_name: str,
    project_id: int | None,
    db: AsyncSession,
) -> CalibrationResult:
    """Compute confidence calibration from handoff + outcome memory.

    Query memory entries where source="blueprint_handoff" for this agent.
    Extract confidence from metadata_json.
    Cross-reference run_id with outcome memories (source="blueprint_outcome")
    to determine actual pass/fail.

    Calibration: if agent reports avg 0.8 confidence but only passes 50%,
    discount = 0.50 / 0.80 = 0.625.
    effective_threshold = 0.5 / discount = 0.8 (needs higher raw confidence).
    """

def apply_calibration(raw_confidence: float, calibration: CalibrationResult) -> float:
    return raw_confidence * calibration.discount
```

### Modified Files

#### `app/core/config.py` — `BlueprintConfig`

```python
confidence_calibration_enabled: bool = False
```

#### `app/ai/blueprints/service.py` — `_build_engine()`

Pre-compute calibrations for known agents:
```python
confidence_calibrations = None
if settings.blueprint.confidence_calibration_enabled and db is not None:
    from app.ai.confidence_calibration import compute_calibration
    calibrations = {}
    for agent in AGENT_NAMES:
        try:
            cal = await compute_calibration(agent, project_id, db)
            if cal.sample_count >= MIN_CALIBRATION_SAMPLES:
                calibrations[f"{agent}_node"] = cal
        except Exception:
            pass
    if calibrations:
        confidence_calibrations = calibrations
```
Pass to `BlueprintEngine(confidence_calibrations=confidence_calibrations)`.

#### `app/ai/blueprints/engine.py`

**`__init__()` (line 126):** Accept `confidence_calibrations` dict, store as `self._confidence_calibrations`.

**`_execute_from()` (line ~470):** Replace static threshold:
```python
effective_threshold = CONFIDENCE_REVIEW_THRESHOLD
if self._confidence_calibrations is not None:
    node_key = current_node_name
    cal = self._confidence_calibrations.get(node_key)
    if cal is not None:
        effective_threshold = cal.effective_threshold

if result.handoff.confidence < effective_threshold:
    run.status = "needs_review"
    ...
```

### Tests

**`app/ai/tests/test_confidence_calibration.py`** (~70 lines):
- `test_compute_calibration_no_data`: Returns default discount=1.0
- `test_compute_calibration_overconfident_agent`: discount < 1.0, threshold raised
- `test_apply_calibration`: Verify multiplication
- `test_engine_uses_calibrated_threshold`: Mock calibration, verify adjusted threshold

---

## Implementation Sequence

| Phase | Feature | Files Created | Files Modified | New DB Table |
|-------|---------|--------------|----------------|-------------|
| 1 | Failure-Outcome Ledger | `recovery_outcomes.py`, migration, tests | `config.py`, `service.py`, `engine.py`, `recovery_router_node.py` | Yes |
| 2 | Correction Few-Shot | `correction_examples.py`, tests | `config.py`, `engine.py` | No |
| 3 | Judge Aggregation | `judge_aggregator.py`, tests | `config.py`, `engine.py` | No |
| 4 | Confidence Calibration | `confidence_calibration.py`, tests | `config.py`, `service.py`, `engine.py` | No |

## Verification

For each feature:
1. `pytest app/ai/tests/test_<feature>.py -v` — unit tests pass
2. `make check` — lint, types, full test suite
3. Feature flag off → zero behavior change (backward compatible)
4. Feature flag on → new behavior with fire-and-forget safety (no failures propagate)

Integration test flow for Feature 1:
1. Run blueprint with `recovery_ledger_enabled=True`
2. Force QA failures that trigger recovery routing
3. Verify `recovery_outcomes` table populated
4. Run again with same failure shape
5. Verify router queries ledger before static map
