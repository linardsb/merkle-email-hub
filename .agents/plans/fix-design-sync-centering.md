# Plan: Fix Design Sync Centering — Imported Email Left-Aligned

## Context

When importing a Figma design via the design sync pipeline and clicking "Open in Workspace", the converted email renders left-aligned instead of centered in the preview. The email content has a bounded width (~600px) but sits flush-left in the viewport.

## Root Cause Analysis

The design sync pipeline has this flow:

```
Converter → initial_html (with centering) → Scaffolder → stored html → Maizzle compile → preview
```

### Converter Output IS Centered (`converter_service.py:35-63`)

The `EMAIL_SKELETON` has proper centering:
- `<table ... align="center" ...>` on MSO wrapper (line 54)
- `<table ... style="margin:0 auto;max-width:{container_width}px;width:100%;" ...>` on main table (line 56)

### But the Scaffolder May NOT Preserve Centering

At `import_service.py:238-244`, the converter HTML is passed as `initial_html` to `_call_scaffolder()`. The Scaffolder generates its own HTML using this as context/reference. The Scaffolder's output may lack:
- `align="center"` on the outer wrapper table
- `margin:0 auto` on the main content table
- `width="600"` HTML attribute on the table
- MSO conditional wrapper with centering

### Evidence from Screenshot

The HTML visible in the code editor shows:
```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="max-width: 600px; margin:...">
```

Missing: `align="center"`, `width="600"` attribute — confirms Scaffolder output differs from converter skeleton.

### Template Upload Pipeline Has This Fixed

`app/templates/upload/wrapper_utils.py` has `detect_centering()` + `inject_centering_wrapper()` but this is **only used in template upload** (`template_builder.py`), NOT in the design sync pipeline.

## Research Summary

| File | Lines | Role |
|------|-------|------|
| `app/design_sync/converter_service.py` | 35-63 | `EMAIL_SKELETON` with centering ✅ |
| `app/design_sync/converter_service.py` | 278-285 | `EMAIL_SKELETON.format()` injects `margin:0 auto` ✅ |
| `app/design_sync/import_service.py` | 238-244 | Passes converter HTML to Scaffolder |
| `app/design_sync/import_service.py` | 258-261 | Post-processing: `_fix_orphaned_footer()`, `_sanitize_email_html()` — no centering check |
| `app/templates/upload/wrapper_utils.py` | 21-121 | `inject_centering_wrapper()` — NOT used in design sync |
| `cms/.../workspace/preview-iframe.tsx` | 106-143 | Preview iframe with `mx-auto` container — frontend is fine |
| `cms/.../workspace/page.tsx` | 228-244 | Auto-compile via Maizzle `triggerPreview()` |

## Test Landscape

- 23 test files in `app/design_sync/tests/`
- No conftest.py — inline `_make_*()` factory functions
- `test_penpot_converter.py` verifies `margin:0 auto` + `max-width:600px` on converter output
- `test_e2e_pipeline.py` checks DOCTYPE + MSO conditionals
- **No test verifies centering survives the full pipeline** (converter → scaffolder → stored template)

## Type Check Baseline

- **Pyright:** 169 errors, 137 warnings
- **Mypy:** 1 error in `design_sync/` (`import_service.py:216` unused type-ignore)

## Implementation Steps

### Step 1: Add centering post-processing call to import_service.py

Between step 6.7 (`_sanitize_email_html`) and step 7 (`_create_template`), add at ~line 262:

```python
# 6.8 Ensure centering (Scaffolder output may lack margin:0 auto)
scaffolder_response = self._ensure_centering(scaffolder_response)
```

### Step 2: Implement `_ensure_centering()` static method

**File:** `app/design_sync/import_service.py` — add after `_sanitize_email_html` (~line 669)

**Do NOT reuse `wrapper_utils.inject_centering_wrapper()`** — it wraps in `<div>` (violates email rules) and strips `<html>`/`<body>` attributes. Instead, add centering attributes to the existing outermost `<table>`.

```python
@staticmethod
def _ensure_centering(response: ScaffolderResponse) -> ScaffolderResponse:
    """Add centering to outermost table if missing."""
    from app.ai.agents.scaffolder.schemas import ScaffolderResponse as _SR

    html = response.html
    # Find the first <table in the body (skip MSO conditionals)
    # Check if it already has align="center" or margin:0 auto
    if "margin:0 auto" in html or "margin: 0 auto" in html:
        return response
    if re.search(r'<table[^>]*align="center"', html, re.IGNORECASE):
        return response

    # Add align="center" and margin:0 auto to the first <table after <body
    body_idx = html.find("<body")
    if body_idx < 0:
        body_idx = 0
    search_region = html[body_idx:]

    # Skip MSO conditional tables — find first non-MSO <table
    table_match = re.search(r"<table\b", search_region)
    if not table_match:
        return response

    abs_idx = body_idx + table_match.start()
    tag_end = html.index(">", abs_idx)
    tag = html[abs_idx : tag_end + 1]

    # Add align="center" if missing
    if 'align=' not in tag.lower():
        tag = tag.replace("<table", '<table align="center"', 1)

    # Add margin:0 auto to style
    if "style=" in tag:
        tag = re.sub(
            r'style="',
            'style="margin:0 auto;',
            tag,
            count=1,
        )
    else:
        tag = tag.replace("<table", '<table style="margin:0 auto;"', 1)

    fixed_html = html[:abs_idx] + tag + html[tag_end + 1 :]

    return _SR(
        html=fixed_html,
        qa_results=response.qa_results,
        qa_passed=response.qa_passed,
        model=response.model,
        confidence=response.confidence,
        skills_loaded=response.skills_loaded,
        mso_warnings=response.mso_warnings,
        plan=response.plan,
    )
```

