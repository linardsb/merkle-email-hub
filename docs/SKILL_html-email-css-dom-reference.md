# HTML Email — Complete CSS & DOM Tag Rendering Reference

> A comprehensive reference of every CSS property, DOM element, and email-specific attribute used in HTML email development, with client support matrices and rendering notes.

---

## TABLE OF CONTENTS

1. [HTML DOCTYPE & Root Elements](#1-html-doctype--root-elements)
2. [Head Meta Tags](#2-head-meta-tags)
3. [Structural DOM Tags](#3-structural-dom-tags)
4. [Typography DOM Tags](#4-typography-dom-tags)
5. [Media DOM Tags](#5-media-dom-tags)
6. [CSS — Box Model Properties](#6-css--box-model-properties)
7. [CSS — Typography Properties](#7-css--typography-properties)
8. [CSS — Background Properties](#8-css--background-properties)
9. [CSS — Border Properties](#9-css--border-properties)
10. [CSS — Display & Layout Properties](#10-css--display--layout-properties)
11. [CSS — Color & Visibility](#11-css--color--visibility)
12. [CSS — Positioning](#12-css--positioning)
13. [CSS — List Properties](#13-css--list-properties)
14. [CSS — At-Rules & Media Queries](#14-css--at-rules--media-queries)
15. [MSO / VML Proprietary Properties](#15-mso--vml-proprietary-properties)
16. [HTML Attributes (Email-Specific)](#16-html-attributes-email-specific)
17. [VML Elements](#17-vml-elements)
18. [Dark Mode CSS](#18-dark-mode-css)
19. [CSS Selectors — Support Matrix](#19-css-selectors--support-matrix)
20. [Complete Client Support Legend](#20-complete-client-support-legend)

---

## CLIENT ABBREVIATIONS

| Code | Client |
|------|--------|
| OL07–19 | Outlook 2007–2019 (Word engine) |
| OL365 | Outlook 365 Desktop (Word engine, pre-2026) |
| OLnew | New Outlook (EdgeHTML, 2026+) |
| OLweb | Outlook.com (webmail) |
| GM | Gmail (webmail + app) |
| APM | Apple Mail (macOS + iOS) |
| YM | Yahoo Mail |
| TB | Thunderbird |
| SAMS | Samsung Mail |
| HE | HEY Email |

Support values: ✅ Full | ⚠️ Partial | ❌ None | 🔧 With workaround

---

## 1. HTML DOCTYPE & Root Elements

### `<!DOCTYPE html>`

```html
<!DOCTYPE html>
```

| Client | Support | Notes |
|--------|---------|-------|
| OL07–19 | ⚠️ | Ignored; Word engine uses its own renderer |
| GM | ✅ | Required for consistent rendering |
| APM | ✅ | Full |
| YM | ✅ | Full |
| OLweb | ✅ | Full |

**Best practice:** Always include. Some clients strip it, but it anchors rendering elsewhere.

---

### `<html>`

```html
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
```

| Attribute | Purpose | Renders In |
|-----------|---------|-----------|
| `lang` | Screen reader language declaration | All clients |
| `xmlns:v` | Enables VML namespace | OL07–365 |
| `xmlns:o` | Enables Office XML namespace | OL07–365 |

---

### `<head>`

Standard. Required. No client-specific rendering issues.

---

### `<body>`

```html
<body style="margin:0; padding:0; background-color:#f4f4f4;">
```

| Property | OL07–19 | GM | APM | YM | OLweb |
|----------|---------|-----|-----|-----|-------|
| `margin` | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `padding` | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `background-color` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `background-image` | ❌ | ✅ | ✅ | ✅ | ✅ |

**Note:** Gmail strips `<body>` tag and replaces it with a `<div>`. Always use a wrapper `<table>` with matching background color.

---

## 2. Head Meta Tags

All `<meta>` tags are placed inside `<head>`. Gmail and some clients strip `<head>` contents, so these tags only apply to clients that preserve the `<head>`.

| Tag | Renders In | Purpose |
|-----|-----------|---------|
| `<meta charset="utf-8">` | All | Character encoding |
| `<meta http-equiv="Content-Type" content="text/html; charset=utf-8">` | All | Legacy encoding fallback |
| `<meta http-equiv="X-UA-Compatible" content="IE=edge">` | OL07–19, IE | Forces Edge rendering mode |
| `<meta name="viewport" content="width=device-width, initial-scale=1.0">` | APM, SAMS, OLweb | Mobile scaling |
| `<meta name="x-apple-disable-message-reformatting">` | APM iOS | Prevents iOS auto-scaling text |
| `<meta name="format-detection" content="telephone=no">` | APM iOS | Disables phone number auto-linking |
| `<meta name="format-detection" content="date=no">` | APM iOS | Disables date auto-linking |
| `<meta name="format-detection" content="address=no">` | APM iOS | Disables address auto-linking |
| `<meta name="format-detection" content="email=no">` | APM iOS | Disables email auto-linking |
| `<meta name="color-scheme" content="light dark">` | APM, OLweb | Declares dark mode support |
| `<meta name="supported-color-schemes" content="light dark">` | APM | Apple-specific dark mode declaration |
| `<meta name="robots" content="noindex, nofollow">` | Webmail clients | Prevents search indexing |

---

## 3. Structural DOM Tags

### `<table>`

The **primary layout element** in HTML email. Replaces `<div>` as the layout primitive.

```html
<table role="presentation" border="0" cellpadding="0" cellspacing="0" width="600">
```

| CSS Property | OL07–19 | GM | APM | YM | OLweb |
|-------------|---------|-----|-----|-----|-------|
| `width` (attribute) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `width` (CSS) | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `max-width` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `background-color` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `background-image` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `border-collapse` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `border-spacing` | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `align` (attribute) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `padding` | ❌ | ✅ | ✅ | ✅ | ✅ |

**Required attributes:**
- `role="presentation"` — Accessibility; tells screen readers it is layout-only
- `border="0"` — Removes default cell borders in all clients
- `cellpadding="0"` — Removes default cell padding
- `cellspacing="0"` — Removes default cell spacing
- `width` — Set as HTML attribute AND inline CSS

---

### `<tr>`

| CSS Property | OL07–19 | GM | APM | YM | Notes |
|-------------|---------|-----|-----|-----|-------|
| `background-color` | ⚠️ | ✅ | ✅ | ✅ | Apply to `<td>` instead for safety |
| `height` | ⚠️ | ✅ | ✅ | ✅ | Use attribute `height` for Outlook |
| `vertical-align` | ❌ | ✅ | ✅ | ✅ | Use `valign` attribute |
| `display` | ❌ | ✅ | ✅ | ✅ | Avoid; breaks table model |

---

### `<td>`

The **primary content/spacing container** in email.

```html
<td align="left" valign="top" width="300" style="padding:20px; background-color:#ffffff;">
```

| CSS Property | OL07–19 | GM | APM | YM | OLweb |
|-------------|---------|-----|-----|-----|-------|
| `padding` | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `padding-top/right/bottom/left` | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `width` (attribute) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `width` (CSS) | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `height` (attribute) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `background-color` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `background-image` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `vertical-align` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `text-align` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `border` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `border-radius` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `font-family` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `font-size` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `color` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `line-height` | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `white-space` | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `word-break` | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| `overflow` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `display:block` | ❌ | ✅ | ✅ | ✅ | ✅ |

**Required attributes on `<td>`:**
- `align` — Use HTML attribute (`left`, `center`, `right`)
- `valign` — Use HTML attribute (`top`, `middle`, `bottom`)

---

### `<div>`

⚠️ **Avoid for layout.** Use only for grouping inline content or as Ghost Table wrappers for non-Outlook clients.

| CSS Property | OL07–19 | GM | APM | YM | Notes |
|-------------|---------|-----|-----|-----|-------|
| `width` | ❌ | ✅ | ✅ | ✅ | Ignored as layout |
| `max-width` | ❌ | ✅ | ✅ | ✅ | Use on wrapper for fluid |
| `display:inline-block` | ❌ | ✅ | ✅ | ✅ | Use Ghost Tables for OL |
| `background-color` | ⚠️ | ✅ | ✅ | ✅ | Apply to `<td>` instead |
| `margin` | ❌ | ✅ | ✅ | ✅ | Use `<td>` padding |
| `padding` | ⚠️ | ✅ | ✅ | ✅ | Partially supported |

**Acceptable uses in email:**
- Hybrid layout outer wrapper for non-Outlook fallback
- `display:none` toggle containers
- Dark mode color target container

---

### `<span>`

Inline styling container. Widely supported.

| CSS Property | OL07–19 | GM | APM | YM | Notes |
|-------------|---------|-----|-----|-----|-------|
| `color` | ✅ | ✅ | ✅ | ✅ | Full |
| `font-size` | ✅ | ✅ | ✅ | ✅ | Full |
| `font-weight` | ✅ | ✅ | ✅ | ✅ | Full |
| `font-family` | ✅ | ✅ | ✅ | ✅ | Full |
| `display:block` | ⚠️ | ✅ | ✅ | ✅ | Avoid; use `<td>` |
| `background-color` | ✅ | ✅ | ✅ | ✅ | Full |
| `text-decoration` | ✅ | ✅ | ✅ | ✅ | Full |
| `letter-spacing` | ⚠️ | ✅ | ✅ | ✅ | OL may ignore |
| `text-transform` | ⚠️ | ✅ | ✅ | ✅ | OL partial |
| `mso-hide:all` | ✅ | N/A | N/A | N/A | Hides from Outlook only |

---

### `<a>`

```html
<a href="https://example.com" target="_blank" style="color:#6D5FF9; text-decoration:none;">
```

| CSS Property | OL07–19 | GM | APM | YM | Notes |
|-------------|---------|-----|-----|-----|-------|
| `color` | ✅ | ✅ | ✅ | ✅ | Must be inline; `<a>` often overridden by client styles |
| `text-decoration` | ✅ | ✅ | ✅ | ✅ | Inline only reliable |
| `font-size` | ✅ | ✅ | ✅ | ✅ | Inline |
| `font-weight` | ✅ | ✅ | ✅ | ✅ | Inline |
| `display:inline-block` | ⚠️ | ✅ | ✅ | ✅ | For button links |
| `padding` | ⚠️ | ✅ | ✅ | ✅ | OL ignores on `<a>` |
| `border-radius` | ❌ | ✅ | ✅ | ✅ | Use VML for Outlook |
| `background-color` | ⚠️ | ✅ | ✅ | ✅ | OL ignores on `<a>` |
| `line-height` | ✅ | ✅ | ✅ | ✅ | For button height control |
| `width` | ⚠️ | ✅ | ✅ | ✅ | OL partial |
| `-webkit-text-size-adjust:none` | N/A | N/A | ✅ | N/A | Prevents iOS text resize |

**Attribute `target="_blank"`:** Supported everywhere but may be stripped by some clients.

**Apple Data Detectors override:**
```css
a[x-apple-data-detectors] {
  color: inherit !important;
  text-decoration: none !important;
}
```

---

## 4. Typography DOM Tags

### `<p>`

| CSS Property | OL07–19 | GM | APM | YM | Notes |
|-------------|---------|-----|-----|-----|-------|
| `margin` | ⚠️ | ✅ | ✅ | ✅ | OL adds default margin; reset with `margin:0` |
| `padding` | ✅ | ✅ | ✅ | ✅ | Full |
| `font-family` | ✅ | ✅ | ✅ | ✅ | Full |
| `font-size` | ✅ | ✅ | ✅ | ✅ | Full |
| `color` | ✅ | ✅ | ✅ | ✅ | Full |
| `line-height` | ✅ | ✅ | ✅ | ✅ | Use px, not unitless in Outlook |
| `text-align` | ✅ | ✅ | ✅ | ✅ | Full |

**Reset required:** `<p style="margin:0; padding:0;">` — Outlook adds ~16px bottom margin by default.

---

### `<h1>` through `<h6>`

| CSS Property | OL07–19 | GM | APM | YM |
|-------------|---------|-----|-----|-----|
| `font-size` | ✅ | ✅ | ✅ | ✅ |
| `font-weight` | ✅ | ✅ | ✅ | ✅ |
| `font-family` | ✅ | ✅ | ✅ | ✅ |
| `color` | ✅ | ✅ | ✅ | ✅ |
| `margin` | ⚠️ | ✅ | ✅ | ✅ |
| `line-height` | ✅ | ✅ | ✅ | ✅ |
| `text-transform` | ⚠️ | ✅ | ✅ | ✅ |
| `letter-spacing` | ⚠️ | ✅ | ✅ | ✅ |

**Reset:** Always include `style="margin:0;"` on headings to strip Outlook default spacing.

---

### `<strong>`, `<b>`

| Client | Renders | Notes |
|--------|---------|-------|
| All | ✅ | Supported universally |

---

### `<em>`, `<i>`

| Client | Renders | Notes |
|--------|---------|-------|
| All | ✅ | Supported universally |

---

### `<u>`

| Client | Renders | Notes |
|--------|---------|-------|
| All | ✅ | Renders underline universally |

---

### `<s>`, `<del>`, `<strike>`

| Client | Renders | Notes |
|--------|---------|-------|
| OL07–19 | ⚠️ | `<s>` partially; use `<del>` |
| GM | ✅ | Full |
| APM | ✅ | Full |

---

### `<br>`

| Client | Renders | Notes |
|--------|---------|-------|
| All | ✅ | Full. Use for forced line breaks |

**Outlook ghost spacer trick:**
```html
<!--[if true]><br><![endif]-->
```

---

### `<hr>`

| CSS Property | OL07–19 | GM | APM | YM | Notes |
|-------------|---------|-----|-----|-----|-------|
| `border` | ✅ | ✅ | ✅ | ✅ | Full |
| `color` | ✅ | ✅ | ✅ | ✅ | Full |
| `width` | ✅ | ✅ | ✅ | ✅ | Full |
| `height` | ⚠️ | ✅ | ✅ | ✅ | Use border shorthand |

**Best practice:** Use a `<td>` with `border-top` instead of `<hr>` for consistent dividers.

---

### `<ul>`, `<ol>`, `<li>`

| CSS Property | OL07–19 | GM | APM | YM | Notes |
|-------------|---------|-----|-----|-----|-------|
| `margin` | ⚠️ | ✅ | ✅ | ✅ | OL adds extra left margin |
| `padding` | ⚠️ | ✅ | ✅ | ✅ | OL may ignore |
| `list-style-type` | ✅ | ✅ | ✅ | ✅ | Full |
| `list-style-position` | ⚠️ | ✅ | ✅ | ✅ | OL partial |
| `mso-list` | ✅ OL only | N/A | N/A | N/A | Required for Outlook rendering |

**Outlook list fix:**
```html
<ul style="margin:0 0 0 20px; padding:0; mso-padding-alt:0px;">
  <li style="mso-list:l0 level1 lfo1;">List item</li>
</ul>
```

---

### `<blockquote>`

| CSS Property | OL07–19 | GM | APM | YM | Notes |
|-------------|---------|-----|-----|-----|-------|
| `margin` | ⚠️ | ✅ | ✅ | ✅ | OL adds default; reset with `margin:0` |
| `border-left` | ✅ | ✅ | ✅ | ✅ | Common use for callout style |
| `padding-left` | ✅ | ✅ | ✅ | ✅ | Full |

---

### `<pre>`, `<code>`

| CSS Property | OL07–19 | GM | APM | YM | Notes |
|-------------|---------|-----|-----|-----|-------|
| `font-family` | ✅ | ✅ | ✅ | ✅ | Full |
| `white-space` | ⚠️ | ✅ | ✅ | ✅ | OL may wrap |
| `overflow-x` | ❌ | ✅ | ✅ | ✅ | OL ignores |

---

## 5. Media DOM Tags

### `<img>`

```html
<img src="https://example.com/img.png" alt="Description" width="600" height="300"
  style="display:block; max-width:100%; border:0; -ms-interpolation-mode:bicubic;">
```

| Attribute/Property | OL07–19 | GM | APM | YM | Notes |
|-------------------|---------|-----|-----|-----|-------|
| `src` | ✅ | ✅ | ✅ | ✅ | Must be absolute HTTPS URL |
| `alt` | ✅ | ✅ | ✅ | ✅ | Always required |
| `width` (attribute) | ✅ | ✅ | ✅ | ✅ | Required for Outlook |
| `height` (attribute) | ✅ | ✅ | ✅ | ✅ | Required for Outlook |
| `border="0"` | ✅ | ✅ | ✅ | ✅ | Removes linked image border |
| `display:block` | ✅ | ✅ | ✅ | ✅ | Removes phantom gap below |
| `max-width:100%` | ❌ | ✅ | ✅ | ✅ | Fluid responsive |
| `-ms-interpolation-mode:bicubic` | ✅ | N/A | N/A | N/A | Improves OL image scaling |

**Critical rules:**
- Always use absolute HTTPS URLs
- Always set both `width` and `height` as HTML attributes
- Always include `alt` text (empty `alt=""` for decorative images)
- `display:block` eliminates the 2–4px phantom gap below inline images

---

### `<picture>`, `<source>`

| Client | Support | Notes |
|--------|---------|-------|
| APM | ✅ | Full dark mode image switching |
| OLnew | ✅ | Full |
| GM | ❌ | Stripped |
| OL07–365 | ❌ | Stripped |
| YM | ❌ | Stripped |

**Dark mode image swap (APM):**
```html
<picture>
  <source srcset="dark-logo.png" media="(prefers-color-scheme: dark)">
  <img src="light-logo.png" alt="Logo" width="200">
</picture>
```

---

### `<video>`, `<audio>`

| Client | Support | Notes |
|--------|---------|-------|
| APM macOS/iOS | ✅ | Inline video plays |
| OL07–365 | ❌ | Falls back to `<img>` poster |
| GM | ❌ | Stripped |
| OLweb | ❌ | Stripped |

**Fallback structure:**
```html
<video width="600" poster="https://example.com/poster.jpg" controls>
  <source src="https://example.com/video.mp4" type="video/mp4">
  <!-- Fallback for non-supporting clients -->
  <img src="https://example.com/poster.jpg" alt="Watch the video" width="600">
</video>
```

---

## 6. CSS — Box Model Properties

| Property | OL07–19 | GM | APM | YM | OLweb | Notes |
|----------|---------|-----|-----|-----|-------|-------|
| `margin` | ⚠️ | ✅ | ✅ | ✅ | ✅ | Partially on `<p>`, `<h1–6>` |
| `margin-top` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `margin-right` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `margin-bottom` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `margin-left` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `margin:0 auto` | ❌ | ✅ | ✅ | ✅ | ✅ | Use `align="center"` on table for OL |
| `padding` | ✅ on `<td>` | ✅ | ✅ | ✅ | ✅ | On `<td>` only for OL |
| `padding-top` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `padding-right` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `padding-bottom` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `padding-left` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `width` | ✅ on tables | ✅ | ✅ | ✅ | ✅ | Use attribute for OL |
| `height` | ⚠️ | ✅ | ✅ | ✅ | ✅ | OL may override |
| `min-width` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `max-width` | ❌ | ✅ | ✅ | ✅ | ✅ | Use Ghost Tables for OL |
| `min-height` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `max-height` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `box-sizing` | ❌ | ✅ | ✅ | ✅ | ✅ | Avoid in email |
| `overflow` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `overflow-x` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `overflow-y` | ❌ | ✅ | ✅ | ✅ | ✅ | |

---

## 7. CSS — Typography Properties

| Property | OL07–19 | GM | APM | YM | OLweb | Notes |
|----------|---------|-----|-----|-----|-------|-------|
| `font-family` | ✅ | ✅ | ✅ | ✅ | ✅ | Web-safe stack required as fallback |
| `font-size` | ✅ | ✅ | ✅ | ✅ | ✅ | Use px; avoid em/rem |
| `font-weight` | ✅ | ✅ | ✅ | ✅ | ✅ | Use numeric (400, 700) or keyword |
| `font-style` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `font-variant` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `line-height` | ✅ | ✅ | ✅ | ✅ | ✅ | Use px in Outlook; unitless may fail |
| `color` | ✅ | ✅ | ✅ | ✅ | ✅ | Full |
| `text-align` | ✅ | ✅ | ✅ | ✅ | ✅ | Also set as HTML `align` attribute |
| `text-decoration` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `text-transform` | ⚠️ | ✅ | ✅ | ✅ | ✅ | OL partial |
| `letter-spacing` | ⚠️ | ✅ | ✅ | ✅ | ✅ | OL may ignore |
| `word-spacing` | ⚠️ | ✅ | ✅ | ✅ | ✅ | OL may ignore |
| `word-break` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `word-wrap` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `white-space` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `text-indent` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `text-overflow` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `vertical-align` | ✅ on `<td>` | ✅ | ✅ | ✅ | ✅ | |
| `direction` | ⚠️ | ✅ | ✅ | ✅ | ✅ | RTL support varies |
| `unicode-bidi` | ⚠️ | ✅ | ✅ | ✅ | ✅ | RTL support varies |
| `-webkit-text-size-adjust` | N/A | N/A | ✅ | N/A | N/A | Prevents iOS auto-zoom |

### Web Fonts (`@font-face`)

| Client | Support | Notes |
|--------|---------|-------|
| APM macOS/iOS | ✅ | Full |
| Thunderbird | ✅ | Full |
| OLnew | ✅ | Full |
| OLweb | ⚠️ | Variable; some fonts blocked |
| GM | ❌ | Strips `<style>` |
| OL07–365 | ❌ | Falls back to font-family stack |
| YM | ❌ | Strips `@font-face` |

**Web font stack pattern:**
```css
@font-face {
  font-family: 'CustomFont';
  src: url('https://example.com/font.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
}
/* Always include safe fallback stack */
font-family: 'CustomFont', Georgia, 'Times New Roman', serif;
```

---

## 8. CSS — Background Properties

| Property | OL07–19 | GM | APM | YM | OLweb | Notes |
|----------|---------|-----|-----|-----|-------|-------|
| `background-color` | ✅ | ✅ | ✅ | ✅ | ✅ | Full; always use `bgcolor` attribute too |
| `background-image` | ❌ | ✅ | ✅ | ✅ | ✅ | Use VML for Outlook |
| `background-repeat` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `background-position` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `background-size` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `background-attachment` | ❌ | ❌ | ✅ | ❌ | ❌ | Avoid |
| `background` (shorthand) | ⚠️ | ✅ | ✅ | ✅ | ✅ | Split into individual properties for OL |
| `background-clip` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `background-origin` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `linear-gradient` | ❌ | ✅ | ✅ | ✅ | ✅ | Use solid color fallback |
| `radial-gradient` | ❌ | ✅ | ✅ | ✅ | ✅ | Use solid color fallback |

**`bgcolor` HTML attribute:**

Always pair CSS `background-color` with the HTML attribute `bgcolor` on `<table>` and `<td>` for maximum client coverage:
```html
<td bgcolor="#ffffff" style="background-color:#ffffff;">
```

---

## 9. CSS — Border Properties

| Property | OL07–19 | GM | APM | YM | OLweb | Notes |
|----------|---------|-----|-----|-----|-------|-------|
| `border` | ✅ | ✅ | ✅ | ✅ | ✅ | Full |
| `border-top` | ✅ | ✅ | ✅ | ✅ | ✅ | Full; used for dividers |
| `border-right` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `border-bottom` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `border-left` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `border-color` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `border-width` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `border-style` | ✅ | ✅ | ✅ | ✅ | ✅ | |
| `border-radius` | ❌ | ✅ | ✅ | ✅ | ✅ | Use VML for Outlook |
| `border-collapse` | ✅ | ✅ | ✅ | ✅ | ✅ | Required on `<table>` |
| `border-spacing` | ⚠️ | ✅ | ✅ | ✅ | ✅ | Use `cellspacing="0"` for OL |
| `outline` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `box-shadow` | ❌ | ✅ | ✅ | ✅ | ✅ | |

---

## 10. CSS — Display & Layout Properties

| Property | OL07–19 | GM | APM | YM | OLweb | Notes |
|----------|---------|-----|-----|-----|-------|-------|
| `display:block` | ⚠️ | ✅ | ✅ | ✅ | ✅ | On `<img>` works; others partial |
| `display:inline` | ⚠️ | ✅ | ✅ | ✅ | ✅ | |
| `display:inline-block` | ❌ | ✅ | ✅ | ✅ | ✅ | Use Ghost Tables for OL |
| `display:none` | ✅ | ✅ | ✅ | ✅ | ✅ | Full; used for hiding content |
| `display:flex` | ❌ | ✅ | ✅ | ✅ | ✅ | Avoid in email |
| `display:grid` | ❌ | ❌ | ✅ | ❌ | ❌ | APM only; avoid |
| `display:table` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `display:table-cell` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `float` | ❌ | ✅ | ✅ | ✅ | ✅ | Avoid; use tables instead |
| `clear` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `position:relative` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `position:absolute` | ❌ | ⚠️ | ✅ | ⚠️ | ⚠️ | Avoid; unpredictable |
| `position:fixed` | ❌ | ❌ | ❌ | ❌ | ❌ | Never use |
| `top/right/bottom/left` | ❌ | ⚠️ | ✅ | ⚠️ | ⚠️ | Paired with position |
| `z-index` | ❌ | ⚠️ | ✅ | ⚠️ | ⚠️ | |
| `flexbox` (all) | ❌ | ✅ | ✅ | ✅ | ✅ | Avoid; use table layout |
| `grid` (all) | ❌ | ❌ | ✅ | ❌ | ❌ | APM only |
| `gap` | ❌ | ❌ | ✅ | ❌ | ❌ | |
| `align-items` | ❌ | ✅ | ✅ | ✅ | ✅ | Avoid in email |
| `justify-content` | ❌ | ✅ | ✅ | ✅ | ✅ | Avoid in email |
| `vertical-align` | ✅ on `<td>` | ✅ | ✅ | ✅ | ✅ | |

---

## 11. CSS — Color & Visibility

| Property | OL07–19 | GM | APM | YM | OLweb | Notes |
|----------|---------|-----|-----|-----|-------|-------|
| `color` | ✅ | ✅ | ✅ | ✅ | ✅ | Full; hex preferred |
| `opacity` | ❌ | ✅ | ✅ | ✅ | ✅ | Use rgba() fallback |
| `visibility:hidden` | ❌ | ✅ | ✅ | ✅ | ✅ | Space is preserved; use `display:none` |
| `visibility:visible` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| `filter` | ❌ | ✅ | ✅ | ✅ | ✅ | Avoid |
| `rgba()` color values | ❌ | ✅ | ✅ | ✅ | ✅ | Provide hex fallback for OL |
| `hsla()` color values | ❌ | ✅ | ✅ | ✅ | ✅ | Provide hex fallback for OL |
| `currentColor` | ❌ | ✅ | ✅ | ✅ | ✅ | |
| CSS variables (`--var`) | ❌ | ❌ | ✅ | ❌ | ❌ | APM only; avoid |

---

## 12. CSS — Positioning

| Property | OL07–19 | GM | APM | YM | Notes |
|----------|---------|-----|-----|-----|-------|
| `position:static` | ✅ | ✅ | ✅ | ✅ | Default; always safe |
| `position:relative` | ❌ | ✅ | ✅ | ✅ | Avoid in email |
| `position:absolute` | ❌ | ⚠️ | ✅ | ⚠️ | Avoid; use table structure |
| `position:fixed` | ❌ | ❌ | ❌ | ❌ | Never use |
| `position:sticky` | ❌ | ❌ | ❌ | ❌ | Never use |

---

## 13. CSS — List Properties

| Property | OL07–19 | GM | APM | YM | Notes |
|----------|---------|-----|-----|-----|-------|
| `list-style-type` | ✅ | ✅ | ✅ | ✅ | Full |
| `list-style-position` | ⚠️ | ✅ | ✅ | ✅ | OL partial |
| `list-style-image` | ❌ | ✅ | ✅ | ✅ | Use `<img>` inline instead |
| `list-style` (shorthand) | ⚠️ | ✅ | ✅ | ✅ | OL partial |
| `mso-list` | ✅ OL only | N/A | N/A | N/A | Required for Outlook list rendering |

---

## 14. CSS — At-Rules & Media Queries

| Rule | OL07–19 | GM | APM | YM | OLweb | Notes |
|------|---------|-----|-----|-----|-------|-------|
| `@media` | ❌ | ❌ | ✅ | ✅ | ✅ | GM strips `<style>`; use inline |
| `@media (max-width)` | ❌ | ❌ | ✅ | ✅ | ✅ | Responsive breakpoint |
| `@media (min-width)` | ❌ | ❌ | ✅ | ✅ | ✅ | |
| `@media (prefers-color-scheme: dark)` | ❌ | ❌ | ✅ | ❌ | ✅ | Dark mode |
| `@media screen` | ❌ | ❌ | ✅ | ✅ | ✅ | |
| `@media print` | ❌ | ❌ | ✅ | ✅ | ✅ | |
| `@font-face` | ❌ | ❌ | ✅ | ❌ | ⚠️ | Custom web fonts |
| `@keyframes` | ❌ | ❌ | ✅ | ❌ | ❌ | CSS animations in APM only |
| `@supports` | ❌ | ❌ | ✅ | ❌ | ❌ | Feature queries; APM only |
| `@import` | ❌ | ❌ | ⚠️ | ❌ | ❌ | Avoid; unreliable |

**Inline CSS is the only universally safe CSS delivery method.** `<style>` block in `<head>` is supported by APM, YM, OLweb, TB, SAMS — but stripped by Gmail.

---

## 15. MSO / VML Proprietary Properties

These are Outlook-only CSS extensions rendered by the Word engine.

| Property | Purpose | Example |
|----------|---------|---------|
| `mso-table-lspace` | Removes left table spacing | `mso-table-lspace:0pt` |
| `mso-table-rspace` | Removes right table spacing | `mso-table-rspace:0pt` |
| `mso-padding-alt` | Alternative padding for lists | `mso-padding-alt:0px` |
| `mso-element` | Positions special elements | `mso-element:para-border-div` |
| `mso-line-height-rule` | Controls line-height calculation | `mso-line-height-rule:exactly` |
| `mso-list` | Enables proper list formatting | `mso-list:l0 level1 lfo1` |
| `mso-hide:all` | Hides element in Outlook only | `mso-hide:all` |
| `mso-color-alt` | Alt color for dark mode in OL | `mso-color-alt:#ffffff` |
| `mso-font-width` | Font scaling percentage | `mso-font-width:100%` |
| `mso-text-raise` | Vertical offset for superscripts | `mso-text-raise:4pt` |
| `mso-border-alt` | Border alternative for Outlook | `mso-border-alt:none` |
| `mso-padding-top-alt` | Top padding override | `mso-padding-top-alt:0px` |
| `mso-cellspacing` | Cell spacing for tables | `mso-cellspacing:0` |
| `mso-table-overlap` | Table overlap control | `mso-table-overlap:never` |
| `mso-width-percent` | Width as percent in Outlook | `mso-width-percent:100` |

### Key MSO Conditional Comment Structure

```html
<!-- Target ALL Outlook desktop -->
<!--[if mso]> ... <![endif]-->

<!-- Target Outlook 2007+ (all desktop) -->
<!--[if gte mso 9]> ... <![endif]-->

<!-- Target Outlook 2016+ -->
<!--[if gte mso 14]> ... <![endif]-->

<!-- Exclude Outlook desktop (show to everyone else) -->
<!--[if !mso]><!--> ... <!--<![endif]-->

<!-- Target IE (webmail fallback) -->
<!--[if (gte mso 9)|(IE)]> ... <![endif]-->
```

---

## 16. HTML Attributes (Email-Specific)

These HTML attributes are essential in email because they work where CSS fails.

| Element | Attribute | Purpose | Notes |
|---------|-----------|---------|-------|
| `<html>` | `lang` | Screen reader language | Always include |
| `<html>` | `xmlns:v` | Enables VML | Required for VML |
| `<html>` | `xmlns:o` | Enables Office XML | Required for MSO conditionals |
| `<table>` | `width` | Sets table width | Use alongside CSS |
| `<table>` | `border` | Removes default borders | Always `border="0"` |
| `<table>` | `cellpadding` | Removes cell padding | Always `cellpadding="0"` |
| `<table>` | `cellspacing` | Removes cell spacing | Always `cellspacing="0"` |
| `<table>` | `align` | Horizontal alignment | `center` for centering |
| `<table>` | `bgcolor` | Background color | Use with CSS for OL |
| `<table>` | `role` | Accessibility role | `role="presentation"` |
| `<td>` | `width` | Cell width | Required for Outlook |
| `<td>` | `height` | Cell height | For spacers |
| `<td>` | `align` | Horizontal alignment | `left`, `center`, `right` |
| `<td>` | `valign` | Vertical alignment | `top`, `middle`, `bottom` |
| `<td>` | `bgcolor` | Background color | Use with CSS |
| `<td>` | `colspan` | Column span | Full support |
| `<td>` | `rowspan` | Row span | Full support |
| `<img>` | `src` | Image source | Must be absolute HTTPS |
| `<img>` | `alt` | Alt text | Always include |
| `<img>` | `width` | Image width | Required for Outlook |
| `<img>` | `height` | Image height | Required for Outlook |
| `<img>` | `border` | Image border | Always `border="0"` |
| `<a>` | `href` | Link destination | Must include `https://` |
| `<a>` | `target` | Link target | `_blank` for new tab |
| `<a>` | `title` | Tooltip / accessibility | Describe the link |
| `<a>` | `x-apple-data-detectors` | Apple override | CSS selector targeting |
| `<body>` | `bgcolor` | Body background | Pair with CSS |

---

## 17. VML Elements

VML (Vector Markup Language) renders in Outlook 2007–2019 and Outlook 365 Desktop only. All VML must be wrapped in MSO conditional comments.

### Required Namespace Declarations

```html
<html xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
```

### VML Element Reference

| Element | Purpose | Key Attributes |
|---------|---------|---------------|
| `<v:rect>` | Rectangle shape | `style`, `fill`, `stroke` |
| `<v:roundrect>` | Rounded rectangle (buttons) | `arcsize`, `fillcolor`, `strokecolor`, `href` |
| `<v:fill>` | Fill a shape | `type`, `src`, `color` |
| `<v:textbox>` | Text inside a shape | `style`, `inset` |
| `<v:image>` | VML image | `src`, `style` |
| `<v:oval>` | Oval shape | `style`, `fillcolor` |
| `<v:line>` | Line element | `from`, `to`, `strokecolor` |
| `<v:group>` | Group of VML shapes | `style`, `coordsize` |
| `<w:anchorlock/>` | Prevents Outlook resizing buttons | (self-closing, inside `<v:roundrect>`) |

### `<v:fill>` Type Values

| Type | Effect |
|------|--------|
| `frame` | Single centered image (background image) |
| `tile` | Tiling/repeating image |
| `solid` | Solid color only |
| `gradient` | Gradient fill |

### Ghost Table Pattern (Multi-column Outlook fix)

```html
<!--[if (gte mso 9)|(IE)]>
<table border="0" cellpadding="0" cellspacing="0" width="600">
  <tr>
    <td width="300" valign="top">
<![endif]-->
  <!-- Column 1 content -->
<!--[if (gte mso 9)|(IE)]>
    </td>
    <td width="300" valign="top">
<![endif]-->
  <!-- Column 2 content -->
<!--[if (gte mso 9)|(IE)]>
    </td>
  </tr>
</table>
<![endif]-->
```

---

## 18. Dark Mode CSS

### Standard Dark Mode (APM, Samsung Mail)

```css
@media (prefers-color-scheme: dark) {
  .dark-bg { background-color: #1a1a2e !important; }
  .dark-text { color: #ffffff !important; }
  .dark-img { display: none !important; }
  .light-img { display: block !important; }
}
```

### Outlook.com / Outlook Mobile Dark Mode Selectors

| Selector | Targets | Use For |
|----------|---------|---------|
| `[data-ogsb]` | Background color overrides | Background dark mode |
| `[data-ogsc]` | Text/foreground color overrides | Text dark mode |
| `[data-ogsb] .class` | Elements with background in dark OL | Scoped background overrides |
| `[data-ogsc] .class` | Elements with text in dark OL | Scoped text overrides |

### Logo / Image Dark Mode Swap

```html
<!-- Method 1: Picture element (APM only) -->
<picture>
  <source srcset="logo-dark.png" media="(prefers-color-scheme: dark)">
  <img src="logo-light.png" alt="Logo" width="200">
</picture>

<!-- Method 2: CSS show/hide (APM + partial OLweb) -->
<img src="logo-light.png" class="light-mode-img" alt="Logo" width="200">
<img src="logo-dark.png" class="dark-mode-img" alt="Logo" width="200"
  style="display:none;">
```

### `mso-color-alt` (Outlook-specific dark mode text)

```html
<p style="color:#000000; mso-color-alt:#ffffff;">
  This text appears white in Outlook dark mode.
</p>
```

---

## 19. CSS Selectors — Support Matrix

| Selector Type | Example | OL07–19 | GM | APM | YM | OLweb |
|---------------|---------|---------|-----|-----|-----|-------|
| Inline style | `style="color:red"` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Class | `.class {}` | ⚠️ | ❌ | ✅ | ✅ | ✅ |
| ID | `#id {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Element | `p {}` | ⚠️ | ❌ | ✅ | ✅ | ✅ |
| Descendant | `td p {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Child | `table > td {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Adjacent sibling | `td + td {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| General sibling | `td ~ td {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Attribute | `a[href] {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Attribute value | `[data-ogsb] {}` | N/A | N/A | N/A | N/A | ✅ |
| Pseudo-class `:hover` | `a:hover {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Pseudo-class `:focus` | `a:focus {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Pseudo-class `:first-child` | `td:first-child {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Pseudo-class `:last-child` | `td:last-child {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Pseudo-class `:nth-child` | `td:nth-child(2) {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Pseudo-class `:not()` | `td:not(.skip) {}` | ❌ | ❌ | ✅ | ✅ | ✅ |
| Pseudo-element `::before` | `p::before {}` | ❌ | ❌ | ✅ | ❌ | ❌ |
| Pseudo-element `::after` | `p::after {}` | ❌ | ❌ | ✅ | ❌ | ❌ |
| Universal | `* {}` | ❌ | ❌ | ✅ | ✅ | ✅ |

**Rule:** If a selector is not fully inline, treat it as progressive enhancement only. Gmail (the largest client) strips all `<style>` blocks — inline CSS is the only guaranteed delivery method.

---

## 20. Complete Client Support Legend

| Client | `<style>` block | Media queries | `@font-face` | Dark mode CSS | VML | AMP |
|--------|----------------|---------------|--------------|---------------|-----|-----|
| Outlook 2007–2019 | ⚠️ partial | ❌ | ❌ | `mso-color-alt` | ✅ | ❌ |
| Outlook 365 Desktop | ⚠️ partial | ❌ | ❌ | `mso-color-alt` | ✅ | ❌ |
| New Outlook (2026) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Outlook.com | ✅ | ✅ | ⚠️ | `[data-ogsb/ogsc]` | ❌ | ❌ |
| Gmail (webmail) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Gmail (iOS/Android) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Apple Mail (macOS) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Apple Mail (iOS) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Yahoo Mail | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Thunderbird | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Samsung Mail | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| HEY | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

---

## Quick Reference: The 10 Golden Rules of HTML Email CSS

1. **Inline CSS always** — It's the only truly universal delivery method
2. **Tables for layout** — Not divs, not flexbox, not grid
3. **Use HTML attributes alongside CSS** — `width`, `height`, `align`, `valign`, `bgcolor`, `border`
4. **Always set even-number px on font-size and line-height** — Prevents Outlook white lines
5. **VML for everything Outlook can't do** — Background images, rounded buttons, shapes
6. **MSO conditionals gate Outlook-specific code** — Ghost tables, VML, font overrides
7. **Progressive enhancement** — Design for Gmail (worst case), enhance for APM (best case)
8. **Reset all default margins on `<p>` and `<h1–6>`** — Outlook adds its own
9. **Dark mode uses two systems** — `@media (prefers-color-scheme)` for most clients; `[data-ogsb/ogsc]` for Outlook.com
10. **All image URLs must be absolute HTTPS** — Outlook 365 webmail rejects HTTP

---

*Reference compiled for HTML email development as of 2026. Outlook desktop Word engine transitions to EdgeHTML in October 2026, after which VML requirements will diminish.*
