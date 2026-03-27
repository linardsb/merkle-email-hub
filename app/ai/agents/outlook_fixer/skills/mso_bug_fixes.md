---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_outlook-mso-fallback-reference.md sections 6-8, 11 -->
<!-- Last synced: 2026-03-13 -->

# MSO Bug Fixes — 15 Common Outlook Rendering Patterns

## Bug 1: Ghost Table for Multi-Column Layout
**Symptom:** Columns stack or misalign in Outlook desktop
**Fix:** Wrap columns in MSO conditional table

```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600">
<tr>
<td width="300" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:300px; vertical-align:top;">
  <!-- Left column content -->
</div>
<!--[if mso]>
</td>
<td width="300" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:300px; vertical-align:top;">
  <!-- Right column content -->
</div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

## Bug 2: Background Image Not Rendering
**Symptom:** Background images show as solid color in Outlook
**Fix:** Use VML `<v:rect>` with `<v:fill>` for background images

```html
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
  style="width:600px; height:300px;">
<v:fill type="frame" src="https://placehold.co/600x300" />
<v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->
<div style="background-image:url('https://placehold.co/600x300');
  background-size:cover; background-position:center;">
  <!-- Content over background -->
</div>
<!--[if mso]>
</v:textbox>
</v:rect>
<![endif]-->
```

## Bug 3: Bulletproof Button
**Symptom:** Buttons with `border-radius` or backgrounds break in Outlook
**Fix:** Use VML `<v:roundrect>` button

```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
  href="https://example.com/cta"
  style="height:44px; v-text-anchor:middle; width:200px;"
  arcsize="10%"
  strokecolor="#007bff"
  fillcolor="#007bff">
<center style="color:#ffffff; font-family:Arial,sans-serif; font-size:16px; font-weight:bold;">
  Shop Now
</center>
</v:roundrect>
<![endif]-->
<!--[if !mso]><!-->
<a href="https://example.com/cta"
  style="display:inline-block; padding:12px 24px; background-color:#007bff;
  color:#ffffff; text-decoration:none; border-radius:4px; font-family:Arial,sans-serif;
  font-size:16px; font-weight:bold;">
  Shop Now
</a>
<!--<![endif]-->
```

## Bug 4: 1px White Lines Between Table Sections
**Symptom:** Thin white lines appear between table rows/cells in Outlook
**Fix:** Add `border-collapse:collapse` and zero font-size on spacer cells

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0"
  style="border-collapse:collapse; mso-table-lspace:0pt; mso-table-rspace:0pt;">
```

For spacer rows:
```html
<tr>
  <td style="font-size:0; line-height:0; mso-line-height-rule:exactly; height:20px;">
    &nbsp;
  </td>
</tr>
```

## Bug 5: Font Falling Back to Times New Roman
**Symptom:** Custom/web fonts render as Times New Roman in Outlook
**Fix:** Set explicit font-family on every `<td>` and add `mso-font-alt`

```html
<td style="font-family:Arial, Helvetica, sans-serif; mso-font-alt:Arial;">
```

For web fonts:
```css
<!--[if mso]>
<style>
  * { font-family: Arial, Helvetica, sans-serif !important; }
</style>
<![endif]-->
```

## Bug 6: Line Height Inconsistency
**Symptom:** Line height differs between Outlook and other clients
**Fix:** Add `mso-line-height-rule: exactly`

```html
<td style="line-height:24px; mso-line-height-rule:exactly; font-size:16px;">
```

## Bug 7: Image Sizing / DPI Scaling
**Symptom:** Images appear wrong size on high-DPI Outlook displays
**Fix:** Set BOTH HTML attributes AND CSS width

```html
<img src="https://placehold.co/600x200" alt="Hero image"
  width="600" height="200"
  style="display:block; width:600px; height:auto; border:0;">
```

## Bug 8: Body Background Bleeding Through Table Gaps
**Symptom:** Body background color shows between table cells in Outlook
**Fix:** Set background color on ALL container cells, not just body

```html
<body style="margin:0; padding:0; background-color:#f5f5f5;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
  style="background-color:#f5f5f5;">
  <tr>
    <td align="center" style="background-color:#f5f5f5;">
      <!-- Inner content table -->
    </td>
  </tr>
</table>
</body>
```

## Bug 9: Animated GIF Showing Only First Frame
**Symptom:** Outlook only shows the first frame of animated GIFs
**Fix:** Ensure the first frame is meaningful; add alt text describing the animation

