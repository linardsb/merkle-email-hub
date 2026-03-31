# Plan: Phase 48 — Converter Learning Loop

## Context

The design-sync converter produces rich structured metadata on every conversion — quality warnings, component match confidences, compatibility hints, design tokens used — but **all of it vanishes** after the HTTP response. The agent learning infrastructure (memory service, insight bus, failure patterns, judge pipeline) is mature but the converter isn't wired into it.

**Result:** Agents can't learn from past conversion quality issues. The Scaffolder can't recall "last time we converted a hero-with-image section, the component match confidence was 0.4 — consider a different template." Quality regressions in the converter go undetected unless they cascade into QA gate failures.

**Goal:** Close the converter → agent learning loop by persisting conversion metadata into existing infrastructure (memory, insights, traces) so agents improve over time from real conversion data.

## Research Summary

**Hook point:** `app/design_sync/import_service.py:250+` — `DesignImportService.run_conversion()` completes here (after `initial_html = conversion.html`). Fire-and-forget via `asyncio.create_task()` with `_on_task_done()` callback (same pattern at `service.py:1469-1478`).

**Memory API:** `MemoryService.store(MemoryCreate) → MemoryEntry`. Schema: `agent_type` (max 50), `memory_type` ("semantic"|"procedural"|"episodic"), `content` (1-4000 chars), `project_id`, `metadata` (dict), `is_evergreen` (bool). Recall: `recall(query, project_id=, agent_type=, memory_type=, limit=)` → `list[tuple[MemoryEntry, float]]`.

**Insight bus API:** `InsightCategory = Literal["color", "layout", "typography", "dark_mode", "accessibility", "mso"]` at `insight_bus.py:42`. `AgentInsight` dataclass. `persist_insights(insights, project_id) → int`. `recall_insights(agent_name, client_ids, project_id, limit) → list[AgentInsight]`. `format_insight_context(insights) → str` (max 800 chars).

**Config:** `DesignSyncConfig` at `config.py:322-359` — has `converter_enabled`, `ai_layout_enabled`, `section_cache_enabled`. Add new fields here.

**ConversionResult fields:** `html`, `sections_count`, `warnings`, `layout`, `compatibility_hints`, `images`, `cache_hit_rate`, `quality_warnings: list[QualityWarning]`, `match_confidences: dict[int, float]`, `figma_url`, `node_id`, `design_tokens_used: dict[str, Any] | None`.

## Test Landscape

**Existing factories:** `make_entry()` (memory), `_make_insight()` (insight bus), `make_design_node()` (design_sync conftest). **Fire-and-forget test pattern:** patch `asyncio.create_task` to prevent execution, test flow separately with `@pytest.mark.asyncio`. **Memory mock pattern:** `AsyncMock` for `MemoryService`, patch `get_db_context` + `get_embedding_provider` + `MemoryService`. **Insight mock pattern:** `_make_insight(**overrides)` factory, verify `store.call_args_list`. **Trace pattern:** JSONL with ISO timestamps (see `correction_tracker.py`).

## Type Check Baseline

| Directory | Pyright errors | Mypy errors |
|-----------|---------------|-------------|
| `app/design_sync/` | 228 | 0 |
| `app/memory/` | 0 | — |
| `app/ai/blueprints/insight_bus.py` | 0 | — |
| `app/ai/agents/knowledge/` | 0 | — |
| `app/ai/agents/scaffolder/` | 12 | — |
| **Total** | **240** | **0** |

## Dependencies

- Memory service operational (`app/memory/service.py`) ✅
- Insight bus operational (`app/ai/blueprints/insight_bus.py`) ✅
- Quality contracts (`app/design_sync/quality_contracts.py`) ✅
- Diagnostic pipeline (`app/design_sync/diagnose/`) ✅
- No dependency on Phases 40–47 (converter learning is orthogonal to VLM/visual verification)

## Files to Modify

