# Link Validation Patterns for Email HTML

> L3 skill file — distilled from docs/SKILL_email-link-validation-dom-reference.md
> Auto-loaded when review focus includes link validation.

## Protocol Rules
- **HTTPS required** for all web links — HTTP triggers spam filters
- **Allowed:** `https:`, `http:`, `mailto:`, `tel:`, `sms:`, `webcal:`
- **BLOCKED (always flag):** `javascript:`, `data:`, `vbscript:`
- **Custom URI schemes** (`myapp://`) — warn; prefer universal links

## URL Format Validation (syntax-only, no HTTP requests)
- Use `urlparse()` — verify scheme, netloc, path present for web URLs
- Flag empty href (`href=""`), fragment-only (`href="#"`), `javascript:void(0)`
- Flag unencoded spaces and special characters (`<`, `>`, `[`, `]`, `{`, `}`, `|`, `\`, `^`, `` ` ``)
- Flag double-encoding (`%2520` = double-encoded space)
- Flag path traversal (`/../..`)

## ESP Template Variable Syntax
- **Liquid (Braze):** `{{ variable }}` / `{% tag %}`
- **AMPscript (SFMC):** `%%[= expression ]%%`
- **JSSP (Adobe Campaign):** `<%= expression %>`
- Validate balanced delimiters — unbalanced = broken link in production
- Skip URL format validation for template-only hrefs

## Phishing Signal Detection
- If visible link text contains a URL domain, it MUST match the href domain
- `<a href="https://evil.com">https://paypal.com</a>` = SEVERE phishing signal
- Action text ("Shop now", "Learn more") with any href = SAFE
- ESP tracking redirect URLs in href with action text = SAFE

## VML Link Coherence (Outlook)
- VML `href` on `<v:roundrect>`, `<v:rect>` etc. is NOT rewritten by ESP click tracking
- Common error: VML button href differs from the `<a>` tag href
- Always flag VML href presence as a reminder to sync with HTML links

## `mailto:` Link Validation
- Format: `mailto:user@example.com?subject=...&body=...`
- Parameters must be URL-encoded (`%20` for space, `%0A` for newline)
- Multiple recipients: comma-separated, no spaces

## `tel:` Link Validation
- Format: `tel:+15551234567` (E.164 — country code, digits only)
- Extension: `,1234` (pause + dial) or `;ext=1234`
- No spaces, no dashes in the `tel:` URL

## Image Link Rules
- Linked images MUST have descriptive alt text (link action, not image description)
- Set `border: 0` and `text-decoration: none` on `<a>` wrapping images
- Linked image without alt = inaccessible + spam signal

## Common Anti-Patterns to Flag
1. HTTP links (should be HTTPS)
2. Empty/placeholder hrefs
3. Unbalanced template variables
4. Display text URL ≠ href domain
5. VML href without matching HTML href
6. Links with no accessible text (no text, no img alt)
7. `javascript:` or `data:` protocols
8. Unencoded special characters in URLs
