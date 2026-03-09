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

## Reduced Motion Considerations

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

## Best Practices

1. **Always progressive enhancement** — Animation is decoration, never essential
2. **Test without animation** — Email must work and look good without it
3. **Respect reduced motion** — Include `prefers-reduced-motion` override
4. **Keep it subtle** — Don't use aggressive or distracting animations
5. **File size** — Animations add CSS weight; monitor 102KB Gmail threshold
6. **No JavaScript** — All animations must be CSS-only