| File | Change | Subtask |
|------|--------|---------|
| `app/design_sync/converter_memory.py` | **New** — Persistence functions for conversion quality | 48.1 |
| `app/design_sync/import_service.py` | Hook persistence calls after `run_conversion()` completes (~line 250) | 48.1 |
| `app/design_sync/converter_service.py` | No changes — read-only reference (ConversionResult source) | — |
| `app/design_sync/quality_contracts.py` | No changes — read-only reference (QualityWarning source) | — |
| `app/design_sync/converter_insights.py` | **New** — Low-confidence → insight extraction | 48.2 |
| `app/ai/blueprints/insight_bus.py` | Add `"conversion"` to `InsightCategory` literal | 48.2 |
| `app/design_sync/converter_traces.py` | **New** — JSONL trace writer for conversions | 48.3 |
| `app/design_sync/converter_regression.py` | **New** — Regression detection on conversion quality | 48.3 |
| `app/ai/agents/knowledge/service.py` | Add conversion history search capability via `search_conversion_memory()` | 48.4 |
| `app/ai/agents/scaffolder/pipeline.py` | Recall conversion memory during template selection | 48.5 |
| `Makefile` | Add `make converter-regression` target | 48.3 |
| `app/design_sync/tests/test_converter_memory.py` | **New** — Tests for 48.1 | 48.1 |
| `app/design_sync/tests/test_converter_insights.py` | **New** — Tests for 48.2 | 48.2 |
| `app/design_sync/tests/test_converter_traces.py` | **New** — Tests for 48.3 | 48.3 |
| `app/design_sync/tests/test_converter_regression.py` | **New** — Tests for 48.3 | 48.3 |
| `app/ai/agents/knowledge/tests/test_conversion_memory_search.py` | **New** — Tests for 48.4 | 48.4 |
| `app/ai/agents/scaffolder/tests/test_conversion_recall.py` | **New** — Tests for 48.5 | 48.5 |

---

## 48.1 — Converter Quality Persistence to Memory

**Goal:** After each conversion, persist `QualityWarning` list and `match_confidences` as semantic memory entries so agents can recall past conversion issues for similar designs.

### Data model

Each conversion produces one memory entry (not one per warning — avoids flooding):

```
agent_type: "design_sync"
memory_type: "semantic"
source: "converter"
content: structured summary (see format below)
metadata: {
    "source": "converter_quality",
    "connection_id": <str|null>,
    "figma_url": <str|null>,
    "node_id": <str|null>,
    "sections_count": <int>,
    "warning_count": <int>,
    "warning_categories": ["contrast", "completeness", ...],
    "avg_match_confidence": <float>,
    "low_confidence_sections": [<int>, ...],   # section indices with confidence < 0.6
    "has_quality_issues": <bool>,
}
is_evergreen: False
```

### Content format

```
Conversion quality report (sections={N}, warnings={M}):
{for each warning category, one line:}
- {category} ({severity}): {message}
{if low-confidence sections:}
Low-confidence matches: sections {indices} (avg {score:.2f})
{if design_tokens_used:}
Design tokens: {primary_colors}, {font_families}
Source: {figma_url or "unknown"}
```

Capped at 4000 chars (MemoryCreate.content max_length).

### Implementation steps

1. **Create `app/design_sync/converter_memory.py`:**
   - `format_conversion_quality(result: ConversionResult, connection_id: str | None) -> str` — Format content string from ConversionResult fields
   - `build_conversion_metadata(result: ConversionResult, connection_id: str | None) -> dict[str, Any]` — Build metadata dict
   - `async persist_conversion_quality(result: ConversionResult, connection_id: str | None, project_id: int | None) -> None` — Fire-and-forget persistence (same pattern as `outcome_logger.py:117`)
   - **Skip persistence when:** `len(result.quality_warnings) == 0 and all(c >= 0.8 for c in result.match_confidences.values())` — Don't store clean conversions (noise reduction)
   - Error handling: `try/except Exception` with `logger.warning("converter_memory.persist_failed", ...)` — never crash the conversion pipeline

