# Email File Size Optimization

## Overview

Email file size directly impacts deliverability, rendering speed, and user experience. The most critical threshold is Gmail's 102KB clipping limit: when an email's HTML exceeds approximately 102KB, Gmail truncates the message and displays a "View entire message" link. Most recipients never click it, meaning your carefully crafted content, tracking pixels, and unsubscribe links are hidden. Beyond Gmail, large emails load slowly on mobile connections, increase bounce rates, and may trigger spam filters. This guide covers practical strategies for keeping email HTML lean.

## The Gmail 102KB Clipping Threshold

Gmail measures the size of the raw HTML source after its preprocessing (which includes stripping certain tags and adding its own markup). The exact limit is approximately 102KB (104,857 bytes), but in practice you should target well below this.

### What Counts Toward the Limit

- All HTML markup, including tags, attributes, and whitespace.
- All inline CSS (`style` attributes on every element).
- Embedded `<style>` blocks.
- HTML entities and comments.
- Tracking pixels and analytics code injected by your ESP.

### What Does NOT Count

- Images (loaded from external URLs, not inline).
- Linked resources (fonts, external CSS — though these are generally stripped anyway).

### Safe Size Targets

| Metric | Target | Why |
|--------|--------|-----|
| Pre-inlining HTML | Under 50KB | Leaves room for ESP injection and CSS inlining expansion |
| Post-inlining HTML | Under 80KB | Safety buffer before the 102KB cliff |
| Total with ESP tracking | Under 95KB | ESP adds tracking params, analytics, unsubscribe links |

## CSS Inlining Strategies

CSS inlining converts `<style>` block rules into inline `style` attributes on each matching element. This is necessary because some clients (Gmail in certain contexts, older mobile clients) strip `<style>` blocks. However, inlining dramatically increases HTML size because styles are duplicated on every matching element.

### Before Inlining

```html
<style>
  .heading { font-family: Arial, sans-serif; font-size: 24px; color: #333333; line-height: 1.3; margin: 0; }
  .body-text { font-family: Arial, sans-serif; font-size: 16px; color: #555555; line-height: 1.5; margin: 0 0 16px; }
</style>

<h1 class="heading">Welcome</h1>
<p class="body-text">First paragraph of content.</p>
<p class="body-text">Second paragraph of content.</p>
<p class="body-text">Third paragraph of content.</p>
```

### After Inlining

```html
<h1 style="font-family: Arial, sans-serif; font-size: 24px; color: #333333; line-height: 1.3; margin: 0;">Welcome</h1>
<p style="font-family: Arial, sans-serif; font-size: 16px; color: #555555; line-height: 1.5; margin: 0 0 16px;">First paragraph of content.</p>
<p style="font-family: Arial, sans-serif; font-size: 16px; color: #555555; line-height: 1.5; margin: 0 0 16px;">Second paragraph of content.</p>
<p style="font-family: Arial, sans-serif; font-size: 16px; color: #555555; line-height: 1.5; margin: 0 0 16px;">Third paragraph of content.</p>
```

The `body-text` style (82 characters) was applied to 3 elements, adding 246 characters versus the original 82-character class definition. In a real email with hundreds of elements, this expansion is substantial.

### Optimization Strategies

**Use shorthand CSS properties:**

```css
/* Verbose: 89 characters */
padding-top: 10px; padding-right: 20px; padding-bottom: 10px; padding-left: 20px;

/* Shorthand: 26 characters */
padding: 10px 20px;

/* Verbose: 95 characters */
font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; font-style: normal;

/* Shorthand: 49 characters */
font: bold 16px/1.5 Arial, sans-serif;
```

**Minimize the number of unique styles.** Consolidate design tokens. If your email uses 8 different font sizes, consider whether 4 would suffice. Each unique style string must be inlined separately.

**Keep the `<style>` block for media queries.** Do not inline media query styles (they cannot be inlined). Keep a small `<style>` block for responsive overrides and `@media` rules. These add minimally to file size compared to repeated inline styles.

## Redundant Code Removal

### Strip HTML Comments

HTML comments add bytes without value in production emails. Remove all comments except MSO conditionals.

```html
<!-- Remove these -->
<!-- Hero Section -->
<!-- End Hero Section -->
<!-- Wrapper table for centering -->

<!-- KEEP these: MSO conditionals are functional, not decorative -->
<!--[if mso]>
<table role="presentation" width="600"><tr><td>
<![endif]-->
```

### Remove Unused CSS

If your email template includes a comprehensive `<style>` block from a design system but only uses a fraction of the rules, strip the unused selectors before sending.

### Eliminate Redundant Table Attributes

