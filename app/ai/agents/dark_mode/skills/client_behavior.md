# Email Client Dark Mode Behavior Matrix

## How Each Client Handles Dark Mode

| Client | Dark Mode Type | Meta Respected | CSS Override | Behavior |
|--------|---------------|----------------|--------------|----------|
| Apple Mail (macOS) | System | Yes | prefers-color-scheme | Respects meta + media query, no auto-inversion |
| Apple Mail (iOS) | System | Yes | prefers-color-scheme | Same as macOS |
| Gmail (iOS) | System | No | None | Auto-inverts light backgrounds to dark |
| Gmail (Android) | System | No | None | Auto-inverts, may override inline colors |
| Gmail (Web) | Setting | No | None | No dark mode rendering (as of 2025) |
| Outlook (Windows) | Setting | Partial | data-ogsc/data-ogsb | Overrides text and background colors |
| Outlook (macOS) | System | Yes | prefers-color-scheme | Respects meta + media query |
| Outlook.com | Setting | Partial | data-ogsc/data-ogsb | Overrides text and background colors |
| Outlook (iOS) | System | Partial | data-ogsc/data-ogsb | Partial override behavior |
| Yahoo (iOS) | System | No | None | Auto-inverts some elements |
| Yahoo (Android) | System | No | None | Auto-inverts some elements |
| Samsung Mail | System | No | None | Aggressive auto-inversion |

## Dark Mode Categories

### Category 1: Full Support (respects your CSS)
- Apple Mail (all platforms)
- Outlook (macOS)

**Strategy:** Use `prefers-color-scheme` media query. Full control.

### Category 2: Partial Support (overrides with own selectors)
- Outlook (Windows, Outlook.com, iOS)

**Strategy:** Must use `[data-ogsc]` for text colors, `[data-ogsb]` for backgrounds.
These are Outlook-specific attribute selectors that override Outlook's own dark mode.

### Category 3: No Support (auto-inverts)
- Gmail (iOS, Android)
- Yahoo (iOS, Android)
- Samsung Mail

**Strategy:** Cannot control dark mode. Focus on ensuring auto-inversion doesn't break layout.
- Use transparent images where possible
- Avoid white text on colored backgrounds (gets inverted to dark-on-dark)
- Test with inverted colors to verify readability

## Priority Implementation Order

1. `<meta name="color-scheme" content="light dark">` -- tells clients we support dark mode
2. `<meta name="supported-color-schemes" content="light dark">` -- Apple Mail compatibility
3. `@media (prefers-color-scheme: dark)` -- Apple Mail, Outlook macOS
4. `[data-ogsc]` / `[data-ogsb]` selectors -- Outlook Windows/web/iOS
5. Transparent/adaptive images -- All clients including auto-inversion

## Color-Scheme Meta Tag Behavior

```html
<meta name="color-scheme" content="light dark">
```

- **With meta:** Client knows the email supports dark mode -> uses CSS overrides
- **Without meta:** Client may auto-invert colors (Gmail, Samsung) -> unpredictable results
- **`light` only:** Forces light mode in supporting clients (Apple Mail)
