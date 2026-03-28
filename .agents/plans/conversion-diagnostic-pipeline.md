# Plan: Conversion Diagnostic Pipeline

**Status:** planned
**Phase:** 33.11+ (Design Sync Observability)
**Depends on:** Phase 33 converter pipeline

## Context

After 6+ debugging attempts on email conversion issues, the root problem is **zero observability** into the pipeline. The layout analyzer (`layout_analyzer.py`), component matcher (`component_matcher.py`), and component renderer (`component_renderer.py`) have **no logging at all**. There are 12+ points where data is silently lost (IMAGE fills on FRAMEs ignored, TEXT nodes with whitespace dropped, UNKNOWN sections getting generic matches, slot fills failing silently). No way to see what the Figma node tree looks like, why a section was classified as "hero" vs "unknown", which images were detected vs missed, or what HTML looks like between transforms.

This plan builds a `DiagnosticRunner` that runs the same pipeline functions but captures every intermediate state, flags data loss, and produces a JSON report with per-section traces. Three interfaces: CLI script, test helper, API endpoint. Also adds a Figma design pattern catalog so we can map which design patterns convert well.

## Research Summary

### Pipeline Architecture (6 stages, all synchronous)

| Stage | File | Entry Point | Returns |
|-------|------|-------------|---------|
| 1. Tree Parse | `figma/service.py` | Figma API → `DesignFileStructure` | `DesignNode` tree |
| 2. Layout | `figma/layout_analyzer.py` | `analyze_layout(structure)` | `DesignLayoutDescription` (sections, texts, images, buttons) |
| 3. Match | `component_matcher.py` | `match_all(sections, container_width=600)` | `list[ComponentMatch]` (slug, confidence, slot_fills) |
| 4. Render | `component_renderer.py` | `ComponentRenderer(cw).load(); .render_all(matches)` | `list[RenderedSection]` (html, dark_mode_classes, images) |
| 5. Assembly | `converter_service.py` | `_convert_with_components()` internal | `str` (concatenated HTML + dark mode CSS) |
| 6. Post | `converter.py` | `sanitize_web_tags_for_email(html)` | `str` (email-safe HTML) |

### Key Types (all frozen dataclasses in `protocol.py`)
- `DesignFileStructure` — root: `file_name`, `pages: list[DesignNode]`
- `DesignNode` — tree node: `id`, `name`, `type`, `children`, `width/height/x/y`, `text_content`, `fill_color`, `layout_mode`, `item_spacing`, 20+ optional fields
- `ExtractedTokens` — colors, typography, spacing, dark_colors, gradients, variables
- `ConversionResult` — `html`, `layout`, `images`, `warnings` (in `converter_service.py`)

### Component Slugs (15 recognized)
`preheader`, `email-header`, `logo-header`, `hero-block`, `full-width-image`, `text-block`, `article-card`, `image-block`, `image-grid`, `cta`, `email-footer`, `spacer`, `social-icons`, `divider`, `navigation-bar`, `col_1`–`col_4`

### Orchestration Pattern (`converter_service.py:DesignConverterService.convert()`)
`_convert_with_components()`: collect frames → `analyze_layout()` → `match_all()` → `ComponentRenderer.render_all()` → assemble sections → `sanitize_web_tags_for_email()`. DiagnosticRunner calls the same functions but captures I/O at each boundary.

## Test Landscape

### Existing Test Files (27 in `app/design_sync/tests/`)
Key reusable files: `test_e2e_pipeline.py` (full pipeline fixtures), `test_component_matcher.py` & `test_component_renderer.py` (section builders), `test_layout_analyzer.py` (structure factory)

### Factory Functions (no conftest.py — all inline)

| File | Function | Returns |
|------|----------|---------|
| `test_e2e_pipeline.py` | `_make_e2e_tokens()` | `ExtractedTokens` with 6 colors, typography, spacing, gradient |
| `test_e2e_pipeline.py` | `_make_e2e_structure()` | `DesignFileStructure` with header/hero/2col/footer |
| `test_layout_analyzer.py` | `make_email_structure()` | `DesignFileStructure` for layout tests |
| `test_component_matcher.py` | `_make_section(...)` | `EmailSection` with 10+ optional fields |
| `test_component_matcher.py` | `_text()`, `_image()`, `_button()` | `TextBlock`, `ImagePlaceholder`, `ButtonElement` |
| `test_e2e_pipeline.py` | `_TagBalanceChecker` | HTMLParser subclass for tag balance validation |

