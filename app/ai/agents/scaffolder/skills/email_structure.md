---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_html-email-components.md sections 1, 3-6, 9-10 -->
<!-- Last synced: 2026-03-13 -->

# Email Structure — Document Skeleton & Core Components

## Document Structure

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
  <meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
  <meta name="x-apple-disable-message-reformatting">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <title>Email Title</title>
</head>
<body style="margin:0; padding:0; background-color:#ffffff;
  -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; word-spacing:normal;">
```

### Required Meta Tags
- `format-detection` — Prevents iOS auto-linking of phone numbers, dates, addresses
- `x-apple-disable-message-reformatting` — Prevents Apple Mail from scaling/resizing
- `color-scheme` + `supported-color-schemes` — Dark mode declaration (MANDATORY)
- `-webkit-text-size-adjust: 100%` — Prevents text resizing in iOS Mail
- `word-spacing: normal` — Fixes spacing bug in Outlook.com

## Preheader / Preview Text

```html
<!-- Visible preheader (above header, doubles as inbox preview) -->
<div style="font-size:14px; color:#666; padding:8px 20px;">Preview text here</div>

<!-- Hidden preheader (inbox preview only) -->
<div style="display:none; max-height:0; overflow:hidden; mso-hide:all;">
  Preview text here
  &zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;
  <!-- Repeat ~100 times to flush trailing content from preview -->
</div>
```

- Character limit: 35–140 characters depending on client and device
- `&zwnj;&nbsp;` padding flushes footer text from preview window

## Header Components

```html
<!-- Logo -->
<img src="https://placehold.co/200x50" alt="Company Name"
  width="200" height="50"
  style="display:block; border:0; outline:none; text-decoration:none;">

<!-- View in browser -->
<a href="https://example.com/mirror" style="color:#999; font-size:12px; text-decoration:underline;">
  View in browser
</a>
```

**Logo requirements:** All 5 attributes mandatory — `width`, `height`, `alt`, `border="0"`, `display:block`.

## Hero / Banner Section

```html
<!-- Bulletproof background image hero -->
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
  style="width:600px; height:300px;">
<v:fill type="frame" src="https://placehold.co/600x300" color="#333" />
<v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->
<td style="background-image:url('https://placehold.co/600x300');
  background-size:cover; background-position:center; padding:40px 20px;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
    <tr>
      <td role="heading" aria-level="1" style="color:#fff; font-family:Arial,sans-serif; font-size:28px; font-weight:bold; line-height:1.3; mso-line-height-rule:exactly;">
        Hero Headline
      </td>
    </tr>
  </table>
</td>
<!--[if mso]>
</v:textbox>
</v:rect>
<![endif]-->
```

Text overlay uses table cell padding/alignment (not CSS positioning).

## Image Handling

| Rule | Detail |
|------|--------|
| `width` + `height` HTML attrs | Prevents layout collapse when images are off |
| `border="0"` | Removes blue link borders in older clients |
| `display:block` | Removes phantom gaps below images |
| `alt` text styling | Style `alt` text (font, color, size) for image-off rendering |
| Retina images | Serve 2x resolution, constrain with `width` attribute |
| Animated GIFs | First frame shown in Outlook — make first frame meaningful |
| `<picture>` dark swap | Apple Mail only: `<source media="(prefers-color-scheme: dark)">` |

## Footer Components

```html
<td style="padding:20px; text-align:center; font-family:Arial,sans-serif; font-size:12px; color:#999;">
  <a href="https://example.com/unsubscribe" style="color:#999; text-decoration:underline;">Unsubscribe</a> |
  <a href="https://example.com/preferences" style="color:#999; text-decoration:underline;">Preferences</a> |
  <a href="https://example.com/privacy" style="color:#999; text-decoration:underline;">Privacy</a>
  <br>
  <span style="display:block; padding-top:10px;">Company Name, 123 Street, City, State 12345</span>
</td>
```

**Legally required:** Unsubscribe link (CAN-SPAM, GDPR, CASL), physical address (CAN-SPAM), privacy link (GDPR/CCPA).

## Accessibility Baseline

| Requirement | Implementation |
|-------------|---------------|
| `lang` attribute | `<html lang="en">` — NEVER omit |
| `dir` attribute | `<html dir="ltr">` (or `rtl` for RTL languages) |
| Layout tables | `role="presentation"` on ALL layout `<table>` elements |
| Content wrapper | `role="article"` + `aria-roledescription="email"` |
| Images | `alt=""` decorative, descriptive `alt` on content images |
| Headings | `<td>` with larger `font-size` + `font-weight:bold` + `role="heading"` + `aria-level="N"` — NO `<h1>`-`<h6>` tags |
| Font size | Minimum 14px–16px for body copy |
| Tap targets | Minimum 44x44px for mobile |
| Color contrast | 4.5:1 minimum for text |
| Hidden text | `mso-hide:all; position:absolute; overflow:hidden;` for screen reader text |

## Bulletproof Buttons

### Padding-Based (simplest)
```html
<a href="https://example.com" style="display:inline-block; padding:12px 24px;
  background-color:#007bff; color:#fff; text-decoration:none; font-family:Arial,sans-serif;
  font-size:16px; font-weight:bold; border-radius:4px;">
  Button Text
</a>
```

### Table-Cell (most reliable)
```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td bgcolor="#007bff" style="background-color:#007bff; border-radius:4px; padding:12px 24px;">
      <a href="https://example.com" style="color:#fff; text-decoration:none;
        font-family:Arial,sans-serif; font-size:16px; font-weight:bold; display:inline-block;">
        Button Text
      </a>
    </td>
  </tr>
</table>
```

Use VML `<v:roundrect>` for Outlook rounded buttons (see MSO/VML reference).