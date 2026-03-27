# Plan: Phase 32.7 — Visual QA Feedback Loop Tightening

## Context

Integrate the Visual QA agent into the blueprint recovery loop with: (1) pre-Maizzle visual check stage in QA gate, (2) post-render screenshot comparison against original design, (3) visual defect routing to fixer agents with screenshots via Layer 20 multimodal context, (4) per-client defect reports in QA gate output.

The Visual QA agent already exists (`visual_qa_node.py`, 317 lines) with VLM screenshot analysis, multimodal support, auto-fix, and ontology enrichment. RenderingService already has `render_screenshots()` and `visual_diff()` (ODiff). Layer 20 multimodal context (`NodeContext.multimodal_context`) is already wired. This phase connects these existing pieces into the recovery loop.

## Research Summary

### Key Files & Current State

| File | Lines | Role |
|------|-------|------|
| `app/ai/blueprints/nodes/qa_gate_node.py` | 87 | Runs 11 QA checks, returns `StructuredFailure` list |
| `app/ai/blueprints/nodes/recovery_router_node.py` | 370 | Routes failures to fixer agents via `CHECK_TO_AGENT` dict |
| `app/ai/blueprints/nodes/visual_qa_node.py` | 317 | VLM screenshot analysis, auto-fix, ontology enrichment |
| `app/ai/agents/visual_qa/service.py` | 327 | `VisualQAService` — multimodal VLM pipeline, `parse_decisions()`, `enrich_with_ontology()` |
| `app/ai/agents/visual_qa/schemas.py` | 54 | `VisualQARequest`, `VisualDefect`, `VisualQAResponse` |
| `app/ai/agents/visual_qa/decisions.py` | — | `VisualQADecisions`, `DetectedDefect` |
| `app/ai/blueprints/protocols.py` | 232 | `NodeContext` (has `multimodal_context`), `NodeResult`, `StructuredFailure`, `AgentHandoff` |
| `app/ai/blueprints/engine.py` | 1200+ | Blueprint engine, Layer 14/20 multimodal injection |
| `app/qa_engine/schemas.py` | 390+ | `QACheckResult`, `QAResultResponse` — no `QAGateResult` yet |
| `app/email_engine/schemas.py` | — | `BuildResponse` with `html`, `qa_score`, `rendering_issues` |
| `app/rendering/service.py` | 562 | `RenderingService` — `render_screenshots()`:233, `visual_diff()`:392 |
| `app/rendering/visual_diff.py` | — | `compare_images()`, `DiffResult` |
| `app/rendering/schemas.py` | — | `ScreenshotRequest/Response`, `VisualDiffRequest/Response` |
| `app/core/config.py` | 641 | `BlueprintConfig`:413, `RenderingConfig`:227, `AIConfig`:48 |

### Recovery Router Routing (recovery_router_node.py)

- `CHECK_PRIORITY` dict (lines 25-39): fix order
- `CHECK_TO_AGENT` dict (lines 40-53): maps check → fixer agent
- `AGENT_SCOPES` dict (lines 55-63): modification scope per fixer
- `SCOPE_PROMPTS` dict (lines 65-72): scope constraint prompts
- Cycle detection via `_fingerprint()` (line 114): MD5 of check_name + details

### Existing Visual QA Agent Capabilities

- VLM multimodal pipeline with `ContentBlock` (ImageBlock + TextBlock)
- `_screenshots_to_blocks()` converts base64 PNG dict to ImageBlock list
- `parse_decisions()` → `VisualQADecisions` with `DetectedDefect` list
- `enrich_with_ontology()` cross-references CSS issues
- Auto-fix mode with verification scoring
- `_MAX_SCREENSHOT_B64_LEN = 14_000_000` (10MB limit)

### Multimodal Context Flow (Already Working)

1. Screenshots generated → base64 PNGs
2. `BlueprintEngine._build_node_context()` converts to ImageBlocks
3. Injected into `context.multimodal_context: list[ContentBlock]`
4. Visual QA node passes blocks to `VisualQAService.process()`
5. VLM receives ImageBlock + TextBlock messages

### Config Pattern

Existing gates: `settings.ai.visual_qa_enabled`, `settings.ai.visual_qa_autofix_enabled`, `settings.rendering.visual_diff_enabled`, `settings.rendering.visual_diff_threshold`. New gates go in `BlueprintConfig`.