### Test Conventions
- Class-scoped fixtures for expensive pipeline runs (`pipeline_html`, `pipeline_result`)
- `AsyncMock(spec=AsyncSession)` for DB, `MagicMock` for model objects
- `app.dependency_overrides[get_current_user]` for auth in route tests
- `limiter.enabled = False` for rate limiter bypass

## Type Check Baseline

| Tool | Scope | Errors | Warnings |
|------|-------|--------|----------|
| Pyright | `app/design_sync/` | 184 | 141 |
| Mypy | `app/design_sync/` | 9 (5 files) | — |
| Pyright | `app/design_sync/routes.py` | 0 | 0 |

**Mypy issues:** `converter.py:827` no-redef, `converter.py:853-854` assignment, `import_service.py:222` unused-ignore, `component_matcher.py:214` no-any-return + not-callable. New code must not increase these counts.

## Files to Create/Modify

| File | Change |
|------|--------|
| `app/design_sync/diagnose/__init__.py` | **New** — public API: `DiagnosticRunner`, `DiagnosticReport` |
| `app/design_sync/diagnose/models.py` | **New** — frozen dataclasses: `DataLossEvent`, `SectionTrace`, `StageResult`, `DesignSummary`, `DiagnosticReport` |
| `app/design_sync/diagnose/analyzers.py` | **New** — per-stage analysis: `analyze_design_tree()`, `analyze_layout_stage()`, `analyze_matching_stage()`, `analyze_rendering_stage()`, `analyze_assembly_stage()`, `analyze_post_processing()` |
| `app/design_sync/diagnose/runner.py` | **New** — `DiagnosticRunner` class: `run_from_structure()` (sync) + `run_from_connection()` (async) |
| `app/design_sync/diagnose/report.py` | **New** — JSON serialization, HTML truncation, `dump_structure()` / `load_structure()` for offline use |
| `app/design_sync/diagnose/__main__.py` | **New** — CLI: `python -m app.design_sync.diagnose --connection-id 8 -o report.json` |
| `app/design_sync/diagnose/schemas.py` | **New** — Pydantic response models for API endpoint |
| `app/design_sync/routes.py` | +1 endpoint: `GET /connections/{id}/diagnose` (developer role, 2/min limit) |
| `app/design_sync/tests/test_diagnose.py` | **New** — tests using existing E2E fixtures |

## 12 Silent Data Loss Points to Detect

| # | Stage | Location | What is Lost | Detection |
|---|-------|----------|-------------|-----------|
| 1 | Parse | `figma/service.py:1101` | Nodes beyond depth 30 | Compare tree depth vs limit |
| 2 | Parse | `figma/service.py:1078` | IMAGE fills on FRAME (only VECTOR→IMAGE reclassified) | Walk fills[], find type=IMAGE on non-VECTOR |
| 3 | Parse | `figma/service.py:1020` | TEXT with whitespace-only content | Count raw TEXT vs parsed |
| 4 | Parse | `figma/service.py:1081` | Non-SOLID fills (gradient on node, not token) | Count skipped fill types |
| 5 | Layout | `layout_analyzer.py:221` | Non-FRAME/COMPONENT top children filtered | Compare children vs candidates |
| 6 | Layout | `layout_analyzer.py:229` | Wrapper unwrap loses wrapper props | Detect unwrap, report lost padding/bg |
| 7 | Layout | `layout_analyzer.py:414` | Buttons: height>80, no fill, no name hint | Walk small frames with text child |
| 8 | Layout | `layout_analyzer.py:384` | Images only at direct/single-frame depth | Report nested IMAGE nodes missed |
| 9 | Match | `component_matcher.py:212` | Unknown slug → empty fills (no builder) | Report builder lookup miss |
| 10 | Match | `component_matcher.py:325` | Multi-text: only 1st heading + joined body | Report text count reduction |
| 11 | Render | `component_renderer.py:66` | Missing template → fallback plain text | Report fallback rendering |
| 12 | Post | `import_service.py:490` | Images only via data-node-id; positional fill | Report remaining empty src="" |

