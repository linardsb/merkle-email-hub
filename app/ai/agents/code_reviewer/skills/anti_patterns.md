<!-- L4 source: none (original content — email anti-pattern catalog) -->
# Email Anti-Patterns — Detection Rules

## Critical Severity

### AP-01: Unmatched MSO Conditionals
**Pattern:** `<!--[if mso]>` without matching `<![endif]-->`
**Detection:** Count opening vs closing MSO comments
**Fix:** Add missing closing comment or remove orphaned opening

### AP-02: VML Outside MSO Conditionals
**Pattern:** `<v:rect>`, `<v:roundrect>`, `<v:fill>` outside `<!--[if mso]>` blocks
**Detection:** Check all `<v:*>` elements are wrapped in MSO conditionals
**Fix:** Wrap VML elements in `<!--[if mso]>...<![endif]-->`

### AP-03: JavaScript in Email
**Pattern:** `<script>`, `onclick`, `onload`, `javascript:`
**Detection:** Regex for script tags and event handlers
**Fix:** Remove entirely — JavaScript is stripped by all email clients

### AP-04: CSS Grid or Flexbox for Layout
**Pattern:** `display:flex`, `display:grid`, `flex-direction`, `grid-template`
**Detection:** Search inline styles and style blocks
**Fix:** Replace with table-based layout

## High Severity

### AP-05: Missing Image Dimensions
**Pattern:** `<img>` without `width` and `height` attributes
**Detection:** Parse all img tags, check for both attributes
**Fix:** Add explicit width and height matching actual image dimensions

### AP-06: Missing Alt Text
**Pattern:** `<img>` without `alt` attribute
**Detection:** Parse all img tags
**Fix:** Add descriptive alt text or `alt=""` for decorative images

### AP-07: CSS Position for Layout
**Pattern:** `position:absolute`, `position:relative`, `position:fixed`
**Detection:** Search inline styles and style blocks
**Fix:** Use table-based layout or margin/padding

### AP-08: Float Without MSO Fallback
**Pattern:** `float:left` or `float:right` without corresponding MSO ghost table
**Detection:** Find floats, check for adjacent MSO conditional tables
**Fix:** Add MSO conditional table for Outlook fallback

### AP-09: Background Image Without VML Fallback
**Pattern:** `background-image` in CSS without VML `<v:rect>` fallback
**Detection:** Find background-image usage, check for VML alternative
**Fix:** Add VML `<v:rect>` with `<v:fill>` for Outlook

### AP-10: Missing MSO Line Height Rule
**Pattern:** `line-height` without `mso-line-height-rule:exactly`
**Detection:** Find line-height declarations, check for MSO property
**Fix:** Add `mso-line-height-rule:exactly` alongside line-height

## Medium Severity

### AP-11: Layout Table Without role="presentation"
**Pattern:** `<table>` used for layout without `role="presentation"`
**Detection:** Tables without data table markup (no `<th>`, `<caption>`)
**Fix:** Add `role="presentation"` to layout tables

### AP-12: CSS Variables
**Pattern:** `var(--custom-property)`
**Detection:** Search for `var(` in styles
**Fix:** Replace with actual color/value

### AP-13: calc/clamp/min/max Functions
**Pattern:** `calc()`, `clamp()`, `min()`, `max()` in CSS
**Detection:** Search for function calls in styles
**Fix:** Replace with fixed pixel values

### AP-14: Missing cellpadding/cellspacing
**Pattern:** `<table>` without `cellpadding="0"` and `cellspacing="0"`
**Detection:** Parse table tags
**Fix:** Add both attributes

### AP-15: @import in Style Block
**Pattern:** `@import` rule in `<style>` block
**Detection:** Search style blocks for @import
**Fix:** Inline the imported styles

### AP-16: Missing Font Fallback Stack
**Pattern:** Single font in `font-family` without fallbacks
**Detection:** Parse font-family declarations
**Fix:** Add web-safe fallback: `Arial, Helvetica, sans-serif`

### AP-17: Inline Style Without Border:0 on Images
**Pattern:** `<img>` without `border:0` in inline style
**Detection:** Parse img tags and check inline styles
**Fix:** Add `border:0` to prevent blue link borders

### AP-18: Missing Color-Scheme Meta
**Pattern:** No `<meta name="color-scheme">` in head
**Detection:** Search for meta tag in head
**Fix:** Add `<meta name="color-scheme" content="light dark">`

## Low Severity

### AP-19: Redundant CSS Properties
**Pattern:** Same property declared multiple times on one element
**Detection:** Parse inline styles for duplicates
**Fix:** Keep only the last declaration

### AP-20: Excessive !important
**Pattern:** More than 5 `!important` declarations in one style block
**Detection:** Count !important occurrences
**Fix:** Use more specific selectors instead

### AP-21: Non-HTTPS URLs
**Pattern:** `http://` in src, href, or url()
**Detection:** Search for http:// protocol
**Fix:** Replace with `https://`

### AP-22: Empty Table Cells Without &nbsp;
**Pattern:** `<td></td>` or `<td> </td>` (whitespace only)
**Detection:** Find td elements with no meaningful content
**Fix:** Add `&nbsp;` or set explicit width/height

### AP-23: Deprecated HTML Attributes
**Pattern:** `bgcolor`, `border`, `align` on non-table elements
**Detection:** Find deprecated attributes on divs, spans, etc.
**Note:** These ARE valid on `<table>`, `<td>`, `<tr>` for email!

### AP-24: Missing DOCTYPE
**Pattern:** No `<!DOCTYPE html>` declaration
**Detection:** Check first non-whitespace content
**Fix:** Add `<!DOCTYPE html>` at document start

### AP-25: Commented-Out Code Bloat
**Pattern:** Large HTML comment blocks (>500 chars)
**Detection:** Find comments, check length
**Fix:** Remove unless they are MSO conditionals

## Info Level

### AP-26: Missing Preheader
**Pattern:** No hidden preheader text in email body
**Detection:** Search for common preheader patterns
**Fix:** Add preheader div with preview text

### AP-27: Single Font Stack
**Pattern:** Using only one font throughout entire email
**Detection:** Collect unique font-family values
**Fix:** Consider using different fonts for headings vs body

### AP-28: No Responsive Breakpoint
**Pattern:** No `@media` query for mobile viewport
**Detection:** Search style blocks for media queries
**Fix:** Add mobile breakpoint at 599px or 480px

### AP-29: Missing View-in-Browser Link
**Pattern:** No fallback link to web version
**Detection:** Search for "view in browser" or "view online"
**Fix:** Add view-in-browser link in preheader area

### AP-30: Excessive Nesting Depth
**Pattern:** Tables nested more than 4 levels deep
**Detection:** Count nesting depth of table elements
**Fix:** Flatten structure where possible