## Test Landscape

### Existing Test Files

| File | Lines | Coverage |
|------|-------|----------|
| `app/ai/agents/visual_qa/tests/test_visual_qa.py` | 545 | VLM integration, defect parsing, ontology enrichment |
| `app/ai/agents/visual_qa/tests/test_correction.py` | 209 | Auto-fix via LLM correction |
| `app/ai/agents/visual_qa/tests/test_node_autofix.py` | 226 | Node orchestration, fix acceptance/rejection |
| `app/ai/blueprints/tests/test_nodes.py` | 150+ | QAGateNode, RecoveryRouterNode execution |
| `app/ai/blueprints/tests/test_engine.py` | 500+ | QA fail → recovery → fix loop |
| `app/rendering/tests/test_visual_diff.py` | 100+ | ODiff wrapper, pixel comparison |
| `app/rendering/tests/test_service.py` | 100+ | RenderingService protocol |

### Key Fixtures & Factories

- `sample_html_valid` / `sample_html_minimal` — in blueprints & qa_engine conftest
- `sample_screenshots` — tiny 1x1 base64 PNGs (`{"gmail_web": ..., "outlook_2019": ..., "apple_mail": ...}`)
- `make_qa_result()`, `make_qa_check()`, `make_qa_check_result()` — qa_engine conftest
- `StubNode`, `FailThenPassNode` — test_engine.py for graph testing
- `_make_context()`, `_make_mock_decisions()` — visual_qa test helpers
- `mock_provider` → `AsyncMock` with `CompletionResponse`
- 15 golden templates, 21 component seeds, 5 representative templates, 7 representative components

### Mock Patterns

- Settings: `patch("...get_settings")` → `MagicMock(ai=MagicMock(visual_qa_enabled=True, ...))`
- Registry: `patch("...get_registry")` → `.get_llm.return_value = mock_provider`
- VLM response: `mock_response.content = '{"defects": [...], "overall_rendering_score": ...}'`
- ODiff: `patch("app.rendering.visual_diff.asyncio.create_subprocess_exec", ...)`

## Type Check Baseline

| Directory | Pyright Errors | Mypy Errors |
|-----------|---------------|-------------|
| `app/ai/blueprints/` | 18 | 17 |
| `app/ai/agents/visual_qa/` | 0 | 1 |
| `app/qa_engine/` | 13 | 16 |
| `app/email_engine/` | 3 | 16 |
| **Total** | **34** | **50** |

Visual QA directory is cleanest (0 pyright errors). Most mypy errors are transitive import issues from `design_sync/`, `rendering/sandbox/`.

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `app/ai/blueprints/nodes/visual_precheck_node.py` | Pre-QA visual check — renders top 3 clients, runs lightweight VLM defect detection |
| `app/ai/blueprints/nodes/visual_comparison_node.py` | Post-Maizzle screenshot comparison vs original design (ODiff + VLM) |
| `app/ai/agents/visual_qa/tests/test_visual_precheck.py` | Tests for visual precheck node |
| `app/ai/agents/visual_qa/tests/test_visual_comparison.py` | Tests for visual comparison node |

### Modified Files

| File | Changes |
|------|---------|
| `app/core/config.py` | Add `visual_qa_precheck` and `visual_comparison` feature gates to `BlueprintConfig` |
| `app/qa_engine/schemas.py` | Add `VisualDefect` model + `visual_defects` field on `QAResultResponse` |
| `app/email_engine/schemas.py` | Add `VisualComparisonResult` model + `visual_drift` field on `BuildResponse` |
| `app/ai/blueprints/nodes/qa_gate_node.py` | Import and run visual precheck before standard checks; merge visual defects into result |
| `app/ai/blueprints/nodes/recovery_router_node.py` | Add `visual_defect` → agent routing; inject screenshot into `multimodal_context` |
| `app/ai/agents/visual_qa/service.py` | Add `detect_defects_lightweight()` and `compare_screenshots()` methods |
| `app/ai/agents/visual_qa/schemas.py` | Add `VisualComparisonResult` schema |
| `app/ai/blueprints/engine.py` | Register new nodes; wire visual comparison after Maizzle build |

## Implementation Steps

### Step 1: Config — Feature Gates

