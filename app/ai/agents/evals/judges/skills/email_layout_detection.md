# Email Layout Detection — Judge Reference

## Core Rule

Email layout MUST use `<table>/<tr>/<td>` exclusively. All text content goes directly in `<td>` with inline styles — no `<p>` or `<h1>`-`<h6>` wrappers. The presence of layout CSS properties on `<div>` elements is a failure.

## Layout CSS Properties (Trigger FAIL on div)

These properties on `<div>` indicate layout usage — always FAIL:
- `width` (except `max-width` on fluid wrappers inside `<td>`)
- `display: flex` / `display: grid` / `display: inline-block` (layout intent)
- `float: left` / `float: right`
- `columns` / `column-count`
- `position: absolute` / `position: relative` (layout positioning)

## Permitted div Usage (Do NOT Flag)

1. **Text alignment wrapper inside `<td>`** — PASS:
```html
<td><div style="text-align:center;">Centered text</div></td>
```

2. **Fluid width constraint inside `<td>`** — PASS:
```html
<td>
  <div style="max-width:600px; margin:0 auto;">
    Content constrained for non-Outlook clients
  </div>
</td>
```

3. **MSO conditional ghost table divs** — PASS:
```html
<!--[if mso]><table><tr><td><![endif]-->
<div style="max-width:300px;">Column content</div>
<!--[if mso]></td></tr></table><![endif]-->
```
The `<div>` here is the non-Outlook fallback for a ghost table column. This is the standard responsive email pattern.

4. **Text content directly in `<td>`** — PASS:
```html
<td style="font-size:16px; line-height:1.5; color:#333333;">Paragraph text</td>
```
`<p>` and `<h1>`-`<h6>` tags should NOT appear in output HTML. All text styling (font-size, font-weight, color) goes as inline styles on `<td>`.

## Decision Flowchart

1. Is the element `<div>`?
   - No → continue to step 2
   - Yes → continue to step 3
2. Is the element `<p>` or `<h1>`-`<h6>`?
   - Yes → **FAIL** (text content should be directly in `<td>` with inline styles, not wrapped in p/h tags)
   - No → not applicable (tables are fine)
3. Does the `<div>` have any layout CSS property from the list above?
   - Yes → **FAIL** (layout div in email)
   - No → continue
4. Is it inside a `<td>` or inside an MSO conditional block?
   - Yes → **PASS** (permitted wrapper usage)
   - No → **FAIL** (structural div outside table context)
