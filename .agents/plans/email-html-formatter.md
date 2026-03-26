# Plan: Email-Safe HTML Formatter

## Context

The design sync converter generates structurally correct but poorly formatted HTML. The `EMAIL_SKELETON` template has zero indentation, `node_to_email_html()` uses a manual `pad = "  " * indent` approach that produces inconsistent nesting, and the two are concatenated with `.format()` — resulting in messy, hard-to-read output. The goal is clean 2-space indented HTML (matching freeformatter.com output) via a **post-processing formatter** that runs after HTML assembly.

## Research Summary

### HTML Assembly Pipeline

| Step | File:Line | What | Returns |
|------|-----------|------|---------|
| 1 | `converter_service.py:222` | `node_to_email_html(frame, indent=1, ...)` per frame | `str` (joined lines) |
| 2 | `converter_service.py:234` | Wrap in `<tr data-section-id><td>...\n{html}\n</td></tr>` | `str` |
| 3 | `converter_service.py:248` | `"\n".join(section_parts)` | `str` |
| 4 | `converter_service.py:278` | `EMAIL_SKELETON.format(style_block=..., sections=...)` | `str` — **formatter hooks here** |
| 5 | `converter_service.py:293` | `ConversionResult(html=result_html, ...)` | `ConversionResult` |

### HTML Patterns to Handle

| Pattern | Source | Example |
|---------|--------|---------|
| Block elements | converter.py | `<table>`, `<tr>`, `<td>`, `<div>`, `<noscript>` |
| Inline leaf elements | `_render_semantic_text` | `<h1>text</h1>`, `<p>text</p>`, `<a>text</a>` |
| Void elements | converter.py:599 | `<img ... />`, `<meta ...>` |
| MSO ghost table (open+close in one comment) | `_render_multi_column_row:1153-1159` | `<!--[if mso]><table ...><tr><![endif]-->` |
| MSO column markers | `_render_multi_column_row:1168` | `<!--[if mso]><td width="68" valign="top"><![endif]-->` |
| MSO wrapper (multi-line) | `EMAIL_SKELETON:43-48,53-55,59-61` | `<!--[if mso]>\n<noscript><xml>...\n<![endif]-->` |
| VML elements | `_render_button:435-453` | `<v:roundrect>`, `<v:textbox>`, `<center>` |
| Style block | `converter_service.py:256-272` | `<style>\n  body { ... }\n  @media ... { }\n</style>` |
| Spacer rows | `converter_service.py:242` | `<tr><td style="height:12px;...">…</td></tr>` |
| Multi-line `<p>` | `_render_semantic_text:320` | `<td>\n<p>Line 1</p>\n<p>Line 2</p>\n</td>` |

### Critical MSO Comment Variants

The converter produces **two distinct MSO comment patterns** that the formatter must distinguish:

1. **Self-contained** (open+close in one token): `<!--[if mso]><td width="68" valign="top"><![endif]-->`
   - Must NOT increase indent — it's a single-line marker
   - Produced by `_render_multi_column_row` for column open/close/spacer

2. **Multi-line block** (open on one line, close on another):
   ```
   <!--[if mso]>
   <table ...><tr><td>
   <![endif]-->
   ```
   - Must increase indent after `<!--[if mso]>`, decrease on `<![endif]-->`
   - Produced by `EMAIL_SKELETON` for outer wrapper

### Files to Modify

| File | Change |
|------|--------|
| `app/design_sync/html_formatter.py` | **Rewrite** — full formatter implementation |
| `app/design_sync/converter_service.py:278-285` | **1-line edit** — call `format_email_html()` on `result_html` |
| `app/design_sync/tests/test_html_formatter.py` | **New** — formatter unit tests |

### Files NOT to Modify

- `converter.py` — fragment generators stay as-is; the `indent` param becomes irrelevant but removing it would break callers
- `import_service.py` — receives already-formatted HTML from `ConversionResult`
- Existing test files — all use `assert "X" in html` (substring), not exact match; formatting changes don't break them

## Test Landscape

- **596 existing design_sync tests** — all pass
- **Assertion pattern**: `assert "substring" in html` (whitespace-insensitive) — **safe** across formatting changes
- **1 exact equality test**: `test_import_service.py:457` — tests `_fill_image_urls()`, not converter output — **safe**
- **Tag balance checker**: `_check_html_balance()` in `test_e2e_pipeline.py` — strips MSO comments, validates tag pairs — **safe**
- **No snapshot/golden file tests** — no fragile comparison baseline to update
- **Factory functions**: `DesignNode(id=, name=, type=, children=[...])`, `ExtractedTokens(colors=, typography=, ...)`, `DesignFileStructure(file_name=, pages=[...])`

