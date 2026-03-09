# Table Layouts — Email Grid Patterns

## Single Column (600px)

```html
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center"
  style="width:600px; max-width:600px; border-collapse:collapse; mso-table-lspace:0pt; mso-table-rspace:0pt;">
  <tr>
    <td style="padding:20px 30px; font-family:Arial, Helvetica, sans-serif;">
      <!-- Content -->
    </td>
  </tr>
</table>
```

## Two Column (50/50)

```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" align="center">
<tr>
<td width="290" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:290px; vertical-align:top;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="padding:10px; font-family:Arial, Helvetica, sans-serif;">
        <!-- Left column -->
      </td>
    </tr>
  </table>
</div>
<!--[if mso]>
</td>
<td width="20"></td>
<td width="290" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:290px; vertical-align:top;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="padding:10px; font-family:Arial, Helvetica, sans-serif;">
        <!-- Right column -->
      </td>
    </tr>
  </table>
</div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

## Three Column (33/33/33)

```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" align="center">
<tr>
<td width="186" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:186px; vertical-align:top;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="padding:10px; font-family:Arial, Helvetica, sans-serif;">
        <!-- Column 1 -->
      </td>
    </tr>
  </table>
</div>
<!--[if mso]>
</td>
<td width="14"></td>
<td width="186" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:186px; vertical-align:top;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="padding:10px; font-family:Arial, Helvetica, sans-serif;">
        <!-- Column 2 -->
      </td>
    </tr>
  </table>
</div>
<!--[if mso]>
</td>
<td width="14"></td>
<td width="186" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:186px; vertical-align:top;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="padding:10px; font-family:Arial, Helvetica, sans-serif;">
        <!-- Column 3 -->
      </td>
    </tr>
  </table>
</div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

## Hero + Content Grid (Full-width hero, 2-col below)

```html
<!-- Hero section -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
  <tr>
    <td>
      <img src="https://placehold.co/600x300" alt="Hero image"
        width="600" height="300" style="display:block; width:100%; height:auto; border:0;">
    </td>
  </tr>
</table>

<!-- Two-column grid below hero -->
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" align="center">
<tr>
<td width="290" valign="top">
<![endif]-->
<!-- ... columns as above ... -->
```

## Sidebar Layout (70/30)

```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" align="center">
<tr>
<td width="400" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:400px; vertical-align:top;">
  <!-- Main content (400px) -->
</div>
<!--[if mso]>
</td>
<td width="20"></td>
<td width="180" valign="top">
<![endif]-->
<div style="display:inline-block; width:100%; max-width:180px; vertical-align:top;">
  <!-- Sidebar (180px) -->
</div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

## Responsive Stacking Pattern

All multi-column layouts above stack on mobile via `display:inline-block` + `max-width`.
Add a media query for explicit mobile override:

```css
@media only screen and (max-width: 599px) {
  .column { display: block !important; width: 100% !important; max-width: 100% !important; }
  .column-pad { padding: 10px 20px !important; }
}
```

Apply class `column` to the `<div>` wrappers and `column-pad` to inner `<td>` elements.