```html
<img src="https://placehold.co/600x300" alt="Animated product showcase — view in browser for full animation"
  width="600" height="300" style="display:block; width:100%; height:auto; border:0;">
```

## Bug 10: Padding on Table Cells Being Ignored
**Symptom:** CSS `padding` on `<td>` not respected consistently
**Fix:** Use explicit `padding` in inline styles AND `mso-padding-alt`

```html
<td style="padding:20px 30px; mso-padding-alt:20px 30px;">
```

## Bug 11: Max-Width Not Supported
**Symptom:** `max-width` CSS is ignored in Outlook — email stretches to full width
**Fix:** Use MSO conditional wrapper table with explicit `width`

```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0"
  width="600" align="center"><tr><td>
<![endif]-->
<div style="max-width:600px; margin:0 auto;">
  <!-- Content constrained to 600px -->
</div>
<!--[if mso]>
</td></tr></table>
<![endif]-->
```

## Bug 12: Border-Radius Not Rendering
**Symptom:** `border-radius` on any element is completely ignored in Outlook
**Fix:** Use VML for rounded elements OR accept square corners with graceful degradation

## Bug 13: Outlook Adding Extra Spacing to Paragraphs
**Symptom:** `<p>` tags get extra top/bottom margin in Outlook
**Fix:** Reset margins explicitly and use `mso-margin-top-alt`

```html
<p style="margin:0 0 16px 0; mso-margin-top-alt:0; mso-margin-bottom-alt:16px;">
  Paragraph text here.
</p>
```

## Bug 14: CSS Float Not Working
**Symptom:** `float:left/right` breaks layout in Outlook
**Fix:** Use MSO conditional tables instead of floats for layout

## Bug 15: Outlook Dark Mode Color Overrides
**Symptom:** Outlook desktop and Outlook.com override colors in dark mode unpredictably
**Fix:** Add `[data-ogsc]` (text) and `[data-ogsb]` (background) selectors

```css
/* Outlook-specific dark mode overrides */
[data-ogsc] .dark-text { color: #ffffff !important; }
[data-ogsb] .dark-bg { background-color: #1a1a2e !important; }
```

---

## Outlook HTML Attribute Requirements

These HTML attributes are more reliable than CSS equivalents in Outlook:

**Tables:** `cellpadding="0"`, `cellspacing="0"`, `border="0"`, `width="600"`, `align="center"`, `bgcolor="#ffffff"`, `valign="top"`

**Images:** `width="600"` (no `px`), `height="300"`, `border="0"`, `style="display:block;"`

**Spacers:** `<!--[if mso]>&nbsp;<![endif]-->` or `&#8203;` (zero-width space) to prevent empty cell collapse.

## MSO Conditional Style Block Resets

```html
<!--[if mso]>
<style type="text/css">
  body { margin: 0; padding: 0; }
  table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
  img { -ms-interpolation-mode: bicubic; }
  p { margin: 0; padding: 0; mso-line-height-rule: exactly; }
  span.MsoHyperlink { color: inherit !important; mso-style-priority: 99 !important; }
  span.MsoHyperlinkFollowed { color: inherit !important; mso-style-priority: 99 !important; }
  .ExternalClass { width: 100%; }
  .ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass td, .ExternalClass div { line-height: 100%; }
</style>
<![endif]-->
```

## Properties Outlook Ignores (Require VML/MSO Fallback)

- `max-width`, `min-width` — Use MSO conditional fixed-width table
- `border-radius` — Use VML `<v:roundrect>` with `arcsize`
- `background-image` (CSS) — Use VML `<v:rect>` + `<v:fill>`
- `background-size`, `background-position` — Use VML fill attributes
- `box-shadow` — Use VML `<v:shadow>`
- `text-shadow` — No VML equivalent
- `opacity`, `rgba()` — Use hex colors; VML supports opacity on fill/stroke
- `linear-gradient()` — Use VML `<v:fill type="gradient">`
- `display: flex/grid` — Use table layout
- `float` — Use table `align` attribute
- `position: absolute/relative/fixed` — Use table-based positioning
- `margin`/`padding` on `<div>` — Use `<td>` padding or `mso-padding-alt`
- `calc()`, `object-fit`, `clip-path` — Not supported
- `@media` queries — Ignored; inline styles only
- `animation`, `transition`, `transform`, `:hover` — Not supported