2. **Hook in `app/design_sync/import_service.py`:**
   - In `run_conversion()` (~line 250, after `initial_html = conversion.html`), call `persist_conversion_quality()` as fire-and-forget
   - Use `asyncio.create_task()` with try/except (same pattern as `service.py:1469-1478` `_on_task_done` callback)
   - Pass `connection_id` from the DesignConnection, `project_id` from the connection's project

3. **Config gate:**
   - Add `conversion_memory_enabled: bool = True` to `DesignSyncConfig` in `app/core/config.py:322-359`
   - Env var: `DESIGN_SYNC__CONVERSION_MEMORY_ENABLED`
   - Check in `persist_conversion_quality()` before storing

### Tests (8 tests)

| Test | What it validates |
|------|-------------------|
| `test_format_conversion_quality_with_warnings` | Content string includes all warning categories, respects 4000 char limit |
| `test_format_conversion_quality_clean` | Returns None/empty when no issues |
| `test_build_conversion_metadata` | Metadata dict has all required keys, correct types |
| `test_persist_skips_clean_conversion` | No memory.store() call when no warnings + high confidence |
| `test_persist_stores_quality_issues` | memory.store() called with correct MemoryCreate fields |
| `test_persist_fire_and_forget` | Exception in memory.store() doesn't propagate |
| `test_persist_respects_config_gate` | Skips when `CONVERSION_MEMORY_ENABLED=False` |
| `test_content_truncation` | Content stays under 4000 chars with many warnings |

---

## 48.2 — Low-Confidence Matches → Insight Bus

**Goal:** When the converter produces low-confidence component matches (`< 0.6`), generate `AgentInsight` entries targeting the Scaffolder so it can adjust template selection strategy for similar designs.

### Design decisions

