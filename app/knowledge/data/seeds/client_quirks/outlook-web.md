# Outlook.com and Office 365 Web Rendering Quirks

## Overview

Outlook.com (formerly Hotmail) and Office 365 Outlook on the web share a rendering engine that is fundamentally different from Outlook Windows. While Outlook Windows uses the Word rendering engine, the web-based versions render emails through a browser-based HTML/CSS sanitizer. This means Outlook on the web supports a broader range of CSS properties than its desktop counterpart, but it applies its own aggressive sanitization, class/ID rewriting, and style modifications that create a unique set of challenges.

The distinction is critical: code that works in Outlook Windows (MSO conditionals, VML) is invisible to Outlook on the web because it runs in a browser context. Conversely, CSS properties like `border-radius` and `background-image` that are unsupported in Outlook Windows work correctly in Outlook on the web. Developers must account for both rendering contexts when targeting the Outlook family.

> **See also:** [outlook-new-windows.md](outlook-new-windows.md) for the "New Outlook" desktop app, which shares this rendering engine but has desktop-specific viewport and dark mode behavior.

## CSS Sanitization and Safe Styles

Outlook on the web processes email HTML through a sanitizer that whitelists specific CSS properties and strips everything else. The sanitizer operates at the inline style level and the embedded stylesheet level.

**Generally safe properties:**
- `background-color`, `background-image`, `background-position`, `background-repeat`, `background-size`
- `border`, `border-radius` (and individual sides)
- `color`, `font-family`, `font-size`, `font-weight`, `font-style`
- `line-height`, `letter-spacing`, `text-align`, `text-decoration`, `text-transform`
- `padding` (and individual sides)
- `margin` (and individual sides)
- `width`, `height`, `max-width`, `min-width`
- `display: block`, `display: inline`, `display: inline-block`, `display: none`
- `vertical-align`
- `opacity`

**Stripped properties:**
- `position` (all values)
- `float`
- `display: flex`, `display: grid`
- `overflow` (in most contexts)
- `z-index`
- `transform`
- `animation`, `transition`, `@keyframes`
- CSS custom properties (`--variable-name`)
- `box-shadow` (stripped in some contexts)
- `@font-face` (web fonts are blocked)

```html
<!-- Works in Outlook.com -->
<td style="background-color: #0066cc; border-radius: 8px; padding: 16px;">
  <p style="color: #ffffff; font-size: 18px; font-weight: bold;
            text-align: center; margin: 0;">
    Rounded button with gradient - works here, not in Outlook Windows
  </p>
</td>

<!-- Stripped in Outlook.com -->
<div style="display: flex; justify-content: space-between; position: relative;">
  <!-- Layout will collapse -->
</div>
```

## Class and ID Rewriting

Outlook on the web rewrites CSS class names and completely strips ID selectors, similar to Gmail. Class names are prefixed with a generated string:

```html
<!-- Original -->
<style>
  .hero-section { background-color: #1a1a2e; }
</style>
<div class="hero-section">Content</div>

<!-- Outlook.com rewrites to approximately -->
<style>
  .x_hero-section { background-color: #1a1a2e; }
</style>
<div class="x_hero-section">Content</div>
```

The `x_` prefix is commonly observed, but the exact prefix can vary. Key implications:

- Class-based selectors in `<style>` blocks work because both the selector and element are rewritten consistently
- ID selectors (`#myElement`) are stripped entirely and will not match
- Attribute selectors are largely unsupported
- Complex selectors using combinators (`>`, `+`, `~`) have limited support

```css
/* Works in Outlook.com */
.cta-button { background-color: #0066cc; }
td.content-cell { padding: 20px; }

/* Does NOT work */
#main-content { padding: 20px; }
[data-section="hero"] { background-color: #0066cc; }
.parent > .child { margin-top: 10px; }
```

## Dark Mode and Forced Colors

Outlook on the web has one of the most aggressive dark mode implementations. When a user enables dark mode in Outlook.com or Office 365, the client applies forced color transformations that can dramatically alter email appearance.

Outlook on the web's dark mode:

- Inverts background colors (light to dark)
- Inverts text colors (dark to light)
- May alter image appearance by applying a semi-transparent overlay
- Ignores `color-scheme` meta declarations in many cases
- May not respect `@media (prefers-color-scheme: dark)` queries consistently

