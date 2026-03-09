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

## Detection Notes
- Only flag CSS in `style` attributes and `<style>` blocks — ignore CSS in MSO conditionals
- `mso-` prefixed properties are Outlook-specific and VALID — never flag
- Check both shorthand and longhand (e.g., `display:flex` and `display: flex`)
