# MSO Conditional Comments — Version Targeting Reference

## Basic Conditional Syntax

### Show content ONLY in Outlook (MSO)
```html
<!--[if mso]>
  Content visible only in Outlook desktop
<![endif]-->
```

### Show content in EVERYTHING EXCEPT Outlook
```html
<!--[if !mso]><!-->
  Content visible everywhere except Outlook desktop
<!--<![endif]-->
```

**Critical:** The non-MSO pattern has `<!-->` after the opening and `<!--` before closing.
Getting this wrong breaks rendering in all clients.

## Version Targeting

### Specific Outlook Version
```html
<!--[if mso 12]>  <!-- Outlook 2007 only -->
<!--[if mso 14]>  <!-- Outlook 2010 only -->
<!--[if mso 15]>  <!-- Outlook 2013 only -->
<!--[if mso 16]>  <!-- Outlook 2016, 2019, and Microsoft 365 -->
```

### Version Ranges
```html
<!--[if gte mso 12]>  <!-- Outlook 2007 and above -->
<!--[if lte mso 15]>  <!-- Outlook 2013 and below -->
<!--[if gt mso 14]>   <!-- Above Outlook 2010 -->
<!--[if lt mso 16]>   <!-- Below Outlook 2016 -->
```

### Operators
- `mso` — Any Outlook version using Word engine
- `mso X` — Exact version X
- `gte mso X` — Greater than or equal to version X
- `lte mso X` — Less than or equal to version X
- `gt mso X` — Greater than version X
- `lt mso X` — Less than version X

### Version Numbers
| Version Number | Outlook Version |
|---------------|-----------------|
| 12 | Outlook 2007 |
| 14 | Outlook 2010 |
| 15 | Outlook 2013 |
| 16 | Outlook 2016, 2019, Microsoft 365 |

**Note:** Outlook 2016, 2019, and Microsoft 365 all report as `mso 16`.
There is no way to distinguish between them via conditionals.

## Ghost Table Pattern (Multi-Column Layouts)

The ghost table is the standard pattern for multi-column layouts in Outlook:

### Two-Column Ghost Table
```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600">
<tr>
<td width="290" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:290px; vertical-align:top;">
  <!-- Column 1 -->
</div>
<!--[if mso]>
</td>
<td width="20"></td>
<td width="290" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:290px; vertical-align:top;">
  <!-- Column 2 -->
</div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

### Three-Column Ghost Table
```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600">
<tr>
<td width="190" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:190px; vertical-align:top;">
  <!-- Column 1 -->
</div>
<!--[if mso]>
</td>
<td width="15"></td>
<td width="190" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:190px; vertical-align:top;">
  <!-- Column 2 -->
</div>
<!--[if mso]>
</td>
<td width="15"></td>
<td width="190" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:190px; vertical-align:top;">
  <!-- Column 3 -->
</div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

## DPI Scaling Fix

Outlook on high-DPI displays scales images and VML incorrectly.

### Fix: Add Office XML namespace and DPI declaration
```html
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<!--[if gte mso 9]>
<xml>
  <o:OfficeDocumentSettings>
    <o:AllowPNG/>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings>
</xml>
<![endif]-->
</head>
```

This forces Outlook to render at 96 DPI regardless of display scaling.

## MSO-Specific CSS Properties

These CSS properties are only understood by Outlook's Word engine:

```css
mso-line-height-rule: exactly;     /* Force exact line-height */
mso-margin-top-alt: 0;            /* Override top margin */
mso-margin-bottom-alt: 16px;      /* Override bottom margin */
mso-table-lspace: 0pt;            /* Remove left table spacing */
mso-table-rspace: 0pt;            /* Remove right table spacing */
mso-padding-alt: 10px 20px;       /* Override cell padding */
mso-font-alt: Arial;              /* Fallback font for Word engine */
mso-text-raise: 0;                /* Vertical text alignment */
mso-style-textfill-fill-color: #333; /* Text fill in VML context */
```

## Conditional Comment Nesting Rules

1. **Never nest conditionals** — MSO conditionals cannot be nested
2. **Always close** — Every `<!--[if` must have a matching `<![endif]-->`
3. **Consistent pairing** — Don't mix `<!--[if mso]>` with `<!--[if !mso]>` closers
4. **Count your comments** — Before output, verify open count = close count
