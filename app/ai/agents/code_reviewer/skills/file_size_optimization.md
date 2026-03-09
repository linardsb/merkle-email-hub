# File Size Optimisation — L3 Reference

## Gmail Clipping Threshold
Gmail clips emails at **102KB** (102,400 bytes). After clipping, a "View entire message" link appears and tracking pixels may not load.

### Size Calculation
- Measure the **rendered HTML** size in bytes (UTF-8 encoded)
- Include inline styles, embedded CSS, MSO conditionals
- Exclude external resources (images loaded via `src`)

### Rule: `filesize-gmail-clip-risk`
- **critical** if HTML > 102KB
- **warning** if HTML > 80KB (approaching limit)
- **info** if HTML > 60KB (monitor)

## Common Bloat Sources

### Inline Style Repetition
- Same `font-family: Arial, Helvetica, sans-serif` on 50+ elements
- Same `color: #333333; font-size: 14px; line-height: 1.5` block repeated
- Rule: `filesize-style-bloat` (severity: warning)
- Suggestion: Use embedded CSS class where client support allows, or extract to `<style>` block with `!important`

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
- A 50KB image becomes ~67KB when base64-encoded
- Rule: `filesize-base64-image` (severity: critical)
- Suggestion: Host images externally and reference via URL

## Size Reporting
Always include current file size in the review summary:
- `"HTML size: 45,230 bytes (44% of Gmail clip limit)"`
