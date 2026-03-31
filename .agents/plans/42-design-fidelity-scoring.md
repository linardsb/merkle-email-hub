# Plan: Design Fidelity Scoring — Figma→HTML Traceability for Judges

## Context

Judges currently evaluate agent HTML output **in isolation** — they see `input_data` (brief/source HTML) and `output_data` (generated HTML) but have **zero Figma context**: no design URL, no node ID, no extracted design tokens (colors, typography, spacing). This means judges cannot answer "does this HTML faithfully reproduce the Figma design?" — only "does this HTML follow email best practices?".

Phase 40.1 built **snapshot regression** for the converter (deterministic HTML diff), not for judge evaluation. The training HTMLs in `for_converter_engine/` document component→Figma mappings in markdown but are not wired into eval infrastructure.

**Goal:** Thread Figma design metadata through the pipeline so judges can score **design fidelity** — how well built HTML matches the source Figma intent.

## Research Summary

### Current Data Flow (no Figma context reaches judges)

```
Figma API → DocumentSource(provider, file_ref) → DB only
                                                    ↓ (never forwarded)
Converter → ConversionResult(html, match_confidences) → Agent → JudgeInput(input_data, output_data)
                                                                   ↑ no figma_url, node_id, design_tokens
```

### Key Files

| File | Role | Gap |
|------|------|-----|
| `app/ai/agents/evals/judges/schemas.py:13` | `JudgeInput` — judge input schema | No design metadata fields |
| `app/ai/agents/evals/judges/base.py:18` | `Judge` Protocol + prompt template | No design context in prompt |
| `app/ai/agents/evals/judge_runner.py:59` | `trace_to_judge_input()` — trace→judge | Drops all design metadata |
| `app/design_sync/converter_service.py:131` | `ConversionResult` — converter output | No `figma_url`, `node_id`, `design_tokens` |
| `app/design_sync/email_design_document.py:62` | `DocumentSource` — origin metadata | Has `provider` + `file_ref` but unused downstream |
| `app/design_sync/figma/service.py` | Figma API, `extract_file_key()` | Tokens extracted but not forwarded to eval |
| `email-templates/training_HTML/for_converter_engine/` | 3 real campaign HTMLs + CONVERTER-REFERENCE.md | Manual docs only, not machine-readable metadata |

### Training HTML Inventory

| File | Brand | Sections | Figma Node |
|------|-------|----------|-----------|
| `starbucks-pumpkin-spice.html` | Starbucks | 9 | `2833-1424` |
| `mammut-duvet-day.html` | Mammut | 18 | `2833-1135` |
| `maap-kask.html` | MAAP | 13 | `2833-1623` |

All three reference Figma file `VUlWjZGAEVZr3mK1EawsYR`. CONVERTER-REFERENCE.md maps each section to source component + slot fills + style overrides + design reasoning — structured tables that can be parsed programmatically.

### Trace Schema (current)

Keys: `id`, `agent`, `expected_challenges`, `elapsed_seconds`, `error`, `timestamp`, `dimensions`, `input`, `output`

No `figma_url`, `node_id`, `design_tokens`, or `section_mapping` fields.

## Test Landscape

| Area | Files | Fixtures |
|------|-------|----------|
| Judge tests | `app/ai/agents/evals/tests/test_judge_criteria_map.py`, `test_golden_references.py` | `JUDGE_REGISTRY`, 14 golden refs in `index.yaml` |
| Snapshot regression | `app/design_sync/tests/test_snapshot_regression.py` | `data/debug/manifest.yaml`, `make_design_node()`, `make_file_structure()` |
| Golden conformance | `app/design_sync/tests/test_golden_conformance.py` | 97+ component seeds, component manifest |
| Figma fixtures | `app/design_sync/figma/tests/test_parse_real_fixtures.py` | 5 fixtures: mammut_hero, ecommerce_grid, newsletter_2col, transactional, navigation_header |
| Mock traces | `app/ai/agents/evals/mock_traces.py` | `generate_mock_trace()`, `generate_mock_verdict()` |
| Baseline metrics | `traces/baseline.json` | 45 criteria pass rates, 123 traces |

No `conftest.py` in `app/ai/agents/evals/tests/` — opportunity to add shared judge fixtures.

## Type Check Baseline

