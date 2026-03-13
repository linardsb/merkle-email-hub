<!-- L4 source: docs/SKILL_html-email-components.md sections 12-13, docs/SKILL_email-dark-mode-dom-reference.md section 18 -->
<!-- Last synced: 2026-03-13 -->

# Email Client Compatibility Reference

## CSS Property Support Matrix

### Universally Safe (use freely)
| Property | Gmail | Outlook | Apple Mail | Yahoo |
|----------|-------|---------|------------|-------|
| color | Yes | Yes | Yes | Yes |
| background-color | Yes | Yes | Yes | Yes |
| font-family | Yes | Yes | Yes | Yes |
| font-size | Yes | Yes | Yes | Yes |
| font-weight | Yes | Yes | Yes | Yes |
| line-height | Yes | Needs mso-line-height-rule | Yes | Yes |
| text-align | Yes | Yes | Yes | Yes |
| text-decoration | Yes | Yes | Yes | Yes |
| padding | Yes | On `<td>` only | Yes | Yes |
| margin | Yes | Partial | Yes | Yes |
| width | Yes | Yes | Yes | Yes |
| height | Yes | Yes | Yes | Yes |
| border | Yes | Yes | Yes | Yes |
| vertical-align | Yes | Yes | Yes | Yes |

### Partially Supported (use with fallbacks)
| Property | Gmail | Outlook | Apple Mail | Yahoo |
|----------|-------|---------|------------|-------|
| border-radius | Yes | No | Yes | Yes |
| background-image | Yes | No, use VML | Yes | Yes |
| max-width | Yes | No, use MSO table | Yes | Yes |
| box-shadow | No | No | Yes | No |
| opacity | No | No | Yes | No |

### Never Use in Email
- `display: flex` / `display: grid`
- `position: absolute/relative/fixed`
- CSS variables (`var(--x)`)
- `calc()`, `clamp()`, `min()`, `max()`
- `float` (except image wrapping with MSO fallback)
- `@import` (stripped by Gmail)

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

## Dark Mode Support Matrix

| Feature | Apple Mail | Outlook.com | Outlook Desktop | Gmail | Samsung |
|---------|-----------|-------------|----------------|-------|---------|
| `color-scheme` meta | Yes | No | No | Stripped | No |
| `prefers-color-scheme` | Yes | No | No | No | Yes |
| `[data-ogsc]`/`[data-ogsb]` | No | Yes | No | No | No |
| `<picture>` dark swap | Yes | No | No | No | No |
| Developer control | Full | Partial | None | None | Partial |

## Client Targeting Selectors

```css
/* WebKit (Apple Mail, iOS) */
@media screen and (-webkit-min-device-pixel-ratio: 0) { }

/* Mozilla (Thunderbird) */
@media all and (min--moz-device-pixel-ratio: 0) { }

/* Outlook.com dark mode */
[data-ogsc] .text { color: #fff !important; }
[data-ogsb] .bg { background-color: #1a1a1a !important; }
```
