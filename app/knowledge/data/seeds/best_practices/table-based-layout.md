# Table-Based Email Layout

## Overview

Despite decades of web standards evolution, HTML email rendering remains anchored to table-based layout. Most email clients — particularly Microsoft Outlook (which uses the Word rendering engine) — do not reliably support modern CSS layout properties like `flexbox`, `grid`, or even consistent `display: block` behavior. Tables remain the only layout method that renders predictably across Gmail, Outlook, Apple Mail, Yahoo Mail, and dozens of other clients.

This guide covers the essential patterns for building robust table-based email layouts, including structural tables, nested patterns, hybrid approaches, and accessibility considerations.

## Why Tables Are Still Required

Email clients strip, modify, or ignore CSS in unpredictable ways:

- **Outlook 2007-2021** uses Microsoft Word's HTML rendering engine, which has no support for `max-width`, `flexbox`, `grid`, or many `display` values.
- **Gmail** strips `<style>` blocks in non-AMP emails when embedded in certain contexts (e.g., forwarded messages), leaving only inline styles.
- **Yahoo Mail** rewrites class names and can mangle media queries.
- **Older mobile clients** may ignore `div`-based layouts entirely.

Tables provide a reliable structure because all email clients support the core HTML table model: `<table>`, `<tr>`, `<td>` with `width`, `height`, `align`, `valign`, `bgcolor`, and `border` attributes.

## The Structural Wrapper Table

Every email should begin with a full-width wrapper table that centers the content and provides a background color for the "canvas" area visible in webmail clients.

```html
<!-- Wrapper table: full-width background -->
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4;">
  <tr>
    <td align="center" style="padding: 20px 0;">

      <!-- Content table: fixed-width email body -->
      <table role="presentation" width="600" border="0" cellpadding="0" cellspacing="0" style="background-color: #ffffff; max-width: 600px;">
        <tr>
          <td style="padding: 40px 30px;">
            <!-- Email content goes here -->
          </td>
        </tr>
      </table>

    </td>
  </tr>
</table>
```

Key details:

- The outer table is `width="100%"` to fill the viewport.
- The inner table uses `width="600"` (the de facto standard for email width) plus `max-width: 600px` as a CSS backup.
- `cellpadding="0"` and `cellspacing="0"` eliminate default browser spacing.
- `border="0"` removes visible borders.

## The role="presentation" Attribute

Every table used for layout purposes **must** include `role="presentation"`. This tells screen readers to treat the table as a layout container rather than a data table. Without it, assistive technology will announce "table with X rows and Y columns" for every layout table, creating a confusing experience.

```html
<!-- Correct: layout table with presentation role -->
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td>Layout content</td>
  </tr>
</table>

<!-- Incorrect: missing role causes screen reader noise -->
<table width="100%" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td>Layout content</td>
  </tr>
</table>
```

Only omit `role="presentation"` when you are displaying actual tabular data (pricing comparisons, schedules, etc.).

## Nested Table Patterns

Complex layouts require nesting tables within `<td>` cells. This is the primary mechanism for creating multi-column layouts in email.

### Two-Column Layout

```html
<table role="presentation" width="600" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td align="center" style="padding: 0 30px;">

      <!-- Two-column row using nested table -->
      <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr>
          <td width="270" valign="top" style="padding-right: 15px;">
            <h2 style="margin: 0 0 10px; font-size: 18px;">Column One</h2>
            <p style="margin: 0; font-size: 14px; line-height: 1.5;">Left column content with appropriate padding between columns.</p>
          </td>
          <td width="270" valign="top" style="padding-left: 15px;">
            <h2 style="margin: 0 0 10px; font-size: 18px;">Column Two</h2>
            <p style="margin: 0; font-size: 14px; line-height: 1.5;">Right column content that aligns at the top thanks to valign.</p>
          </td>
        </tr>
      </table>

    </td>
  </tr>
</table>
```

### Three-Column Product Grid