- **Threshold:** `_LOW_MATCH_CONFIDENCE = 0.6` (aligns with insight bus's existing `_LOW_CONFIDENCE_THRESHOLD = 0.7` but slightly lower for converter — component matching is inherently noisier)
- **Category:** Add `"conversion"` to `InsightCategory` literal in `insight_bus.py`
- **Source agent:** `"design_sync"` (converter is the source)
- **Target agents:** `("scaffolder",)` (Scaffolder picks templates; converter confidence helps it)
- **Dedup:** Use `_compute_dedup_hash()` from insight_bus (hash on source+target+category+insight text)

### Implementation steps

1. **Add `"conversion"` to `InsightCategory`** in `app/ai/blueprints/insight_bus.py:42`:
   - Current: `InsightCategory = Literal["color", "layout", "typography", "dark_mode", "accessibility", "mso"]`
   - New: add `"conversion"` to the literal

2. **Create `app/design_sync/converter_insights.py`:**
   - `extract_conversion_insights(result: ConversionResult, connection_id: str | None) -> list[AgentInsight]` — Scan `match_confidences` for entries below threshold; build one insight per low-confidence section grouping
   - **Insight text format:** `"Section {idx} ({classified_type}) matched to '{component_name}' with {confidence:.0%} confidence. Consider alternative templates for this layout pattern."`
   - Group nearby low-confidence sections into a single insight when they share the same classified type (avoid insight flooding)
   - `async persist_conversion_insights(result: ConversionResult, connection_id: str | None, project_id: int | None) -> int` — Call `persist_insights()` from insight_bus, return count stored

3. **Hook in `app/design_sync/import_service.py`:**
   - Call `persist_conversion_insights()` alongside `persist_conversion_quality()` in `run_conversion()` (~line 250, same fire-and-forget pattern)

4. **Config gate:**
   - Reuse `DESIGN_SYNC__CONVERSION_MEMORY_ENABLED` — insights are part of the same learning loop

### Tests (6 tests)

| Test | What it validates |
|------|-------------------|
| `test_extract_no_insights_high_confidence` | Empty list when all confidences ≥ 0.6 |
| `test_extract_single_low_confidence` | One insight generated for one low section |
| `test_extract_groups_same_type` | Adjacent same-type low sections → single insight |
| `test_insight_targets_scaffolder` | `target_agents == ("scaffolder",)` |
| `test_insight_category_is_conversion` | `category == "conversion"` |
| `test_persist_fire_and_forget` | Exception doesn't propagate |

---

## 48.3 — Converter Traces JSONL + Regression Detection

**Goal:** Write per-conversion traces to `traces/converter_traces.jsonl` with structured quality data. Build regression detection that compares conversion quality metrics against a baseline, matching the pattern in `app/ai/agents/evals/regression.py`.

### Trace schema

```jsonl
{
  "trace_id": "conv-{connection_id}-{uuid8}",
  "timestamp": "2026-03-31T12:00:00Z",
  "connection_id": "42",
  "figma_url": "https://figma.com/...",
  "node_id": "2833:1623",
  "sections_count": 9,
  "warnings": [
    {"category": "contrast", "severity": "warning", "message": "..."}
  ],
  "match_confidences": {"0": 0.95, "1": 0.72, "3": 0.41},
  "avg_confidence": 0.69,
  "min_confidence": 0.41,
  "quality_score": 0.78,
  "compatibility_hint_count": 2,
  "cache_hit_rate": 0.85,
  "design_tokens_used": {"primary_color": "#1a1a1a", "font_family": "Arial"}
}
```

**`quality_score`** = weighted combination:
- `avg_confidence * 0.5` (component matching quality)
- `(1 - warning_ratio) * 0.3` where `warning_ratio = min(warning_count / sections_count, 1.0)`
- `(1 - error_ratio) * 0.2` where `error_ratio` = proportion of severity="error" warnings

### Implementation steps

1. **Create `app/design_sync/converter_traces.py`:**
   - `build_trace(result: ConversionResult, connection_id: str | None) -> dict[str, Any]` — Build trace dict from ConversionResult
   - `compute_quality_score(result: ConversionResult) -> float` — Weighted score computation
   - `append_trace(trace: dict[str, Any], path: Path | None = None) -> None` — Append JSONL line to `traces/converter_traces.jsonl` (sync file I/O, same pattern as eval trace writers)
   - `async persist_converter_trace(result: ConversionResult, connection_id: str | None) -> None` — Build + append, fire-and-forget

2. **Create `app/design_sync/converter_regression.py`:**
   - `load_traces(path: Path | None = None, last_n: int = 100) -> list[dict]` — Load recent traces
   - `compute_aggregate_metrics(traces: list[dict]) -> dict[str, float]` — Aggregate: `avg_quality_score`, `avg_confidence`, `warning_rate`, `error_rate`, `low_confidence_section_rate`
   - `load_baseline(path: Path | None = None) -> dict[str, float] | None` — Load `traces/converter_baseline.json`
   - `save_baseline(metrics: dict[str, float], path: Path | None = None) -> None` — Save current as baseline
   - `detect_regressions(current: dict[str, float], baseline: dict[str, float], tolerance: float = 0.05) -> list[str]` — Return list of regressed metric names (drop > tolerance)
   - `run_converter_regression(update_baseline: bool = False) -> tuple[bool, str]` — CLI entry point, returns (passed, report_text)

3. **Add Makefile target:**
   ```makefile
   converter-regression:
   	python -m app.design_sync.converter_regression
   ```

4. **Hook in `app/design_sync/import_service.py`:**
   - Call `persist_converter_trace()` alongside the other persistence calls in `run_conversion()` (~line 250)

5. **Config:**
   - `DESIGN_SYNC__CONVERSION_TRACES_ENABLED` (default: `True`)
   - Trace file path configurable via `DESIGN_SYNC__CONVERSION_TRACES_PATH` (default: `traces/converter_traces.jsonl`)

### Tests (10 tests)

| Test | What it validates |
|------|-------------------|
| `test_build_trace_complete` | All fields present, correct types |
| `test_build_trace_minimal` | Works with empty warnings/confidences |
| `test_quality_score_perfect` | 1.0 when no warnings + all confidences 1.0 |
| `test_quality_score_degraded` | Lower score with warnings + low confidence |
| `test_append_trace_creates_file` | Creates JSONL file if not exists |
| `test_append_trace_appends` | Appends without overwriting |
| `test_aggregate_metrics` | Correct averages over multiple traces |
| `test_detect_regressions_none` | Empty list when within tolerance |
| `test_detect_regressions_found` | Detects quality_score drop > 5% |
| `test_regression_baseline_round_trip` | Save → load → compare works |

---

## 48.4 — Knowledge Agent Access to Conversion History

**Goal:** Let the Knowledge agent answer questions like "what are the most common conversion failures?" or "which component types have low match confidence?" by querying the memory table.

### Design decisions

- **Don't modify KnowledgeService.search()** — it's document-oriented (chunks, embeddings, reranking). Memory is a different storage.
- **Instead:** Add a `search_conversion_memory()` method to the Knowledge agent service (`app/ai/agents/knowledge/service.py`) that directly queries `MemoryService.recall()` filtered by `agent_type="design_sync"`.
- **Agent routing:** When the Knowledge agent detects a conversion-related query (keywords: "conversion", "converter", "design sync", "component match", "quality warning"), it also queries conversion memory alongside document search.

### Implementation steps

1. **Add `search_conversion_memory()` to Knowledge agent** (`app/ai/agents/knowledge/service.py`):
   - `async search_conversion_memory(query: str, project_id: int | None, limit: int = 5) -> list[str]` — Recall from memory with `agent_type="design_sync"`, format results as context strings
   - Return format: list of formatted memory content strings with timestamps

2. **Integrate into agent's main `process()` method:**
   - After the main knowledge search, check if query contains conversion-related keywords
   - If yes, also call `search_conversion_memory()` and append results to context
   - Mark these as `[Source: Conversion Memory]` in citations

3. **Add conversion keyword detection:**
   - `_is_conversion_query(query: str) -> bool` — Simple keyword check: `{"conversion", "converter", "design sync", "design-sync", "component match", "quality warning", "match confidence", "figma convert"}`

### Tests (5 tests)

| Test | What it validates |
|------|-------------------|
| `test_is_conversion_query_positive` | Detects "why did the conversion fail?" |
| `test_is_conversion_query_negative` | Doesn't trigger on "what is dark mode?" |
| `test_search_conversion_memory_returns_formatted` | Results include timestamps and content |
| `test_search_conversion_memory_empty` | Returns empty list when no memories |
| `test_process_includes_conversion_context` | Conversion memory appended to context for relevant queries |

---

## 48.5 — Scaffolder Recall of Conversion Memory

**Goal:** During template selection, the Scaffolder recalls past conversion quality data for similar designs and uses it to bias template selection toward higher-fidelity matches.

### Design decisions

- **When to recall:** In the Scaffolder's `_layout_pass()` (`pipeline.py:291`), before the LLM picks a template
- **What to recall:** Conversion memories with low confidence or quality warnings, filtered by project
- **How to use:** Inject as additional context in the template selection prompt: "Previous conversions of similar designs had issues with {component_type} — prefer templates with explicit {slot_type} slots"
- **Recall limit:** 3 memories max (avoid prompt bloat)

### Implementation steps

1. **Add `recall_conversion_context()` to Scaffolder pipeline** (`app/ai/agents/scaffolder/pipeline.py`):
   - `async recall_conversion_context(brief: str, project_id: int | None) -> str | None` — Query memory with brief text, filtered to `agent_type="design_sync"`, return formatted context or None if no relevant memories
   - Format: `"## Conversion History Insights\n{formatted memories}"`

2. **Inject into `_layout_pass()` (`pipeline.py:291`):**
   - After building template list (~line 299) and section list (~line 306), before LLM prompt construction (~line 308)
   - Call `recall_conversion_context(brief, project_id)` and prepend result to system prompt if not None
   - Gate behind `DESIGN_SYNC__CONVERSION_MEMORY_ENABLED` (reuse from 48.1)

3. **Recall filtering:**
   - Only recall memories where `metadata.has_quality_issues == True` (skip clean conversions)
   - Sort by recency (most recent first)
   - Limit to 3 entries

### Tests (5 tests)

| Test | What it validates |
|------|-------------------|
| `test_recall_conversion_context_with_memories` | Returns formatted context string |
| `test_recall_conversion_context_empty` | Returns None when no memories match |
| `test_recall_filters_clean_conversions` | Skips memories without quality issues |
| `test_template_selection_includes_context` | Context injected into selection prompt |
| `test_recall_respects_config_gate` | Skips when disabled |

---

## Implementation Order & Effort

| Subtask | Depends on | Effort | Priority |
|---------|-----------|--------|----------|
| **48.1** Converter quality → memory | None | Small (1-2h) | P0 — foundational |
| **48.2** Low-confidence → insight bus | 48.1 | Small (1h) | P1 — amplifies 48.1 |
| **48.3** Converter traces + regression | None | Medium (2-3h) | P1 — observability |
| **48.4** Knowledge agent access | 48.1 | Small (1h) | P2 — query capability |
| **48.5** Scaffolder recall | 48.1 | Small (1h) | P2 — closes the loop |

**Recommended order:** 48.1 → 48.3 → 48.2 → 48.5 → 48.4

48.1 and 48.3 are independent and can be done in parallel. 48.2 and 48.5 both depend on 48.1. 48.4 depends on 48.1 having data in memory to query.

## Config Summary

| Setting | Default | Subtask |
|---------|---------|---------|
| `DESIGN_SYNC__CONVERSION_MEMORY_ENABLED` | `True` | 48.1, 48.2, 48.5 |
| `DESIGN_SYNC__CONVERSION_TRACES_ENABLED` | `True` | 48.3 |
| `DESIGN_SYNC__CONVERSION_TRACES_PATH` | `traces/converter_traces.jsonl` | 48.3 |
| `DESIGN_SYNC__LOW_MATCH_CONFIDENCE_THRESHOLD` | `0.6` | 48.2 |

## Risk Assessment

- **Low risk:** All persistence is fire-and-forget; converter pipeline performance unaffected
- **Low risk:** Memory entries have `is_evergreen=False` so compaction manages growth
- **Medium risk:** Insight flooding if converter runs frequently on same design — mitigated by dedup hash in insight bus and skip-clean-conversion filter in 48.1
- **Low risk:** No schema migrations needed — uses existing `memory_entries` table and JSONL files

## Preflight Warnings

- `app/design_sync/` has 228 pre-existing pyright errors — don't chase those, just ensure new code is clean
- `app/ai/agents/scaffolder/` has 12 pre-existing pyright errors (slowapi decorator types in `variant_routes.py`)
- Memory mock pattern requires patching 3 things: `get_db_context`, `get_embedding_provider`, `MemoryService` — see `test_insight_bus.py` for the canonical pattern
- `MemoryCreate.content` has a 4000 char max — all content formatters must enforce this

## Security Checklist

- No new endpoints exposed (all persistence is internal fire-and-forget)
- No user input flows directly into `content` or `metadata` — data comes from `ConversionResult` (internal)
- JSONL traces written to `traces/` dir — ensure no PII in trace data (figma URLs are acceptable, user emails are not)
- Config gates default to `True` but can be disabled — no secrets in config values

## Verification

- [ ] `make test` passes with new test files
- [ ] `make types` passes (all new functions fully typed)
- [ ] `make lint` passes
- [ ] Pyright errors ≤ baseline (240 errors before)
- [ ] Manual: run a Figma conversion with known quality issues → verify memory entry created → verify Scaffolder recalls it on next run
