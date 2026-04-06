---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_outlook-mso-fallback-reference.md section 11 -->
<!-- Last synced: 2026-03-13 -->

# Redundant Code Detection — L3 Reference

## Patterns to Detect

### Duplicate Inline Styles
- Same `style` attribute value repeated on adjacent/sibling elements
- Identical `background-color` + `color` pairs that could use a CSS class
- Rule: `redundant-duplicate-style`

### Unused CSS Classes
- Classes defined in `<style>` block but never referenced in HTML body
- Rule: `redundant-unused-class`

### Dead MSO Conditionals
- `<!--[if mso]>` blocks with empty content or only whitespace
- Nested MSO conditionals that target the same version (e.g., nested `[if gte mso 9]`)
- Rule: `redundant-dead-mso`

### Repeated Table Attributes
- `cellpadding="0" cellspacing="0" border="0"` on every nested table — only needed on outermost
- `role="presentation"` repeated on layout tables already inside a presentation table (though not wrong, it's redundant at inner levels if outer already has it — classify as `info`)
- Rule: `redundant-table-attrs`

### Empty Elements
- `<td>&nbsp;</td>` spacers that could use `height` on `<td>` (info only)
- Empty `<style>` blocks
- Rule: `redundant-empty-element`

## Outlook-Ignored CSS Properties (Dead Code When MSO Fallbacks Exist)

When VML or MSO conditional fallbacks are present, the following CSS properties serve
no purpose for Outlook and may be dead code if only targeting that client. Flag when
the property appears alongside its VML/MSO equivalent:

### Layout Properties Outlook Ignores
- `max-width` — ignored; use MSO conditional fixed-width table
- `min-width` — ignored
- `display: flex` / `display: grid` — ignored; use table layout
- `float` — unreliable; use table `align` attribute
- `position: absolute/relative/fixed` — ignored; use table-based positioning
- `calc()` — ignored; use fixed pixel values

### Visual Properties Outlook Ignores
- `border-radius` — ignored; use VML `<v:roundrect>` with `arcsize`
- `background-image` (CSS) — ignored on most elements; use VML `<v:rect>` + `<v:fill>`
- `background-size` / `background-position` — ignored; use VML `<v:fill>` attributes
- `box-shadow` — ignored; use VML `<v:shadow>`
- `text-shadow` — ignored; no VML equivalent (truly dead code in email)
- `opacity` — ignored on HTML elements
- `rgba()` colors — ignored; use hex colors

### Interaction Properties Outlook Ignores
- `animation` / `@keyframes` — ignored
- `transition` — ignored
- `transform` — ignored
- `:hover` pseudo-class — ignored

Rule: `redundant-outlook-dead-css` (severity: info when standalone, warning when
VML/MSO fallback duplicates the same visual effect)

## Duplicate VML + CSS Background Pattern

When both a VML `<v:rect>` with `<v:fill>` AND a CSS `background-image` target the
same element, the CSS version is dead code for Outlook. Flag when:
- A `<v:rect>` or `<v:fill>` provides the same background image as a nearby CSS
  `background-image` declaration and the CSS version has no non-Outlook audience
- VML `fillcolor` duplicates `background-color` on the same container — intentional
  for cross-client but flag if they diverge (mismatched colors = bug)
- Rule: `redundant-vml-css-duplicate`

## Redundant Font-Family on Nested Elements

- `font-family` inherited from parent — no need to repeat on every child `<td>`, `<span>`
- Exception: Outlook may not inherit `font-family` reliably across table boundaries
- Rule: flag only when the same `font-family` stack appears on a parent `<td>` and its direct child elements (severity: info)
- Rule: `redundant-font-family-inheritance`

## Unnecessary Vendor Prefixes for Email

These vendor prefixes have no meaningful email client target:
- `-moz-` prefixes — Thunderbird uses Gecko but supports unprefixed equivalents
- `-o-` prefixes — no Opera-based email client exists
- `-webkit-` prefixes — only useful for Apple Mail; flag if no Apple Mail audience
- Exception: `-ms-interpolation-mode: bicubic` is valid Outlook CSS — never flag
- Exception: `-webkit-text-size-adjust: 100%` is valid iOS Mail CSS — never flag
- Rule: `redundant-vendor-prefix` (severity: info)

## False Positive Prevention
- Multiple inline styles are NORMAL in email — only flag when truly identical on siblings
- MSO conditionals with different version targeting are NOT redundant
- Tables with `cellpadding="0"` at every level is defensive and often intentional — severity: info
- CSS properties inside `<!--[if !mso]><!-->` blocks are NOT dead code — they target non-Outlook clients
- VML + CSS duplication is intentional cross-client strategy — only flag when they conflict or one is provably unreachable