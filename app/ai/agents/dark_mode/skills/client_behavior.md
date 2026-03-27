---
priority: 3
version: "1.0.0"
---

> Client rendering constraints are injected via audience context from the
> centralized client matrix (`data/email-client-matrix.yaml`). Per-client
> CSS support details have been removed — see the matrix for current data.
> For specific client capabilities, see Phase 32.4 `lookup_client_support` tool.

# Email Client Dark Mode Behavior — Agent Decision Guide

## Three Types of Dark Mode Behavior

1. **No color change** — dark chrome (inbox, toolbar) but email HTML untouched (rare)
2. **Partial inversion** — only light backgrounds changed to dark; dark backgrounds and text left alone (Apple Mail, iOS Mail default)
3. **Full forced inversion** — ALL colors forcibly inverted regardless of design intent (Outlook desktop Windows, Outlook.com, Gmail Android)

## Dark Mode Categories

### Category 1: Full Support (respects your CSS)
- Apple Mail (all platforms)
- Outlook (macOS)
- Thunderbird

**Strategy:** Use `prefers-color-scheme` media query. Full control.

### Category 2: Partial Support (own selectors)
- Outlook (Windows, Outlook.com, iOS)

**Strategy:** Must use `[data-ogsc]` for text colors, `[data-ogsb]` for backgrounds.

### Category 3: No Support (auto-inverts)
- Gmail (iOS, Android, Web)
- Yahoo (iOS, Android)
- Samsung Mail (partial — see double-inversion note)

**Strategy:** Cannot control dark mode. Focus on defensive color choices:
- Use transparent images where possible
- Avoid white text on colored backgrounds (gets inverted to dark-on-dark)
- Test with inverted colors to verify readability

## Priority Implementation Order

1. `<meta name="color-scheme" content="light dark">` — tells clients we support dark mode
2. `<meta name="supported-color-schemes" content="light dark">` — Apple Mail compatibility
3. `@media (prefers-color-scheme: dark)` — Apple Mail, Outlook macOS, Thunderbird
4. `[data-ogsc]` / `[data-ogsb]` selectors — Outlook Windows/web/iOS
5. Defensive color choices — Gmail, Yahoo, Samsung (no CSS control)
6. Transparent/adaptive images — All clients including auto-inversion