```html
<!-- Outlook.com dark mode workarounds -->
<head>
  <meta name="color-scheme" content="light dark">
  <style>
    /* Use [data-ogsc] and [data-ogsb] selectors for Outlook.com dark mode */
    [data-ogsc] .dark-text {
      color: #ffffff !important;
    }
    [data-ogsb] .dark-bg {
      background-color: #1a1a2e !important;
    }

    /* Standard prefers-color-scheme as fallback */
    @media (prefers-color-scheme: dark) {
      .dark-text { color: #ffffff !important; }
      .dark-bg { background-color: #1a1a2e !important; }
    }
  </style>
</head>
```

The `[data-ogsc]` (Outlook Generated Style Color) and `[data-ogsb]` (Outlook Generated Style Background) attribute selectors are Outlook.com-specific hooks that target elements affected by Outlook's dark mode transformations. These selectors allow developers to override Outlook's forced color changes.

To prevent Outlook on the web from inverting specific elements:

```html
<!-- Technique: Use a transparent 1x1 image as a background to block inversion -->
<td style="background-image: url('https://example.com/1x1-transparent.gif');
           background-color: #ffffff;">
  <!-- Outlook.com may skip inversion when background-image is present -->
  Content that keeps its light background in dark mode
</td>
```

This technique works because Outlook's dark mode heuristic sometimes skips elements that have a `background-image` set, assuming the developer has intentionally styled that element.

## Differences from Outlook Windows

The rendering gap between Outlook on the web and Outlook Windows is substantial:

| Feature | Outlook Windows | Outlook.com / O365 Web |
|---------|----------------|----------------------|
| Rendering engine | Word (WordHTML) | Browser + CSS sanitizer |
| `border-radius` | Not supported | Supported |
| `background-image` (CSS) | Not supported | Supported |
| MSO conditionals | Processed | Ignored (hidden) |
| VML | Supported | Not supported |
| `max-width` | Not supported | Supported |
| Media queries | Not supported | Supported |
| `@font-face` | Not supported | Not supported (blocked) |
| `display: flex/grid` | Not supported | Not supported (stripped) |
| `box-shadow` | Not supported | Partially supported |
| Animated GIFs | First frame only | Fully animated |
| Dark mode | None | Forced color inversion |

This divergence means that Outlook-targeted code often needs two separate strategies: one for Outlook Windows (tables, VML, MSO conditionals) and one for Outlook on the web (modern CSS with sanitization awareness).

```html
<!-- Strategy for both Outlook variants -->
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0">
<tr><td style="background-color: #0066cc; padding: 14px 28px;">
<![endif]-->

<div style="max-width: 600px; background-color: #0066cc; border-radius: 8px;
            padding: 14px 28px; text-align: center;">
  <a href="https://example.com"
     style="color: #ffffff; text-decoration: none; font-size: 16px;
            font-weight: bold;">
    Call to Action
  </a>
</div>

<!--[if mso]>
</td></tr></table>
<![endif]-->
```

In this example, Outlook Windows sees the table-based version (without border-radius), while Outlook on the web sees the `<div>` version with rounded corners. MSO conditional content is treated as HTML comments in browser contexts, so it is invisible to Outlook on the web.

## Media Query Support

Outlook on the web supports `@media` queries in `<style>` blocks, enabling responsive layouts:

```css
@media screen and (max-width: 480px) {
  .column {
    width: 100% !important;
    display: block !important;
  }
  .mobile-padding {
    padding: 16px !important;
  }
  .desktop-only {
    display: none !important;
  }
}
```

However, media queries in Outlook on the web are subject to the same class name rewriting as all other CSS. This generally works transparently but can occasionally cause specificity issues.

## Email Size and Rendering

Outlook on the web does not clip emails at a specific size like Gmail's 102KB limit. However, extremely large emails may render slowly or trigger Outlook's security warnings. Best practice is to keep HTML under 100KB regardless of client.

## Key Takeaways

- Outlook on the web uses a browser-based sanitizer, not the Word engine; it supports `border-radius`, `background-image`, and `max-width` that Outlook Windows cannot render
- CSS is sanitized on a whitelist basis; `flex`, `grid`, `position`, `float`, animations, and web fonts are all stripped
- Class names are rewritten with a prefix (commonly `x_`); ID selectors and attribute selectors are stripped
- Dark mode applies forced color inversion that is among the most aggressive of any email client; use `[data-ogsc]` and `[data-ogsb]` selectors for targeted overrides
- MSO conditional comments and VML are invisible to Outlook on the web (they are HTML comments in a browser context)
- Code targeting the Outlook family often needs dual strategies: table/VML for Windows, modern CSS for web
- Media queries are supported, enabling responsive designs that work across Outlook on the web
- Web fonts are blocked by security policy; always include system font fallbacks
- Animated GIFs play fully, unlike Outlook Windows which shows only the first frame
