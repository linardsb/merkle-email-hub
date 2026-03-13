<!-- L4 source: docs/SKILL_email-dark-mode-dom-reference.md -->
# Email Dark Mode DOM Rendering — Validation Reference

Condensed validation-focused reference from `docs/SKILL_email-dark-mode-dom-reference.md`.
Use this when implementing or validating dark mode support across email clients.

---

## 1. Required Meta Tags

### `<meta name="color-scheme" content="light dark">`
- MUST be in `<head>`, before any `<style>` blocks
- Parsed by: Apple Mail, iOS Mail, macOS Mail
- Without this: Apple Mail may auto-invert colors even with dark mode CSS
- `content="light dark"` — recommended (declares both schemes)

### `<meta name="supported-color-schemes" content="light dark">`
- Legacy companion for older Apple Mail versions
- Place immediately after color-scheme meta

### CSS `color-scheme` Property
```css
:root { color-scheme: light dark; }
/* or */
html { color-scheme: light dark; }
```
- Reinforces meta tag for CSS-aware clients
- Apple Mail/iOS Mail read this alongside the meta tag

---

## 2. Media Query Structure

### Required Pattern
```css
@media (prefers-color-scheme: dark) {
  .element { background-color: #1a1a1a !important; }
  .element { color: #e0e0e0 !important; }
}
```

### Critical Rules
- **`!important` required** on all color declarations — inline styles override without it
- **Must contain color properties** — empty blocks provide no value
- Color properties: `color`, `background-color`, `background`, `border-color`, `border-*-color`
- Place media query inside `<style>` in `<head>`

---

## 3. Outlook.com Attribute Selectors

Outlook.com injects `data-ogsc` (text) and `data-ogsb` (background) attributes on elements:

```css
[data-ogsc] .text { color: #e0e0e0; }
[data-ogsb] .container { background-color: #1a1a1a; }
```

### Rules
- `[data-ogsc]` — controls text color overrides (foreground)
- `[data-ogsb]` — controls background color overrides
- Both should contain actual CSS declarations (not empty)
- Without these: Outlook.com will force-invert colors unpredictably

---

## 4. Color Coherence

### Avoid Invisible Text
- Dark mode color pairs must maintain contrast
- WCAG AA minimum: 4.5:1 contrast ratio for normal text
- Watch for white-on-white or dark-on-dark after inversion
- Background colors in dark mode should have low luminance (< 0.4)

### Safe Dark Mode Color Pairs
| Light Mode | Dark Mode | Purpose |
|-----------|-----------|---------|
| `#ffffff` | `#1a1a1a` | Background |
| `#333333` | `#e0e0e0` | Body text |
| `#000000` | `#f5f5f5` | Headings |

### Dangerous Patterns
- Pure `#ffffff`/`#000000` pairs — clients may double-invert
- Same color for text and background in dark mode
- Light backgrounds in `@media (prefers-color-scheme: dark)` block

---

## 5. Image Handling Patterns

### CSS Show/Hide Pattern
```html
<!-- Light mode image (hidden in dark mode) -->
<img src="logo-light.png" alt="Logo" class="light-img"
     style="display: block; mso-hide: all;">
<!-- Dark mode image (hidden by default, shown in dark mode) -->
<img src="logo-dark.png" alt="" class="dark-img"
     style="display: none; mso-hide: all;">
```

```css
@media (prefers-color-scheme: dark) {
  .light-img { display: none !important; }
  .dark-img { display: block !important; }
}
```

### Rules
- Hidden dark images: `alt=""` to avoid duplicate screen reader announcements
- Hidden dark images: `mso-hide: all` to prevent Outlook showing both
- `<picture>` + `<source media="(prefers-color-scheme: dark)">` for Apple Mail

### 1x1 Pixel Background Prevention (Outlook Desktop)
```html
<td style="background-image: url('1x1-dark.png'); background-color: #1a1a1a;">
```
- Outlook desktop ignores CSS dark mode — use 1x1 pixel background image trick
- Image prevents Outlook from overriding the background color
- Combine with `background-color` as fallback for non-Outlook clients

---

## 6. Client Behavior Matrix

| Client | Meta Tag | Media Query | Forced Inversion | Attribute Selectors |
|--------|----------|-------------|------------------|---------------------|
| Apple Mail | Yes | Yes | Partial | No |
| iOS Mail | Yes | Yes | Partial | No |
| Outlook.com | Ignored | Yes | Full | `[data-ogsc]`, `[data-ogsb]` |
| Outlook Desktop | Ignored | No | Full | No |
| Gmail (web) | Ignored | Yes | No | No |
| Gmail (Android) | Ignored | Sometimes | Sometimes | No |
| Yahoo Mail | Ignored | Yes | No | No |

### Key Implications
- Always include meta tags (Apple) + media queries (most clients) + Outlook selectors
- Outlook desktop requires VML/MSO workarounds for dark mode (1x1 pixel trick)
- Gmail Android behavior is unpredictable — test thoroughly
- No single technique covers all clients — use all three approaches

---

## 7. Validation Checklist

1. `<meta name="color-scheme" content="light dark">` in `<head>` ✓
2. `<meta name="supported-color-schemes" content="light dark">` ✓
3. `:root { color-scheme: light dark; }` in `<style>` ✓
4. `@media (prefers-color-scheme: dark)` block with color declarations ✓
5. All dark mode color declarations use `!important` ✓
6. `[data-ogsc]` selectors for Outlook.com text colors ✓
7. `[data-ogsb]` selectors for Outlook.com backgrounds ✓
8. Color pairs maintain WCAG AA 4.5:1 contrast ✓
9. Dark backgrounds have low luminance (< 0.4) ✓
10. Swap images use `alt=""` and `mso-hide: all` ✓