```html
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td width="33%" valign="top" style="padding: 10px;">
      <img src="product1.jpg" width="160" alt="Product name" style="display: block; width: 100%; max-width: 160px;" />
      <p style="margin: 10px 0 0; font-size: 14px;">Product One</p>
    </td>
    <td width="34%" valign="top" style="padding: 10px;">
      <img src="product2.jpg" width="160" alt="Product name" style="display: block; width: 100%; max-width: 160px;" />
      <p style="margin: 10px 0 0; font-size: 14px;">Product Two</p>
    </td>
    <td width="33%" valign="top" style="padding: 10px;">
      <img src="product3.jpg" width="160" alt="Product name" style="display: block; width: 100%; max-width: 160px;" />
      <p style="margin: 10px 0 0; font-size: 14px;">Product Three</p>
    </td>
  </tr>
</table>
```

## Width Patterns and Sizing

Consistent width management prevents layout breakage:

- **Use both HTML attributes and CSS**: `width="600"` for Outlook, `style="width: 600px;"` for modern clients.
- **Percentage widths for fluid cells**: Use `width="50%"` on `<td>` elements when you want proportional columns.
- **Explicit image widths**: Always set the `width` attribute on `<img>` tags. Outlook ignores CSS-only width on images.
- **Avoid unitless padding in CSS**: Always specify `px` units. Some clients misinterpret unitless values.

```html
<!-- Width pattern: HTML attribute + CSS for maximum compatibility -->
<table role="presentation" width="600" style="width: 600px; max-width: 600px;" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <!-- Fixed-width sidebar -->
    <td width="200" style="width: 200px;" valign="top">
      Sidebar
    </td>
    <!-- Fluid main content -->
    <td valign="top" style="padding-left: 20px;">
      Main content
    </td>
  </tr>
</table>
```

## The Hybrid (Ghost Table) Approach

The hybrid approach uses `<div>` elements with `display: inline-block` for modern clients while wrapping them in Outlook-only conditional tables (ghost tables) using MSO conditional comments.

```html
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
<tr>
<td width="300" valign="top">
<![endif]-->
<div style="display: inline-block; width: 100%; max-width: 300px; vertical-align: top;">
  <p>Column one content</p>
</div>
<!--[if mso]>
</td>
<td width="300" valign="top">
<![endif]-->
<div style="display: inline-block; width: 100%; max-width: 300px; vertical-align: top;">
  <p>Column two content</p>
</div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

This approach enables responsive stacking on mobile (where divs collapse to `width: 100%`) while maintaining the fixed table structure Outlook requires. It is the recommended pattern for new email builds that need to balance modern flexibility with legacy support.

## Common Mistakes to Avoid

- **Using `<div>` for layout without ghost tables**: Outlook will collapse or misalign div-based layouts.
- **Forgetting `cellpadding="0" cellspacing="0"`**: Default values differ across clients and add unwanted gaps.
- **Nesting too deeply**: Outlook has a roughly 23-level nesting limit for tables. Keep nesting under 10 levels.
- **Using `margin` on table cells**: Outlook ignores `margin` on `<td>`. Use `padding` instead.
- **Omitting `role="presentation"`**: Creates accessibility problems for screen reader users.
- **Using `colspan` or `rowspan` for layout**: These are fragile and render inconsistently. Use nested tables instead.

## Key Takeaways

- Tables are the only reliable layout method across all major email clients, especially Outlook.
- Always include `role="presentation"` on layout tables for accessibility.
- Use `cellpadding="0"`, `cellspacing="0"`, and `border="0"` to reset default table styling.
- Set widths using both HTML attributes and inline CSS for maximum compatibility.
- Use nested tables (not `colspan`/`rowspan`) for multi-column layouts.
- The hybrid/ghost table approach combines modern `<div>` flexibility with Outlook table support.
- Keep table nesting under 10 levels to avoid Outlook rendering limits.
- Use `padding` instead of `margin` on `<td>` elements — Outlook ignores margin on cells.
