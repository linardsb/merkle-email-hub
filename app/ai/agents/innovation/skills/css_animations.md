---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_html-email-components.md section 27 -->
<!-- Last synced: 2026-03-13 -->

# CSS Animations in Email

## Client Support

| Client | @keyframes | transition | :hover | transform |
|--------|-----------|------------|--------|-----------|
| Apple Mail | ✅ | ✅ | ✅ | ✅ |
| Gmail (Web) | ❌ | ❌ | ❌ | ❌ |
| Gmail (App) | ❌ | ❌ | ❌ | ❌ |
| Outlook desktop | ❌ | ❌ | ❌ | ❌ |
| Outlook.com | ❌ | ❌ | ❌ | ❌ |
| Yahoo (Web) | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| Samsung Mail | ❌ | ❌ | ❌ | ❌ |
| Thunderbird | ✅ | ✅ | ✅ | ✅ |

**Coverage:** ~25-30% of email opens (Apple Mail + Thunderbird)

## Pattern 1: Fade-In Animation

```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fadeIn 1s ease-in-out;
}
```

**Fallback:** Element is immediately visible (opacity defaults to 1).

## Pattern 2: Slide-In from Left

```css
@keyframes slideIn {
  from { transform: translateX(-50px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.slide-in {
  animation: slideIn 0.6s ease-out;
}
```

**Fallback:** Element appears in final position without animation.

## Pattern 3: Hover Effect on CTA

Desktop webmail clients only (`:hover` does not work on touch devices).

```css
.cta-button {
  display: inline-block;
  padding: 12px 24px;
  background-color: #007bff;
  color: #ffffff;
  text-decoration: none;
  transition: background-color 0.3s ease;
}

.cta-button:hover {
  background-color: #0056b3;
}
```

**Fallback:** Button has static color. No visual change on hover.

## Pattern 4: Pulse Attention Grabber

```css
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.pulse {
  animation: pulse 2s ease-in-out infinite;
}
```

**Fallback:** Element stays at normal size.

## Pattern 5: Countdown Timer (Visual Only)

Uses a series of elements shown/hidden over time with `animation-delay`:

```css
.countdown-digit { display: none; position: absolute; top: 0; left: 0; }
.countdown-digit:nth-child(1) { animation: showHide 1s 0s forwards; }
.countdown-digit:nth-child(2) { animation: showHide 1s 1s forwards; }
.countdown-digit:nth-child(3) { animation: showHide 1s 2s forwards; }

@keyframes showHide {
  0%, 99% { display: block; opacity: 1; }
  100% { display: none; opacity: 0; }
}
```

Note: This is a visual trick, not a real countdown. Use for promotional effect only.

## Reduced Motion (REQUIRED)

Always respect user preferences for reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  .fade-in, .slide-in, .pulse {
    animation: none !important;
    transition: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
```

## High Contrast Mode

Respect high contrast preferences for users with visual impairments:

```css
@media (prefers-contrast: high) {
  .cta-button {
    border: 2px solid currentColor !important;
  }
  /* Ensure text/background contrast meets WCAG AAA (7:1) */
}
```

## Progressive Enhancement with @supports

Use `@supports` queries to apply advanced CSS only in capable clients:

```css
/* Base: works everywhere */
.hero-text { font-size: 24px; }

/* Enhanced: only in clients that support @supports */
@supports (font-size: clamp(16px, 4vw, 32px)) {
  .hero-text { font-size: clamp(16px, 4vw, 32px); }
}
```

## Emerging CSS Features (Apple Mail)

### CSS clamp() for Fluid Typography
Fluid sizing that scales between min and max values. Apple Mail only.
```css
.heading { font-size: clamp(18px, 5vw, 36px); }
.body-text { font-size: clamp(14px, 3vw, 18px); }
```
**Fallback:** Fixed `font-size` value in the base rule (loaded first).

### Variable Fonts
Emerging Apple Mail support. Reduce font file count by using a single variable font file with weight/width axes.
```css
@font-face {
  font-family: 'InterVariable';
  src: url('https://example.com/Inter-Variable.woff2') format('woff2');
  font-weight: 100 900;
}
.variable-heading { font-family: 'InterVariable', Arial, sans-serif; font-weight: 700; }
.variable-body { font-family: 'InterVariable', Arial, sans-serif; font-weight: 400; }
```
**Fallback:** System font stack via `font-family` cascade.

## Best Practices

1. **Always progressive enhancement** — Animation is decoration, never essential
2. **Test without animation** — Email must work and look good without it
3. **Respect reduced motion** — Include `prefers-reduced-motion` override (REQUIRED)
4. **Respect high contrast** — Include `prefers-contrast` styles where relevant
5. **Keep it subtle** — Don't use aggressive or distracting animations
6. **File size** — Animations add CSS weight; monitor 102KB Gmail threshold
7. **No JavaScript** — All animations must be CSS-only
8. **Use @supports for emerging features** — Never assume client support for clamp(), variable fonts, etc.
9. **Hover is desktop-only** — `:hover` effects are invisible on mobile; never rely on hover for essential information