| Directory | Pyright Errors | Mypy Errors |
|-----------|---------------|-------------|
| `app/ai/agents/evals/` | 0 | 0 |
| `app/design_sync/` | 226 (test warnings) | 0 |

## Implementation Steps

### Step 1: Extend `JudgeInput` with Design Metadata

**File:** `app/ai/agents/evals/judges/schemas.py:13`

Add optional design context fields to `JudgeInput`:

```python
class DesignContext(BaseModel):
    """Figma/Penpot design source metadata for fidelity scoring."""
    figma_url: str | None = None
    node_id: str | None = None
    file_id: str | None = None
    design_tokens: DesignTokenSummary | None = None
    section_mapping: list[SectionDesignMapping] = Field(default_factory=list)

class DesignTokenSummary(BaseModel):
    """Extracted design tokens from Figma for judge comparison."""
    colors: dict[str, str] = Field(default_factory=dict)        # role → hex
    fonts: dict[str, str] = Field(default_factory=dict)          # role → font family
    font_sizes: dict[str, str] = Field(default_factory=dict)     # role → size
    spacing: dict[str, str] = Field(default_factory=dict)        # role → px value

class SectionDesignMapping(BaseModel):
    """Maps a built HTML section back to its Figma frame + source component."""
    section_index: int
    component_slug: str
    figma_frame_name: str | None = None
    slot_fills: dict[str, str] = Field(default_factory=dict)
    style_overrides: dict[str, str] = Field(default_factory=dict)

class JudgeInput(BaseModel):
    trace_id: str
    agent: str
    input_data: dict[str, object]
    output_data: dict[str, object] | None
    expected_challenges: list[str]
    design_context: DesignContext | None = None  # NEW — backward-compatible
```

**Tests:** Update `test_judge_criteria_map.py` — verify `JudgeInput` accepts `design_context=None` (backward compat) and `design_context=DesignContext(...)`.

### Step 2: Extend Trace Schema

**File:** `app/ai/agents/evals/judge_runner.py:59`

Update `trace_to_judge_input()` to forward design metadata when present in traces:

```python
def trace_to_judge_input(trace: dict[str, Any]) -> JudgeInput:
    design_raw = trace.get("design_context")
    design_context = DesignContext(**design_raw) if design_raw else None
    return JudgeInput(
        trace_id=trace["id"],
        agent=trace["agent"],
        input_data=trace["input"],
        output_data=trace["output"],
        expected_challenges=trace.get("expected_challenges", []),
        design_context=design_context,
    )
```

**Trace enrichment:** Update `runner.py` to inject `design_context` into traces when the synthetic test case provides it (scaffolder cases that reference Figma designs).

### Step 3: Extend `ConversionResult` with Figma Metadata

**File:** `app/design_sync/converter_service.py:131`

```python
@dataclass(frozen=True)
class ConversionResult:
    html: str
    sections_count: int
    warnings: list[str] = field(default_factory=list)
    layout: DesignLayoutDescription | None = None
    compatibility_hints: list[CompatibilityHint] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    cache_hit_rate: float | None = None
    quality_warnings: list[QualityWarning] = field(default_factory=list)
    match_confidences: dict[int, float] = field(default_factory=dict)
    figma_url: str | None = None           # NEW
    node_id: str | None = None             # NEW
    design_tokens_used: dict[str, Any] | None = None  # NEW — tokens applied during conversion
```

Thread `DocumentSource.file_ref` through the converter pipeline so it lands on `ConversionResult`.

### Step 4: Add Design Fidelity Criterion to Scaffolder Judge

**File:** `app/ai/agents/evals/judges/scaffolder.py`

Add a 6th criterion (or replace the least discriminative one based on `traces/baseline.json` pass rates):

```python
JudgeCriteria(
    name="design_fidelity",
    description=(
        "When design context is provided: Does the HTML faithfully reproduce "
        "the Figma design's color palette, typography, spacing, and section "
        "structure? Compare extracted design tokens against actual inline styles. "
        "When no design context is provided: auto-pass this criterion."
    ),
)
```

Update `build_prompt()` to conditionally include a design context section:

```python
def build_prompt(self, judge_input: JudgeInput) -> str:
    # ... existing prompt building ...
    if judge_input.design_context and judge_input.design_context.design_tokens:
        prompt += format_design_context_section(judge_input.design_context)
    return prompt
```

