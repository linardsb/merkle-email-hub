# Dark Mode CSS in Email

## Overview

Dark mode in email is one of the most complex rendering challenges developers face. Unlike web browsers where you control the dark mode experience entirely, email clients apply dark mode transformations in different and often unpredictable ways. Some clients respect your dark mode styles, some partially transform your colors, and some completely override your design. There are three categories of email client dark mode behavior: full support (they use your `prefers-color-scheme` styles), partial/forced inversion (they automatically adjust colors), and no support (they display the email as-is regardless of OS theme). This guide covers the CSS techniques, meta tags, and client-specific workarounds needed for robust dark mode email support.

## Dark Mode Behavior by Client

| Client | Behavior | Method |
|---|---|---|
| Apple Mail | Full support | `prefers-color-scheme` media query |
| iOS Mail | Full support | `prefers-color-scheme` media query |
| Samsung Email | Full support | `prefers-color-scheme` media query |
| Outlook.com | Partial (forced) | `[data-ogsc]` / `[data-ogsb]` attribute selectors |
| Outlook (Win) new | Partial (forced) | Inverts light backgrounds automatically |
| Outlook (Win) classic | No support | Renders as-is |
| Gmail (Web) | No support | No dark mode transformation |
| Gmail (iOS) | Partial (forced) | Auto-inverts backgrounds and text |
| Gmail (Android) | Partial (forced) | Auto-inverts backgrounds and text |
| Yahoo | No support | No dark mode transformation |

## The color-scheme Meta Tag

The `color-scheme` meta tag and CSS property tell email clients that your email supports both light and dark color schemes. This is the first step in dark mode support.

```html
<head>
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <style>
    :root {
      color-scheme: light dark;
    }
  </style>
</head>
```

| Meta/Property | Apple Mail | iOS Mail | Samsung | Outlook.com | Gmail |
|---|---|---|---|---|---|
| `<meta name="color-scheme">` | Yes | Yes | Yes | No | No |
| `<meta name="supported-color-schemes">` | Yes | Yes | Partial | No | No |
| `color-scheme` CSS property | Yes | Yes | Yes | No | No |

Including these declarations signals to Apple Mail and iOS Mail that you have dark mode styles ready. Without them, these clients may still apply their own color transformations.

## prefers-color-scheme Media Query

The `prefers-color-scheme` media query is the standard CSS mechanism for dark mode. It only works in Apple Mail, iOS Mail, and Samsung Email.

```html
<style>
  /* Light mode defaults (inline styles handle this) */

  @media (prefers-color-scheme: dark) {
    /* Override background colors */
    .body-bg {
      background-color: #1a1a2e !important;
    }
    .content-bg {
      background-color: #16213e !important;
    }
    .card-bg {
      background-color: #0f3460 !important;
    }

    /* Override text colors */
    .text-primary {
      color: #e8e8e8 !important;
    }
    .text-secondary {
      color: #b4b4b4 !important;
    }
    .text-muted {
      color: #8a8a8a !important;
    }

    /* Override border colors */
    .border-light {
      border-color: #2a2a4a !important;
    }

    /* Image swapping */
    .light-logo {
      display: none !important;
      max-height: 0 !important;
      overflow: hidden !important;
    }
    .dark-logo {
      display: block !important;
      max-height: none !important;
      overflow: visible !important;
    }
  }
</style>
```

### Full Example: Dark Mode Email Structure

```html
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <style>
    :root { color-scheme: light dark; }

    @media (prefers-color-scheme: dark) {
      .email-bg { background-color: #121212 !important; }
      .container-bg { background-color: #1e1e1e !important; }
      .heading { color: #ffffff !important; }
      .body-text { color: #d4d4d4 !important; }
      .link { color: #82b1ff !important; }
      .btn-bg { background-color: #4fc3f7 !important; }
      .btn-text { color: #000000 !important; }
    }
  </style>
</head>
<body style="margin: 0; padding: 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         class="email-bg" bgcolor="#f5f5f5"
         style="background-color: #f5f5f5;">
    <tr>
      <td align="center" style="padding: 20px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
               class="container-bg" bgcolor="#ffffff"
               style="background-color: #ffffff;">
          <tr>
            <td style="padding: 32px;">
              <h1 class="heading"
                  style="margin: 0 0 16px; font-family: Arial, sans-serif;
                         font-size: 24px; color: #1a1a1a;">
                Dark Mode Ready Heading
              </h1>
              <p class="body-text"
                 style="margin: 0 0 24px; font-family: Arial, sans-serif;
                        font-size: 16px; line-height: 24px; color: #444444;">
                This text adapts to dark mode in supported clients.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

## Outlook.com Dark Mode: [data-ogsc] and [data-ogsb]

Outlook.com applies dark mode by adding `data-ogsc` (Outlook Gmail Style Color) and `data-ogsb` (Outlook Gmail Style Background) attributes to elements. You can target these with attribute selectors to control Outlook.com's dark mode rendering.

```html
<style>
  /* Outlook.com dark mode overrides */
  [data-ogsc] .heading {
    color: #ffffff !important;
  }
  [data-ogsc] .body-text {
    color: #d4d4d4 !important;
  }
  [data-ogsb] .email-bg {
    background-color: #121212 !important;
  }
  [data-ogsb] .container-bg {
    background-color: #1e1e1e !important;
  }
  [data-ogsb] .btn-bg {
    background-color: #4fc3f7 !important;
  }
