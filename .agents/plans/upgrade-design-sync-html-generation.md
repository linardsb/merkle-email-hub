# Upgrade Design Sync Converter — Hybrid Email HTML Generation

**Supersedes:** `fix-div-p-tag-contamination.md` (which assumed "never use div/p" — research shows that's wrong)

## Research Summary

Online research across caniemail.com, Email on Acid, Litmus, Email Markup Consortium, and industry guides (2025-2026) found:

- **`<div>` has 100% email client support** as an element (caniemail.com). The issue isn't the tag — it's CSS layout properties ON divs (width, flex, float) that Classic Outlook's Word engine ignores.
- **`<p>` inside `<td>` is safe and recommended** for accessibility. Screen readers navigate by paragraphs/headings. Stripping `<p>` into `content<br><br>` (what we do now) destroys semantic structure.
- **Nesting div/p inside table cells does NOT break table layout** in any email client. The table grid holds firm — only CSS on nested elements behaves inconsistently.
- **Classic Outlook (Word engine) dies October 2026.** New Outlook uses Chromium. Enterprise migration April 2026. Market share already ~5% and falling.
- **The industry standard is hybrid/ghost table coding:** divs for modern clients (90%+), MSO conditional tables for Classic Outlook only.
- **Padding on `<td>` is the only universal CSS combo.** Margin on `<p>` works with inline resets. Padding on `<div>`/`<p>` breaks in Classic Outlook.

## Current State Assessment

### What the converter does well
1. `node_to_email_html()` correctly maps FRAME/GROUP → `<table>`, TEXT → `<td>`, IMAGE → `<img>` (converter.py:21-27)
2. `_group_into_rows()` correctly groups sibling nodes into `<tr>` rows by y-position (converter.py:370-422)
3. `EMAIL_SKELETON` already uses ghost table pattern with MSO conditional wrapper (converter_service.py:26-52)
4. Props extraction handles padding, font, bg color correctly (converter_service.py:183-213)
5. Color → BrandPalette conversion with WCAG contrast checking is solid (converter.py:84-142)

### What needs improvement (NOT overengineering — direct issues)

1. **`sanitize_web_tags_for_email()` is too aggressive** — strips ALL `<p>` and `<div>`, destroying accessibility semantics. Should preserve `<p>` inside `<td>` and simple `<div>` wrappers.

2. **TEXT nodes map to bare `<td>` with escaped text** — no semantic wrapping. Multi-paragraph text becomes a single `<td>` blob. Should use `<p>` tags inside `<td>` for accessibility.

3. **VECTOR nodes map to `<div>`** — should be skipped entirely (they're already warned about and not email-safe). The current code returns empty string for vectors anyway (converter.py:333-334), so the mapping at line 26 is dead code.

4. **Assembler social links `<div>` bug** — generates `<div>` after sanitization runs (assembler.py:324). Still a real bug.

5. **Scaffolder prompt says "NEVER use `<p>`"** — contradicts accessibility best practice. Should say "use `<p>` for text content inside `<td>`, always with margin:0 reset."

## Is This Overengineering?

**No.** Here's the cost/benefit for each change:

| Change | Lines of code | Impact |
|--------|--------------|--------|
| Fix `sanitize_web_tags_for_email` to preserve `<p>` inside `<td>` | ~15 lines | Accessibility improvement for ALL design imports |
| Fix assembler social links div | 1 line | Fixes a real rendering bug |
| Update scaffolder prompt | 4 lines | Better LLM output, fewer post-processing fixes needed |
| Remove dead VECTOR→div mapping | 1 line | Code cleanup |
| Update CLAUDE.md/memory with nuanced rule | Already done partially | Prevents future sessions from stripping valid tags |

What WOULD be overengineering:
- ~~Adding a full ghost table generator for multi-column layouts~~ — the scaffolder already handles this via prompt + skills
- ~~Creating separate sanitization profiles per email client~~ — the rendering emulators already handle this
- ~~Building a CSS-property-aware div scanner~~ — the QA engine's css_support check already flags unsupported properties
- ~~Adding a config flag for post-October-2026 table-free mode~~ — premature until Classic Outlook is actually dead

## Implementation Plan

### Phase A: Fix the sanitizer (core change)

**File:** `app/design_sync/converter.py` — `sanitize_web_tags_for_email()`

Current behavior:
```python
# Strips ALL <p> → content<br><br>
# Strips ALL <div> → unwraps content
```

New behavior:
```python
# 1. Stash MSO conditionals (unchanged)
# 2. <p> inside <td>: PRESERVE with margin reset
#    <p> outside <td>: strip → content<br><br> (unchanged)
# 3. <div> with layout CSS (width/max-width/display:flex/display:inline-block/float):
#    convert → <table role="presentation"><tr><td style="...">content</td></tr></table>
#    <div> simple wrapper inside <td> (text-align, etc.): PRESERVE
#    <div> outside <td> with no layout CSS: unwrap (unchanged)
# 4. Restore MSO blocks (unchanged)
```

Implementation detail:
- Parse with regex (consistent with existing approach, not introducing new dependencies)
- For `<p>` preservation: check if the `<p>` appears between `<td...>` and `</td>` — if yes, add `style="margin:0 0 10px 0;"` inline reset if no margin already set
- For `<div>` classification: check style attribute for layout properties (`width`, `max-width`, `display:inline-block`, `display:flex`, `float`). If present → convert to table. If absent → preserve as-is when inside `<td>`, unwrap when not.
- Edge case: `<div>` with `text-align:center` inside `<td>` — this is a content wrapper, preserve it

**Tests to update:** `app/design_sync/tests/test_penpot_converter.py` — existing tests for `sanitize_web_tags_for_email` need updating for new behavior

### Phase B: Fix known bugs

**B.1: Assembler social links** (`app/ai/agents/scaffolder/assembler.py:324`)
```python
# Before:
social_html = '<div style="text-align:center;padding:16px 0;">' + "".join(parts) + "</div>"

# After:
social_html = (
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
    '<tr><td style="text-align:center;padding:16px 0;">'
    + "".join(parts)
    + "</td></tr></table>"
)
```

**B.2: Remove dead VECTOR→div mapping** (`app/design_sync/converter.py:26`)
```python
# Before:
DesignNodeType.VECTOR: "div",

# After: remove the line entirely (vectors return "" at line 333-334 anyway)
```

### Phase C: Update scaffolder prompt

**File:** `app/ai/agents/scaffolder/prompt.py:98-108`

Replace:
```
- NEVER use `<p>` tags anywhere — use `<td>` with inline styles for ALL text content
- NEVER use `<div>` tags for layout — only for `role="article"` wrapper and MSO hybrid columns
- Every section: `<table>` > `<tr>` > `<td>` > content (text directly in `<td>`, no `<p>` wrapper)
```

With:
```
- Use `<p style="margin:0 0 10px 0;">` for text content inside `<td>` cells (accessibility — screen readers navigate by paragraphs)
- Use `<h1>`-`<h6>` with inline styles for headings inside `<td>` cells (screen readers scan by headings)
- NEVER use `<div>` or `<p>` for LAYOUT — no width, max-width, display:flex, float on div/p
- `<div>` allowed ONLY for: `role="article"` wrapper, MSO hybrid columns (inside conditionals), simple text-align wrappers inside `<td>`
- Multi-column layout: `<table>` with ghost table MSO pattern — NEVER div-based columns
- Every section structure: `<table>` > `<tr>` > `<td>` > semantic content (`<p>`, `<h1>`-`<h6>`, `<a>`, `<img>`)
- Spacing: padding on `<td>` only (universal). margin:0 reset on every `<p>` and heading.
```

### Phase D: Update CLAUDE.md + memory

**File:** `CLAUDE.md` — update the "HTML Email Structure Rules" section (already partially added)

Replace current rule with nuanced version:
```markdown
## HTML Email Structure Rules

- **Layout:** `<table>/<tr>/<td>` for ALL structural layout. Never use div/p for layout (width, flex, float, columns).
- **Text content:** Use `<p style="margin:0 0 10px 0;">` inside `<td>` cells. Better for accessibility than bare text.
- **Headings:** Use `<h1>`-`<h6>` with inline styles inside `<td>` cells. Screen readers scan by headings.
- **Simple wrappers:** `<div style="text-align:center;">` inside `<td>` is OK. No layout CSS on it.
- **MSO conditionals:** Ghost table pattern for multi-column. `<div>` inside MSO blocks is expected.
- **Spacing:** `padding` on `<td>` only (universal). `margin:0` reset on every `<p>` and heading.
- **Sanitizer:** `sanitize_web_tags_for_email()` preserves `<p>` inside `<td>`, strips layout divs, preserves MSO blocks.
```

**File:** `memory/feedback_no_div_p_in_email.md` — update with nuanced rule

### Phase E: Update TEXT node conversion (optional, low priority)

**File:** `app/design_sync/converter.py` — `node_to_email_html()` TEXT branch (line 221-244)

Current: renders text as `<td style="...">escaped content</td>`

Consider: if the text content contains newlines or is multi-paragraph, wrap each paragraph in `<p style="margin:0 0 10px 0;">` inside the `<td>`. This gives screen readers paragraph-level navigation.

**Skip for now** — the scaffolder rewrites text content anyway, so the converter skeleton's text is mostly placeholders. Only worth doing if we move toward brief-only template creation (Phase 29.1) where the converter output is closer to final.

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `app/design_sync/converter.py` | Smart sanitizer: preserve p-in-td, strip layout divs | P0 |
| `app/ai/agents/scaffolder/assembler.py:324` | Social links div → table | P0 |
| `app/ai/agents/scaffolder/prompt.py:98-108` | Update from "never p" to "p for text, table for layout" | P0 |
| `app/design_sync/converter.py:26` | Remove dead VECTOR→div mapping | P1 |
| `CLAUDE.md` | Update HTML email structure rules | P1 |
| `memory/feedback_no_div_p_in_email.md` | Update with nuanced rule | P1 |
| `app/design_sync/tests/test_penpot_converter.py` | Update sanitizer tests for new behavior | P0 |

## Test Strategy

1. **Unit tests for updated sanitizer:**
   - `<p>` inside `<td>` → preserved with margin reset
   - `<p>` outside `<td>` → stripped to content + `<br><br>` (backward compat)
   - `<div style="width:300px">` → converted to table wrapper
   - `<div style="text-align:center">` inside `<td>` → preserved
   - `<div>` with no style outside `<td>` → unwrapped
   - MSO conditional blocks → untouched (existing test)
   - Nested `<p>` inside `<p>` → handled gracefully

2. **Regression tests:**
   - All existing golden templates still pass QA
   - Design sync import test with real Penpot data → output has tables for layout, p for text
   - Scaffolder pipeline → verify social links use table, not div

3. **Accessibility spot-check:**
   - Output HTML has `<p>` tags for text content (screen reader navigable)
   - Output HTML has heading tags for section titles
   - All tables have `role="presentation"`

## What NOT to Do

- Don't add a full ghost table generator — the scaffolder already handles multi-column via prompt/skills
- Don't add CSS-property-aware div validation — the QA css_support check already handles this
- Don't add post-Oct-2026 table-free mode — premature
- Don't change the EMAIL_SKELETON — it already uses the correct ghost table wrapper
- Don't add semantic HTML elements (`<section>`, `<header>`, `<footer>`) — only 66% email client support per caniemail
- Don't change the nh3 sanitization profiles — the sanitizer runs AFTER nh3, so nh3 allowing div/p is fine
