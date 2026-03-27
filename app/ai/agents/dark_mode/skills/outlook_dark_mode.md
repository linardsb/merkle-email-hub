---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_email-dark-mode-dom-reference.md sections 6-9 -->
<!-- Last synced: 2026-03-13 -->

# Outlook Dark Mode — Selectors, Patterns, and Prevention

## Outlook Desktop — The Forced Override Engine

Outlook desktop is the most aggressive dark mode renderer. It ignores `@media (prefers-color-scheme: dark)`, ignores `<meta name="color-scheme">`, and forcibly rewrites colors using its Word rendering engine.

### How Outlook Categorizes Colors (Luminance-Based)
- Scans every element's `color`, `background-color`, and `bgcolor` values
- Categorizes each color as "light" or "dark" based on luminance
- **Light backgrounds** (high luminance like #ffffff) → inverted to dark
- **Dark backgrounds** (low luminance like #1a1a1a) → left alone
- **Dark text** (low luminance like #333333) → inverted to light
- **Light text** (high luminance like #ffffff) → left alone
- **Mid-range colors** (#666666 to #999999) → **unpredictable** — may or may not invert

### Three Rendering Behaviors
1. **No background change** — Outlook keeps your backgrounds but inverts text for contrast
2. **Full background inversion** — Outlook inverts both backgrounds and text
3. **Partial inversion** — Outlook inverts only certain elements based on luminance analysis

The user's Outlook dark mode setting determines which behavior applies. Email developers cannot control which mode the recipient uses.

### Outlook Desktop Versions
- **Outlook 2019+** and **Microsoft 365** — dark mode built in
- **Outlook 2016** — no native dark mode (Windows dark mode affects chrome only)
- **"New Outlook" for Windows** (web engine) — different behavior, more like Outlook.com

## Outlook Dark Mode Attribute Selectors

### `[data-ogsc]` — Outlook General Style Color (text/foreground)
```css
[data-ogsc] .heading { color: #f5f5f5 !important; }
[data-ogsc] .body-text { color: #e0e0e0 !important; }
[data-ogsc] .link-text { color: #4da3ff !important; }
```

### `[data-ogsb]` — Outlook General Style Background
```css
[data-ogsb] .email-body { background-color: #1a1a2e !important; }
[data-ogsb] .content-area { background-color: #16213e !important; }
[data-ogsb] .card { background-color: #252540 !important; }
```

### How `[data-ogsc]` / `[data-ogsb]` Work
- Outlook.com adds `data-ogsc` to wrapper when overriding foreground/text colors
- Outlook.com adds `data-ogsb` to wrapper when overriding background colors
- **ONLY work in Outlook.com webmail** — NOT in Outlook desktop (Windows)
- Must be in the `<style>` block in `<head>` (Outlook.com preserves `<style>`)

### `[data-outlook-cycle]` — Outlook Mobile Dark Mode
```css
[data-outlook-cycle] .dark-override {
  background-color: #1a1a1a !important;
  color: #ffffff !important;
}
```
- Outlook iOS and Android apps may inject this attribute in dark mode
- Limited and inconsistent support — test thoroughly

### `.darkmode` Class Targeting
Some email clients inject a `.darkmode` class on `<body>` or wrapper in dark mode:
```css
.darkmode .text-color { color: #ffffff !important; }
.darkmode .bg-color { background-color: #1a1a1a !important; }
```
- Not standardized — client support varies, test in specific clients

## The 1x1 Pixel Background Trick (Outlook Dark Mode Prevention)

Exploits Outlook's Word engine behavior: when an element has a `background-image`, the engine may skip inverting its `background-color`.

### Implementation Patterns

#### On Wrapper `<table>`
```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background-color: #ffffff; background-image: url('https://example.com/1x1.gif'); background-repeat: repeat;">
```

#### On CTA Button `<td>`
```html
<td style="background-color: #1a73e8; background-image: url('https://example.com/1x1-blue.gif'); background-repeat: repeat; padding: 12px 40px;">
  <a href="..." style="color: #ffffff; text-decoration: none;">Shop Now</a>
</td>
```

#### Base64-Encoded Inline (No External Dependency)
```html
<td style="background-color: #ffffff; background-image: url(data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7); background-repeat: repeat;">
```

### Color-Matched Variants
- **1x1 white GIF** — for white/light backgrounds
- **1x1 colored GIF** — matching the exact background color (e.g., blue 1x1 for blue button)
- **1x1 transparent GIF** — universal fallback; `background-color` remains visible
- **Base64 inline** — avoids external hosting; data URI in `style` attribute

### When to Use
- Colored CTA button `<td>` cells — preserves button background in dark mode
- Branded header/banner backgrounds — preserves brand colors
- Email wrapper `<table>` — preserves body background
- Any element where forced inversion would destroy design intent

### Limitations
- NOT universally reliable — behavior changes between Outlook versions and updates
- Some Outlook builds ignore the `background-image` signal entirely
- Base64 data URI may not work in all Outlook versions (some strip data URIs)
- Externally hosted images require load; if images are blocked, the trick fails
- **Preserves BACKGROUND only** — does NOT prevent text color inversion (risk: white text on white background)

## Mid-Range Color Strategy for Outlook Desktop

Since you cannot detect Outlook dark mode state, choose colors that survive inversion:
- Avoid pure white `#ffffff` backgrounds — use `#f5f5f5` or `#fafafa` instead
- Avoid pure black `#000000` text — use `#333333` or `#222222` instead
- Mid-range grays (#666666 to #999999) are in the **unpredictable zone**
- Saturated brand colors — inversion depends on luminance
- General rule: high-luminance = inverted; low-luminance = left alone

## Complete Outlook Dark Mode Pattern

```html
<head>
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <style>
    /* Standard dark mode (Apple Mail, Outlook macOS) */
    @media (prefers-color-scheme: dark) {
      .dark-bg { background-color: #1a1a2e !important; }
      .dark-bg-card { background-color: #16213e !important; }
      .dark-text { color: #e0e0e0 !important; }
      .dark-text-h { color: #f5f5f5 !important; }
      .dark-link { color: #4da3ff !important; }
      .dark-border { border-color: #2d2d50 !important; }
      .dark-img-light { display: none !important; }
      .dark-img-dark { display: block !important; max-height: none !important; overflow: visible !important; }
    }

    /* Outlook Windows / Outlook.com / Outlook iOS */
    [data-ogsc] .dark-text { color: #e0e0e0 !important; }
    [data-ogsc] .dark-text-h { color: #f5f5f5 !important; }
    [data-ogsc] .dark-link { color: #4da3ff !important; }
    [data-ogsb] .dark-bg { background-color: #1a1a2e !important; }
    [data-ogsb] .dark-bg-card { background-color: #16213e !important; }
    [data-ogsb] .dark-border { border-color: #2d2d50 !important; }
  </style>
</head>
```

## VML in Dark Mode

VML fills don't respond to CSS dark mode. Options:

### Option 1: Accept Default Behavior
VML `fillcolor` stays the same in dark mode. If the fill is a brand color or
dark color, this usually works fine.

### Option 2: Transparent VML with CSS Background
```html
<!--[if mso]>
<v:rect fill="false" stroke="false" style="width:600px; height:44px;">
<v:textbox inset="0,0,0,0">
<![endif]-->
<div class="dark-bg" style="background-color:#007bff;">
  <!-- Button content -->
</div>
<!--[if mso]>
</v:textbox>
</v:rect>
<![endif]-->
```

## Common Outlook Dark Mode Issues

### Issue 1: White Text Disappearing
When Outlook auto-darkens backgrounds, white text (#ffffff) stays white and becomes invisible.
**Fix:** Use `[data-ogsc]` to set a visible dark-mode text color.

### Issue 2: Logo on White Background
White logos on transparent backgrounds vanish in dark mode.
**Fix:** Add a white border/outline or use the image swap pattern.

### Issue 3: Background Color Attribute on TD
Outlook dark mode overrides `bgcolor` HTML attribute but may miss `background-color` CSS.
**Fix:** Set BOTH `bgcolor="#ffffff"` AND `style="background-color:#ffffff"` AND add `[data-ogsb]` override.

### Issue 4: Horizontal Rules / Dividers
`<hr>` and `border-top` dividers may vanish in dark mode.
**Fix:** Use `[data-ogsb]` to set a visible border color in dark mode.