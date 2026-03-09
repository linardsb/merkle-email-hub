# Outlook Dark Mode — Selectors and Patterns

## Outlook Dark Mode Attribute Selectors

Outlook desktop and Outlook.com use proprietary attribute selectors:

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

### Option 2: MSO-Specific Dark Style Override
```html
<!--[if mso]>
<style>
  /* Note: [data-ogsb] does NOT work reliably on VML fills */
  /* Best approach: use neutral VML fills that work in both modes */
</style>
<![endif]-->
```

### Option 3: Use Transparent VML with CSS Background
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
