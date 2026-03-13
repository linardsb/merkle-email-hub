<!-- L4 source: docs/SKILL_html-email-components.md section 11, docs/SKILL_email-dark-mode-dom-reference.md section 18 -->
<!-- Last synced: 2026-03-13 -->

# CSS Client Support — L3 Reference

## Critical (Breaks Rendering)

| CSS Property | Unsupported In | Rule ID |
|---|---|---|
| `display: flex` | Outlook (all), Gmail (partial) | `css-unsupported-flex` |
| `display: grid` | Outlook (all), Gmail, Yahoo | `css-unsupported-grid` |
| `position: fixed` | All email clients | `css-unsupported-position-fixed` |
| `position: sticky` | All email clients | `css-unsupported-position-sticky` |
| `position: absolute` | Outlook, many webmail | `css-unsupported-position-absolute` |
| `float` | Outlook (all versions) | `css-unsupported-float` |
| `calc()` | Outlook, Gmail (partial) | `css-unsupported-calc` |
| `var()` / CSS custom properties | Outlook, Gmail | `css-unsupported-custom-props` |

## Warning (Degraded Experience)

| CSS Property | Unsupported In | Rule ID |
|---|---|---|
| `border-radius` | Outlook (Windows) | `css-partial-border-radius` |
| `box-shadow` | Outlook (Windows) | `css-partial-box-shadow` |
| `background-image` (CSS) | Outlook (use VML) | `css-partial-bg-image` |
| `max-width` without MSO fallback | Outlook | `css-needs-mso-fallback` |
| `gap` | Most email clients | `css-unsupported-gap` |
| `object-fit` | Outlook | `css-partial-object-fit` |
| `clip-path` | Most email clients | `css-unsupported-clip-path` |

## Info (Minor Compatibility)

| CSS Property | Note | Rule ID |
|---|---|---|
| `margin: auto` for centering | Outlook needs `align="center"` | `css-info-margin-auto` |
| `line-height` as unitless | Some clients need px value | `css-info-unitless-line-height` |

## Responsive Technique Support by Client

### Media Query Support (`@media` in `<style>` block)
- Apple Mail / iOS Mail — full support, including `prefers-color-scheme`, `prefers-reduced-motion`
- Outlook desktop (Windows) — **no support** — ignores all `@media` queries, renders base inline styles only
- Gmail (web) — strips `<style>` blocks in clipped/forwarded emails; prefixes class names when preserved
- Gmail (Android/iOS) — strips `<style>` blocks entirely
- Yahoo Mail — supports `@media` but renames CSS classes (prefix mangling)
- Samsung Mail (Android 9+) — supports `@media` including `prefers-color-scheme`
- Thunderbird — full support

### Fluid-Hybrid (Spongy) Layout Support
- Works everywhere including Gmail (no `<style>` dependency)
- Uses `display: inline-block`, `min-width`, `max-width` on `<div>` elements
- Requires MSO conditional ghost tables for Outlook (Outlook ignores `max-width`)
- Rule: `css-fluid-hybrid-missing-mso` — flag `max-width` on `<div>` without adjacent MSO conditional table

### Column Stacking Techniques
- `display: block !important; width: 100% !important` — media query-dependent; fails in Gmail
- `display: table-header-group` / `table-footer-group` — content reordering; limited support
- Rule: `css-responsive-gmail-incompatible` — flag responsive techniques that require `<style>` without a Gmail fallback

## Dark Mode CSS Support Matrix

### `@media (prefers-color-scheme: dark)`
- Apple Mail / iOS Mail — **full support**
- Outlook for Mac — **full support**
- Samsung Mail (Android 9+) — **supported** (but may double-invert: your styles + Samsung's engine)
- Thunderbird — **full support**
- Outlook for iOS/Android — **partial support**
- Outlook.com (webmail) — **ignored** (uses `[data-ogsc]`/`[data-ogsb]` instead)
- Outlook desktop (Windows) — **ignored** (forced Word-engine inversion, cannot be overridden)
- Gmail (all versions) — **stripped** with `<style>` block
- Yahoo Mail / AOL — **limited/inconsistent**

### `[data-ogsc]` / `[data-ogsb]` Selectors (Outlook.com Only)
- `[data-ogsc]` — targets foreground/text color overrides
- `[data-ogsb]` — targets background color overrides
- Must be in `<style>` block in `<head>`
- Rule: `css-dark-mode-outlook-com` — flag dark mode CSS without `[data-ogsc]`/`[data-ogsb]` equivalents

### `<picture><source media="(prefers-color-scheme: dark)">` Image Swap
- Apple Mail / iOS Mail only — no other email client supports this
- Rule: `css-picture-swap-apple-only` — info-level flag that this technique is Apple-only

## Gmail-Specific Style Behavior

### Style Stripping
- Gmail strips `<style>` blocks in clipped emails (>102KB) and forwarded emails
- When Gmail preserves `<style>`, it prefixes all class names with a unique string (e.g., `.m_-123456 .your-class`)
- Gmail does NOT support `@media` queries, CSS custom properties, or `@import`
- Rule: `css-gmail-style-strip-risk` — warn when layout depends on `<style>` block without inline fallbacks

### Gmail Dark Mode
- Forced inversion based on luminance — no developer control
- Strips `<meta name="color-scheme">` entirely
- Only mitigation: defensive color choices (avoid pure `#ffffff`/`#000000`)

## Yahoo Mail Class Renaming

- Yahoo renames CSS classes by adding a prefix (e.g., `yiv1234567890`)
- Attribute selectors and ID selectors may be stripped
- Rule: `css-yahoo-class-rename` — info-level flag for complex CSS selectors that may break in Yahoo

## Review Checklist: Properties to Flag per Client

### Outlook Desktop (Flag These)
- [ ] `display: flex/grid` without table fallback
- [ ] `max-width` without MSO conditional table
- [ ] `border-radius` without VML `<v:roundrect>`
- [ ] `background-image` without VML `<v:fill>`
- [ ] `float` without table `align` fallback
- [ ] `calc()`, `var()`, CSS custom properties
- [ ] `@media` queries as sole responsive mechanism

### Gmail (Flag These)
- [ ] Layout depending on `<style>` block classes without inline style fallbacks
- [ ] `@media (prefers-color-scheme: dark)` without acceptance that Gmail ignores it
- [ ] Complex CSS selectors that Gmail may mangle

### Yahoo Mail (Flag These)
- [ ] CSS class selectors that break with prefix renaming
- [ ] Attribute selectors in `<style>` block

## Detection Notes
- Only flag CSS in `style` attributes and `<style>` blocks — ignore CSS in MSO conditionals
- `mso-` prefixed properties are Outlook-specific and VALID — never flag
- Check both shorthand and longhand (e.g., `display:flex` and `display: flex`)
- Dark mode CSS requires `!important` on ALL declarations — flag missing `!important` as warning
