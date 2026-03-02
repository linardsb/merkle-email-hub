# CSS Borders and Shadows in Email

## Overview

Borders and shadows add visual depth and structure to email designs. Basic border properties (`border`, `border-color`, `border-style`, `border-width`) are well-supported, but `border-radius` has a notable gap in Outlook on Windows. `box-shadow` is stripped by Gmail and ignored by Outlook, making it unreliable for critical design elements. This guide covers what works, the specific limitations of each client, and the workarounds for achieving rounded corners and shadow effects in email.

## Border Properties

Standard border properties are broadly supported across email clients. Both the shorthand `border` and the individual longhand properties work reliably.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `border` (shorthand) | Yes | Yes | Yes | Yes | Yes | Yes |
| `border-width` | Yes | Yes | Yes | Yes | Yes | Yes |
| `border-style` | Yes | Yes | Yes | Yes | Yes | Yes |
| `border-color` | Yes | Yes | Yes | Yes | Yes | Yes |
| `border-top/right/bottom/left` | Yes | Yes | Yes | Yes | Yes | Yes |

### Code Example: Table Cell Borders

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="border: 1px solid #e0e0e0; padding: 20px;
               font-family: Arial, sans-serif; font-size: 16px;">
      Content with border
    </td>
  </tr>
</table>
```

### Code Example: Bottom Border as Divider

```html
<td style="border-bottom: 2px solid #1a73e8; padding-bottom: 16px;">
  <h2 style="margin: 0; font-family: Arial, sans-serif;
             font-size: 20px; color: #1a1a1a;">
    Section Heading
  </h2>
</td>
```

## Border Collapse

`border-collapse` controls how table borders interact. It is important for creating clean table layouts without double borders.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `border-collapse: collapse` | Yes | Yes | Yes | Yes | Yes | Yes |
| `border-collapse: separate` | Yes | Yes | Yes | Yes | Yes | Yes |
| `border-spacing` | Yes | Partial | Yes | Yes | Yes | Yes |

Outlook has inconsistent behavior with `border-spacing`. Always use `cellspacing="0"` as an HTML attribute alongside the CSS.

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0"
       style="border-collapse: collapse;">
  <tr>
    <td style="border: 1px solid #cccccc; padding: 12px;">Cell 1</td>
    <td style="border: 1px solid #cccccc; padding: 12px;">Cell 2</td>
  </tr>
</table>
```

## Border Radius

`border-radius` is one of the most commonly requested CSS properties in email, and it has a significant gap: Outlook on Windows does not support it. Corners will render as square in Outlook.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `border-radius` | Yes | No | Yes | Yes | Yes | Yes |
| `border-top-left-radius` | Yes | No | Yes | Yes | Yes | Yes |
| `border-top-right-radius` | Yes | No | Yes | Yes | Yes | Yes |
| `border-bottom-left-radius` | Yes | No | Yes | Yes | Yes | Yes |
| `border-bottom-right-radius` | Yes | No | Yes | Yes | Yes | Yes |

### Progressive Enhancement Approach

Apply `border-radius` as a progressive enhancement. The design should still look acceptable with square corners in Outlook.

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="background-color: #f0f4f8; border-radius: 8px;
               padding: 24px; font-family: Arial, sans-serif;">
      <h3 style="margin: 0 0 8px 0; font-size: 18px; color: #1a1a1a;">
        Card Title
      </h3>
      <p style="margin: 0; font-size: 14px; color: #666666; line-height: 20px;">
        Card content with rounded corners in supported clients.
        Square corners in Outlook -- still looks fine.
      </p>
    </td>
  </tr>
</table>
```

### VML Rounded Rectangles for Outlook

If rounded corners are essential for a design element (such as buttons), use VML in Outlook:

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td align="center">
      <!--[if mso]>
      <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
                   xmlns:w="urn:schemas-microsoft-com:office:word"
                   href="https://example.com"
                   style="height:44px;v-text-anchor:middle;width:200px;"
                   arcsize="10%"
                   strokecolor="#1a73e8"
                   fillcolor="#1a73e8">
        <w:anchorlock/>
        <center style="color:#ffffff;font-family:Arial,sans-serif;
                       font-size:16px;font-weight:bold;">
          Click Here
        </center>
      </v:roundrect>
      <![endif]-->
      <!--[if !mso]><!-->
      <a href="https://example.com"
         style="display: inline-block; background-color: #1a73e8;
                color: #ffffff; font-family: Arial, sans-serif;
                font-size: 16px; font-weight: bold;
                text-decoration: none; padding: 12px 32px;
                border-radius: 4px;">
        Click Here
      </a>
      <!--<![endif]-->
    </td>
  </tr>
</table>
```

This gives rounded corners in all clients, including Outlook, using VML `v:roundrect` with the `arcsize` attribute.

## Box Shadow

`box-shadow` is not reliably supported in email. Gmail strips it, and Outlook ignores it.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `box-shadow` | No | No | Yes | Yes | No | Partial |
| `-webkit-box-shadow` | No | No | Yes | Yes | No | Partial |

### Workaround: Simulated Shadow with Borders

Instead of `box-shadow`, simulate a shadow effect using a subtle border:

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="background-color: #ffffff;
               border: 1px solid #e0e0e0;
               border-bottom: 3px solid #cccccc;
               border-radius: 8px;
               padding: 24px;">
      <p style="margin: 0; font-family: Arial, sans-serif;
                font-size: 16px; color: #333333;">
        Card with simulated shadow using borders
      </p>
    </td>
  </tr>
</table>
```

### Workaround: Shadow Using Nested Tables

For a more pronounced shadow effect, use a nested table with a slightly larger background:

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
  <tr>
    <td bgcolor="#e0e0e0" style="background-color: #e0e0e0;
                                 border-radius: 10px; padding: 0 0 3px 0;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
        <tr>
          <td bgcolor="#ffffff" style="background-color: #ffffff;
                                       border-radius: 8px; padding: 24px;">
            Content with simulated shadow
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
```

## Outline

The `outline` property has limited support in email clients.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `outline` | No | No | Yes | Yes | No | Partial |
| `outline-color` | No | No | Yes | Yes | No | Partial |
| `outline-style` | No | No | Yes | Yes | No | Partial |
| `outline-width` | No | No | Yes | Yes | No | Partial |

`outline` is stripped by Gmail and ignored by Outlook. Do not rely on it for visual design. Use `border` instead for visible element boundaries.

## Key Takeaways

- Standard `border` properties (`border`, `border-width`, `border-style`, `border-color`) are universally supported across all major email clients
- Use `border-collapse: collapse` and `cellspacing="0"` together for clean table borders
- `border-radius` works everywhere except Outlook on Windows -- design so that square corners are an acceptable fallback
- For rounded buttons in Outlook, use VML `v:roundrect` with `arcsize` inside MSO conditional comments
- `box-shadow` is stripped by Gmail and ignored by Outlook -- simulate shadows using borders or nested tables with contrasting background colors
- `outline` is not supported in Gmail or Outlook -- use `border` as a universally supported alternative
- Apply `border-radius` and `box-shadow` as progressive enhancements, not as load-bearing design elements
- Always test border-heavy designs in Outlook, as its Word rendering engine handles border rendering differently than browser-based clients
