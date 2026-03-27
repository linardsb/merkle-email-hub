---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_outlook-mso-fallback-reference.md sections 1, 3 -->
<!-- Last synced: 2026-03-13 -->

# HTML Nesting Validation — L3 Reference

## Critical Nesting Violations (Email Context)

### Table Structure
- `<tr>` directly inside `<table>` without `<tbody>` — OK in email (not a violation)
- `<td>` outside `<tr>` — always invalid. Rule: `nesting-td-outside-tr`
- `<tr>` outside `<table>` — always invalid. Rule: `nesting-tr-outside-table`
- Nested `<table>` directly inside `<tr>` (must be inside `<td>`). Rule: `nesting-table-in-tr`

### Block-in-Inline
- `<div>` inside `<span>` — invalid. Rule: `nesting-block-in-inline`
- `<table>` inside `<a>` — invalid in most clients. Rule: `nesting-table-in-link`
- `<p>` inside `<p>` — auto-closed by parser, causes unexpected layout. Rule: `nesting-p-in-p`

### Unclosed Tags
- Unclosed `<td>`, `<tr>`, `<table>` — critical rendering issue. Rule: `nesting-unclosed-tag`
- Note: self-closing tags like `<br/>`, `<img/>`, `<hr/>` are valid

### Excessive Depth
- Table nesting depth > 6 levels — Outlook rendering degrades. Rule: `nesting-excessive-depth`
- More than 15 nested `<table>` elements total — Gmail performance. Rule: `nesting-too-many-tables`

## MSO Conditional Nesting Rules

### Never Nest MSO Conditionals
- `<!--[if mso]>` blocks must NEVER contain another `<!--[if mso]>` block
- MSO conditional comments are parsed by Outlook's HTML preprocessor before the Word rendering engine — nested conditionals cause unpredictable parsing failures
- Rule: `nesting-mso-nested-conditional` (severity: critical)
- Detection: scan for `<!--[if` inside an already-open conditional region

### MSO Conditional Pairing
- Every `<!--[if mso]>` must have a matching `<![endif]-->`
- Every `<!--[if !mso]><!-->` must have a matching `<!--<![endif]-->`
- Mismatched pairs cause entire sections to be hidden or shown incorrectly
- Rule: `nesting-mso-unmatched-conditional` (severity: critical)
- Detection: count opening vs closing conditionals; check balanced pairs

### MSO Version Conditionals
- `<!--[if gte mso 9]>` through `<!--[if mso 16]>` — all must have matching closers
- Version-targeted conditionals (e.g., `[if mso 12]`) are NOT the same as general `[if mso]` — do not count them as duplicates
- Rule: `nesting-mso-version-unmatched` (severity: critical)

## VML Nesting Rules

### VML Must Be Inside MSO Conditionals
- ALL VML elements (`<v:rect>`, `<v:roundrect>`, `<v:oval>`, `<v:shape>`, `<v:line>`, `<v:image>`, `<v:group>`) must be inside `<!--[if mso]>` or `<!--[if gte mso 9]>` blocks
- VML outside conditionals is rendered as broken/unknown HTML by non-Outlook clients
- Rule: `nesting-vml-outside-conditional` (severity: critical)

### VML Element Nesting Hierarchy
Valid parent-child relationships:
- `<v:textbox>` must be inside a VML shape (`<v:rect>`, `<v:roundrect>`, `<v:oval>`, `<v:shape>`)
- `<v:fill>`, `<v:stroke>`, `<v:shadow>` must be inside a VML shape (not standalone)
- `<w:anchorlock/>` must be inside `<v:roundrect>` (for bulletproof buttons)
- `<v:imagedata>` must be inside a VML shape
- `<v:group>` can contain other VML shapes (`<v:rect>`, `<v:oval>`, `<v:shape>`, etc.)
- Rule: `nesting-vml-invalid-parent` (severity: warning)

### VML Closure Requirements
- All VML shapes must be properly closed: `<v:rect>...</v:rect>`, not left open
- Self-closing VML is valid for child elements: `<v:fill ... />`, `<v:stroke ... />`, `<w:anchorlock/>`
- `<v:textbox>` must be both opened and closed — it contains HTML content
- Rule: `nesting-vml-unclosed` (severity: critical)
- Detection: track VML open/close tags within each MSO conditional block

## Ghost Table Structure Validation

### Matching td/tr Counts
- MSO ghost tables split across multiple conditional blocks must have balanced `<td>` and `<tr>` counts
- Pattern: opening block has `<table><tr><td>`, middle blocks have `</td><td>`, closing block has `</td></tr></table>`
- Mismatched counts cause Outlook to render broken layouts
- Rule: `nesting-ghost-table-unbalanced` (severity: critical)
- Detection: within a sequence of MSO conditional blocks, sum `<td>` opens vs closes, `<tr>` opens vs closes, `<table>` opens vs closes

### Ghost Table Width Consistency
- Column `<td>` widths in a ghost table must sum to the outer `<table>` width
- Example: `<table width="600">` with `<td width="300">` + `<td width="300">` = correct
- Example: `<table width="600">` with `<td width="300">` + `<td width="200">` = 100px unaccounted
- Rule: `nesting-ghost-table-width-mismatch` (severity: warning)

## Table Accessibility Nesting

### `role="presentation"` Requirement
- ALL layout tables must have `role="presentation"` — tells screen readers to ignore table structure
- Data tables (with `<th>`, `<caption>`) must NOT have `role="presentation"`
- Rule: `nesting-table-missing-role` (severity: warning)
- Detection: tables without `role="presentation"` that also lack `<th>` or `<caption>` children

### Nested Layout Table Inheritance
- `role="presentation"` on an outer table does NOT propagate to inner tables
- Each layout table at every nesting level needs its own `role="presentation"`
- Rule: `nesting-inner-table-missing-role` (severity: info)

## False Positive Prevention
- `<div>` inside `<td>` is VALID and common
- `<a>` wrapping inline content is VALID
- Multiple `<table>` elements (not deeply nested) is NORMAL for email layout
- MSO conditional comments may contain apparent nesting violations — skip content inside `<!--[if mso]>...<![endif]-->` ONLY for HTML nesting rules, NOT for VML nesting rules
- VML elements inside conditionals follow their own nesting rules (see VML section above)
- Ghost table fragments are intentionally split across multiple conditional blocks — validate the aggregate structure, not individual fragments