```html
<!-- Verbose: unnecessary attributes on every table -->
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"
       style="border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">

<!-- Minimal: move repeated resets to a <style> rule -->
<style>
  table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
</style>
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
```

## HTML Minification

Minification removes unnecessary whitespace, line breaks, and formatting from HTML without changing its rendering.

### What to Minify

- **Whitespace between tags**: `</td>   <td>` becomes `</td><td>`.
- **Line breaks and indentation**: Remove all formatting whitespace.
- **Redundant attribute quotes**: `width="600"` can become `width=600` (though quoted is safer for email).
- **Empty attributes**: Remove `class=""` or `style=""` left by template engines.

### What NOT to Minify

- **MSO conditional comments**: Minifiers may corrupt the `<!--[if mso]>` syntax.
- **Preheader whitespace hack**: The hidden preheader text trick uses `&zwnj;&nbsp;` sequences that must be preserved.
- **Content whitespace**: Spaces within text content must be maintained.

### Build Tool Integration

Maizzle (the build tool used in this project) handles minification as part of its production build pipeline:

```javascript
// maizzle.config.production.js
module.exports = {
  build: {
    posthtml: {
      options: {
        // Collapses whitespace between tags
        xmlMode: false,
      },
    },
  },
  inlineCSS: true,
  removeUnusedCSS: true,
  shorthandCSS: true,
  minify: {
    collapseWhitespace: true,
    removeComments: true,
    // Preserve MSO conditionals
    ignoreCustomComments: [/\[if/, /endif/],
    minifyCSS: true,
  },
}
```

## Code Splitting for Long Emails

When an email exceeds the 102KB limit despite optimization, consider structural changes.

### Content Prioritization

Move secondary content to a landing page and link to it from the email.

```html
<!-- Instead of including the full article in the email -->
<h2 style="font-size: 20px; margin: 0 0 12px;">Top Stories This Week</h2>

<!-- Include a summary with a link to full content -->
<p style="font-size: 16px; line-height: 1.5; margin: 0 0 8px;">
  <strong>AI in Email Marketing: What Changed in 2025</strong>
</p>
<p style="font-size: 14px; line-height: 1.5; margin: 0 0 16px;">
  New personalization capabilities are transforming how brands communicate.
  <a href="https://blog.example.com/ai-email-2025" style="color: #1a73e8;">Read the full article</a>
</p>
```

### Dynamic Content Modules

Use your ESP's dynamic content features to show only relevant sections to each recipient, reducing the HTML each person receives.

```html
<!-- Braze Liquid: only include section if user is in segment -->
{% if ${user.segment} == "premium" %}
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding: 20px;">
      <h2>Exclusive Premium Offer</h2>
      <p>As a premium member, you get early access.</p>
    </td>
  </tr>
</table>
{% endif %}
```

### Template Modularization

Break long emails into reusable component modules. This does not directly reduce file size but makes it easier to audit and trim individual sections.

## Measuring File Size

Always measure the final rendered HTML, not the source template.

```bash
# Check file size of compiled HTML
wc -c compiled-email.html

# Check size after gzip (for reference, though emails are not typically gzip-served)
gzip -c compiled-email.html | wc -c

# Check HTML size excluding images
# This is the number that matters for Gmail clipping
```

## Do's and Don'ts

**Do:**
- Target under 80KB for final HTML output (post-inlining, pre-ESP injection).
- Use CSS shorthand properties to reduce inline style length.
- Minify HTML in production builds while preserving MSO conditionals.
- Remove HTML comments, unused CSS, and redundant whitespace.
- Move detailed content to landing pages and link from the email.
- Test the final ESP-rendered version for total size, including tracking code.

**Don't:**
- Don't ignore the 102KB Gmail clipping threshold — it hides content and breaks tracking.
- Don't inline CSS unnecessarily for properties only used in media queries.
- Don't embed images as base64 data URIs — they count toward the HTML size limit.
- Don't include web fonts via `@font-face` if you are close to the size limit (adds 500-2000 bytes per font).
- Don't use verbose HTML when concise alternatives exist (e.g., prefer `<br>` over empty spacer divs when possible).
- Don't forget to account for ESP-injected tracking pixels, unsubscribe links, and analytics parameters.

## Key Takeaways

- Gmail clips emails at approximately 102KB of HTML. Target under 80KB post-inlining to leave room for ESP additions.
- CSS inlining is the largest contributor to file size growth. Use shorthand properties and minimize style variety.
- Remove HTML comments (except MSO conditionals), unused CSS rules, and formatting whitespace.
- Minify production HTML using your build tool (Maizzle handles this natively).
- Move secondary content to landing pages rather than cramming everything into the email body.
- Use ESP dynamic content to serve only relevant sections to each recipient.
- Always measure the final rendered HTML size, including ESP-injected code, before sending.