## Implementation Steps

### Step 1: Data models (`app/design_sync/diagnose/models.py`)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class DataLossEvent:
    """A single instance of data being silently lost in the pipeline."""
    type: str          # "depth_truncated"|"image_fill_ignored"|"text_empty"|...
    node_id: str
    node_name: str
    detail: str        # Human-readable explanation
    stage: str         # Pipeline stage name

@dataclass(frozen=True)
class SectionTrace:
    """Full diagnostic trace for one email section through the pipeline."""
    section_idx: int
    node_id: str
    node_name: str
    classified_type: str       # "HERO"|"CONTENT"|"FOOTER"|"UNKNOWN"
    matched_component: str     # "hero-block"|"article-card"|...
    match_confidence: float
    texts_found: int
    images_found: int
    buttons_found: int
    slot_fills: tuple[dict[str, str], ...]   # (slot_id, value_preview, slot_type)
    unfilled_slots: tuple[str, ...]          # Template slots with no matching fill
    html_preview: str                        # First 3000 chars of rendered HTML

@dataclass(frozen=True)
class StageResult:
    """Diagnostic result for one pipeline stage."""
    name: str          # "layout_analysis"|"component_matching"|...
    elapsed_ms: float
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    data_loss: tuple[DataLossEvent, ...]
    warnings: tuple[str, ...]
    error: str | None = None

@dataclass(frozen=True)
class DesignSummary:
    """Catalog of design patterns in the Figma file."""
    total_nodes: int
    node_type_counts: dict[str, int]        # {"FRAME": 42, "TEXT": 18, "IMAGE": 6}
    max_tree_depth: int
    image_fill_frames: tuple[dict[str, str], ...]  # FRAMEs with IMAGE fills (silently lost)
    auto_layout_frames: int
    naming_compliance: float                # % of frames matching _SECTION_PATTERNS
    naming_misses: tuple[str, ...]          # Frame names that didn't match any pattern

@dataclass(frozen=True)
class DiagnosticReport:
    """Complete diagnostic report from one pipeline run."""
    id: str
    connection_id: int | None
    timestamp: str
    total_elapsed_ms: float
    stages_completed: int
    total_warnings: int
    total_data_loss_events: int
    design_summary: DesignSummary
    stages: tuple[StageResult, ...]
    section_traces: tuple[SectionTrace, ...]
    final_html_preview: str                 # First 5000 chars
    final_html_length: int
```

### Step 2: Stage analyzers (`app/design_sync/diagnose/analyzers.py`)

Six analyzer functions — one per pipeline stage. Each takes input + output and returns `StageResult`.

**`analyze_design_tree(structure) -> DesignSummary`**
Walks the full `DesignFileStructure` tree. For each node:
- Count by type → `node_type_counts`
- Track max depth → `max_tree_depth`
- If FRAME with children, check `node.fill_color` pattern (limitation: can't detect IMAGE fills from parsed tree, need raw JSON)
- Count `layout_mode is not None` → `auto_layout_frames`
- Match `node.name.lower()` against `_SECTION_PATTERNS` from `layout_analyzer.py` → `naming_compliance`

**Critical detection:** For IMAGE fill detection (loss #2), the analyzer needs the raw Figma JSON (pre-parse). Add a `raw_figma_nodes: dict[str, dict] | None` parameter. If available, walk raw JSON `fills[]` arrays looking for `{type: "IMAGE"}` on FRAME nodes. These are hero/section backgrounds the parser silently ignores.

```python
def analyze_design_tree(
    structure: DesignFileStructure,
    raw_figma_json: dict[str, Any] | None = None,
) -> tuple[DesignSummary, list[DataLossEvent]]:
    """Analyze the design tree for patterns and data loss."""
