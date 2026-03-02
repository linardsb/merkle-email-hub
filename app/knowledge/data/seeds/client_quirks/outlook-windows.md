# Outlook Windows Rendering Quirks

## Overview

Microsoft Outlook on Windows (2007, 2010, 2013, 2016, 2019, 2021, and Microsoft 365 desktop) uses the Microsoft Word rendering engine (WordHTML) to display HTML emails. This decision, made in Outlook 2007 when Microsoft switched away from Internet Explorer's rendering engine, is the single most impactful factor in email development. Word's HTML rendering capabilities are severely limited compared to any browser engine, forcing email developers to rely on table-based layouts, VML for advanced graphics, and MSO conditional comments for targeted fixes.

Understanding Outlook Windows quirks is non-negotiable for any email that targets a corporate audience, as Outlook remains dominant in enterprise environments with an estimated 30-40% market share in B2B communications.

## The Word Rendering Engine

The Word rendering engine (also called WordHTML) interprets HTML and CSS through the lens of a word processor, not a web browser. This means:

- CSS `float`, `position`, `flexbox`, and `grid` are completely ignored
- `max-width` and `max-height` have no effect
- `background-image` on HTML elements is not supported (VML is required)
- `margin` on block elements behaves inconsistently
- `padding` on `<td>` works but `padding` on `<div>` or `<p>` is unreliable
- Line-height rendering differs from browser calculations
- `border-radius` is completely unsupported

Because of these limitations, all layout in Outlook Windows must be built with nested `<table>` elements using explicit `width`, `cellpadding`, and `cellspacing` attributes.

## MSO Conditional Comments

MSO conditional comments allow developers to serve Outlook-specific code that is invisible to all other email clients. These comments use Microsoft's proprietary conditional syntax.

```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600">
<tr><td>
<![endif]-->

<div style="max-width: 600px; margin: 0 auto;">
  <!-- Content visible to all clients -->
</div>

<!--[if mso]>
</td></tr></table>
<![endif]-->
```

You can target specific Outlook versions:

```html
<!--[if mso 12]> Outlook 2007 only <![endif]-->
<!--[if mso 14]> Outlook 2010 only <![endif]-->
<!--[if mso 15]> Outlook 2013 only <![endif]-->
<!--[if mso 16]> Outlook 2016/2019/2021/365 <![endif]-->
<!--[if gte mso 12]> Outlook 2007 and above <![endif]-->
```

Version operators include `gt` (greater than), `gte` (greater than or equal), `lt` (less than), `lte` (less than or equal), and `!` (not).

## VML Backgrounds

Since Outlook does not support CSS `background-image`, Vector Markup Language (VML) must be used for background images on table cells or containers.

```html
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
  style="width:600px;height:400px;">
<v:fill type="frame" src="https://example.com/bg.jpg" color="#1a1a2e" />
<v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->

<div style="background-image: url('https://example.com/bg.jpg');
            background-color: #1a1a2e;
            background-size: cover;">
  <p style="color: #ffffff;">Content over background image</p>
</div>

<!--[if mso]>
</v:textbox>
</v:rect>
<![endif]-->
```

The VML namespace must be declared in the `<html>` tag for this to work:

```html
<html xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office">
```

## DPI Scaling Issues

Outlook on Windows respects the system DPI scaling setting. At 120 DPI (125% scaling) or 144 DPI (150% scaling), images and table widths can render larger than specified, breaking layouts.

```html
<!--[if gte mso 9]>
<xml>
  <o:OfficeDocumentSettings>
    <o:AllowPNG/>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings>
</xml>
<![endif]-->
```

This XML declaration forces Outlook to render at 96 DPI regardless of the system setting. Without it, a 600px-wide email can render at 750px on a 125% scaled display, causing horizontal scrolling or layout breaks.

## Image Rendering

Outlook has several image-specific quirks:

- Images default to `display: inline`, adding a small gap below. Fix with `display: block` on all `<img>` tags.
- Always specify `width` and `height` attributes directly on `<img>` elements, not just in CSS.
- SVG images are not supported; use PNG or JPEG.
- Animated GIFs display only the first frame.
- Images are blocked by default until the user clicks "Download pictures."

```html
<img src="https://example.com/hero.jpg"
     width="600" height="300"
     alt="Descriptive alt text shown when images are blocked"
     style="display: block; border: 0; outline: none; text-decoration: none;"
/>
```

## Table Rendering Specifics

Tables in Outlook require careful attribute usage because CSS equivalents are unreliable:

```html
<table role="presentation" border="0" cellpadding="0" cellspacing="0"
       width="600" style="border-collapse: collapse; mso-table-lspace: 0pt;
       mso-table-rspace: 0pt;">
  <tr>
    <td width="300" valign="top"
        style="padding: 10px; font-family: Arial, sans-serif; font-size: 14px;
               line-height: 20px; color: #333333;">
      Column content
    </td>
  </tr>
</table>
```

The `mso-table-lspace` and `mso-table-rspace` properties remove the default 1.95pt spacing Outlook adds between table cells. Without these, multi-column layouts will have unexpected gaps.

## Line Height and Font Rendering

Outlook calculates line-height differently from browsers. A `line-height: 1.5` declaration may render taller in Outlook. Use pixel values instead:

```css
/* Unreliable in Outlook */
line-height: 1.5;

/* Reliable across clients */
line-height: 22px;
```

Outlook also adds extra spacing above and below `<p>` tags. To normalize:

```html
<p style="margin: 0; mso-line-height-rule: exactly; line-height: 22px;">
  Paragraph text
</p>
```

The `mso-line-height-rule: exactly` property forces Outlook to respect the declared line-height value precisely.

## CSS Support Gaps

Properties completely unsupported in Outlook Windows:

| Property | Status |
|----------|--------|
| `border-radius` | Not supported |
| `box-shadow` | Not supported |
| `background-image` (CSS) | Not supported (use VML) |
| `max-width` / `max-height` | Not supported |
| `float` | Not supported |
| `position` | Not supported |
| `flexbox` / `grid` | Not supported |
| `opacity` | Not supported |
| `text-shadow` | Not supported |
| `@media` queries | Not supported |

## Key Takeaways

- Outlook Windows uses the Word rendering engine, not a browser engine, making it the most restrictive major email client
- All layouts must be table-based; CSS layout properties (`float`, `flexbox`, `grid`, `position`) are ignored
- Use MSO conditional comments (`<!--[if mso]>`) to serve Outlook-specific fixes invisible to other clients
- VML is required for background images; CSS `background-image` does not work
- Include `PixelsPerInch` XML declaration to prevent DPI scaling from breaking layouts
- Always set `width` and `height` attributes on images, use `display: block`, and provide meaningful alt text
- Use `mso-table-lspace: 0pt` and `mso-table-rspace: 0pt` to eliminate default table cell spacing
- Apply `mso-line-height-rule: exactly` for predictable line-height rendering
- Animated GIFs show only the first frame; SVGs are not supported
- Test thoroughly at 100%, 125%, and 150% DPI scaling settings
