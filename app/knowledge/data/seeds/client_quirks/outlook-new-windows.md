# New Outlook for Windows Rendering Quirks

## Overview

New Outlook for Windows (codenamed "Monarch") is Microsoft's Chromium-based replacement for classic Outlook. Unlike Outlook 2016/2019/365 which use the Word rendering engine, New Outlook shares the Outlook.com/OWA rendering engine. This means dramatically different CSS support, no MSO conditional processing, and no VML rendering.

Developers must test both classic and New Outlook during the transition (classic Outlook deprecation: October 2026). Code that relies on MSO conditionals or VML will be invisible in New Outlook.

## Rendering Engine Differences

| Feature | Classic Outlook (Word) | New Outlook (Chromium) |
|---|---|---|
| MSO Conditionals | Processed | Ignored (hidden) |
| VML Shapes | Rendered | Ignored |
| border-radius | Not supported | Supported |
| background-image (CSS) | Not supported | Supported |
| max-width | Ignored | Supported |
| Media queries | Not supported | Not supported (same as OWA) |
| Flexbox | Not supported | Not supported (stripped) |
| CSS Grid | Not supported | Not supported (stripped) |

## CSS Sanitization

New Outlook applies the same CSS sanitization pipeline as Outlook.com/OWA. The sanitizer whitelists specific CSS properties and strips everything else:

**Stripped properties (same as OWA):**
- `position` (all values except `static`)
- `float` (stripped entirely)
- `display: flex` and `display: grid`
- `overflow` (stripped in most contexts)
- CSS custom properties (`--var`)
- `@keyframes`, `animation`, `transition`
- `transform` (all values)

**Supported properties (unlike classic Outlook):**
- `border-radius` — works on `<td>`, `<a>`, and block elements
- `background-image` via CSS (no VML needed)
- `max-width` — fluid layouts work correctly
- `box-shadow` — renders as expected
- `opacity` and `rgba()` colors
- CSS gradients (`linear-gradient`, `radial-gradient`) — partial support

**Class and ID rewriting:**
New Outlook renames CSS classes and IDs with unique prefixes (same as OWA), breaking class-based selectors. Use `data-*` attribute selectors as a workaround:

```html
<!-- Class selectors may break due to renaming -->
<style>
  [data-ogsc] .dark-text { color: #ffffff !important; }
  [data-ogsb] .dark-bg { background-color: #1a1a2e !important; }
</style>
```

For full CSS sanitization details, see [outlook-web.md](outlook-web.md).

## Dark Mode Behavior

New Outlook respects Windows system dark mode settings. Behavior:
- Applies forced color inversion on light backgrounds
- `prefers-color-scheme: dark` media query NOT supported (no media queries in OWA engine)
- Use `data-ogsc` and `data-ogsb` attribute selectors for dark mode control
- `[data-ogsc] .dark-text { color: #ffffff !important; }` pattern works
- Images are NOT auto-inverted (unlike some mobile clients)
- Background colors may be forcibly changed — use `data-ogsb` to override

```html
<style>
  /* Dark mode overrides for New Outlook */
  [data-ogsc] .header-text { color: #ffffff !important; }
  [data-ogsb] .email-body { background-color: #1a1a2e !important; }
  [data-ogsc] .footer-text { color: #cccccc !important; }
</style>
```

Unlike Outlook.com in a browser, New Outlook's dark mode activation is tied to the Windows system dark mode toggle, not an in-app setting. This means users who have Windows set to dark mode will always see emails in dark mode in New Outlook.

## Viewport and Layout

Unlike Outlook.com in a browser tab, New Outlook runs as a resizable desktop window:
- Window can be resized from ~320px to full screen width
- No media query support — use fluid table layouts
- `max-width: 600px` on wrapper table is reliable
- `width: 100%` with `max-width` provides fluid behavior
- Desktop window DPI scaling handled by Chromium (no Word DPI bugs)

```html
<!-- Fluid layout that works in New Outlook -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="max-width: 600px; margin: 0 auto;">
  <tr>
    <td style="padding: 0 20px;">
      <!-- Content adapts to window width -->
    </td>
  </tr>
</table>
```

The reading pane in New Outlook can be positioned to the right (narrow, ~400px) or bottom (wide, full width), affecting the available rendering width. Fluid layouts handle both configurations gracefully.

## Migration from Classic Outlook

For codebases with heavy MSO conditional usage:
- MSO conditionals (`<!--[if mso]>...<![endif]-->`) are completely ignored — content inside is hidden
- VML backgrounds/buttons must have CSS fallbacks visible without conditionals
- Ghost table pattern still needed for classic Outlook but invisible in New Outlook — ensure the non-MSO content path renders correctly standalone
- `mso-` prefixed CSS properties are silently ignored

```html
<!-- Ghost table: visible in classic Outlook, invisible in New Outlook -->
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0">
<tr><td>
<![endif]-->

<div style="max-width: 600px; margin: 0 auto;">
  <!-- This div IS visible in New Outlook -->
  <!-- This div is wrapped by the ghost table in classic Outlook -->
</div>

<!--[if mso]>
</td></tr>
</table>
<![endif]-->
```

Ensure that the non-MSO path (the `<div>` above) renders correctly on its own, because that is all New Outlook will see.

## Image Handling

- External images: loaded by default (no click-to-load prompt)
- Image proxy: hybrid local cache + Microsoft proxy
- Tracking pixels: function normally
- `display: block` on images: recommended (prevents gap bug)
- SVG: partial support (inline SVG stripped, `<img src="*.svg">` works)

```html
<img src="hero.jpg" width="600" height="300"
     alt="Hero image"
     style="display: block; max-width: 100%; height: auto; border: 0;"
/>
```

## Key Takeaways

- New Outlook uses Chromium, NOT Word — treat it like Outlook.com, not like Outlook 365
- MSO conditionals and VML are invisible — ensure non-MSO fallback content renders correctly
- No media query support — use fluid tables for responsive design
- Dark mode via data-ogsc/data-ogsb attributes (no prefers-color-scheme)
- CSS sanitization identical to Outlook.com/OWA
- Test alongside classic Outlook during transition (deprecation October 2026)
- Rapidly growing market share as Microsoft forces migration