```

**`analyze_layout_stage(structure, layout) -> StageResult`**
- Count TEXT nodes in input tree → compare with `layout.total_text_blocks`
- Count IMAGE nodes in input → compare with `layout.total_images`
- For each section: report `section.section_type`, flag UNKNOWN
- Walk input tree for button candidates (small frames with single TEXT child, height ≤ 80) → compare with detected buttons
- Report sections with `images_found=0` where the node tree has IMAGE descendants (loss #8)

**`analyze_matching_stage(sections, matches) -> StageResult`**
- For each `ComponentMatch`: report slug, confidence
- Flag confidence < 0.8 as uncertain
- For each match, compare `len(section.texts)` vs `len(match.slot_fills where type=text)` — text count reduction = loss #10
- Check if builder function exists for the slug (loss #9)

**`analyze_rendering_stage(matches, rendered) -> StageResult`**
- Flag fallback rendering (template not found, loss #11)
- For each rendered section: find `data-slot="..."` attrs in the component seed HTML template, compare with filled slots → `unfilled_slots`
- Capture `html_preview` (first 3000 chars per section)

**`analyze_assembly_stage(section_htmls, final_html) -> StageResult`**
- Count `<table>` open/close tags — must balance
- Count MSO conditionals (`<!--[if mso]>` vs `<![endif]-->`) — must balance
- Check CSS brace balance in `<style>` blocks (the `}}` bug that caused issues)
- Report total HTML length

**`analyze_post_processing(before, after) -> StageResult`**
- Count `<div>` → `<table>` conversions by sanitizer
- Count remaining `src=""` (loss #12)
- Count contrast fixes (dark bg + light text injections)
- Report length delta

### Step 3: Diagnostic runner (`app/design_sync/diagnose/runner.py`)

```python
class DiagnosticRunner:
    """Runs the full conversion pipeline with diagnostic capture at each stage."""

    def run_from_structure(
        self,
        structure: DesignFileStructure,
        tokens: ExtractedTokens,
        *,
        raw_figma_json: dict[str, Any] | None = None,
        target_clients: list[str] | None = None,
    ) -> DiagnosticReport:
        """Synchronous entry — for CLI and tests.

        Calls the same pipeline functions as converter_service._convert_with_components()
        but captures input/output at each stage boundary.
        """
```

**Flow inside `run_from_structure`:**

```
1. design_summary = analyze_design_tree(structure, raw_figma_json)
2. layout = analyze_layout(structure)                          # real call
   stage1 = analyze_layout_stage(structure, layout)            # capture
3. matches = match_all(layout.sections, container_width=cw)    # real call
   stage2 = analyze_matching_stage(layout.sections, matches)   # capture
4. renderer = ComponentRenderer(cw); renderer.load()
   rendered = [renderer.render_section(m) for m in matches]    # real call
   stage3 = analyze_rendering_stage(matches, rendered)         # capture
5. sections_html = assemble(rendered, tokens, cw)              # real call
   stage4 = analyze_assembly_stage(rendered, sections_html)    # capture
6. post_html = sanitize_web_tags_for_email(sections_html)      # real call
   stage5 = analyze_post_processing(sections_html, post_html)  # capture
7. section_traces = build_section_traces(layout, matches, rendered)
8. return DiagnosticReport(...)
```

**`build_section_traces()`** — zips layout sections, component matches, and rendered HTML to produce one `SectionTrace` per section. This is the key debugging view — shows the full journey of each section.

**`run_from_connection()`** — async wrapper that fetches structure + tokens from DB via `DesignSyncService`, then calls `run_from_structure()`.

### Step 4: Report serialization (`app/design_sync/diagnose/report.py`)

```python
def report_to_dict(report: DiagnosticReport) -> dict[str, Any]:
    """Serialize DiagnosticReport to JSON-safe dict."""

def report_to_json(report: DiagnosticReport, *, indent: int = 2) -> str:
    """Serialize to JSON string."""

def dump_structure_to_json(structure: DesignFileStructure, path: Path) -> None:
    """Dump DesignFileStructure to JSON for offline diagnostic re-runs.

    Use this to capture the exact data the pipeline receives, then debug offline.
    """

def load_structure_from_json(path: Path) -> DesignFileStructure:
    """Load DesignFileStructure from a JSON dump file."""