### Step 5: Create `format_design_context_section()` Helper

**File:** `app/ai/agents/evals/judges/base.py` (alongside existing `format_golden_section`)

```python
def format_design_context_section(ctx: DesignContext) -> str:
    """Build design fidelity prompt section from Figma metadata."""
    lines = ["\n## DESIGN REFERENCE (from Figma)\n"]
    if ctx.figma_url:
        lines.append(f"Source: {ctx.figma_url}")
    if ctx.design_tokens:
        lines.append("\n### Expected Design Tokens")
        if ctx.design_tokens.colors:
            lines.append("Colors: " + ", ".join(f"{k}={v}" for k, v in ctx.design_tokens.colors.items()))
        if ctx.design_tokens.fonts:
            lines.append("Fonts: " + ", ".join(f"{k}={v}" for k, v in ctx.design_tokens.fonts.items()))
    if ctx.section_mapping:
        lines.append("\n### Section-to-Component Mapping")
        for m in ctx.section_mapping:
            lines.append(f"  Section {m.section_index}: {m.component_slug} (frame: {m.figma_frame_name})")
    return "\n".join(lines)
```

Token budget: cap at 1500 chars (~375 tokens) to stay within `_GOLDEN_TOKEN_BUDGET`.

### Step 6: Create Training-Data-Backed Synthetic Cases

**File:** `app/ai/agents/evals/synthetic_data_scaffolder.py` (extend existing 12 cases)

Parse CONVERTER-REFERENCE.md programmatically to create 3 synthetic test cases with full `design_context`:

```python
# Case: Starbucks Pumpkin Spice — 9-section email with full Figma metadata
{
    "brief": "Starbucks seasonal campaign email with hero image, heading, body copy, two CTAs, product grid, and footer",
    "design_context": {
        "figma_url": "https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/...?node-id=2833-1424",
        "node_id": "2833-1424",
        "file_id": "VUlWjZGAEVZr3mK1EawsYR",
        "design_tokens": {
            "colors": {"background": "#F2F0EB", "primary": "#1e3932", "accent": "#00754A", "cta": "#00754A"},
            "fonts": {"heading": "SoDo Sans", "body": "SoDo Sans"},
            "font_sizes": {"heading": "40px", "body": "16px", "cta": "16px"},
        },
        "section_mapping": [
            {"section_index": 0, "component_slug": "full-width-image", "figma_frame_name": "Hero Image"},
            {"section_index": 1, "component_slug": "heading", "figma_frame_name": "Heading"},
            # ... remaining 7 sections from CONVERTER-REFERENCE.md
        ],
    },
    "expected_challenges": ["color_fidelity", "font_override", "section_mapping"],
}
```

Use the **real training HTML** from `for_converter_engine/` as expected output for these cases. Do NOT fabricate synthetic HTML.

### Step 7: Extend Judge Criteria Map

**File:** `app/ai/agents/evals/judge_criteria_map.py`

Add `design_fidelity` criterion mapping for scaffolder (and later for other agents that receive design context):

```python
"design_fidelity": CriteriaMapping(
    judge_criterion="design_fidelity",
    qa_checks=[],  # No QA check equivalent — LLM-only evaluation
    description="Figma design token fidelity (colors, fonts, spacing, section structure)",
),
```

### Step 8: Wire `DocumentSource` Through Converter Pipeline

**File:** `app/design_sync/service.py`

When `DesignSyncService` calls the converter, pass the `DocumentSource` metadata so it can be attached to `ConversionResult`:

```python
# In convert_design_to_email() or equivalent
result = converter.convert(document, ...)
return ConversionResult(
    html=result.html,
    # ... existing fields ...
    figma_url=f"https://www.figma.com/design/{source.file_ref}" if source.provider == "figma" else None,
    node_id=source.file_ref.split("node-id=")[-1] if "node-id" in (source.file_ref or "") else None,
    design_tokens_used=extracted_tokens.to_dict() if extracted_tokens else None,
)
```

### Step 9: Update Eval Runner to Propagate Design Context into Traces

**File:** `app/ai/agents/evals/runner.py`

When generating traces from synthetic data, include `design_context` if the test case provides it:

