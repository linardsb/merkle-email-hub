# CSS Media Queries in Email

## Overview

Media queries are essential for responsive email design, allowing layouts to adapt to different screen sizes and user preferences. However, support is far from universal. Gmail (the largest email client by market share) strips `<style>` blocks in many of its interfaces, which means media queries are removed entirely. Outlook on Windows ignores media queries completely. Understanding exactly where media queries work -- and building fallback strategies for where they do not -- is the foundation of responsive email development.

## @media Support by Client

| Feature | Gmail (Web) | Gmail (App) | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|---|
| `<style>` block | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| `@media screen` | Yes | Yes | No | Yes | Yes | Yes | Yes |
| `@media (max-width)` | Yes | Yes | No | Yes | Yes | Yes | Yes |
| `@media (min-width)` | Yes | Yes | No | Yes | Yes | Yes | Yes |
| `@media (prefers-color-scheme)` | No | No | No | Yes | Yes | No | Yes |
| `@media (prefers-reduced-motion)` | No | No | No | Yes | Yes | No | No |

Important nuance: Gmail web and Gmail app now support `<style>` blocks and media queries in most cases. However, Gmail strips `<style>` when the email is forwarded, viewed in a third-party app, or when the HTML exceeds certain size thresholds. Always code defensively.

### Gmail's Style Block Behavior

Gmail supports `<style>` blocks but with restrictions:

- Styles must be in the `<head>`, not `<body>`
- Gmail prefixes all class names (e.g., `.my-class` becomes `.abc123_my-class`)
- `!important` is required to override Gmail's prefixing specificity
- ID selectors are stripped
- Embedded `<style>` only works in Gmail webmail and Gmail mobile apps (not IMAP clients)

## Responsive Width Breakpoints

The standard approach for responsive emails uses `max-width` media queries to stack columns on small screens.

```html
<style>
  @media screen and (max-width: 600px) {
    .container {
      width: 100% !important;
      max-width: 100% !important;
    }
    .column {
      display: block !important;
      width: 100% !important;
      max-width: 100% !important;
    }
    .mobile-padding {
      padding-left: 20px !important;
      padding-right: 20px !important;
    }
    .mobile-hide {
      display: none !important;
      mso-hide: all !important;
    }
    .mobile-center {
      text-align: center !important;
    }
  }
</style>
```

### Two-Column to Single-Column Stacking

```html
<style>
  @media screen and (max-width: 600px) {
    .stack-column {
      display: block !important;
      width: 100% !important;
    }
  }
</style>

<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
<tr><td>
<![endif]-->
<div style="max-width: 600px; margin: 0 auto;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td class="stack-column" width="50%"
          style="width: 50%; padding: 10px; vertical-align: top;">
        Left column content
      </td>
      <td class="stack-column" width="50%"
          style="width: 50%; padding: 10px; vertical-align: top;">
        Right column content
      </td>
    </tr>
  </table>
</div>
<!--[if mso]>
</td></tr></table>
<![endif]-->
```

## Fluid-Hybrid Method (No Media Query Required)

Because media queries are not universally supported, the "fluid-hybrid" or "spongy" method is the most reliable responsive technique. It uses `max-width`, `min-width`, and the `calc()` function to create layouts that adapt without media queries.

```html
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
<tr>
<td width="300">
<![endif]-->
<div style="display: inline-block; width: 100%; max-width: 300px;
            min-width: 200px; vertical-align: top;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="padding: 10px; font-family: Arial, sans-serif; font-size: 16px;">
        Column 1
      </td>
    </tr>
  </table>
</div>
<!--[if mso]>
</td>
<td width="300">
<![endif]-->
<div style="display: inline-block; width: 100%; max-width: 300px;
            min-width: 200px; vertical-align: top;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="padding: 10px; font-family: Arial, sans-serif; font-size: 16px;">
        Column 2
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

This layout stacks naturally when the viewport is too narrow for both columns, without any media query. The MSO conditional tables ensure fixed-width rendering in Outlook.

## Dark Mode Media Query

`prefers-color-scheme: dark` allows you to provide explicit dark mode styles. However, support is limited to Apple Mail, iOS Mail, and Samsung Email.

| Client | prefers-color-scheme Support |
|---|---|
| Apple Mail | Yes |
| iOS Mail | Yes |
| Samsung Email | Yes |
| Gmail | No |
| Outlook (Win) | No |
| Yahoo | No |
| Outlook.com | No |

```html
<style>
  @media (prefers-color-scheme: dark) {
    .email-body {
      background-color: #1a1a2e !important;
    }
    .text-primary {
      color: #e0e0e0 !important;
    }
    .text-secondary {
      color: #b0b0b0 !important;
    }
    .dark-img {
      display: block !important;
      width: auto !important;
      overflow: visible !important;
      max-height: none !important;
    }
    .light-img {
      display: none !important;
      max-height: 0 !important;
      overflow: hidden !important;
    }
  }
</style>
```

See the dark-mode-css guide for comprehensive dark mode strategies including Outlook.com and Gmail workarounds.

## Responsive Font Sizes

```html
<style>
  @media screen and (max-width: 600px) {
    .heading {
      font-size: 24px !important;
      line-height: 30px !important;
    }
    .body-text {
      font-size: 16px !important;
      line-height: 24px !important;
    }
    .small-text {
      font-size: 13px !important;
      line-height: 18px !important;
    }
  }
</style>
```

## Responsive Image Sizing

```html
<style>
  @media screen and (max-width: 600px) {
    .fluid-img {
      width: 100% !important;
      max-width: 100% !important;
      height: auto !important;
    }
  }
</style>

<img src="hero.jpg" width="600" height="300" alt="Hero image"
     class="fluid-img"
     style="display: block; width: 100%; max-width: 600px; height: auto;" />
```

## Mobile-Specific Content

Show or hide content based on screen size:

```html
<style>
  @media screen and (max-width: 600px) {
    .desktop-only { display: none !important; }
    .mobile-only { display: block !important; max-height: none !important; overflow: visible !important; }
  }
</style>

<!-- Visible on desktop, hidden on mobile -->
<div class="desktop-only" style="font-size: 16px;">
  Desktop navigation or wide-format content
</div>

<!-- Hidden on desktop, visible on mobile -->
<div class="mobile-only" style="display: none; max-height: 0; overflow: hidden;">
  Mobile-optimized content
</div>
```

## Key Takeaways

- Gmail now supports `<style>` blocks and media queries in webmail and mobile apps, but strips them when emails are forwarded or exceed size limits -- never rely solely on media queries
- Outlook on Windows ignores all media queries -- use MSO conditional comments for Outlook-specific layouts
- The fluid-hybrid (spongy) method using `max-width` + `min-width` + `display: inline-block` is the most reliable responsive technique because it works without media queries
- Always use `!important` on media query declarations to override Gmail's specificity from class name prefixing
- `prefers-color-scheme: dark` only works in Apple Mail, iOS Mail, and Samsung Email
- Place all `<style>` blocks in the `<head>`, not the `<body>`, for Gmail compatibility
- Use the `max-height: 0; overflow: hidden` technique for hiding mobile/desktop-only content, as it is more reliable than `display: none` alone across clients
- Test responsive behavior in actual email clients -- browser-based responsive testing does not accurately reflect email client rendering