**File:** `app/core/config.py` — `BlueprintConfig` class (~line 413)

Add two feature gates:

```python
visual_qa_precheck: bool = False        # BLUEPRINT__VISUAL_QA_PRECHECK
visual_comparison: bool = False          # BLUEPRINT__VISUAL_COMPARISON
visual_comparison_threshold: float = 5.0 # % pixel diff threshold for drift warning
visual_precheck_top_clients: int = 3     # Number of clients to render for precheck
```

### Step 2: Schemas — VisualDefect + VisualComparisonResult

**File:** `app/qa_engine/schemas.py`

Add `VisualDefect` model (reuse field names from existing `app/ai/agents/visual_qa/schemas.py:VisualDefect` but adapt for QA gate output):

```python
class VisualDefect(BaseModel):
    type: str                                           # e.g., "layout_collapse", "style_stripping"
    severity: Literal["low", "medium", "high", "critical"]
    client_id: str                                      # e.g., "outlook_2019"
    description: str
    suggested_agent: str | None = None                  # e.g., "outlook_fixer", "dark_mode"
    screenshot_ref: str | None = None                   # content block ID for downstream injection
    bounding_box: dict[str, int] | None = None          # {"x": 0, "y": 100, "w": 600, "h": 50}
```

Add `visual_defects` to `QAResultResponse`:

```python
visual_defects: list[VisualDefect] = Field(default_factory=list)
```

**File:** `app/ai/agents/visual_qa/schemas.py`

Add `VisualComparisonResult`:

```python
class VisualComparisonResult(BaseModel):
    drift_score: float                    # 0.0–100.0 percentage
    diff_regions: list[dict[str, object]] = Field(default_factory=list)
    diff_image_ref: str | None = None     # path or content block ID
    semantic_description: str = ""        # VLM interpretation of differences
    regressed: bool = False               # True if worse than previous iteration
```

**File:** `app/email_engine/schemas.py`

Add to `BuildResponse`:

```python
visual_drift: VisualComparisonResult | None = None
```

### Step 3: Visual QA Service — Lightweight Detection + Screenshot Comparison

**File:** `app/ai/agents/visual_qa/service.py`

Add two methods to `VisualQAService`:

**`detect_defects_lightweight()`** — fast-path VLM call for QA gate precheck:

- Accepts `screenshots: dict[str, str]` (client → base64 PNG), `html: str`, `client_ids: list[str]`
- Builds minimal prompt: "Detect rendering defects in these email screenshots. Return JSON with defects array only."
- Uses smaller `max_tokens` (1024 vs 4096) for speed
- Parses response → `list[VisualDefect]` (QA engine schema)
- Maps VLM `DetectedDefect.affected_clients` → individual `VisualDefect` per client
- Maps `DetectedDefect.suggested_fix` → `suggested_agent` via heuristic (mentions "Outlook"/"VML" → "outlook_fixer", "dark mode" → "dark_mode", "contrast"/"alt" → "accessibility", default → "scaffolder")
- No ontology enrichment (speed optimization)

**`compare_screenshots()`** — ODiff + VLM comparison:

- Accepts `original: dict[str, str]`, `rendered: dict[str, str]`, `client_ids: list[str]`
- For each client in both dicts: call `compare_images()` from `app/rendering/visual_diff`
- If any diff_percentage > threshold: run VLM on the diff image + both screenshots for semantic interpretation
- Returns `VisualComparisonResult` with aggregated drift_score (max across clients), diff_regions, VLM description

### Step 4: Visual Precheck Node

**File:** `app/ai/blueprints/nodes/visual_precheck_node.py` (NEW)

```
VisualPrecheckNode (deterministic node)
├── Check feature gate: settings.blueprint.visual_qa_precheck → skip if False
├── Get audience profile from context.metadata → extract top N client_ids
├── Render HTML via RenderingService.render_screenshots() for those clients
├── Call VisualQAService.detect_defects_lightweight()
├── Convert defects to StructuredFailure list:
│   ├── check_name = f"visual_defect:{defect.client_id}"
│   ├── suggested_agent = defect.suggested_agent
│   ├── severity = defect.severity
│   └── priority = 0 (highest — visual defects should be fixed first)
├── Store screenshots in context.metadata["precheck_screenshots"] for downstream use
└── Return NodeResult with structured_failures (empty = success)
```

