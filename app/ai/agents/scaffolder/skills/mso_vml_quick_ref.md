---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_outlook-mso-fallback-reference.md sections 1, 3, 10, bug-fixes -->
<!-- Last synced: 2026-03-13 -->

# MSO & VML Quick Reference

## MSO Conditional Comments

### Target All Outlook Desktop (Word engine)
```html
<!--[if mso]>
  Outlook desktop only content
<![endif]-->
```

### Target Everything Except Outlook Desktop
```html
<!--[if !mso]><!-->
  Non-Outlook content
<!--<![endif]-->
```

### Version Targeting
```html
<!--[if mso 12]>  Outlook 2007 only  <![endif]-->
<!--[if mso 14]>  Outlook 2010 only  <![endif]-->
<!--[if mso 15]>  Outlook 2013 only  <![endif]-->
<!--[if mso 16]>  Outlook 2016/2019/365  <![endif]-->
<!--[if gte mso 12]>  Outlook 2007 and later  <![endif]-->
<!--[if lte mso 15]>  Outlook 2013 and earlier  <![endif]-->
<!--[if mso | IE]>  Outlook + legacy IE  <![endif]-->
```

### Ghost Table (Width Constraint)
```html
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0">
<tr><td>
<![endif]-->
<div style="max-width:600px; margin:0 auto;">
  <!-- Content -->
</div>
<!--[if mso]>
</td></tr></table>
<![endif]-->
```

## VML Namespace Declaration

When using VML, add to `<html>` tag:
```html
<html xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word">
```

## VML Bulletproof Button

```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
  xmlns:w="urn:schemas-microsoft-com:office:word"
  href="https://example.com/cta"
  style="height:44px; v-text-anchor:middle; width:200px;"
  arcsize="10%"
  strokecolor="#007bff"
  fillcolor="#007bff">
<w:anchorlock/>
<center style="color:#ffffff; font-family:Arial,sans-serif; font-size:16px; font-weight:bold;">
  Button Text
</center>
</v:roundrect>
<![endif]-->
<!--[if !mso]><!-->
<a href="https://example.com/cta"
  style="display:inline-block; padding:12px 24px; background-color:#007bff;
  color:#ffffff; text-decoration:none; border-radius:4px; font-family:Arial,sans-serif;
  font-size:16px; font-weight:bold;">
  Button Text
</a>
<!--<![endif]-->
```

## VML Background Image

```html
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
  style="width:600px; height:300px;">
<v:fill type="frame" src="https://placehold.co/600x300" color="#333333" />
<v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->
<div style="background-image:url('https://placehold.co/600x300');
  background-size:cover; background-position:center; padding:40px;">
  <!-- Content over background -->
</div>
<!--[if mso]>
</v:textbox>
</v:rect>
<![endif]-->
```

## VML Gradient Background

```html
<!--[if gte mso 9]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
  style="width:600px;height:200px;">
<v:fill type="gradient" color="#1a73e8" color2="#6ab7ff" angle="90" />
<v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->
<div style="background: linear-gradient(90deg, #1a73e8, #6ab7ff);">
  <!-- Content -->
</div>
<!--[if gte mso 9]>
</v:textbox>
</v:rect>
<![endif]-->
```

## Outlook Column Fallback (2-col with gutter)

```html
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
<tr>
<td width="290" valign="top">
<![endif]-->
<div style="display:inline-block; max-width:290px; width:100%; vertical-align:top;">
  <!-- Column 1 -->
</div>
<!--[if mso]>
</td>
<td width="20"></td>
<td width="290" valign="top">
<![endif]-->
<div style="display:inline-block; max-width:290px; width:100%; vertical-align:top;">
  <!-- Column 2 -->
</div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

## DPI Scaling Fix

Outlook on high-DPI displays scales images incorrectly. Fix:
```html
<img src="https://placehold.co/600x200" alt="Hero"
  width="600" height="200"
  style="display:block; width:600px; height:auto; border:0;">
```

Set BOTH `width` HTML attribute AND `width` CSS property.

## MSO-Specific CSS Properties

```css
mso-line-height-rule: exactly;     /* Consistent line-height */
mso-font-alt: Arial;               /* Web font fallback */
mso-table-lspace: 0pt;             /* Remove table left spacing */
mso-table-rspace: 0pt;             /* Remove table right spacing */
mso-padding-alt: 20px 30px;        /* Outlook padding override */
mso-margin-top-alt: 0;             /* Paragraph margin override */
mso-margin-bottom-alt: 16px;       /* Paragraph margin override */
mso-text-raise: 10px;              /* Vertical text alignment */
mso-hide: all;                     /* Hide from Outlook only */
```

## Full MSO Namespace Setup

```html
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office"
      lang="en" dir="ltr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Email Title</title>
  <!--[if gte mso 9]>
  <xml>
    <o:OfficeDocumentSettings>
      <o:AllowPNG/>
      <o:PixelsPerInch>96</o:PixelsPerInch>
    </o:OfficeDocumentSettings>
  </xml>
  <![endif]-->
  <!--[if mso]>
  <style type="text/css">
    body, table, td, a, p { font-family: Arial, Helvetica, sans-serif; }
    table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    img { -ms-interpolation-mode: bicubic; border: 0; outline: none; }
    p { margin: 0; padding: 0; mso-line-height-rule: exactly; }
    span.MsoHyperlink { color: inherit !important; }
    span.MsoHyperlinkFollowed { color: inherit !important; }
  </style>
  <![endif]-->
</head>
```

## Outlook Spacer Row

```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
<td style="height:30px; font-size:1px; line-height:1px; mso-line-height-rule:exactly;">&nbsp;</td>
</tr></table>
<![endif]-->
```

## Common Outlook Bugs to Avoid During Generation

### Bug: Font Fallback (Outlook uses Times New Roman)
Outlook ignores `font-family` on `<div>`, `<span>`. Always set font directly on `<td>` (td-only layout — no `<p>` or `<h>` tags):
```html
<td style="font-family:Arial,Helvetica,sans-serif; font-size:16px; line-height:24px; color:#333333; mso-line-height-rule:exactly;">
  Your text here
</td>
```

### Bug: Line-Height Inconsistency
Outlook has its own line-height calculation. Fix with MSO-specific property:
```css
mso-line-height-rule: exactly;
line-height: 24px;
```

### Bug: Table Gaps (1px White Lines)
Outlook inserts gaps between table rows. Prevent with:
```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0"
  style="border-collapse:collapse; mso-table-lspace:0pt; mso-table-rspace:0pt;">
```

### Bug: Image DPI Scaling
Outlook on high-DPI displays scales images. Always set both HTML `width` attribute AND CSS `width`:
```html
<img src="image.jpg" width="600" height="200" alt="Hero"
  style="display:block; width:600px; height:auto; border:0; -ms-interpolation-mode:bicubic;">
```

### Bug: Padding Not Supported on Some Elements
Outlook ignores `padding` on `<div>`, `<a>`, `<span>`. Use `padding` only on `<td>`:
```html
<!-- WRONG: padding on <a> -->
<a style="padding:12px 24px;">CTA</a>

<!-- RIGHT: padding on wrapping <td> -->
<td style="padding:12px 24px;">
  <a style="color:#ffffff; text-decoration:none;">CTA</a>
</td>
```