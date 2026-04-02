# Email Layout Detection — Judge Reference

## Core Rule

Email layout MUST use `<table>/<tr>/<td>` exclusively. The presence of layout CSS properties on `<div>` or `<p>` elements is a failure.

## Layout CSS Properties (Trigger FAIL on div/p)

These properties on `<div>` or `<p>` indicate layout usage — always FAIL:
- `width` (except `max-width` on fluid wrappers inside `<td>`)
- `display: flex` / `display: grid` / `display: inline-block` (layout intent)
- `float: left` / `float: right`
- `columns` / `column-count`
- `position: absolute` / `position: relative` (layout positioning)

## Permitted div/p Usage (Do NOT Flag)

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

4. **`<p>` for text content inside `<td>`** — PASS:
```html
<td><p style="margin:0 0 10px 0;">Paragraph text</p></td>
```

## Decision Flowchart

1. Is the element `<div>` or `<p>`?
   - No → not applicable (tables are fine)
   - Yes → continue
2. Does it have any layout CSS property from the list above?
   - Yes → **FAIL** (layout div/p in email)
   - No → continue
3. Is it inside a `<td>` or inside an MSO conditional block?
   - Yes → **PASS** (permitted wrapper usage)
   - No → **FAIL** (structural div/p outside table context)
