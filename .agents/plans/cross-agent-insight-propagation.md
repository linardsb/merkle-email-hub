# Plan: Phase 32.5 — Cross-Agent Insight Propagation

## Context
Agent learning is siloed. Dark Mode stores failures tagged `agent_type="dark_mode"`, Scaffolder queries `agent_type="scaffolder"` — they never see each other's learnings. The Scaffolder keeps generating patterns the Dark Mode agent keeps fixing, run after run. This phase builds an **InsightBus** that extracts learnings from completed runs and routes them to the agents that need them.

## Research Summary

### Existing Infrastructure (already built)
| Component | File | What it does |
|-----------|------|-------------|
| **LAYER 9** | `engine.py:707-727` | Injects `failure_patterns` into `NodeContext.metadata` for agentic nodes |
| **FailurePattern** | `failure_patterns.py:37-47` | Dataclass: `agent_name`, `qa_check`, `client_ids`, `description`, `workaround`, `confidence` |
| **extract_failure_patterns** | `failure_patterns.py:82-154` | Parses `BlueprintRun` → `list[FailurePattern]` using `_QA_CHECK_AGENT_MAP` |
| **persist_failure_patterns** | `failure_patterns.py:184-253` | Stores as `memory_type="semantic"`, `source="failure_pattern"` |
| **recall_failure_patterns** | `failure_patterns.py:335-401` | Queries memory by `agent_type` + `project_id`, returns formatted context |
| **outcome_logger** | `outcome_logger.py:177-213` | Post-run hook: calls `extract_failure_patterns` → `persist_failure_patterns` |
| **handoff_memory** | `handoff_memory.py:44-86` | Stores each handoff as `memory_type="episodic"` |
| **LAYER 16** | `engine.py:744-768` | Judge aggregation → `prompt_patches` injection |
| **LAYER 15** | `engine.py:710-742` | Correction examples → few-shot injection |

### Key Insight: Failure Patterns ≠ Cross-Agent Insights
`failure_patterns.py` stores patterns scoped to the *fixer* agent (`agent_type=fixer_agent_name`). The gap: insights are never routed to the *root cause* agent. A Dark Mode fix for Samsung → stored under `agent_type="dark_mode"` → Scaffolder never sees it.

### Core Data Structures

**BlueprintRun** (`protocols.py` / `engine.py`):
- `_handoff_history: list[AgentHandoff]` — full chain of agent outputs
- `qa_failure_details: list[StructuredFailure]` — current failures
- `iteration_counts: dict[str, int]` — retry counts per node
- `status`, `qa_passed`, `qa_failures`

**AgentHandoff** (`protocols.py:94-129`):
- `agent_name`, `artifact`, `decisions`, `warnings`, `confidence`, `uncertainties`
- `typed_payload` — agent-specific structured output
- `compact()` / `summary()` for context economy

**NodeContext** (`protocols.py:47-69`):
- `metadata: dict[str, object]` — extensible context bag
- Existing keys: `upstream_handoff`, `handoff_history`, `failure_patterns`, `audience_client_ids`, `prompt_patches`, `correction_examples`

**MemoryService** (`memory/service.py`):
- `store(MemoryCreate)` → `MemoryEntry`
- `recall(query, *, project_id, agent_type, memory_type, limit)` → `list[tuple[MemoryEntry, float]]`
- `MemoryCreate`: `agent_type`, `memory_type` (procedural|episodic|semantic), `content` (max 4000), `project_id`, `metadata`, `is_evergreen`

**StructuredFailure** (`protocols.py:133-154`):
- `qa_check`, `details`, `severity`, `client_ids`

### Audience Client ID Flow
`engine.py:695` → `context.metadata["audience_client_ids"] = tuple(self._audience_profile.client_ids)` — available to all agentic nodes.

### Memory Persistence Pattern
```python
async with get_db_context() as db:
    svc = MemoryService(db, get_embedding_provider(get_settings()))
    await svc.store(MemoryCreate(agent_type=..., memory_type="semantic", content=..., project_id=..., metadata={...}))
```

### `_QA_CHECK_AGENT_MAP` (`failure_patterns.py`)
Maps QA check → responsible agent: `dark_mode→dark_mode`, `fallback→outlook_fixer`, `accessibility→accessibility`, `css_support→scaffolder`, etc. Reusable for root-cause attribution.

## Test Landscape

