# File Size Optimisation — Gmail 102KB Clipping

## The 102KB Rule

Gmail clips emails where the HTML source exceeds approximately 102KB (104,857 bytes).
Content after the clipping point is hidden behind a "View entire message" link.

**What counts:** Raw HTML source size (UTF-8 encoded), including:
- All HTML tags and attributes
- Inline styles
- Style blocks
- Comments (including MSO conditionals)
- Whitespace and line breaks
- Script tags (stripped by Gmail but counted before clipping check)

**What doesn't count:**
- Linked images (loaded separately)
- External CSS (stripped anyway)

## Size Reduction Techniques

### Technique 1: CSS Consolidation (10-30% savings)
**Before:**
```html
<td style="font-family:Arial, Helvetica, sans-serif; font-size:16px; line-height:24px; color:#333333;">
<td style="font-family:Arial, Helvetica, sans-serif; font-size:16px; line-height:24px; color:#333333;">
```
**After:**
```html
<style>.body-text { font-family:Arial,Helvetica,sans-serif; font-size:16px; line-height:24px; color:#333 }</style>
<td class="body-text">
<td class="body-text">
```
Note: Only works in clients that support `<style>` blocks. Keep inline styles as fallback for Gmail.

### Technique 2: Shorthand Properties (5-15% savings)
```css
/* Before */
padding-top:10px; padding-right:20px; padding-bottom:10px; padding-left:20px;
/* After */
padding:10px 20px;

/* Before */
border-top:1px solid #cccccc; border-right:1px solid #cccccc;
border-bottom:1px solid #cccccc; border-left:1px solid #cccccc;
/* After */
border:1px solid #ccc;
```

### Technique 3: Color Shorthand (2-5% savings)
```css
/* Before */ color:#ffffff; background-color:#000000;
/* After */  color:#fff; background-color:#000;
/* Before */ color:#aabbcc;
/* After */  color:#abc;
```

### Technique 4: Remove Unnecessary Whitespace (5-10% savings)
- Remove blank lines between table rows
- Collapse multiple spaces to single space
- Remove HTML comments (except MSO conditionals)
- Minimize line breaks in inline styles

### Technique 5: Remove Unused CSS (5-20% savings)
- Audit `<style>` blocks for selectors not used in the HTML
- Remove responsive styles for breakpoints not needed
- Remove dark mode styles if not implementing dark mode

### Technique 6: Attribute Optimization (2-5% savings)
```html
<!-- Before -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
<!-- After (if role=presentation handles it) -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
```
Note: Don't remove email-critical attributes to save space.

### Technique 7: Image URL Shortening (1-5% savings)
- Use shorter image hosting URLs
- Remove unnecessary query parameters from image URLs
- Use relative paths where supported

## Size Budget

| Component | Target | Max |
|-----------|--------|-----|
| HTML structure | 20KB | 30KB |
| Inline styles | 15KB | 25KB |
| Style block | 5KB | 10KB |
| MSO conditionals | 10KB | 15KB |
| Content text | 10KB | 20KB |
| **Total** | **60KB** | **102KB** |

## Measuring Size

```
Size = UTF-8 byte length of the complete HTML source
Risk levels:
- Green: < 80KB (safe)
- Yellow: 80-95KB (approaching limit)
- Red: 95-102KB (high risk)
- Critical: > 102KB (WILL be clipped)
```
