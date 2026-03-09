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

## Outlook-Specific Constraints

- Uses Word rendering engine (Outlook 2007-2019, Microsoft 365 desktop)
- Outlook.com uses modern rendering (separate from desktop)
- No CSS `max-width`, `border-radius`, `background-image`, `opacity`
- Tables are the ONLY reliable layout mechanism
- Set width via HTML `width` attribute AND CSS `width` property

## Apple Mail

- Best CSS support of any email client
- Supports `<style>`, media queries, `border-radius`, `background-image`
- Supports dark mode via `prefers-color-scheme`
- Can be used as the "ideal" target — others degrade gracefully

## Yahoo Mail

- Supports `<style>` blocks
- Strips `id` attributes
- Renames CSS class names (prefix with `.yiv`)
- Limited media query support in mobile app