def dump_tokens_to_json(tokens: ExtractedTokens, path: Path) -> None:
    """Dump ExtractedTokens to JSON for offline use."""

def load_tokens_from_json(path: Path) -> ExtractedTokens:
    """Load ExtractedTokens from a JSON dump file."""
```

The dump/load utilities are critical — they let you:
1. Run one design sync to cache the Figma data
2. Dump structure + tokens to JSON files
3. Re-run diagnostics offline indefinitely while debugging
4. Share the JSON files for collaborative debugging

### Step 5: CLI entry point (`app/design_sync/diagnose/__main__.py`)

```
Usage:
  python -m app.design_sync.diagnose --structure-json cached.json -o report.json
  python -m app.design_sync.diagnose --structure-json cached.json --tokens-json tokens.json
  python -m app.design_sync.diagnose --connection-id 8 -o report.json  # requires DB

Options:
  --structure-json PATH  Cached DesignFileStructure JSON (from dump_structure)
  --tokens-json PATH     Cached ExtractedTokens JSON (optional, defaults to empty)
  --raw-figma-json PATH  Raw Figma API response (for IMAGE fill detection)
  --connection-id INT    Live connection ID (requires DATABASE__URL env)
  -o, --output PATH      Output file (default: stdout)
  --verbose              Include full HTML (not truncated)
  --dump-structure PATH  Dump the structure JSON for future offline use
  --dump-tokens PATH     Dump the tokens JSON for future offline use
```

**Key offline workflow:**
```bash
# First run: dump structure for offline analysis
python -m app.design_sync.diagnose --connection-id 8 \
  --dump-structure data/debug/structure.json \
  --dump-tokens data/debug/tokens.json \
  -o data/debug/report.json

# Subsequent runs: iterate offline (no DB/API needed)
python -m app.design_sync.diagnose \
  --structure-json data/debug/structure.json \
  --tokens-json data/debug/tokens.json \
  -o data/debug/report.json
```

### Step 6: API endpoint (`app/design_sync/routes.py`)

Add one route after existing design-sync endpoints:

```python
@router.get("/connections/{connection_id}/diagnose")
@limiter.limit("2/minute")
async def diagnose_connection(
    connection_id: int,
    request: Request,
    current_user: User = Depends(require_role("developer")),
    db: AsyncSession = Depends(get_db),
) -> DiagnosticReportResponse:
    """Run conversion diagnostics on a design connection."""
```

Response uses Pydantic schema from `diagnose/schemas.py`. HTML previews truncated to 3000 chars in API response.

### Step 7: Pydantic schemas (`app/design_sync/diagnose/schemas.py`)

Mirror the frozen dataclass models as Pydantic `BaseModel` for API serialization:

```python
class DataLossEventResponse(BaseModel): ...
class SectionTraceResponse(BaseModel): ...
class StageResultResponse(BaseModel): ...
class DesignSummaryResponse(BaseModel): ...
class DiagnosticReportResponse(BaseModel):
    @classmethod
    def from_report(cls, report: DiagnosticReport) -> DiagnosticReportResponse: ...
```

### Step 8: Tests (`app/design_sync/tests/test_diagnose.py`)

Reuse existing fixtures from `test_e2e_pipeline.py`:

```python
class TestDesignSummary:
    def test_counts_node_types(self): ...
    def test_detects_auto_layout(self): ...
    def test_naming_compliance(self): ...

class TestLayoutAnalyzer:
    def test_flags_unknown_sections(self): ...
    def test_detects_missed_images(self): ...
    def test_detects_unmatched_buttons(self): ...

class TestMatchingAnalyzer:
    def test_flags_low_confidence(self): ...
    def test_detects_text_reduction(self): ...

class TestRenderingAnalyzer:
    def test_detects_fallback_rendering(self): ...
    def test_detects_unfilled_slots(self): ...

class TestAssemblyAnalyzer:
    def test_detects_tag_imbalance(self): ...
    def test_detects_css_brace_imbalance(self): ...

class TestPostProcessingAnalyzer:
    def test_counts_div_to_table_conversions(self): ...
    def test_counts_unfilled_images(self): ...

