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
      xmlns:o="urn:schemas-microsoft-com:office:office">
```

## VML Bulletproof Button

```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
  href="https://example.com/cta"
  style="height:44px; v-text-anchor:middle; width:200px;"
  arcsize="10%"
  strokecolor="#007bff"
  fillcolor="#007bff">
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
<v:fill type="frame" src="https://placehold.co/600x300" />
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
```

## XML Processing Instructions

For Office XML features (used in `<head>`):
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
