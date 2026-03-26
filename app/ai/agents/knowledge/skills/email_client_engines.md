# Email Client Rendering Engines

> Client rendering data (engines, CSS support, dark mode) is centralized in
> `data/email-client-matrix.yaml`. The engine map table has been removed.
> For specific client capabilities, see Phase 32.4 `lookup_client_support` tool.

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