```python
trace = {
    "id": trace_id,
    "agent": agent,
    "input": case["input"] if isinstance(case.get("input"), dict) else {"brief": case.get("brief", "")},
    "output": output,
    "design_context": case.get("design_context"),  # NEW — forwarded to judge
    # ... existing fields
}
```

### Step 10: Tests

| Test | File | What |
|------|------|------|
| JudgeInput backward compat | `evals/tests/test_judge_schemas.py` (new) | `JudgeInput(design_context=None)` works; `JudgeInput(design_context=DesignContext(...))` works |
| DesignContext validation | same | Token summary accepts partial data; section mapping validates indices |
| Scaffolder judge with design context | `evals/tests/test_scaffolder_judge.py` (new or extend) | `build_prompt()` includes design tokens when provided, omits when `None` |
| format_design_context_section | `evals/tests/test_base_judge.py` (extend) | Output under 1500 chars; handles empty tokens; handles empty section_mapping |
| trace_to_judge_input with design_context | `evals/tests/test_judge_runner.py` (new or extend) | Trace with `design_context` key → `JudgeInput.design_context` populated |
| ConversionResult new fields | `design_sync/tests/test_converter_service.py` (extend) | Backward compat: `figma_url=None` default; new fields accepted |
| Training HTML cases | `evals/tests/test_design_fidelity.py` (new) | 3 cases load real training HTML, build DesignContext from CONVERTER-REFERENCE.md |

## What's Already Done vs. What's New

| Capability | Status | Notes |
|-----------|--------|-------|
| Snapshot regression (converter HTML diff) | **Done** (40.1) | `test_snapshot_regression.py`, 3 golden cases |
| Training HTML with Figma links | **Done** (40.1) | 3 files + CONVERTER-REFERENCE.md |
| Judge scoring (45 criteria, 9 agents) | **Done** (37.3) | But no design fidelity criterion |
| Golden references in judge prompts | **Done** (37.3) | `format_golden_section()` helper |
| Figma metadata in `JudgeInput` | **NEW** | Step 1 |
| Design tokens in judge prompts | **NEW** | Steps 4-5 |
| ConversionResult with Figma URL | **NEW** | Step 3 |
| Design fidelity criterion | **NEW** | Steps 4, 7 |
| Training-HTML-backed eval cases | **NEW** | Step 6 |
| Trace schema with design_context | **NEW** | Steps 2, 9 |

## Rollout Strategy

**Phase A (schema + plumbing, no behavior change):** Steps 1-3, 7-9 — all backward-compatible, `design_context=None` is default. Existing judges and traces unaffected.

**Phase B (scaffolder judge, one agent):** Steps 4-6 — add design fidelity criterion to scaffolder only. Validate with 3 training HTML cases. Measure flip rate vs. baseline.

**Phase C (remaining agents):** Extend to dark_mode, accessibility, personalisation judges. Each gets a design-fidelity criterion relevant to their domain (dark mode: "do dark-mode overrides preserve design intent?"; accessibility: "are design-specified alt texts preserved?").

## Preflight Warnings

- `JudgeInput` is a Pydantic model — adding optional field is backward-compatible but any code doing `**judge_input.model_dump()` will now include `design_context`
- `ConversionResult` is `frozen=True` — adding fields with defaults is safe
- `traces/baseline.json` will need re-baselining after adding 6th criterion to scaffolder
- Training HTML files contain brand-specific values (Starbucks green `#1e3932`, etc.) — synthetic cases must treat these as examples, not hard-coded expectations

## Security Checklist

- [ ] No new endpoints (schema-only changes)
- [ ] `DesignContext.figma_url` is logged but never rendered in frontend HTML (no XSS risk)
- [ ] `design_tokens` dict values are treated as opaque strings — no `eval()` or template injection
- [ ] Path traversal: `CONVERTER-REFERENCE.md` parser must not accept arbitrary file paths

## Verification

- [ ] `make check` passes
- [ ] `make eval-golden` passes (backward compat — no design_context in golden cases)
- [ ] Pyright errors ≤ baseline (evals: 0, design_sync: 226)
- [ ] New test: scaffolder judge with design_context scores design_fidelity criterion
- [ ] New test: trace round-trip preserves design_context through JSONL serialize/deserialize
- [ ] `make eval-check` — re-baseline after scaffolder gets 6th criterion
