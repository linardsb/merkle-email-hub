---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_email-spam-score-dom-reference.md sections 3, 4, 5, 7, 8, 11, 13 -->
<!-- Last synced: 2026-03-13 -->

# Spam Patterns — HTML/DOM Level Detection — L3 Reference

## Forbidden/High-Risk Tags — Strong Spam Signals

These tags trigger strong negative scoring or outright rejection.

| Tag | Impact | Reason |
|-----|--------|--------|
| `<script>`, `<script src>` | SEVERE | JavaScript = malicious intent |
| `<iframe>`, `<iframe src>` | SEVERE | External content loading = phishing |
| `<object>`, `<embed>` | SEVERE | Executable/media content |
| `<applet>` | SEVERE | Java applets = malware |
| `<form>`, `<input>`, `<select>`, `<textarea>` | HIGH | Credential capture = phishing |
| `<meta http-equiv="refresh">` | SEVERE | Auto-redirect = phishing |
| `<base href>` | HIGH | Disguises link destinations |
| `<link rel="stylesheet">` | MODERATE | External resource loading |
| `<marquee>`, `<blink>` | MODERATE | Classic spam aesthetics |
| `<bgsound>`, `<video autoplay>`, `<audio autoplay>` | HIGH-MODERATE | Auto-playing media |

**Exception:** `<input>` + `<label>` for CSS checkbox hacks without `<form>` wrapper are less heavily flagged.
**Exception:** `@import` in `<style>` is MODERATE negative — the `<style>` block itself is fine.

Rule: `spam-forbidden-tag` (severity: critical for SEVERE tags, warning for MODERATE)

## Hidden Content CSS — Strong Negative Signals

Spam filters parse inline `style` attributes on every element.

| CSS Pattern | Impact | Rule |
|------------|--------|------|
| `display: none` on text elements | HIGH | `spam-hidden-text-display` |
| `visibility: hidden` on text elements | HIGH | `spam-hidden-text-visibility` |
| `opacity: 0` on text elements | HIGH | `spam-hidden-text-opacity` |
| `font-size: 0` / `font-size: 0px` | SEVERE | `spam-hidden-text-fontsize` |
| `font-size: 1px` | HIGH | `spam-hidden-text-tiny` |
| `line-height: 0` on text | HIGH | `spam-hidden-text-lineheight` |
| `color` matching `background-color` | SEVERE | `spam-hidden-text-color-match` |
| `color: transparent` | HIGH | `spam-hidden-text-transparent` |
| `text-indent: -9999px` | HIGH | `spam-hidden-text-indent` |
| `position: absolute; left: -9999px` | HIGH | `spam-hidden-text-offscreen` |
| `height: 0; width: 0; overflow: hidden` on text | HIGH | `spam-hidden-text-zero-dim` |

### Legitimate Hidden Content (NOT spam)
- Hidden preheader: `max-height: 0; overflow: hidden; mso-hide: all` — single instance at top
- Responsive show/hide: `display: none` in `@media` queries
- Spacer cells: `font-size: 1px; line-height: 1px` with `&nbsp;`
- Screen-reader-only text: `clip: rect(0,0,0,0)` with `position: absolute`

**Key distinction:** Legitimate hidden content is structural (spacing, responsive, preheader). Spam hidden content is textual (keywords, invisible copy, hidden links).

## Link URL Patterns — Spam Signals

| Pattern | Impact | Rule |
|---------|--------|------|
| URL shorteners (`bit.ly`, `t.co`, `goo.gl`, `tinyurl.com`) | MODERATE-HIGH | `spam-link-shortener` |
| IP address URLs (`http://192.168.1.1/...`) | HIGH | `spam-link-ip-address` |
| Hex-encoded URLs (`http://%68%65%6C%6C%6F.com`) | SEVERE | `spam-link-encoded` |
| Display text ≠ href destination (phishing mismatch) | SEVERE | `spam-link-mismatch` |
| `href` containing `@` (`http://legit.com@evil.com`) | SEVERE | `spam-link-at-sign` |
| URLs >200 characters | MODERATE | `spam-link-long-url` |
| Suspicious TLDs (`.xyz`, `.top`, `.click`, `.buzz`, `.tk`) | MODERATE | `spam-link-suspicious-tld` |
| `data:` URIs in `href` | SEVERE | `spam-link-data-uri` |
| `javascript:` in `href` | SEVERE | `spam-link-javascript` |
| Mixed HTTP and HTTPS links | SLIGHT | `spam-link-mixed-protocol` |

### Link Density
- Too many links relative to text — Negative
- All-link email (just images with links, no text) — HIGH negative
- SpamAssassin: >10–15 links in short email may trigger scoring

### Positive Link Signals
- HTTPS links, consistent sender domain, unsubscribe link, `mailto:` links

## Image-to-Text Ratio — SpamAssassin Rules

| Ratio | SpamAssassin Rule | Impact |
|-------|-------------------|--------|
| 0–20% text | `HTML_IMAGE_RATIO_02` | Negative |
| 20–40% text | `HTML_IMAGE_RATIO_04` | Slight negative |
| 40–60% text | `HTML_IMAGE_RATIO_06` | Neutral |
| 60–80% text | `HTML_IMAGE_RATIO_08` | Neutral-positive |
| 0–400 bytes text with images | `HTML_IMAGE_ONLY_04` | Negative |

**Recommended:** At least 60% text content, 40% or less images.

Rule: `spam-image-text-ratio` — flag when text ratio drops below 40% (severity: warning)

### Image Source Signals
- Images from free hosting (Imgur, Photobucket) — MODERATE negative
- Base64-encoded large images — MODERATE negative
- Multiple tracking pixels from different domains — MODERATE negative

## HTML Validity & Complexity — Spam Signals

| Pattern | Impact | Rule |
|---------|--------|------|
| Duplicate `<html>`, `<head>`, `<body>` | Negative | `spam-duplicate-structure` |
| Very large HTML (150KB+) | MODERATE | `spam-excessive-size` |
| Very small HTML (<200 bytes) | SLIGHT | `spam-minimal-html` |
| Excessive tags (1000+ in short email) | MODERATE | `spam-excessive-tags` |
| 20+ nesting depth | MODERATE | `spam-deep-nesting` |
| Random hash comments | MODERATE | `spam-hash-busting` |
| CSS `expression(...)`, `behavior: url(...)` | SEVERE | `spam-css-expression` |

## Table-Based Hidden Content

| Pattern | Impact | Rule |
|---------|--------|------|
| `<td>` with `display: none` containing text | MODERATE | `spam-td-hidden` |
| `<td>` with `font-size: 0` and content | HIGH | `spam-td-zero-font` |
| `<td>` with matching `color` and `bgcolor` | HIGH | `spam-td-invisible-text` |
| `<tr height="0" overflow="hidden">` with text | MODERATE | `spam-tr-hidden` |
| `<td width="0">` with text | MODERATE | `spam-td-zero-width` |
| Empty tables (no content) | SLIGHT | `spam-empty-table` |

## Pre-Send Checklist (Positive Signals)
- `<!DOCTYPE html>` present
- `<html lang="...">` present
- Complete `<head>` with `<meta charset>` and `<title>`
- No forbidden tags (`<script>`, `<iframe>`, `<form>`, `<embed>`, `<object>`)
- No hidden text (color matching background, font-size: 0, display: none)
- Image-to-text ratio: 60%+ text
- All links HTTPS, no shorteners, no IP URLs
- Unsubscribe link + physical address in footer
- Properly closed/nested HTML tags
- No Unicode obfuscation or zero-width character stuffing