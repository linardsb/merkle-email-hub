---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_outlook-mso-fallback-reference.md -->
# Diagnostic Table — Symptom to Cause to Fix

Use this table to identify the root cause of an Outlook rendering issue
from its visible symptoms, then apply the corresponding fix.

## Layout Issues

| Symptom | Cause | Fix | Bug # |
|---------|-------|-----|-------|
| Columns stack instead of side-by-side | Outlook ignores `display:inline-block` without ghost table | Add MSO conditional ghost table | 1 |
| Email stretches beyond 600px | Outlook ignores `max-width` | Add MSO conditional wrapper table with explicit `width="600"` | 11 |
| Content misaligned left/right | Missing `align` attribute on table/td | Add `align="center"` on wrapper table | 11 |
| Float-based layout broken | Outlook ignores CSS `float` | Replace with MSO conditional table layout | 14 |
| Extra whitespace between sections | Missing border-collapse and zero-spacing styles | Add `border-collapse:collapse; mso-table-lspace:0pt; mso-table-rspace:0pt` | 4 |
| Thin white lines between cells | Cell gap rendering in Word engine | Add spacer cells with `font-size:0; line-height:0; mso-line-height-rule:exactly` | 4 |

## Typography Issues

| Symptom | Cause | Fix | Bug # |
|---------|-------|-----|-------|
| Text renders in Times New Roman | Web font not available; no fallback on `<td>` | Add explicit `font-family` on each `<td>`; add `mso-font-alt` | 5 |
| Line height differs from other clients | Word engine line-height calculation | Add `mso-line-height-rule: exactly` | 6 |
| Extra space above/below text | Legacy `<p>` tags in imported HTML (converter strips these automatically) | Ensure td-only layout — text directly in `<td>` with inline styles, no `<p>` or `<h>` tags | 13 |

## Image Issues

| Symptom | Cause | Fix | Bug # |
|---------|-------|-----|-------|
| Images wrong size | Missing HTML width/height attributes | Add both HTML attributes AND CSS `width:Xpx` | 7 |
| Images blurry on high-DPI displays | Outlook DPI scaling | Add `<o:PixelsPerInch>96</o:PixelsPerInch>` in Office XML | DPI |
| Gap below images | Default inline display | Add `style="display:block; border:0"` | 7 |
| Animated GIF shows only first frame | Outlook limitation (no fix) | Ensure first frame is meaningful; add descriptive alt text | 9 |

## Background Issues

| Symptom | Cause | Fix | Bug # |
|---------|-------|-----|-------|
| Background image not showing | Outlook ignores CSS `background-image` | Use VML `<v:rect>` with `<v:fill type="frame">` | 2 |
| Body background bleeding through | Table cell gaps in Word engine | Set `background-color` on ALL container cells, not just `<body>` | 8 |

## Button Issues

| Symptom | Cause | Fix | Bug # |
|---------|-------|-----|-------|
| Button has no background color | CSS background on `<a>` not reliable | Use VML `<v:roundrect>` for bulletproof buttons | 3 |
| Button has no border-radius | Outlook ignores `border-radius` entirely | Use VML `<v:roundrect>` with `arcsize` OR accept square corners | 12 |
| Button click area too small | VML not covering full button | Set explicit `width` and `height` on `<v:roundrect>` style | 3 |

## Dark Mode Issues

| Symptom | Cause | Fix | Bug # |
|---------|-------|-----|-------|
| Colors inverted incorrectly in Outlook dark mode | Missing Outlook-specific dark mode selectors | Add `[data-ogsc]` and `[data-ogsb]` selectors | 15 |
| VML colors wrong in dark mode | VML fill colors not overridden | Set both light and dark fill colors in VML | 15 |
| Logo invisible on dark background | Logo has no background and Outlook forced dark bg | Add `background-color` to image container cell | 15 |

## MSO Conditional Issues

| Symptom | Cause | Fix | Bug # |
|---------|-------|-----|-------|
| Content shows in wrong clients | Incorrect conditional syntax | Verify `<!--[if mso]>` / `<!--[if !mso]><!-->` patterns | — |
| Broken HTML in all clients | Mismatched conditional open/close | Count all `<!--[if` and ensure matching `<![endif]-->` | — |
| VML renders as text | Missing VML namespace | Add `xmlns:v="urn:schemas-microsoft-com:vml"` to `<html>` | — |
| VML appears in non-Outlook clients | VML outside conditional block | Wrap ALL VML in `<!--[if mso]>` blocks | — |