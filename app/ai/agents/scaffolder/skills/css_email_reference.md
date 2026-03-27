---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_html-email-css-dom-reference.md -->
<!-- Last synced: 2026-03-13 -->

# CSS Email Reference — L3 Quick Lookup

## Safe Properties (Use Freely)

`color`, `background-color`, `font-family`, `font-size`, `font-weight`, `font-style`,
`line-height`, `text-align`, `text-decoration`, `padding` (on `<td>`), `width`, `height`,
`border`, `border-collapse`, `vertical-align`, `display: block/inline/none`

## Partially Supported (Add Fallbacks)

| Property | Issue | Fallback |
|----------|-------|----------|
| `border-radius` | No Outlook | VML `<v:roundrect>` |
| `background-image` | No Outlook | VML `<v:fill>` |
| `max-width` | No Outlook | MSO conditional `<table>` |
| `box-shadow` | No Outlook | Accept degradation |
| `@media` | No Outlook/Gmail | Mobile-first with inline base |

## Never Use in Email

`display: flex/grid`, `position: fixed/sticky/absolute`, `float` (use `align`),
`calc()`, `var()` (CSS custom props), `clip-path`, `transform`, `animation` (limited)

## Vendor Prefixes: Skip

No email client uses `-moz-`, `-ms-`, `-o-`. Only Apple Mail uses `-webkit-`.
Exception: `-webkit-text-size-adjust: 100%` prevents iOS auto-resize.

## Key Rules

1. ALWAYS inline CSS on elements — Gmail strips `<style>` blocks
2. Use HTML attributes alongside CSS (`width="600"` + `style="width:600px"`)
3. Even-number px for `font-size` and `line-height`
4. Use `mso-` prefixed properties for Outlook Word engine control
5. `!important` only in dark mode `@media` blocks