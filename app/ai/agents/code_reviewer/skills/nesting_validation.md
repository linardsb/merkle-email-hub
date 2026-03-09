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

## False Positive Prevention
- `<div>` inside `<td>` is VALID and common
- `<a>` wrapping inline content is VALID
- Multiple `<table>` elements (not deeply nested) is NORMAL for email layout
- MSO conditional comments may contain apparent nesting violations — skip content inside `<!--[if mso]>...<![endif]-->`
