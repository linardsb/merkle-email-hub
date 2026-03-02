# CSS Layout Properties in Email

## Overview

Layout properties control how elements are positioned and arranged within an email. Unlike web browsers, email clients have wildly inconsistent support for modern CSS layout. The table-based layout paradigm persists in email development precisely because properties like `display`, `position`, `float`, `flexbox`, and `grid` cannot be relied upon across major email clients. Understanding which layout properties work -- and where they fail -- is critical for building emails that render correctly for every subscriber.

## Display Property

The `display` property is partially supported across email clients. `display: block` and `display: inline` work reliably, but more advanced values have significant gaps.

| Value | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `display: block` | Yes | Yes | Yes | Yes | Yes | Yes |
| `display: inline` | Yes | Yes | Yes | Yes | Yes | Yes |
| `display: inline-block` | Yes | No | Yes | Yes | Yes | Yes |
| `display: none` | Yes | Yes | Yes | Yes | Yes | Yes |
| `display: flex` | No | No | Yes | Yes | No | Yes |
| `display: grid` | No | No | Yes | Yes | No | Partial |
| `display: table` | Yes | Partial | Yes | Yes | Yes | Yes |

Outlook on Windows uses the Word rendering engine (Microsoft Word's HTML renderer), which has no support for `inline-block`, `flex`, or `grid`. Gmail strips `display: flex` and `display: grid` from both inline styles and `<style>` blocks.

### Code Example: Hiding Content

```html
<!-- Works across all clients -->
<div style="display: none; mso-hide: all;">
  Hidden content for screen readers or conditional display
</div>
```

The `mso-hide: all` property is required to hide content in Outlook (Windows), as Outlook may ignore `display: none` on certain elements.

## Position Property

The `position` property is almost entirely unsupported in email clients. Avoid using it.

| Value | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `position: relative` | No | No | Yes | Yes | No | Partial |
| `position: absolute` | No | No | Yes | Yes | No | Partial |
| `position: fixed` | No | No | No | No | No | No |
| `position: sticky` | No | No | No | No | No | No |

Gmail and Yahoo strip all `position` declarations. Outlook's Word engine has no concept of CSS positioning. Only Apple Mail and iOS Mail have reliable support, but since they represent a subset of your audience, you cannot depend on them alone.

### Workaround: Overlapping Elements

Instead of absolute positioning, use negative margins or the `margin-top` / `margin-left` trick with known fixed dimensions:

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding: 0;">
      <img src="background.jpg" width="600" height="300" alt="" style="display: block;" />
    </td>
  </tr>
  <tr>
    <td style="margin-top: -100px; padding: 0 40px;">
      <!-- Overlapping text content -->
      <p style="font-size: 24px; color: #ffffff;">Overlay Text</p>
    </td>
  </tr>
</table>
```

For true overlapping content in Outlook, use VML (Vector Markup Language) backgrounds with `v:rect` elements.

## Float Property

`float` has limited and inconsistent support. Gmail removes it entirely, and Outlook ignores it.

| Value | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `float: left` | No | No | Yes | Yes | Partial | Yes |
| `float: right` | No | No | Yes | Yes | Partial | Yes |

### Workaround: Side-by-Side Columns

Use `<table>` cells with `align` attributes for reliable multi-column layouts:

```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td width="50%" valign="top" style="padding-right: 10px;">
      Left column content
    </td>
    <td width="50%" valign="top" style="padding-left: 10px;">
      Right column content
    </td>
  </tr>
</table>
```

For responsive stacking on mobile, wrap `<table>` elements with `align="left"` and use `@media` queries to set `width: 100% !important` and `display: block !important`.

## Flexbox

Flexbox is not viable for email layouts. Gmail, Outlook, and Yahoo all strip or ignore `display: flex` and all flex-related properties (`flex-direction`, `justify-content`, `align-items`, `flex-wrap`, etc.).

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `display: flex` | No | No | Yes | Yes | No | Yes |
| `flex-direction` | No | No | Yes | Yes | No | Yes |
| `justify-content` | No | No | Yes | Yes | No | Yes |
| `align-items` | No | No | Yes | Yes | No | Yes |
| `flex-wrap` | No | No | Yes | Yes | No | Yes |

Do not use flexbox in production emails. There is no reliable fallback that degrades gracefully.

## CSS Grid

CSS Grid has even less support than flexbox. It is not supported in Gmail, Outlook, or Yahoo.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `display: grid` | No | No | Yes | Yes | No | Partial |
| `grid-template-columns` | No | No | Yes | Yes | No | Partial |
| `grid-template-rows` | No | No | Yes | Yes | No | Partial |
| `grid-gap` / `gap` | No | No | Yes | Yes | No | Partial |

Do not use CSS Grid in production emails. Stick to table-based layouts.

## Recommended Layout Approach

The only layout method that works across all email clients is HTML tables with `role="presentation"`. Use table cells for columns, `width` attributes (both HTML attribute and inline CSS) for sizing, and `align` attributes for horizontal positioning.

```html
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
<tr><td>
<![endif]-->
<div style="max-width: 600px; margin: 0 auto;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td align="center" style="padding: 20px;">
        Your email content here
      </td>
    </tr>
  </table>
</div>
<!--[if mso]>
</td></tr></table>
<![endif]-->
```

This hybrid approach uses a `<div>` with `max-width` for modern clients and an MSO conditional table for Outlook, which does not support `max-width`.

## Key Takeaways

- Use HTML tables with `role="presentation"` for all email layouts -- they are the only universally supported layout method
- `display: block`, `display: inline`, and `display: none` work across all major clients
- `display: inline-block` fails in Outlook on Windows
- `position`, `float`, `flexbox`, and `grid` are not reliable for email layouts
- Outlook on Windows (Word rendering engine) is the most restrictive client for layout properties
- Gmail strips `position`, `float`, `display: flex`, and `display: grid` from styles
- Use MSO conditional comments (`<!--[if mso]>`) to provide Outlook-specific table wrappers
- Use `mso-hide: all` alongside `display: none` for reliable content hiding
- For responsive layouts, combine `align="left"` tables with `@media` queries for mobile stacking