### Existing Test Files (directly relevant)
| File | Tests | Key patterns |
|------|-------|-------------|
| `blueprints/tests/test_failure_patterns.py` | Extract/persist/recall | `_make_run()`, `_make_audience()`, MemoryService mocking |
| `blueprints/tests/test_outcome_logger.py` | Post-run persistence | `_make_run()`, format+store pattern |
| `blueprints/tests/test_handoff.py` | Handoff propagation (9 tests) | `StubAgenticNode`, `StubDeterministicNode`, `BlueprintDefinition` |
| `blueprints/tests/test_judge_aggregator.py` | LAYER 16 injection | MemoryService recall mocking |
| `memory/tests/test_service.py` | Store/recall/decay | `make_entry()` factory |
| `memory/tests/test_repository.py` | Similarity search | `make_entry()` factory |

### Mock Patterns (proven)
```python
# MemoryService mock (from test_outcome_logger.py)
mock_memory_svc = AsyncMock()
mock_memory_svc.store = AsyncMock()
mock_memory_svc.recall = AsyncMock(return_value=results)
with (
    patch("app.core.database.get_db_context") as mock_db_ctx,
    patch("app.knowledge.embedding.get_embedding_provider"),
    patch("app.memory.service.MemoryService", return_value=mock_memory_svc),
):
    mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
```

### Fixtures Available
- `sample_html_valid` / `sample_html_minimal` (conftest)
- `mock_provider` (LLM AsyncMock)
- `_make_run()` — configurable BlueprintRun factory
- `make_entry()` — MemoryEntry factory
- `StubAgenticNode` / `StubDeterministicNode` — pipeline stubs

## Type Check Baseline

| Directory | Pyright errors | Mypy local errors |
|-----------|---------------|-------------------|
| `app/ai/blueprints/` | 18 (all in tests, typing edge cases) | 2 (`recovery_router_node.py`, `visual_qa_node.py`) |
| `app/memory/` | 0 | 0 |

New code must not increase these counts.

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `app/ai/blueprints/insight_bus.py` | `AgentInsight` dataclass + module-level extract/persist/recall/format functions |
| `app/ai/blueprints/tests/test_insight_bus.py` | Unit tests for InsightBus |

### Modified Files
| File | Change |
|------|--------|
| `app/ai/blueprints/protocols.py` | Add `learnings: tuple[str, ...] = ()` to `AgentHandoff`; add `insights_extracted: int = 0` to `BlueprintRun` |
| `app/ai/blueprints/engine.py` | Add LAYER 17 (cross-agent insight injection) + post-run insight extraction hook |
| `app/ai/blueprints/outcome_logger.py` | Call `extract_and_store_insights()` in post-run flow |
| `app/core/config.py` | Add `insight_propagation_enabled: bool = True` to `BlueprintConfig` |

## Implementation Steps

### Step 1: Add `learnings` to `AgentHandoff` (`protocols.py`)

