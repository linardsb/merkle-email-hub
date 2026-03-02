# CSS Box Model Properties in Email

## Overview

The CSS box model -- `margin`, `padding`, `width`, `height`, `max-width`, and `box-sizing` -- behaves inconsistently across email clients. Outlook on Windows is the most problematic client, ignoring `max-width` entirely and handling margins unpredictably. Gmail has its own quirks with margin support. Understanding these differences is essential for achieving pixel-consistent layouts across all email clients.

## Width and Height

The `width` and `height` properties are generally well-supported, but you should always set them as both HTML attributes and inline CSS for maximum compatibility.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `width` (CSS) | Yes | Yes | Yes | Yes | Yes | Yes |
| `width` (HTML attr) | Yes | Yes | Yes | Yes | Yes | Yes |
| `height` (CSS) | Yes | Partial | Yes | Yes | Yes | Yes |
| `height` (HTML attr) | Yes | Yes | Yes | Yes | Yes | Yes |
| `min-width` | Yes | No | Yes | Yes | Yes | Yes |
| `max-width` | Yes | No | Yes | Yes | Yes | Yes |
| `min-height` | Yes | No | Yes | Yes | Yes | Yes |
| `max-height` | Yes | No | Yes | Yes | Yes | Yes |

Outlook on Windows ignores `max-width`, `min-width`, `max-height`, and `min-height`. This is one of the most impactful rendering differences because `max-width` is commonly used to constrain email width on desktop.

### Code Example: Outlook-Safe Container Width

```html
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
<tr><td>
<![endif]-->
<div style="max-width: 600px; margin: 0 auto;">
  <!-- Email content -->
</div>
<!--[if mso]>
</td></tr></table>
<![endif]-->
```

This pattern wraps the content in a fixed-width table for Outlook while using `max-width` for all other clients.

### Percentage Widths

Percentage widths work in most clients but behave differently in Outlook when applied to `<div>` elements vs. `<td>` elements. Always use percentage widths on `<td>` elements for consistency.

```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td width="33%" style="width: 33%;" valign="top">Column 1</td>
    <td width="33%" style="width: 33%;" valign="top">Column 2</td>
    <td width="34%" style="width: 34%;" valign="top">Column 3</td>
  </tr>
</table>
```

## Margin

Margins are one of the most inconsistently supported properties in email. Outlook and Gmail both have significant limitations.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `margin` (shorthand) | Partial | Partial | Yes | Yes | Yes | Yes |
| `margin-top` | No | Yes | Yes | Yes | Yes | Yes |
| `margin-right` | No | Yes | Yes | Yes | Yes | Yes |
| `margin-bottom` | No | Yes | Yes | Yes | Yes | Yes |
| `margin-left` | No | Yes | Yes | Yes | Yes | Yes |
| `margin: 0 auto` | Yes | No | Yes | Yes | Yes | Yes |
| Negative margins | No | No | Yes | Yes | No | Partial |

Gmail strips individual margin properties (`margin-top`, `margin-left`, etc.) but supports the shorthand `margin` property. Outlook supports individual margins but does not support `margin: 0 auto` for centering.

### Code Example: Centering Without margin: 0 auto

```html
<!-- For Outlook, use align="center" on the table -->
<table role="presentation" cellpadding="0" cellspacing="0" border="0"
       align="center" style="margin: 0 auto;">
  <tr>
    <td style="padding: 20px;">
      Centered content
    </td>
  </tr>
</table>
```

### Workaround: Spacing Without Margins

Replace margins with padding on parent elements or use spacer table rows:

```html
<!-- Spacer row approach -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding: 0; font-size: 1px; line-height: 1px; height: 20px;">&nbsp;</td>
  </tr>
</table>
```

## Padding

Padding is well-supported across email clients with one notable exception: Outlook does not reliably support padding on `<p>`, `<div>`, or `<a>` elements. Always apply padding to `<td>` elements.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `padding` on `<td>` | Yes | Yes | Yes | Yes | Yes | Yes |
| `padding` on `<div>` | Yes | Partial | Yes | Yes | Yes | Yes |
| `padding` on `<p>` | Yes | No | Yes | Yes | Yes | Yes |
| `padding` on `<a>` | Yes | No | Yes | Yes | Yes | Yes |
| `padding` shorthand | Yes | Yes | Yes | Yes | Yes | Yes |
| `padding-top/right/bottom/left` | Yes | Yes | Yes | Yes | Yes | Yes |

### Code Example: Reliable Padding

```html
<!-- Apply padding to <td>, not inner elements -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="padding: 20px 30px;">
      <p style="margin: 0; font-size: 16px; line-height: 24px;">
        Text content with consistent spacing
      </p>
    </td>
  </tr>
</table>
```

### Bulletproof Buttons with Padding

Padding on `<a>` tags does not work in Outlook. Use the "bulletproof button" technique with a `<td>` wrapper:

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td align="center" bgcolor="#1a73e8"
        style="background-color: #1a73e8; border-radius: 4px;">
      <a href="https://example.com"
         style="display: inline-block; padding: 14px 28px;
                font-size: 16px; font-weight: bold;
                color: #ffffff; text-decoration: none;
                font-family: Arial, sans-serif;">
        Call to Action
      </a>
    </td>
  </tr>
</table>
```

## Box-Sizing

`box-sizing` has limited support in email clients.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `box-sizing: content-box` | Yes | No | Yes | Yes | Yes | Yes |
| `box-sizing: border-box` | Yes | No | Yes | Yes | Yes | Yes |

Outlook ignores `box-sizing` entirely. Since Outlook uses the content-box model by default (and you cannot change it), design your width calculations accordingly. When specifying widths on table cells, account for padding separately.

### Width Calculation Example

```html
<!-- 600px container, 2 columns with 20px padding each -->
<!-- Content-box: width = 300 - 40 = 260px per column -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td width="300" style="width: 300px; padding: 0 20px;">
      Column 1 (260px content area)
    </td>
    <td width="300" style="width: 300px; padding: 0 20px;">
      Column 2 (260px content area)
    </td>
  </tr>
</table>
```

## Overflow

The `overflow` property has limited support and behaves unexpectedly in several clients.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `overflow: hidden` | Yes | No | Yes | Yes | Yes | Yes |
| `overflow: auto` | No | No | Yes | Yes | No | Partial |
| `overflow: scroll` | No | No | Yes | Yes | No | No |

Avoid relying on `overflow` for clipping content. Instead, structure your HTML so that content does not overflow its container.

## Key Takeaways

- Always set `width` as both an HTML attribute and inline CSS (`width="600"` and `style="width: 600px;"`) for maximum compatibility
- Outlook on Windows ignores `max-width`, `min-width`, `max-height`, and `min-height` -- use MSO conditional comments to provide fixed-width wrappers
- Gmail strips individual margin properties (`margin-top`, etc.) but supports the shorthand `margin` -- however, prefer padding on `<td>` elements over margins
- Apply padding exclusively to `<td>` elements for Outlook compatibility, never to `<p>`, `<div>`, or `<a>` tags
- `box-sizing` is ignored by Outlook -- always calculate widths using the content-box model
- For centering, use `align="center"` on tables combined with `margin: 0 auto` for non-Outlook clients
- Use spacer rows (`height` + `font-size: 1px; line-height: 1px;`) instead of margins for vertical spacing
- Negative margins are not supported in Gmail, Outlook, or Yahoo