**Key design decisions:**
- Regex-based, not lxml — preserves MSO conditionals and all attributes
- Follows `_fix_orphaned_footer` / `_sanitize_email_html` pattern for `ScaffolderResponse` construction
- Checks both `margin:0 auto` (no spaces) and `margin: 0 auto` (with spaces) for detection
- Adds to existing table instead of wrapping in new element

### Step 3: Add test for centering in full pipeline

**File:** `app/design_sync/tests/test_e2e_pipeline.py`

```python
def test_email_centered(self, pipeline_html: str) -> None:
    """Pipeline output centers the email container."""
    assert "margin:0 auto" in pipeline_html
    assert 'align="center"' in pipeline_html
```

### Step 4: Add tests for `_ensure_centering` method

**File:** `app/design_sync/tests/test_import_service.py`

Use established test pattern (direct `ScaffolderResponse` construction):

```python
class TestEnsureCentering:
    def test_adds_centering_when_missing(self) -> None:
        """Scaffolder output without centering gets attributes injected."""
        html = (
            "<html><body>"
            '<table role="presentation" cellpadding="0" cellspacing="0">'
            "<tr><td>content</td></tr></table>"
            "</body></html>"
        )
        response = ScaffolderResponse(html=html, model="test", confidence=0.9, qa_passed=True)
        result = DesignImportService._ensure_centering(response)
        assert "margin:0 auto" in result.html
        assert 'align="center"' in result.html

    def test_preserves_existing_centering(self) -> None:
        """Already-centered HTML is not double-modified."""
        html = (
            "<html><body>"
            '<table align="center" style="margin:0 auto;max-width:600px;">'
            "<tr><td>content</td></tr></table>"
            "</body></html>"
        )
        response = ScaffolderResponse(html=html, model="test", confidence=0.9, qa_passed=True)
        result = DesignImportService._ensure_centering(response)
        assert result.html == html  # unchanged

    def test_preserves_existing_margin_auto_with_spaces(self) -> None:
        """Detects margin: 0 auto (with spaces) as already centered."""
        html = (
            "<html><body>"
            '<table style="margin: 0 auto; max-width: 600px;">'
            "<tr><td>content</td></tr></table>"
            "</body></html>"
        )
        response = ScaffolderResponse(html=html, model="test", confidence=0.9, qa_passed=True)
        result = DesignImportService._ensure_centering(response)
        assert result.html == html  # unchanged
```

## Files to Create/Modify

| File | Change |
|------|--------|
| `app/design_sync/import_service.py` | Add `_ensure_centering()` static method + call at step 6.8 |
| `app/design_sync/tests/test_import_service.py` | Add `TestEnsureCentering` class (3 tests) |
| `app/design_sync/tests/test_e2e_pipeline.py` | Add centering assertion to pipeline test |

## Preflight Corrections Applied

| # | Original Plan Issue | Correction |
|---|---------------------|------------|
| 1 | Used `wrapper_utils.inject_centering_wrapper()` | Replaced with regex-based approach — `inject_centering_wrapper` uses `<div>` (email rule violation) and strips `<html>`/`<body>` attributes |
| 2 | Used `response._replace()` | `ScaffolderResponse` is Pydantic `BaseModel`, not NamedTuple — use `_SR(html=..., ...)` constructor pattern per `_fix_orphaned_footer` (line 637-646) |
| 3 | Referenced `_make_scaffolder_response()` | Doesn't exist — tests use direct `ScaffolderResponse(html=..., model="test", confidence=0.9, qa_passed=True)` |
| 4 | `detect_centering()` regex order | `_MAX_WIDTH_MARGIN_RE` requires `max-width` before `margin` — converter uses opposite order; replaced with simple string checks |

## Pyright Baseline

- **Target files:** 1 error, 53 warnings (pre-existing)
- New errors above 1 after implementation are regressions

## Security Checklist

- No new endpoints — internal processing only
- No user input involved — HTML is from Scaffolder/converter output
- `wrapper_utils.inject_centering_wrapper` uses hardcoded template, no injection risk

## Verification

- [ ] `make check` passes
- [ ] Pyright errors ≤ 169 (baseline)
- [ ] `pytest app/design_sync/tests/test_import_service.py -x` passes
- [ ] `pytest app/design_sync/tests/test_e2e_pipeline.py -x` passes
- [ ] Manual: import Figma design → "Open in Workspace" → email is centered
