# CSS Colors and Backgrounds in Email

## Overview

Color and background properties are fundamental to email design, but their support varies significantly across clients. Basic properties like `background-color` and `color` work universally, but more advanced features like CSS gradients, `rgba()` transparency, and `background-image` with CSS have major gaps -- particularly in Outlook on Windows. This guide covers what works, what breaks, and the workarounds needed for consistent email rendering.

## Color Values

Different color value formats have varying levels of support.

| Format | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| Hex (`#ff0000`) | Yes | Yes | Yes | Yes | Yes | Yes |
| 3-digit hex (`#f00`) | Yes | Yes | Yes | Yes | Yes | Yes |
| `rgb()` | Yes | Yes | Yes | Yes | Yes | Yes |
| `rgba()` | Yes | No | Yes | Yes | Yes | Yes |
| Named colors (`red`) | Yes | Yes | Yes | Yes | Yes | Yes |
| `hsl()` | Yes | No | Yes | Yes | Yes | Yes |
| `hsla()` | Yes | No | Yes | Yes | Yes | Yes |
| `currentColor` | No | No | Yes | Yes | No | Partial |

Outlook on Windows does not support `rgba()`, `hsl()`, or `hsla()`. Always use hex colors or `rgb()` as your primary format. If you need transparency effects, provide a solid hex fallback.

### Code Example: Safe Color Declaration

```html
<!-- Always use hex for maximum compatibility -->
<td style="color: #333333; background-color: #f5f5f5;">
  Content with safe color values
</td>

<!-- If using rgba, provide hex fallback first -->
<td style="background-color: #1a73e8; background-color: rgba(26, 115, 232, 0.9);">
  Falls back to solid hex in Outlook
</td>
```

## Background Color

`background-color` is universally supported when applied correctly. Use both the CSS property and the `bgcolor` HTML attribute for full compatibility.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `background-color` (CSS) | Yes | Yes | Yes | Yes | Yes | Yes |
| `bgcolor` (HTML attr) | Yes | Yes | Yes | Yes | Yes | Yes |

### Code Example: Full-Width Background Color

```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       bgcolor="#1a1a2e" style="background-color: #1a1a2e;">
  <tr>
    <td align="center" style="padding: 40px 20px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="color: #ffffff; font-family: Arial, sans-serif; font-size: 16px;">
            Content on dark background
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
```

## Background Image (CSS)

`background-image` in CSS is one of the most problematic properties in email. Outlook on Windows completely ignores CSS background images.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `background-image: url()` | No | No | Yes | Yes | No | Yes |
| `background-repeat` | No | No | Yes | Yes | No | Yes |
| `background-position` | No | No | Yes | Yes | No | Yes |
| `background-size` | No | No | Yes | Yes | No | Yes |
| `background` shorthand | No | No | Yes | Yes | No | Yes |

Gmail strips `background-image` from inline styles. Outlook ignores all CSS background image properties.

### Workaround: VML Backgrounds for Outlook

Use VML (Vector Markup Language) to render background images in Outlook, combined with CSS for other clients:

```html
<td background="https://example.com/bg.jpg"
    bgcolor="#1a1a2e"
    style="background-image: url('https://example.com/bg.jpg');
           background-color: #1a1a2e;
           background-size: cover;
           background-position: center;"
    valign="top">
  <!--[if gte mso 9]>
  <v:rect xmlns:v="urn:schemas-microsoft-com:vml"
          fill="true" stroke="false"
          style="width:600px;height:300px;">
    <v:fill type="frame" src="https://example.com/bg.jpg"
            color="#1a1a2e" />
    <v:textbox inset="0,0,0,0">
  <![endif]-->
  <div style="padding: 40px;">
    <p style="margin: 0; color: #ffffff; font-family: Arial, sans-serif;">
      Content over background image
    </p>
  </div>
  <!--[if gte mso 9]>
    </v:textbox>
  </v:rect>
  <![endif]-->
</td>
```

The `background` HTML attribute on `<td>` works in Gmail and most clients as a simpler alternative, though it offers no control over sizing or positioning.

## CSS Gradients

CSS gradients have very limited support in email. They fail in Outlook, Gmail, and Yahoo.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `linear-gradient()` | No | No | Yes | Yes | No | Yes |
| `radial-gradient()` | No | No | Yes | Yes | No | Yes |
| `repeating-linear-gradient()` | No | No | Yes | Yes | No | Partial |

### Workaround: Gradient Fallback Strategy

```html
<td bgcolor="#1a73e8"
    style="background-color: #1a73e8;
           background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);">
  <!--[if gte mso 9]>
  <v:rect xmlns:v="urn:schemas-microsoft-com:vml"
          fill="true" stroke="false"
          style="width:600px;height:200px;">
    <v:fill type="gradient" color="#1a73e8" color2="#0d47a1"
            angle="135" />
    <v:textbox inset="0,0,0,0">
  <![endif]-->
  <div style="padding: 30px;">
    <p style="color: #ffffff; margin: 0; font-family: Arial, sans-serif;">
      Gradient background with solid color fallback
    </p>
  </div>
  <!--[if gte mso 9]>
    </v:textbox>
  </v:rect>
  <![endif]-->
</td>
```

This provides the gradient for Apple Mail/iOS/Samsung, a solid fallback for Gmail/Yahoo, and a VML gradient for Outlook.

## Opacity

The `opacity` property is not reliably supported for creating transparency effects.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `opacity` | Yes | No | Yes | Yes | Yes | Yes |

Outlook ignores `opacity` completely. If you need a semi-transparent overlay effect, use a semi-transparent PNG image instead of CSS opacity.

## Mix Blend Mode and Filters

Advanced visual effects are not viable in email.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `mix-blend-mode` | No | No | Yes | Yes | No | No |
| `filter` | No | No | Yes | Yes | No | Partial |
| `backdrop-filter` | No | No | Partial | Partial | No | No |

Do not use these properties in production emails. They are only supported in Apple ecosystem clients.

## Dark Mode Color Considerations

When email clients apply dark mode, they may automatically invert or adjust your colors. To maintain design control:

```html
<!-- Specify both light and dark mode colors -->
<style>
  @media (prefers-color-scheme: dark) {
    .dark-bg { background-color: #1a1a2e !important; }
    .dark-text { color: #e0e0e0 !important; }
  }
</style>

<td class="dark-bg" style="background-color: #ffffff;">
  <p class="dark-text" style="color: #333333;">
    Colors adapt to dark mode where supported
  </p>
</td>
```

See the dark-mode-css guide for comprehensive dark mode strategies.

## Key Takeaways

- Use hex colors (`#rrggbb`) as your default format -- they work in every email client
- `rgba()`, `hsl()`, and `hsla()` are not supported in Outlook on Windows -- always provide hex fallbacks
- Set `background-color` both as inline CSS and as the `bgcolor` HTML attribute for reliability
- CSS `background-image` is stripped by Gmail and ignored by Outlook -- use the `background` HTML attribute on `<td>` and VML for Outlook
- CSS gradients only work in Apple Mail, iOS Mail, and Samsung -- use VML `<v:fill type="gradient">` for Outlook and solid color fallbacks for Gmail/Yahoo
- `opacity` is ignored by Outlook -- use semi-transparent PNG images for transparency effects
- Advanced visual properties (`filter`, `mix-blend-mode`, `backdrop-filter`) are not viable for email
- Always test background images and gradients across clients, as they are the most inconsistently rendered visual feature in email
- Consider dark mode color inversion when choosing background and text color pairs