## Type Check Baseline

| Tool | Scope | Errors | Notes |
|------|-------|--------|-------|
| Pyright | `app/design_sync/` | 170 errors, 137 warnings | Pre-existing |
| Mypy | `app/design_sync/` | 1 error (unused type:ignore) | Pre-existing |
| Pyright | `html_formatter.py` | 0 errors | Draft file clean |

## Design Decisions

### D1: Post-processing, not generation-time fix

Changing how `node_to_email_html()` and its 5+ helpers generate indentation would touch 300+ lines across recursive call chains. A post-processing formatter is a single function applied once at the end — simpler, more maintainable, and catches all code paths.

### D2: Regex tokenizer, not HTMLParser/BeautifulSoup

- `html.parser.HTMLParser` chokes on MSO conditional comments and VML namespace elements
- BeautifulSoup modifies HTML structure (adds closing tags, normalizes attributes)
- A regex tokenizer splitting on `<...>` / `<!--...-->` boundaries handles all email patterns faithfully

### D3: Inline-leaf accumulation for content elements

`<h3 style="...">text</h3>` must stay on one line. The formatter accumulates tokens between inline-leaf open/close tags and emits them as a single line. This handles both simple (`<p>text</p>`) and nested (`<a href="#"><span>text</span></a>`) cases.

### D4: Self-contained MSO comments as opaque single-line tokens

Comments like `<!--[if mso]><td width="68" valign="top"><![endif]-->` are a single regex token. They get indented as-is with no indent change — they're structural markers, not block openers.

### D5: `<style>` block preserved with re-indented lines

Style content is re-indented at `level + 1` but internal structure (selectors, media queries, braces) is preserved line-by-line. No CSS parsing.

## Implementation Steps

### Step 1: Rewrite `html_formatter.py`

The draft has these issues to fix:

**Bug 1: Self-contained MSO detection**
Line 122 has an operator precedence bug: `"<![endif]-->" in stripped or "endif" in stripped.lower() and stripped.endswith("-->")` — the `or`/`and` bind incorrectly. Fix: check if token contains both `<!--[if` and `<![endif]-->`.

**Bug 2: `_vml_lower()` returns `_VML_BLOCK_TAGS` as-is**
The set has lowercase names but the constant name implies a transformation. Replace with direct set usage and ensure case-insensitive comparison.

**Bug 3: Multi-line MSO comments**
The `EMAIL_SKELETON` has MSO blocks like:
```
<!--[if mso]>
<noscript><xml>
<o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml></noscript>
<![endif]-->
```
The tokenizer splits `<!--[if mso]>\n<noscript><xml>` into separate tokens. The `<!--[if mso]>` part (without `<![endif]-->`) correctly triggers indent. But `<noscript>` and `<xml>` are block tags that would double-indent. Inside MSO blocks, we should still indent block tags normally — this matches the freeformatter output.

**Bug 4: `&nbsp;` entity in spacer rows**
Text tokens like `&nbsp;` between `<td>` and `</td>` should stay on the same line as the `<td>` when the content is trivial. Current code would put it on its own line.

**Improvement 1: Handle `<td>` with single inline child on one line**
When a `<td>` contains only a single inline element + text (like `<td><h3>text</h3></td>`), collapse to one line. This matches the freeformatter output pattern:
```html
<td>
  <h3 style="...">text</h3>
</td>
```
Not collapsed — `<td>` is block, `<h3>` is its own indented line inside.

**Improvement 2: Trim trailing whitespace on all lines**

### Rewritten algorithm (pseudocode):

```
tokenize(html) → list of (tag | comment | text) tokens
level = 0
for each token:
  if in_style_block:
    re-indent style lines at level+1; close on </style>
  elif in_inline_leaf:
    accumulate; close when matching closing tag found
  elif self_contained_mso_comment (has both <!--[if and endif]-->):
    emit at current level, no indent change
  elif mso_block_open (<!--[if mso]> without endif):
    emit at current level, level += 1
  elif mso_block_close (<![endif]-->):
    level -= 1, emit at current level
  elif closing_block_tag:
    level -= 1, emit at current level
  elif opening_block_tag:
    emit at current level, level += 1
  elif void_tag or self_closing:
    emit at current level
  elif inline_leaf_open:
    start accumulating
  else:
    emit at current level (text or unknown tag)
```