</style>
```

These attribute selectors work because Outlook.com does not strip them (unlike Gmail, which would strip attribute selectors).

## Outlook on Windows: MSO Dark Mode Properties

Outlook on Windows (the new version based on web rendering) applies automatic color inversion. The classic desktop version using the Word rendering engine does not apply dark mode at all.

For the new Outlook on Windows, you can use MSO-specific properties to prevent unwanted color changes:

```html
<!-- Prevent Outlook from changing background color -->
<td style="background-color: #1a73e8; mso-fill-color: #1a73e8;">
  <p style="color: #ffffff; mso-color-alt: #ffffff;">
    Button text that stays white
  </p>
</td>
```

## Gmail Dark Mode Workarounds

Gmail applies automatic dark mode transformations on mobile (iOS and Android). There is no CSS mechanism to control this behavior. Gmail's dark mode engine:

1. Inverts light backgrounds to dark
2. Adjusts text colors for contrast
3. Leaves dark backgrounds mostly untouched
4. Does not honor `prefers-color-scheme` or `color-scheme` meta

### Strategies for Gmail Dark Mode

**Use transparent backgrounds on images**: Gmail's auto-inversion can create jarring backgrounds behind images with non-transparent backgrounds.

```html
<!-- Use PNG with transparency instead of JPG for logos -->
<img src="logo-transparent.png" width="150" height="50" alt="Logo"
     style="display: block;" />
```

**Avoid pure white (#ffffff) backgrounds on inner containers**: Gmail aggressively inverts pure white. Using a very slightly off-white (`#fefefe` or `#fafafa`) can sometimes reduce unexpected inversion.

**Add invisible text elements**: Some developers use a 1px transparent text element to influence Gmail's dark mode heuristics, though this is fragile and not recommended as a primary strategy.

## Image Swapping for Dark Mode

Display different images (such as logos) depending on the color scheme:

```html
<style>
  @media (prefers-color-scheme: dark) {
    .light-only { display: none !important; max-height: 0 !important; overflow: hidden !important; }
    .dark-only { display: block !important; max-height: none !important; overflow: visible !important; }
  }
  [data-ogsc] .light-only { display: none !important; max-height: 0 !important; overflow: hidden !important; }
  [data-ogsc] .dark-only { display: block !important; max-height: none !important; overflow: visible !important; }
</style>

<!-- Light mode logo (default visible) -->
<img src="logo-dark-text.png" width="150" height="50" alt="Logo"
     class="light-only"
     style="display: block;" />

<!-- Dark mode logo (default hidden) -->
<div class="dark-only" style="display: none; max-height: 0; overflow: hidden;">
  <img src="logo-light-text.png" width="150" height="50" alt="Logo"
       style="display: block;" />
</div>
```

## Color Selection Guidelines for Dark Mode

When choosing colors for dark mode compatibility, follow these contrast and readability principles:

| Element | Light Mode | Dark Mode | Notes |
|---|---|---|---|
| Background (outer) | `#f5f5f5` | `#121212` | Gmail may auto-invert |
| Background (content) | `#ffffff` | `#1e1e1e` | Use `bgcolor` + CSS |
| Heading text | `#1a1a1a` | `#ffffff` | Ensure 4.5:1 contrast |
| Body text | `#444444` | `#d4d4d4` | Ensure 4.5:1 contrast |
| Muted text | `#777777` | `#9e9e9e` | Minimum 3:1 contrast |
| Links | `#1a73e8` | `#82b1ff` | Lighter blue for dark bg |
| CTA button bg | `#1a73e8` | `#4fc3f7` | Bold, accessible |
| CTA button text | `#ffffff` | `#000000` | High contrast |
| Borders | `#e0e0e0` | `#333333` | Subtle separation |

## Key Takeaways

- Include `<meta name="color-scheme" content="light dark">` and the CSS `color-scheme: light dark` property in every email to signal dark mode support
- `prefers-color-scheme: dark` only works in Apple Mail, iOS Mail, and Samsung Email -- provide these styles but expect them to reach only part of your audience
- Use `[data-ogsc]` and `[data-ogsb]` attribute selectors to control Outlook.com's dark mode color transformations
- Gmail dark mode is fully automatic with no CSS control -- design your light-mode colors to degrade gracefully when inverted
- Use transparent PNG images for logos to avoid jarring background color mismatches in dark mode
- Implement image swapping with `display: none` / `max-height: 0` technique for light/dark logo variants
- Always use `!important` on dark mode style overrides to ensure they take effect
- Test dark mode rendering in real email clients, as dark mode behavior differs between client versions and platforms
- Outlook on Windows (classic/Word engine) has no dark mode support -- your light-mode design is what these users see
- Maintain WCAG AA contrast ratios (4.5:1 for body text, 3:1 for large text) in both light and dark color schemes