Pattern: follow `qa_gate_node.py` structure. Node type: `"deterministic"`.

### Step 5: Visual Comparison Node

**File:** `app/ai/blueprints/nodes/visual_comparison_node.py` (NEW)

```
VisualComparisonNode (deterministic node)
├── Check feature gate: settings.blueprint.visual_comparison → skip if False
├── Get original design screenshots from context.metadata["original_screenshots"]
│   └── If none available → skip (advisory only)
├── Get current rendered screenshots from context.metadata["screenshots"]
│   └── If none → render via RenderingService
├── Get previous iteration screenshots from context.metadata.get("prev_screenshots")
├── Call VisualQAService.compare_screenshots(original, rendered, client_ids)
├── If iteration > 0 and prev_screenshots: also compare vs previous → detect regression
├── Store result in context.metadata["visual_comparison"]
└── Return NodeResult(status="success", details=f"drift_score={result.drift_score:.1f}%")
    └── Advisory only — never returns "failed" (does not block output)
```

### Step 6: QA Gate Node — Integrate Visual Precheck Results

**File:** `app/ai/blueprints/nodes/qa_gate_node.py`

Modify `execute()`:

1. Before running standard 11 checks, check if `context.metadata.get("visual_precheck_failures")` exists (set by visual precheck node upstream)
2. Merge visual precheck `StructuredFailure` items into the standard failure list
3. Add `visual_defects` list to the QA gate details output (for API response)
4. High/critical visual defects count as QA failures (trigger recovery)

### Step 7: Recovery Router — Visual Defect Routing with Multimodal Context

**File:** `app/ai/blueprints/nodes/recovery_router_node.py`

Modifications:

1. Add to `CHECK_TO_AGENT` dict:
   ```python
   "visual_defect:outlook_2019": "outlook_fixer",
   "visual_defect:outlook_365": "outlook_fixer",
   # ... pattern: "visual_defect:{client}" → agent based on defect.suggested_agent
   ```
   Better approach: add dynamic routing in `execute()` — if `check_name.startswith("visual_defect:")`, use the `suggested_agent` from `StructuredFailure.details` (encode agent name in details JSON).

2. When routing a visual defect to a fixer agent, inject screenshot into multimodal context:
   ```python
   if check_name.startswith("visual_defect:"):
       client_id = check_name.split(":", 1)[1]
       screenshots = context.metadata.get("precheck_screenshots", {})
       if client_id in screenshots:
           # Build multimodal context for fixer
           from app.ai.multimodal import ImageBlock, TextBlock
           multimodal = [
               TextBlock(text=f"Visual defect in {client_id}: {failure.details}"),
               ImageBlock(data=base64.b64decode(screenshots[client_id]),
                         media_type="image/png", source="base64"),
           ]
           context.metadata["multimodal_context_override"] = multimodal
   ```

3. Add to `AGENT_SCOPES` and `SCOPE_PROMPTS` for visual defect routing.

### Step 8: Blueprint Engine — Register New Nodes + Wire Edges

**File:** `app/ai/blueprints/engine.py`

1. Import `VisualPrecheckNode` and `VisualComparisonNode`
2. Register in node registry
3. When building blueprint definition, conditionally add edges:
   - If `visual_qa_precheck` enabled: insert `visual_precheck` node between scaffolder output and `qa_gate`
   - If `visual_comparison` enabled: insert `visual_comparison` node after `maizzle_build`, before `export`
4. In `_build_node_context()`: when routing to fixer agent after visual defect, check for `multimodal_context_override` in metadata and inject into `context.multimodal_context`

### Step 9: Tests

**File:** `app/ai/agents/visual_qa/tests/test_visual_precheck.py` (NEW)

| Test | Description |
|------|-------------|
| `test_skipped_when_disabled` | Feature gate off → status="skipped" |
| `test_skipped_no_audience` | No audience profile → skip (no clients to render) |
| `test_no_defects_returns_success` | VLM finds no issues → status="success", empty failures |
| `test_high_severity_defect_returns_failure` | VLM finds critical defect → structured_failure with check_name, agent |
| `test_screenshots_stored_in_metadata` | Screenshots saved for downstream multimodal injection |
| `test_multiple_clients_multiple_defects` | 3 clients, mixed defects → correct per-client failures |
| `test_rendering_service_failure_graceful` | RenderingService throws → skip, don't crash pipeline |
| `test_vlm_failure_graceful` | VLM call fails → skip, log warning |

