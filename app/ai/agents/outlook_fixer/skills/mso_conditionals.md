<!-- L4 source: docs/SKILL_outlook-mso-fallback-reference.md sections 1-2 -->
<!-- Last synced: 2026-03-13 -->

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
<!--[if mso 16]>  <!-- Outlook 2016, 2019, 2021, Microsoft 365 -->
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
- `!mso` — NOT Outlook (everything else)
- `mso | IE` — Outlook OR Internet Explorer
- `mso & IE` — Outlook AND IE context (rare)

### Full Version Number Mapping
| Version Number | Outlook Version |
|---------------|-----------------|
| 9 | Outlook 2000 |
| 10 | Outlook 2002/XP |
| 11 | Outlook 2003 |
| 12 | Outlook 2007 (first Word engine) |
| 14 | Outlook 2010 (skipped 13) |
| 15 | Outlook 2013 |
| 16 | Outlook 2016, 2019, 2021, Microsoft 365 |

**Note:** Outlook 2016+ all report as `mso 16` — no way to distinguish via conditionals.

## Ghost Table Pattern (Multi-Column Layouts)

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

## Office XML Namespace Block

Required in `<head>` for DPI fix and PNG support:
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

- `<o:AllowPNG/>` — Enables PNG rendering (some Outlook versions need this)
- `<o:PixelsPerInch>96</o:PixelsPerInch>` — Prevents high-DPI scaling distortion
- `<o:TargetScreenSize>` — Target display resolution (rarely used)

### Namespace Declarations on `<html>`
```html
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word">
```
- `xmlns:v` — Required for ALL VML shapes
- `xmlns:o` — Required for `<o:OfficeDocumentSettings>`, `<o:AllowPNG/>`, `<o:PixelsPerInch>`
- `xmlns:w` — Required for `<w:anchorlock/>` in VML buttons

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
mso-hide: all;                    /* Hide element from Outlook only */
```

## Conditional Comment Nesting Rules

1. **Never nest conditionals** — MSO conditionals cannot be nested
2. **Always close** — Every `<!--[if` must have a matching `<![endif]-->`
3. **Consistent pairing** — Don't mix `<!--[if mso]>` with `<!--[if !mso]>` closers
4. **Count your comments** — Before output, verify open count = close count
