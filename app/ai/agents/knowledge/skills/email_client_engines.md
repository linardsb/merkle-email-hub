<!-- L4 source: docs/SKILL_html-email-css-dom-reference.md -->
# Email Client Rendering Engines

## Rendering Engine Map

| Client | Platform | Engine | CSS Support |
|--------|----------|--------|-------------|
| Apple Mail | macOS, iOS | WebKit | Excellent |
| Gmail | Web | Blink (restricted) | Good (with caveats) |
| Gmail | Android | WebView (restricted) | Moderate |
| Gmail | iOS | WebKit (restricted) | Good |
| Outlook 2007-2019 | Windows | Microsoft Word | Poor |
| Outlook 365 | Windows | Microsoft Word | Poor |
| Outlook.com | Web | Blink/WebKit | Good |
| Outlook | macOS | WebKit | Good |
| Outlook | iOS/Android | WebKit/WebView | Good |
| Yahoo Mail | Web | Blink/WebKit | Moderate |
| Yahoo Mail | Mobile | WebView | Moderate |
| Samsung Mail | Android | WebView | Moderate |
| Thunderbird | Desktop | Gecko | Good |
| AOL Mail | Web | Blink/WebKit | Good |

## Engine Implications

### WebKit (Apple Mail, Outlook macOS, iOS clients)
- Full CSS3 support including media queries, animations, flexbox
- Supports `<style>` blocks and `@media` queries
- Best target for progressive enhancement
- Supports `prefers-color-scheme` for dark mode

### Microsoft Word (Outlook 2007-2019, 365 desktop)
- Renders HTML using Word's HTML engine — NOT a browser engine
- No CSS3, no media queries, no border-radius, no background-image
- Tables are the ONLY reliable layout mechanism
- Supports VML for advanced shapes and backgrounds
- MSO-specific CSS properties (mso-line-height-rule, mso-font-alt, etc.)

### Blink/WebKit Restricted (Gmail)
- Strips `<style>` blocks in some contexts (Gmail app on non-Gmail accounts)
- Prefixes CSS class names (`.xyz` → `.m_-xyz`)
- Strips `<link>` tags and `@import`
- Removes `id` attributes in some cases
- Supports most inline CSS properties
- **Gmail web** supports `<style>` blocks in `<head>`
- **Gmail app** behavior varies by account type (Gmail vs IMAP)

### WebView (Mobile apps, Samsung Mail)
- Generally good CSS support but varies by Android/WebView version
- Media query support inconsistent
- Dark mode behavior varies by OS version and settings
- Samsung Mail aggressively auto-inverts colors

## Version Fragmentation

### Outlook Desktop
- 2007 (Word 2007 engine) — worst support
- 2010 (Word 2010) — slight improvements
- 2013 (Word 2013) — same as 2010 in practice
- 2016/2019/365 (Word 2016) — best Word engine, still limited
- Target: `<!--[if gte mso 12]>` for all Word-engine versions

### Gmail
- Gmail web (logged in) — supports `<style>`
- Gmail web (not logged in / delegation) — may strip `<style>`
- Gmail app (Gmail account) — supports most `<style>`
- Gmail app (non-Gmail IMAP) — strips `<style>`
- Always inline critical styles as fallback

### Apple Mail
- macOS 13+ and iOS 16+ — excellent support
- Older versions — still good, minor differences
- Dark mode fully supported via `prefers-color-scheme`
