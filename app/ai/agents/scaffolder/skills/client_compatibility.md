---
priority: 3
---

> Client rendering constraints are injected via audience context from the
> centralized client matrix (`data/email-client-matrix.yaml`). CSS property
> support tables have been removed — see the matrix for current data.
> For specific client capabilities, see Phase 32.4 `lookup_client_support` tool.

# Email Client Compatibility — Scaffolder Behavioral Guidance

## Gmail-Specific Constraints

### 102KB Clipping Threshold
- Gmail clips emails over ~102KB (HTML source size)
- Everything after the clip point is hidden behind "View entire message"
- Mitigation: minify HTML, consolidate CSS, remove comments, use shorthand properties
- Measure: raw HTML file size, NOT rendered size

### Gmail CSS Handling
- Strips `<style>` blocks in non-Gmail apps (Gmail app on iOS/Android keeps them)
- Gmail web supports `<style>` in `<head>` only
- Always inline critical styles as fallback
- Gmail prefixes class names — avoid generic class names

### Gmail Link Handling
- Auto-links URLs, dates, addresses, phone numbers
- Prevent with zero-width non-joiner: `&zwnj;` or `<span>` wrapping

### Gmail Dark Mode
- Strips `<style>` blocks, ignores `@media (prefers-color-scheme: dark)`
- Uses forced color inversion — no developer control
- Only approach: defensive color choices (avoid pure `#ffffff`/`#000000`)

## Outlook-Specific Constraints

- Uses Word rendering engine (Outlook 2007-2019, Microsoft 365 desktop)
- Outlook.com uses modern rendering (separate from desktop)
- No CSS `max-width`, `border-radius`, `background-image`, `opacity`
- Tables are the ONLY reliable layout mechanism
- Set width via HTML `width` attribute AND CSS `width` property
- VML `fillcolor` may be inverted in dark mode — no reliable override

## Apple Mail

- Best CSS support of any email client
- Supports `<style>`, media queries, `border-radius`, `background-image`
- Full `@media (prefers-color-scheme: dark)` support
- Supports `<picture><source media="(prefers-color-scheme: dark)">` for image swap
- `color-scheme: light only` prevents dark mode inversion
- Can be used as the "ideal" target — others degrade gracefully

## Yahoo Mail

- Supports `<style>` blocks
- Strips `id` attributes
- Renames CSS class names (prefix with `.yiv`)
- Limited media query support in mobile app
- Limited/inconsistent dark mode support

## Samsung Mail

- Supports `@media (prefers-color-scheme: dark)` (Android 9+)
- Caution: applies BOTH your dark styles AND its own partial inversion — double-inversion risk
- Use `!important` on all dark mode declarations