Add field to `AgentHandoff` dataclass:
```
learnings: tuple[str, ...] = ()  # What the agent learned during this execution
```
Update `compact()` to preserve `learnings` (small strings, don't strip).
Update `summary()` to append learnings count if non-empty.

### Step 2: Add `insights_extracted` to `BlueprintRun` (`protocols.py` or `engine.py`)

Add to `BlueprintRun.__init__`:
```
self.insights_extracted: int = 0
```

### Step 3: Add `insight_propagation_enabled` setting (`config.py`)

In `BlueprintConfig` (`config.py:413`):
```
insight_propagation_enabled: bool = False  # Cross-agent insight propagation
```

### Step 4: Create `insight_bus.py`

**`InsightCategory`** Literal type + **`AgentInsight`** dataclass:
```python
from typing import Literal
from datetime import datetime

InsightCategory = Literal["color", "layout", "typography", "dark_mode", "accessibility", "mso"]

@dataclass(frozen=True)
class AgentInsight:
    source_agent: str                # "dark_mode"
    target_agents: tuple[str, ...]   # ("scaffolder", "code_reviewer")
    client_ids: tuple[str, ...]      # ("samsung_mail",)
    insight: str                     # "Avoid #1a1a1a backgrounds — Samsung double-inverts"
    category: InsightCategory        # Literal type — compile-time safe
    confidence: float                # 0.0–1.0
    evidence_count: int              # 3
    first_seen: datetime             # UTC timestamp (serialize to ISO only at MemoryCreate boundary)
    last_seen: datetime              # UTC timestamp
```

All functions are module-level async (no class, matches `failure_patterns.py` pattern):

`extract_insights(run: BlueprintRun, blueprint_name: str, audience_profile: AudienceProfile | None) -> list[AgentInsight]`:
- Walk `run._handoff_history` — for each handoff with `learnings`, create insight targeting upstream agents
- Walk `run.qa_failure_details` — for each failure fixed (present in `previous_qa_failure_details` but absent in final `qa_failure_details`):
  - Use `_QA_CHECK_AGENT_MAP` to find root-cause agent
  - Use handoff chain to find fixer agent
  - Create insight: source=fixer, targets=[root_cause, "code_reviewer"], category from qa_check
- Walk handoffs with `confidence < 0.7` — create advisory insight
- Dedup by hash of `(source_agent, category, sorted(client_ids), insight[:100])`
- Return deduplicated list

`persist_insights(insights: list[AgentInsight], project_id: int | None) -> int`:
- For each insight, for each target_agent (per-item try/except — one failure doesn't block the rest):
  - Store as `MemoryCreate(agent_type=target_agent, memory_type="semantic", content=formatted_insight, metadata={"source": "cross_agent_insight", "source_agent": ..., "client_ids": [...], "category": ..., "evidence_count": ..., "dedup_hash": ...}, is_evergreen=(evidence_count >= 5))`
  - Truncate `content` to 4000 chars if needed (MemoryCreate max)
  - Dedup at recall time via `metadata.dedup_hash` filtering (avoids N+1 recall-before-store)
- Log `"insights.persisted"` with `count`, `project_id`, `run_id` at info level
- Return count of insights stored

`recall_insights(agent_name: str, client_ids: tuple[str, ...] | None, project_id: int | None, limit: int = 5) -> list[AgentInsight]`:
- Query `MemoryService.recall(query=build_query(agent_name, client_ids), agent_type=agent_name, memory_type="semantic", project_id=project_id, limit=limit * 2)` (over-fetch to account for dedup filtering)
- Filter results: `metadata.get("source") == "cross_agent_insight"`
- Deduplicate by `metadata.dedup_hash` — keep highest `evidence_count` entry per hash
- Parse `MemoryEntry` back into `AgentInsight`
- Return top `limit` sorted by `evidence_count * similarity_score` descending

`format_insight_context(insights: list[AgentInsight]) -> str`:
- Format as:
  ```
  --- CROSS-AGENT INSIGHTS ---
  From {source} ({evidence_count}x, {clients}):
    {insight text}
  ```
- Cap at 800 chars total (truncate least-confident insights)

### Step 5: Add LAYER 17 in `engine.py`

After LAYER 16 (judge aggregation), add insight injection block — follows exact pattern of LAYER 9:

```python
# LAYER 17: Cross-agent insights
if (
    node.node_type == "agentic"
    and settings.blueprint.insight_propagation_enabled
    and self._audience_profile is not None
):
    from app.ai.blueprints.insight_bus import recall_insights, format_insight_context
    try:
        audience_client_ids = tuple(self._audience_profile.client_ids)
        insights = await recall_insights(
            agent_name=agent_name,
            client_ids=audience_client_ids,
            project_id=self._project_id,
        )
        if insights:
            context.metadata["cross_agent_insights"] = format_insight_context(insights)
            logger.info("blueprint.insights_injected", agent=agent_name, count=len(insights))
    except Exception:
        logger.debug("blueprint.insight_recall_failed", agent=agent_name)
```

### Step 6: Add post-run hook in `outcome_logger.py`

In `extract_and_store_failure_patterns()` (or as separate function called alongside it):

```python
from app.ai.blueprints.insight_bus import extract_insights, persist_insights

async def extract_and_store_insights(
    run: BlueprintRun,
    blueprint_name: str,
    audience_profile: AudienceProfile | None,
    project_id: int | None,
) -> int:
    insights = extract_insights(run, blueprint_name, audience_profile)
    if not insights:
        return 0
    count = await persist_insights(insights, project_id)
    run.insights_extracted = count
    return count
```

Wire into `log_blueprint_outcome()` or wherever `extract_and_store_failure_patterns` is called from `engine.py`.

### Step 7: Wire handoff `learnings` into context

In `engine.py` `_build_node_context()`, when building `upstream_constraints` from handoff, also include `learnings`:

```python
if run._last_handoff and run._last_handoff.learnings:
    context.metadata["upstream_learnings"] = run._last_handoff.learnings
```

### Step 8: Write tests (`test_insight_bus.py`)

**Test classes:**

`TestExtractInsights`:
- `test_extract_from_qa_fix` — QA failure in `previous_qa_failure_details` but not `qa_failure_details` → insight routed to root-cause agent
- `test_extract_from_handoff_learnings` — handoff with `learnings` → insight created
- `test_extract_low_confidence` — handoff with `confidence < 0.7` → advisory insight
- `test_dedup_same_pattern` — duplicate patterns → merged with incremented `evidence_count`
- `test_no_insights_clean_run` — clean run (no failures, high confidence) → empty list
- `test_category_mapping` — QA check names map to correct categories
- `test_extract_no_audience` — `audience_profile=None` → insights created without `client_ids` (global scope)
- `test_insight_content_truncation` — insight text exceeding 4000 chars → truncated before MemoryCreate

`TestPersistInsights`:
- `test_store_new_insight` — new insight → `MemoryService.store()` called with correct `MemoryCreate`
- `test_evergreen_threshold` — `evidence_count >= 5` → `is_evergreen=True`
- `test_multi_target` — insight targeting 2 agents → stored once per target agent
- `test_persist_error_resilience` — `MemoryService.store` raises on 1st call, succeeds on 2nd → 1 stored, 1 logged error, no crash

`TestRecallInsights`:
- `test_recall_filters_by_source` — only returns entries with `source="cross_agent_insight"` metadata
- `test_recall_with_client_filter` — client_ids influence query construction
- `test_recall_empty` — no matching memories → empty list
- `test_recall_dedup_by_hash` — 2 memories with same `dedup_hash` → only highest `evidence_count` returned

`TestFormatInsightContext`:
- `test_format_single` — single insight → clean formatted block
- `test_format_multiple` — 3 insights → sorted by evidence count
- `test_format_truncation` — > 800 chars → truncated with least confident dropped

`TestInsightInjectionLayer`:
- `test_layer17_injects_insights` — mock `recall_insights` returns data → `context.metadata["cross_agent_insights"]` populated
- `test_layer17_disabled` — `insight_propagation_enabled=False` → no injection
- `test_layer17_no_audience` — no audience profile → skipped
- `test_layer17_error_resilience` — `recall_insights` raises → logged, execution continues

`TestHandoffLearnings`:
- `test_learnings_field_default` — `AgentHandoff()` → `learnings == ()`
- `test_learnings_preserved_in_compact` — `compact()` keeps `learnings`
- `test_learnings_in_context` — handoff with learnings → visible in downstream `metadata["upstream_learnings"]`

## Preflight Warnings

- `_QA_CHECK_AGENT_MAP` in `failure_patterns.py` — hardcoded mapping, may need updating if new QA checks added. Import and reuse, don't duplicate.
- `MemoryCreate.content` max 4000 chars — insight text must be concise.
- `MemoryService.recall()` filters `agent_type` by exact match — cross-agent routing requires storing one memory entry *per target agent* (not comma-joined).
- `AgentHandoff` is `frozen=True` — adding `learnings` field with default `()` is safe for existing code.
- `BlueprintRun` is NOT frozen — adding `insights_extracted: int = 0` in `__init__` is straightforward.

## Security Checklist

- No new endpoints — insight bus is internal to blueprint engine
- No user input flows into insight content — derived from agent execution data
- Memory storage uses existing `MemoryService` with project scoping
- Insight text is descriptive (rendering patterns) — no executable code, no PII
- No new auth/rate-limit concerns (no HTTP surface)

## Verification

- [ ] `make check` passes
- [ ] `make test` passes — including new `test_insight_bus.py`
- [ ] Pyright errors ≤ baseline (18 blueprints, 0 memory)
- [ ] Mypy errors ≤ baseline (2 local in blueprints, 0 in memory)
- [ ] New `AgentHandoff.learnings` field doesn't break existing handoff tests
- [ ] LAYER 17 follows same error-resilience pattern as LAYER 9 (fire-and-forget)
- [ ] Insight dedup hash prevents unbounded memory growth
- [ ] `is_evergreen=True` only set for `evidence_count >= 5`
