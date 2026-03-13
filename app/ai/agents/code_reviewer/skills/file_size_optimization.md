<!-- L4 source: docs/SKILL_html-email-components.md sections 6, 22 -->
<!-- Last synced: 2026-03-13 -->

# File Size Optimisation — L3 Reference

## Gmail Clipping Threshold

Gmail clips emails at **102KB** (102,400 bytes). After clipping:
- A "View entire message" link replaces the rest of the email
- Tracking pixels placed after the clip point will **not load** (open tracking fails)
- Unsubscribe links after the clip point become inaccessible (legal/compliance risk)
- `<style>` blocks are preserved only in the visible portion — CSS for clipped content is lost
- AMP content is entirely disabled if the HTML MIME part exceeds 102KB

### Size Calculation
- Measure the **rendered HTML** size in bytes (UTF-8 encoded)
- Include inline styles, embedded CSS, MSO conditionals, VML blocks
- Exclude external resources (images loaded via `src`)
- MSO conditional blocks (`<!--[if mso]>...<![endif]-->`) count toward the total even though non-Outlook clients ignore them

### Rule: `filesize-gmail-clip-risk`
- **critical** if HTML > 102KB
- **warning** if HTML > 80KB (approaching limit)
- **info** if HTML > 60KB (monitor)

## Image Optimisation

### Retina Images (2x Resolution)
- Serve images at 2x their display dimensions for sharp rendering on retina/HiDPI screens
- Constrain display size with HTML `width` attribute: `<img src="hero-1200.jpg" width="600">`
- The `width` HTML attribute (not CSS) is what Outlook uses to size the image
- Do NOT rely on CSS `max-width` alone — Outlook ignores it
- Rule: `filesize-retina-missing-width` — flag `<img>` with large intrinsic size but no constraining `width` attribute (severity: warning)

### Image Format Selection
- **JPEG** — best for photographs and complex images with gradients; no transparency
- **PNG-8** — best for simple graphics, icons, logos with flat colors (small file size)
- **PNG-24** — best for images requiring transparency (larger file size than PNG-8)
- **GIF** — best for simple animations; limited to 256 colors; first frame shown in Outlook desktop
- **WebP** — NOT supported in Outlook desktop, older Gmail, or many email clients — avoid in email
- **SVG** — NOT reliably supported in email; stripped by Gmail, partially supported in Apple Mail
- Rule: `filesize-unsupported-format` — flag WebP/SVG images in email (severity: warning)

### Mandatory Image Attributes
- `width` and `height` HTML attributes on ALL `<img>` tags — prevents layout collapse when images are off
- `border="0"` — removes blue link borders in older clients
- `display: block` in inline style — removes phantom gaps below images
- `alt` text — required for accessibility and image-off rendering
- Rule: `filesize-img-missing-attrs` — flag images missing any of width/height/border/alt (severity: warning)

## Tracking Pixel Best Practices

### Standard Open Tracking Pixel
```html
<img src="https://tracking.example.com/open/abc123.gif"
     width="1" height="1" border="0"
     alt="" style="display: block; height: 1px; width: 1px;">
```
- Must be a 1x1 transparent GIF (or PNG) — smallest possible image
- Must include `width="1" height="1"` HTML attributes
- Must include `border="0"` and `display: block`
- `alt=""` (empty) — decorative image, screen readers should skip
- Place **before** the closing `</body>` or at the end of content — ensures it loads even in partially rendered emails
- Place **before the 102KB Gmail clip threshold** — tracking pixels after clip point never load
- Rule: `filesize-tracking-pixel-placement` — flag tracking pixels after 80KB mark (severity: warning)

### Apple Mail Privacy Protection (MPP) Considerations
- Apple Mail pre-fetches all images via proxy — open tracking is unreliable for Apple Mail users
- Do NOT rely solely on pixel-based open tracking for engagement metrics
- Rule: `filesize-tracking-pixel-only` — info-level note when open tracking pixel is the sole tracking mechanism

## Common Bloat Sources

### Inline Style Repetition
- Same `font-family: Arial, Helvetica, sans-serif` on 50+ elements
- Same `color: #333333; font-size: 14px; line-height: 1.5` block repeated
- Rule: `filesize-style-bloat` (severity: warning)
- Suggestion: Use embedded CSS class where client support allows, or extract to `<style>` block with `!important`

### CSS Minification Strategies for Email
- **Consolidate inline styles** — extract repeated inline style patterns into `<style>` block classes
- **Use shorthand properties** — `font: 14px/1.5 Arial, sans-serif` instead of separate `font-family`, `font-size`, `line-height`
- **Shorthand padding/margin** — `padding: 20px 10px` instead of `padding-top: 20px; padding-right: 10px; padding-bottom: 20px; padding-left: 10px`
- **Remove redundant units** — `padding: 0` instead of `padding: 0px`
- Caveat: inline styles are still required for Gmail compatibility — minify but do not eliminate them entirely
- Rule: `filesize-unminified-css` (severity: info)

### Comment Removal
- HTML comments (non-MSO) add to file size with zero rendering benefit
- Large comment blocks (>500 characters) are significant bloat
- MSO conditional comments (`<!--[if mso]>`) must be preserved — they are functional, not documentation
- Rule: `filesize-comment-bloat` — flag non-MSO HTML comments >200 bytes (severity: info)

### Unnecessary Whitespace
- Excessive indentation (4+ levels of nested indentation in production)
- Multiple blank lines between elements
- Rule: `filesize-whitespace` (severity: info)
- Suggestion: Minify for production builds (Maizzle handles this via `purgeCSS` + `minify`)

### Oversized MSO Blocks
- VML backgrounds/buttons can add 2-5KB each
- Multiple VML elements for same visual effect
- Rule: `filesize-heavy-mso` (severity: info)

### Embedded Images (Base64)
- Base64-encoded images in `src="data:image/..."` dramatically increase size
- A 50KB image becomes ~67KB when base64-encoded (33% overhead from base64 encoding)
- Rule: `filesize-base64-image` (severity: critical)
- Suggestion: Host images externally and reference via URL

## Size Reporting
Always include current file size in the review summary:
- `"HTML size: 45,230 bytes (44% of Gmail clip limit)"`
- `"Estimated savings: ~8KB from inline style consolidation"`
- `"MSO block overhead: 12,400 bytes (12% of total)"`