### Step 2: Hook into `converter_service.py`

At `converter_service.py:285`, after `EMAIL_SKELETON.format()`:

```python
from app.design_sync.html_formatter import format_email_html

# Line 285, after result_html = EMAIL_SKELETON.format(...)
result_html = format_email_html(result_html)
```

Single import + single line change.

### Step 3: Write tests in `test_html_formatter.py`

Test categories:

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_basic_document_structure` | DOCTYPE + html + head + body at correct levels |
| 2 | `test_block_element_indentation` | `<table>/<tr>/<td>` nest at increasing indent levels |
| 3 | `test_inline_leaf_single_line` | `<h3 style="...">text</h3>` stays on one line |
| 4 | `test_paragraph_single_line` | `<p style="...">text</p>` stays on one line |
| 5 | `test_anchor_single_line` | `<a href="..." style="...">CTA</a>` stays on one line |
| 6 | `test_void_elements` | `<img .../>` and `<meta ...>` at correct indent, no children |
| 7 | `test_style_block_preserved` | `<style>` content re-indented but rules intact |
| 8 | `test_mso_self_contained` | `<!--[if mso]><td ...><![endif]-->` no indent change |
| 9 | `test_mso_multi_line_block` | `<!--[if mso]>\n...\n<![endif]-->` indents inner content |
| 10 | `test_mso_wrapper_skeleton` | Full EMAIL_SKELETON MSO wrapper formatted correctly |
| 11 | `test_vml_roundrect` | `<v:roundrect>/<v:textbox>/<center>` indented as blocks |
| 12 | `test_multi_column_ghost_table` | Full multi-column pattern from `_render_multi_column_row` |
| 13 | `test_spacer_row` | `<tr><td style="height:12px;...">…</td></tr>` formatted |
| 14 | `test_empty_td` | `<td></td>` stays on one line or splits cleanly |
| 15 | `test_full_email_round_trip` | Build a mini email via `DesignConverterService.convert()`, verify formatted output has consistent 2-space indent |
| 16 | `test_existing_tests_unaffected` | Run `_check_html_balance()` on formatted output — no regressions |
| 17 | `test_nbsp_in_spacer` | `&nbsp;` text doesn't float as standalone line |
| 18 | `test_idempotent` | `format_email_html(format_email_html(html)) == format_email_html(html)` |
| 19 | `test_empty_input` | Empty string returns empty string |
| 20 | `test_indent_size_param` | `indent_size=4` produces 4-space indentation |

### Step 4: Validate against user's expected output

Use the exact "freeformatter formatted" HTML the user provided as a golden reference. Write one test that:
1. Takes the raw converter output (first HTML sample from user)
2. Runs `format_email_html()` on it
3. Compares structural indentation against the formatted version (second HTML sample)
4. Validates key patterns: each `<table>` indented 2 deeper than parent `<td>`, each `<tr>` indented 2 deeper than `<table>`, inline content on same line as tag

### Step 5: Run full test suite

```bash
make test                    # All backend tests (includes 596 design_sync tests)
make types                   # pyright + mypy
make lint                    # ruff format + lint
```

## Edge Cases & Risks

| Risk | Mitigation |
|------|------------|
| Existing 596 tests break | All use `assert "X" in html` (substring match) — whitespace changes don't affect this |
| MSO comments parsed incorrectly | Dedicated self-contained vs multi-line detection; tokenizer captures full `<!--...-->` blocks |
| VML namespace tags ignored | Explicit `_VML_BLOCK_TAGS` set with `v:` and `o:` prefixes |
| `<style>` CSS mangled | Style block content preserved line-by-line, only re-indented |
| Inline leaf with nested tags | Accumulator tracks depth; only closes when matching depth returns to 0 |
| Performance on large emails | Linear tokenizer + single pass — O(n) on HTML length; email HTML is ~50-200KB max |
| `&nbsp;` or entity text between tags | Treated as text token, indented at current level (acceptable) |

## Security Checklist

No new endpoints, no user input, no database access. The formatter is a pure function (`str → str`) called internally. No security surface.

## Verification

- [ ] `make test` passes — all 596+ design_sync tests green
- [ ] `make types` — pyright errors ≤ 170, mypy errors ≤ 1
- [ ] `make lint` — no new ruff violations
- [ ] New `test_html_formatter.py` tests all pass (20 tests)
- [ ] Formatted output matches freeformatter.com 2-space style on user's sample email
- [ ] `format_email_html()` is idempotent
- [ ] MSO conditionals, VML blocks, inline content all formatted correctly
