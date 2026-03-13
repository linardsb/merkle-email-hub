<!-- L4 source: docs/SKILL_email-dark-mode-dom-reference.md sections 13-15, 18 -->
<!-- Last synced: 2026-03-13 -->

# Email Client Dark Mode Behavior Matrix

## Three Types of Dark Mode Behavior

1. **No color change** — dark chrome (inbox, toolbar) but email HTML untouched (rare)
2. **Partial inversion** — only light backgrounds changed to dark; dark backgrounds and text left alone (Apple Mail, iOS Mail default)
3. **Full forced inversion** — ALL colors forcibly inverted regardless of design intent (Outlook desktop Windows, Outlook.com, Gmail Android)

## Client Support Matrix

### Apple Mail / iOS Mail — Full Developer Control
- `<meta name="color-scheme" content="light dark">` — Parsed
- `<meta name="supported-color-schemes" content="light dark">` — Parsed
- `color-scheme: light dark` CSS property — Parsed
- `@media (prefers-color-scheme: dark)` — Full support
- `<picture><source media="(prefers-color-scheme: dark)">` — Supported (Apple Mail only)
- CSS show/hide image swap — Supported
- `color-scheme: light only` (prevent dark mode) — Works

**Auto-inversion rules:**
- With `color-scheme: light dark` AND `@media` dark CSS present: uses YOUR styles (no auto-inversion)
- With `color-scheme: light dark` but NO dark CSS: applies partial auto-inversion
- Without `color-scheme` meta: applies full auto-inversion
- With `color-scheme: light only`: attempts light mode regardless of system setting

**Transparent image behavior:** May add subtle white background/glow behind transparent PNGs in dark mode. Workaround: bake slight dark edges or shadow into the image file.

### Outlook.com (Webmail) — Partial Control via Selectors
- `<meta name="color-scheme">` — Ignored
- `@media (prefers-color-scheme: dark)` — Ignored
- `[data-ogsc]` foreground targeting — Supported
- `[data-ogsb]` background targeting — Supported
- Forced color inversion — Active (overridable via selectors)

### Outlook Desktop (Windows) — No Developer Control
- `<meta name="color-scheme">` — Ignored
- `@media (prefers-color-scheme: dark)` — Ignored
- `[data-ogsc]` / `[data-ogsb]` — Not applicable (not webmail)
- MSO conditional styles — Cannot detect dark mode state
- 1x1 pixel background trick — May prevent background inversion (version-dependent)
- Forced color inversion — Active, cannot be overridden

### Gmail (All Versions) — No Developer Control
- `<meta name="color-scheme">` — Stripped
- `@media (prefers-color-scheme: dark)` — Stripped with `<style>` block
- 1x1 pixel trick — Does not prevent inversion
- Forced color inversion — Active, cannot be overridden

**Gmail Web:** Strips `<style>` in some contexts (clipped/forwarded emails). Prefixes class names. Uses own forced inversion targeting `background-color`, `bgcolor`, `color` inline styles.

**Gmail Android:** Most aggressive forced inversion. Strips `<style>` blocks entirely. No dark mode CSS support whatsoever.

**Gmail iOS:** Similar to Android but occasionally less aggressive. Also strips `<style>`.

**Gmail defensive strategy:** Since Gmail ignores all dark mode CSS, the only approach is defensive color choices:
- Avoid pure `#ffffff` backgrounds — use `#f5f5f5` or off-white
- Avoid pure `#000000` text — use `#333333`
- Use mid-to-dark saturated brand colors that look acceptable whether inverted or not
- Ensure text meets contrast ratios against BOTH light and inverted dark backgrounds

### Samsung Mail (Android 9+) — Partial Support with Caveats
- `@media (prefers-color-scheme: dark)` — Supported
- Forced partial inversion — Also active alongside your CSS

**Double-inversion issue:** Samsung applies BOTH your custom dark styles AND its own partial inversion. This can cause unexpected results (your dark override + Samsung's inversion = colors reverting toward light). Workaround: use `!important` on all dark mode declarations and test specifically in Samsung Mail.

### Thunderbird — Full Support
- `@media (prefers-color-scheme: dark)` — Full support
- `color-scheme` CSS property — Supported

### Yahoo Mail / AOL Mail — Limited
- `@media (prefers-color-scheme: dark)` — Limited/inconsistent
- May apply own forced inversion

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
