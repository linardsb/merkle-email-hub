<!-- L4 source: docs/SKILL_html-email-css-dom-reference.md sections 6-14 -->
<!-- Last synced: 2026-03-13 -->

# CSS Syntax Validation — L3 Reference

## Syntax Errors to Flag

| Pattern | Severity | Example |
|---------|----------|---------|
| Empty value | warning | `color: ;` |
| Missing semicolon in multi-line | info | `color: red\nfont-size: 14px` |
| Unclosed braces | error | `.class { color: red` |
| Invalid property name | warning | `colr: blue;` |
| Unitless numeric (non-zero) | warning | `font-size: 14` (needs `px`) |

## Vendor Prefixes (Flag All in Email)

| Prefix | Engine | Email Relevance |
|--------|--------|-----------------|
| `-webkit-` | Chrome/Safari | Only Apple Mail uses WebKit |
| `-moz-` | Firefox | No email client uses Gecko |
| `-ms-` | IE/Edge Legacy | Outlook uses Word, not IE |
| `-o-` | Opera Legacy | Dead engine |

**Rule:** Any vendor-prefixed property is wasted bytes in email. Exception: `-webkit-text-size-adjust` in Apple Mail.

## External Resources (Always Error)

| Pattern | Why |
|---------|-----|
| `<link rel="stylesheet">` | Stripped by ALL email clients |
| `@import url(...)` | Stripped by Gmail, most webmail |
| `@font-face` with external URL | Only Apple Mail loads web fonts |

## !important Usage Guidelines

- **Expected in dark mode**: `@media (prefers-color-scheme: dark)` requires `!important`
- **Expected for resets**: Body margin/padding reset
- **Flag if**: >10 non-dark-mode `!important` declarations
- **Why problematic**: Email clients inject their own `!important` styles for dark mode; conflicts cause unpredictable colors

## Non-Inlined CSS Risk

Properties that MUST have inline fallbacks for Gmail:
- `display`, `width`, `max-width`, `height`
- `background-color`, `color`, `font-size`, `font-family`
- `margin`, `padding`, `text-align`, `vertical-align`

Gmail strips `<style>` blocks in: clipped emails (>102KB), forwarded emails, AMP-disabled views.