**File:** `app/ai/agents/visual_qa/tests/test_visual_comparison.py` (NEW)

| Test | Description |
|------|-------------|
| `test_skipped_when_disabled` | Feature gate off → status="skipped" |
| `test_skipped_no_original_screenshots` | No original design screenshots → skip |
| `test_low_drift_advisory` | <5% drift → success with drift_score in details |
| `test_high_drift_warning` | >5% drift → success with warning, VLM description |
| `test_regression_detection` | iteration>0, worse than previous → regressed=True |
| `test_odiff_failure_graceful` | ODiff binary missing/fails → skip |
| `test_result_stored_in_metadata` | VisualComparisonResult stored for BuildResponse |

**Modify:** `app/ai/blueprints/tests/test_nodes.py`

| Test | Description |
|------|-------------|
| `test_qa_gate_merges_visual_precheck_failures` | Visual precheck failures merged into QA gate output |
| `test_recovery_router_routes_visual_defect` | `visual_defect:outlook_2019` → routes to `outlook_fixer` |
| `test_recovery_router_injects_multimodal` | Screenshot injected into fixer's multimodal context |
| `test_recovery_router_visual_defect_cycle_detection` | Same visual defect persists → escalate |

**Modify:** `app/ai/agents/visual_qa/tests/test_visual_qa.py`

| Test | Description |
|------|-------------|
| `test_detect_defects_lightweight_success` | Fast-path VLM returns defects → mapped to QA VisualDefect |
| `test_detect_defects_lightweight_empty` | No defects → empty list |
| `test_detect_defects_lightweight_vlm_error` | VLM fails → empty list, no crash |
| `test_compare_screenshots_low_diff` | ODiff <5% → low drift_score, no VLM call |
| `test_compare_screenshots_high_diff` | ODiff >5% → VLM called for semantic description |
| `test_compare_screenshots_partial_clients` | Only some clients have originals → compare available ones |

## Preflight Warnings

- `recovery_router_node.py` `CHECK_TO_AGENT` dict is hardcoded — visual defect routing needs dynamic lookup (use `suggested_agent` from StructuredFailure, not static dict)
- `qa_gate_node.py` is only 87 lines — keep modifications minimal; delegate visual precheck to separate node
- `VisualQAService._screenshots_to_blocks()` has `_MAX_SCREENSHOT_B64_LEN` check — precheck should respect same limit
- Existing `VisualDefect` in `app/ai/agents/visual_qa/schemas.py` has different fields than the QA engine `VisualDefect` — use distinct names or adapt with a mapping function
- `BlueprintEngine._build_node_context()` is already 500+ lines — keep new logic in node classes, not engine

## Security Checklist

- [ ] No new endpoints (internal pipeline changes only)
- [ ] Screenshots generated from pipeline HTML — no external content fetched
- [ ] VLM calls use existing API key + rate limits from `AIConfig`
- [ ] ODiff is deterministic image comparison — no code execution
- [ ] Screenshots are ephemeral (not persisted by default)
- [ ] Feature gates default to `False` — zero latency impact unless opted in
- [ ] Base64 screenshot data validated against size limits before VLM calls
- [ ] No user input reaches `sa.text()`, `subprocess`, `eval`

## Verification

- [ ] `make check` passes
- [ ] `make test` passes — no regressions in existing 977 visual_qa test lines
- [ ] `make types` — pyright errors ≤ 34 (baseline), mypy errors ≤ 50 (baseline)
- [ ] Feature gates off (default) → zero behavior change, zero latency impact
- [ ] `BLUEPRINT__VISUAL_QA_PRECHECK=true` → visual precheck runs, defects route to fixers with screenshots
- [ ] `BLUEPRINT__VISUAL_COMPARISON=true` → drift score reported in build response
- [ ] Visual defect → recovery router → fixer agent receives multimodal context (screenshot + description)
- [ ] Rendering/VLM failures handled gracefully (skip, log, don't crash pipeline)
- [ ] `make bench` — acceptable latency increase (<2s per visual check when enabled)