class TestDiagnosticRunner:
    def test_full_pipeline_e2e(self): ...
    def test_section_traces_complete(self): ...

class TestDumpLoad:
    def test_roundtrip_structure(self): ...
    def test_roundtrip_tokens(self): ...
```

## Design Pattern Catalog (Figma Patterns → Email Conversion Quality)

The `DesignSummary` captures patterns that predict conversion quality:

| Pattern | Good for Email | Why |
|---------|---------------|-----|
| `naming_compliance > 80%` | Yes | Sections classified deterministically, not by heuristic |
| `auto_layout_frames` high | Yes | Auto-layout maps cleanly to table structure |
| `image_fill_frames = []` | Yes | No silently lost background images |
| `max_tree_depth < 10` | Yes | Shallow trees convert more reliably |
| FRAME names: "hero", "header", "footer" | Yes | Match `_SECTION_PATTERNS` directly |
| Hero bg as child IMAGE node | Yes | Detected by `_extract_images()` |
| Hero bg as FRAME fill | No | Silently lost — parser only reclassifies VECTOR→IMAGE |
| Buttons with fill_color set | Yes | Detected by `_extract_buttons()` |
| Buttons with only border (no fill) | No | May fail fill check |
| `node_type_counts["VECTOR"]` high | Risky | Vectors stripped as non-email-safe |

Over time, running diagnostics on multiple designs builds a reference of which patterns work. The `naming_compliance` score becomes a pre-conversion quality gate.

## Verification

1. **Unit tests:** `pytest app/design_sync/tests/test_diagnose.py -v`
2. **CLI smoke test:**
   ```bash
   python -m app.design_sync.diagnose --structure-json data/debug/structure.json | python -m json.tool | head -50
   ```
3. **Check section traces:**
   ```bash
   python -m app.design_sync.diagnose --structure-json data/debug/structure.json | \
     python -c "import json,sys; r=json.load(sys.stdin); [print(f'{t[\"section_idx\"]}: {t[\"classified_type\"]} → {t[\"matched_component\"]} (conf={t[\"match_confidence\"]}) texts={t[\"texts_found\"]} imgs={t[\"images_found\"]} unfilled={t[\"unfilled_slots\"]}') for t in r['section_traces']]"
   ```
4. **Check data loss:**
   ```bash
   python -m app.design_sync.diagnose --structure-json data/debug/structure.json | \
     python -c "import json,sys; r=json.load(sys.stdin); [print(f'[{e[\"stage\"]}] {e[\"type\"]}: {e[\"detail\"]}') for s in r['stages'] for e in s['data_loss']]"
   ```
5. **API test:** `curl localhost:8891/api/v1/design-sync/connections/8/diagnose -H "Authorization: Bearer ..." | jq .design_summary`
6. **Type check:** Pyright errors ≤ 184, mypy errors ≤ 9

## Security Checklist (`GET /connections/{id}/diagnose`)

- [x] Auth: `require_role("developer")` — not viewer-accessible
- [x] Rate limit: `@limiter.limit("2/minute")` — prevents DoS via expensive pipeline runs
- [ ] Input validation: `connection_id` is path param (int) — no injection vector
- [ ] Error responses: Use `AppError` hierarchy, never leak stack traces or internal types
- [ ] HTML truncation: Previews capped at 3000/5000 chars — no unbounded response size
- [ ] No secrets in output: Report contains node IDs/names/HTML only, no tokens or API keys

## Preflight Warnings

- `_SECTION_PATTERNS` in `layout_analyzer.py` is a module-level dict — import it, don't copy
- `ComponentRenderer.load()` reads `COMPONENT_SEEDS` — must call before `render_all()`
- Frozen dataclasses with `list` defaults need `field(default_factory=list)` — use `tuple` for immutable collections (plan already does this)
- No conftest.py in `app/design_sync/tests/` — diagnostic tests must be self-contained
- `_make_e2e_structure()` and `_make_e2e_tokens()` in `test_e2e_pipeline.py` are private helpers, not importable fixtures — copy or re-implement for diagnostic tests
