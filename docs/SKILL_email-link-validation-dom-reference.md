# HTML Email Link Validation — Complete DOM Tag Reference

Every link-related tag, attribute, protocol, URL pattern, validation rule, rendering behavior, and email-client-specific quirk that affects how links are parsed, validated, rewritten, rendered, and interacted with in HTML email.

---

## 1. How Email Clients Validate and Process Links

Email clients don't just render links — they actively parse, validate, rewrite, and in some cases block links before the recipient ever sees them. Understanding the full link processing pipeline is critical.

### Link Processing Pipeline in Email Clients
1. **Spam filter URL scanning** — every `href` is extracted and checked against blocklists (SURBL, URIBL, DBL, Google Safe Browsing, Microsoft SmartScreen)
2. **URL rewriting** — ESP click tracking rewrites all `href` values through redirect servers before sending
3. **Client-side URL rewriting** — some clients (Gmail, Outlook) rewrite links AGAIN through their own proxy/safe-link systems
4. **Link preview/prefetch** — some security systems pre-click links to check for malware (can trigger tracking pixels and conversions)
5. **DOM rendering** — the client renders the `<a>` tag with the final (potentially rewritten) URL
6. **Click handling** — the client intercepts the click, may show a warning, then redirects to the destination
7. **Post-click tracking** — the ESP redirect server logs the click before forwarding to the final URL

### What Gets Validated
- The `href` attribute value (URL structure, protocol, domain, path, parameters)
- The visible link text (compared against the `href` for phishing detection)
- The `title` attribute (scanned for spam keywords)
- The `alt` text of linked images (compared against `href`)
- CSS styling on the link (hidden links, invisible links, deceptive styling)
- The `target` attribute (stripped or overridden by most clients)
- Surrounding context (what text/content is near the link)

---

## 2. `<a>` Tag — Core Link Element

### Required Attributes for Email Links

#### `href` — Link Destination (Mandatory)
```html
<a href="https://example.com/page">Link text</a>
```
- **MUST be present** — an `<a>` tag without `href` is not a functional link; some clients ignore it entirely
- **MUST be a valid URL** — malformed URLs may be stripped, blocked, or trigger security warnings
- **MUST use absolute URLs** — relative URLs (`/page.html`) don't work in email because email has no base URL context
- **Should use HTTPS** — HTTP links are increasingly flagged by spam filters; some clients show security warnings for HTTP links
- **Must not be empty** (`href=""`) — empty href may cause the email client to reload or behave unexpectedly
- **Must not contain only a hash** (`href="#"`) — fragment-only links don't work reliably in email; some clients strip them
- **Maximum practical length:** ~2,083 characters (IE/legacy limit; modern clients handle longer, but ESP tracking adds to URL length)
- **No whitespace in URL** — spaces in URLs must be encoded as `%20`; unencoded spaces break the link
- **No line breaks in `href`** — line breaks in the `href` attribute value can break the URL across email clients

#### `style` — Inline Styling (Required in Email)
```html
<a href="https://example.com" style="color: #1a73e8; text-decoration: underline; font-family: Arial, sans-serif; font-size: 16px;">Link text</a>
```
- **`color`** — must be set inline; email clients apply inconsistent default link colors
- **`text-decoration`** — must be set inline; controls underline visibility; `underline` for body links, `none` for buttons/navigation
- **`font-family`** — must be set inline; links don't reliably inherit font from parent elements in all clients
- **`font-size`** — must be set inline for same reason
- **`font-weight`** — set inline if the link should be bold
- **`line-height`** — set inline for consistent vertical spacing
- **`display`** — `inline` (default), `block`, or `inline-block` depending on usage context

### Optional Attributes on Email `<a>` Tags

#### `title` — Supplementary Link Description
```html
<a href="https://example.com" title="Visit our winter sale page">Winter Sale</a>
```
- Provides tooltip on hover in desktop webmail clients (Gmail web, Outlook.com, Yahoo web)
- Screen readers may announce the `title` attribute
- **Spam filter scanning:** `title` text is scanned for spam keywords
- **Not a substitute for descriptive link text** — many email clients and assistive technologies ignore `title`
- **Should not duplicate the link text** — if `title` matches the visible text, it adds no value and causes screen reader repetition

#### `target` — Link Target Window
```html
<a href="https://example.com" target="_blank">Link text</a>
```
- **`target="_blank"`** — most email clients force links to open in a new window/tab regardless of this attribute; including it is defensive
- **Gmail:** ignores `target` and always opens links in a new tab
- **Outlook desktop:** opens links in the default browser (ignores `target`)
- **Apple Mail:** respects `target="_blank"`
- **Outlook.com:** strips `target` and forces new tab
- **`target="_self"`** — may cause webmail clients to navigate away from the inbox (dangerous; avoid)
- **`target="_parent"` / `target="_top"`** — unreliable in email; may break out of webmail frame
- **Recommendation:** include `target="_blank"` as defensive default; most clients override it anyway

#### `id` — Link Identifier
```html
<a href="https://example.com" id="cta-primary">Shop Now</a>
```
- Used for fragment link targets (`#cta-primary`) within the same email
- Fragment links (`<a href="#section-id">`) have limited support in email — work in Apple Mail, some webmail; fail in Gmail, Outlook desktop
- `id` must be unique within the email DOM
- Gmail may prefix/rename `id` values

#### `class` — CSS Class
```html
<a href="https://example.com" class="link-color dm-link">Link text</a>
```
- Used for `<style>` block targeting (media queries, dark mode overrides)
- **Gmail strips or renames classes** — do not rely on class alone for critical styling; always include inline styles as baseline
- Useful for: responsive link styling, dark mode color overrides (`@media (prefers-color-scheme: dark)`), Outlook.com dark mode (`[data-ogsc]`)

#### `name` — Named Anchor (Deprecated)
```html
<a name="section-top"></a>
```
- Legacy attribute for creating anchor targets; replaced by `id` attribute
- Some older email clients may still use `name` for fragment navigation
- **Not recommended** — use `id` instead

#### `rel` — Link Relationship
```html
<a href="https://example.com" rel="noopener noreferrer">Link text</a>
```
- **`rel="noopener"`** — prevents the linked page from accessing the opener window; security best practice for `target="_blank"` links
- **`rel="noreferrer"`** — prevents the browser from sending the referrer header; hides the email client URL from the destination server
- **`rel="nofollow"`** — tells search engines not to follow; irrelevant in email but some ESPs add it
- **Most email clients strip `rel`** — Gmail, Outlook.com, and others remove the `rel` attribute; include it for clients that preserve it (Apple Mail, Thunderbird)
- **`rel="noopener noreferrer"` combined with `target="_blank"`** — the security-safe pattern for email links

#### `aria-label` — Accessible Link Name
```html
<a href="https://example.com/winter-sale" aria-label="Shop the winter sale — 50% off all coats" style="color: #1a73e8;">Read more</a>
```
- Provides a descriptive accessible name when the visible link text is generic ("Read more", "Click here")
- **Gmail strips `aria-label`** — do not rely on it as the only accessible name; always make visible text as descriptive as possible
- Apple Mail, iOS Mail, Thunderbird preserve `aria-label`
- Outlook desktop may or may not preserve it depending on version

#### `aria-describedby` — Additional Link Description
```html
<a href="https://example.com" aria-describedby="link-desc-1">Shop Now</a>
<span id="link-desc-1" style="position: absolute; clip: rect(0,0,0,0); height: 1px; width: 1px; overflow: hidden;">Opens the winter sale page with 50% discounts on all outerwear</span>
```
- References a hidden element with additional description
- Screen readers announce the referenced text after the link text
- Same client support limitations as `aria-label`

#### `tabindex` — Tab Order Control
```html
<a href="https://example.com" tabindex="0">Link text</a>
```
- `tabindex="0"` — default; link is in normal tab order (unnecessary on `<a>` tags which are natively focusable)
- `tabindex="-1"` — removes from tab order; link cannot be reached via keyboard Tab; use for hidden/duplicate links
- `tabindex="1"` or higher — forces tab order priority; NOT recommended in email; disrupts natural flow
- **Webmail context:** tab order in email is relative to the email client's own UI; the email content tab order starts after the client's toolbar/navigation

---

## 3. Link Protocol Schemes

### `https://` — Secure HTTP (Recommended)
```html
<a href="https://example.com/page">Link text</a>
```
- **Recommended for all email links** — HTTPS signals legitimacy; some spam filters penalize HTTP-only links
- **All modern ESPs use HTTPS** for tracking redirect URLs
- **Gmail, Outlook, Yahoo** may show security indicators for HTTPS vs HTTP links

### `http://` — Unsecure HTTP
```html
<a href="http://example.com/page">Link text</a>
```
- **Discouraged** — HTTP links may trigger spam filter scoring; some clients show "not secure" warnings
- **Still functional** — all email clients render HTTP links; they just may be flagged
- **Redirect concern:** if your HTTPS tracking link redirects to a final HTTP destination, some clients warn about the unsecure destination

### `mailto:` — Email Composition
```html
<a href="mailto:support@example.com">Email us</a>
<a href="mailto:support@example.com?subject=Help%20Request">Email support</a>
<a href="mailto:support@example.com?subject=Help&body=Please%20describe%20your%20issue">Email with pre-filled body</a>
<a href="mailto:support@example.com?cc=manager@example.com&bcc=log@example.com">Email with CC and BCC</a>
```
- **Parameters:**
  - `subject=` — pre-fills subject line (URL-encoded)
  - `body=` — pre-fills email body (URL-encoded; `%0A` for line breaks, `%20` for spaces)
  - `cc=` — adds CC recipient(s) (comma-separated for multiple)
  - `bcc=` — adds BCC recipient(s)
  - `to=` (after `?`) — additional To recipients
- **Validation:** email address must be valid format; invalid addresses may not trigger the compose window
- **Client behavior:**
  - Desktop webmail (Gmail, Outlook.com): opens compose window within the webmail client
  - Outlook desktop: opens new Outlook compose window
  - Mobile: opens default mail app compose screen
  - Apple Mail: opens compose window
- **Spam considerations:** `mailto:` links are generally positive spam signals (indicates real contact info)
- **Multiple recipients:** `mailto:a@example.com,b@example.com` (comma-separated, no spaces)
- **Maximum URL length:** very long `body=` pre-fills may be truncated; keep under 2,000 characters total

### `tel:` — Phone Call
```html
<a href="tel:+15551234567">Call us: (555) 123-4567</a>
<a href="tel:+15551234567,1234">Call and dial extension 1234</a>
<a href="tel:+15551234567;ext=1234">Call with extension</a>
```
- **Format:** `tel:` followed by full international number with country code (E.164 format recommended)
- **`,` (comma)** — inserts a pause before dialing the extension digits
- **`;ext=`** — declares a phone extension
- **No spaces or dashes in the `tel:` URL** — use only `+`, digits, `,`, `;`, `*`, `#`
- **Client behavior:**
  - Mobile (iOS, Android): initiates phone call or shows call confirmation
  - Desktop: may open Skype, FaceTime, or other VoIP app; or show error
  - Webmail: may do nothing on desktop; may prompt on mobile web
- **iOS auto-detection:** iOS Mail auto-detects phone numbers in text and makes them tappable even without `<a href="tel:">` — use `<meta name="format-detection" content="telephone=no">` to prevent unwanted auto-linking, then manually wrap numbers you want linked
- **Visible text should include the readable phone number** — so users know what they're calling
- **Spam considerations:** `tel:` links are generally neutral; presence of a phone number is a slight legitimacy signal

### `sms:` — Text Message
```html
<a href="sms:+15551234567">Text us</a>
<a href="sms:+15551234567?body=Hi%2C%20I%20need%20help">Text with pre-filled message</a>
<a href="sms:+15551234567&body=Hi%2C%20I%20need%20help">Text (alternate syntax)</a>
```
- **`?body=`** — pre-fills the message body (iOS)
- **`&body=`** — pre-fills the message body (Android) — some implementations require `&` instead of `?`
- **Cross-platform safe:** use `?&body=` (includes both) or test per platform
- **Client behavior:** opens the default messaging app with the number and optional pre-filled text
- **Desktop:** may do nothing or open iMessage (Mac) / messaging app

### `facetime:` and `facetime-audio:` — FaceTime Call (Apple Only)
```html
<a href="facetime:+15551234567">FaceTime video call</a>
<a href="facetime-audio:+15551234567">FaceTime audio call</a>
```
- **Apple devices only** — iOS Mail, Apple Mail
- Non-Apple devices: link does nothing or shows error
- Use alongside regular `tel:` link as fallback

### `whatsapp://` — WhatsApp Deep Link
```html
<a href="https://wa.me/15551234567">Message us on WhatsApp</a>
<a href="https://wa.me/15551234567?text=Hi%20I%20need%20help">WhatsApp with pre-filled message</a>
<a href="whatsapp://send?phone=15551234567&text=Hello">WhatsApp (native scheme)</a>
```
- **`https://wa.me/` is preferred** — works as a universal link; falls back to web if app not installed
- **`whatsapp://` native scheme** — only works if WhatsApp is installed; broken link otherwise
- Phone number format: country code + number, no `+`, no dashes, no spaces

### `tg://` — Telegram Deep Link
```html
<a href="https://t.me/username">Message on Telegram</a>
<a href="tg://resolve?domain=username">Telegram (native scheme)</a>
```
- **`https://t.me/` preferred** — universal link with web fallback

### `fb-messenger://` — Facebook Messenger
```html
<a href="https://m.me/pagename">Message us on Messenger</a>
```
- **`https://m.me/` preferred** — universal link

### `webcal://` — Calendar Subscription
```html
<a href="webcal://example.com/calendar.ics">Subscribe to calendar</a>
```
- Opens the default calendar app and subscribes to the ICS feed
- Supported by: Apple Calendar, Outlook (desktop), Google Calendar (via redirect)
- **Not the same as adding a single event** — this is an ongoing subscription

### `geo:` — Geographic Location
```html
<a href="geo:37.7749,-122.4194">View on map</a>
<a href="https://maps.google.com/?q=37.7749,-122.4194">View on Google Maps</a>
<a href="https://maps.apple.com/?ll=37.7749,-122.4194">View on Apple Maps</a>
```
- `geo:` protocol: opens the default map app (Android); limited iOS support
- **Google Maps HTTPS link preferred** for cross-platform compatibility
- **Apple Maps link** for Apple-targeted emails

### Custom URI Schemes — App Deep Links
```html
<a href="myapp://product/12345">Open in app</a>
<a href="https://example.com/app-link/product/12345">Universal link (opens app or web)</a>
```
- **Custom URI schemes** (`myapp://`) — only work if the specific app is installed; broken link otherwise
- **Universal links (iOS) / App Links (Android)** — HTTPS URLs that the OS intercepts and opens in the app if installed; falls back to web browser if not
- **Email client behavior:** most email clients allow custom URI scheme links; some clients (Gmail) may show a warning before opening
- **Best practice:** always use HTTPS universal/app links with web fallback rather than custom URI schemes

### `data:` URI Scheme — BLOCKED
```html
<!-- DO NOT USE — blocked by most email clients and flagged by spam filters -->
<a href="data:text/html,<h1>Hello</h1>">Link</a>
```
- **BLOCKED by all major email clients** — security risk; can execute HTML/JavaScript
- **Spam filter:** SEVERE negative signal
- **Never use `data:` URIs in email `href` attributes**

### `javascript:` — BLOCKED
```html
<!-- DO NOT USE — blocked by all email clients and flagged by spam filters -->
<a href="javascript:alert('hello')">Link</a>
```
- **BLOCKED universally** — no email client executes JavaScript
- **Spam filter:** SEVERE negative signal
- **Never use `javascript:` in email links**

---

## 4. Link URL Structure Validation

### Domain Validation
- **Domain must resolve** — dead domains cause link errors and hurt sender reputation
- **Domain must match or relate to sender domain** — links to completely unrelated domains raise phishing flags
- **Subdomain consistency** — `shop.example.com`, `tracking.example.com` should all share the sender's root domain where possible
- **Avoid newly registered domains** — domains less than 30 days old are flagged by many filters
- **Domain reputation** — links to domains on blocklists (SURBL, URIBL, Spamhaus DBL) cause delivery failure regardless of email content
- **Internationalized domain names (IDN)** — punycode domains (`xn--...`) may be flagged as suspicious; some clients display the punycode version, which looks phishy to recipients

### URL Path Validation
- **Valid URL encoding** — special characters in paths must be percent-encoded (`%20` for space, `%2F` for forward slash, etc.)
- **No double encoding** — `%2520` (double-encoded space) is suspicious; indicates manipulation
- **Meaningful paths** — `/product/blue-tshirt` is more trustworthy than `/a1b2c3d4e5f6`
- **No path traversal** — `/../../../etc/passwd` patterns are severe phishing/hacking signals
- **No excessively deep paths** — `/a/b/c/d/e/f/g/h/i/j/k/l` may indicate redirect chains or obfuscation
- **File extensions in path** — `.html`, `.php`, `.aspx` are normal; `.exe`, `.zip`, `.bat`, `.scr`, `.js` are malware signals

### URL Query Parameter Validation
- **Standard query format** — `?key=value&key2=value2`
- **UTM parameters** — `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` — standard marketing tracking; neutral to positive signal
- **ESP tracking parameters** — `?e=abc123&c=campaign456` — ESP-specific; recognized by filters
- **Excessive parameters** — very long query strings (20+ parameters) may indicate tracking overload or obfuscation
- **Parameters containing email addresses** — `?email=user@example.com` in URL is a privacy concern; some clients may flag or strip
- **Parameters containing PII** — `?name=John&phone=5551234` — should be avoided for privacy; not directly a spam signal but poor practice
- **Encoded characters in parameters** — normal (`%20`, `%3D`); excessive encoding is suspicious

### URL Fragment Validation
- **`#fragment`** — refers to an anchor within the destination page
- **`#` in email internal links** — `<a href="#section-id">` — limited email client support:
  - Apple Mail: works
  - iOS Mail: works
  - Outlook desktop: does not work (no in-email anchor navigation)
  - Gmail: does not work (strips or ignores fragment links)
  - Outlook.com: limited
  - Yahoo: limited
- **Fragment-only links** (`href="#"`) — do nothing in most email clients; avoid
- **Fragment after tracking redirect** — `https://track.esp.com/click/abc#section` — the fragment may be lost after the redirect; test with your ESP

---

## 5. ESP Click Tracking Link Rewriting

ESPs (Email Service Providers) rewrite all link `href` values for click tracking before the email is sent. Understanding this rewriting is critical for link validation.

### How ESP Link Rewriting Works
```
Original:  https://example.com/sale
Rewritten: https://clicks.esp-domain.com/track/click/abc123def456?url=https%3A%2F%2Fexample.com%2Fsale
```
1. ESP extracts every `href` from the email HTML DOM
2. Each URL is stored in the ESP's database with a unique tracking ID
3. The `href` is replaced with a redirect URL through the ESP's click tracking server
4. When the recipient clicks, the request hits the ESP server, which logs the click and redirects (302) to the original URL

### Link Types ESPs Typically Rewrite
- All `<a href="https://...">` links — rewritten for tracking
- All `<a href="http://...">` links — rewritten for tracking
- **NOT rewritten:** `mailto:` links (some ESPs offer mailto tracking, most don't)
- **NOT rewritten:** `tel:` links
- **NOT rewritten:** `sms:` links
- **NOT rewritten:** `#fragment` anchor links
- **ESP-configurable:** unsubscribe links may use a different tracking domain or be excluded from tracking
- **ESP-configurable:** some ESPs allow excluding specific links from tracking

### ESP Tracking Domain Validation
- **Custom tracking domain** (`clicks.yourdomain.com`) — RECOMMENDED; improves deliverability because the link domain matches the sender domain; requires DNS CNAME setup
- **Default ESP tracking domain** (`clicks.sendgrid.net`, `track.mailchimp.com`, etc.) — functional but the link domain doesn't match the sender domain, which can be a slight negative for phishing detection
- **Tracking domain must have valid SSL certificate** — HTTPS tracking URLs require SSL on the tracking domain
- **Tracking domain must not be on blocklists** — if your ESP's tracking domain is blocklisted (happens with shared infrastructure), all your links are affected

### Double Tracking / Link Proxy Chains
```
Click → ESP tracking server (302) → Gmail Safe Browsing proxy → Final URL
Click → ESP tracking server (302) → Outlook Safelinks proxy → Final URL
```
- Gmail may route clicks through its own link proxy (`google.com/url?...`)
- Outlook/Microsoft routes clicks through Safelinks (`safelinks.protection.outlook.com/...`)
- Yahoo may route through its own proxy
- This means the final redirect chain can be: ESP tracking → client proxy → destination
- **Long redirect chains** can add latency, cause timeouts, or break tracking
- **Test click tracking** through each major client to verify the full redirect chain works

### Link Rewriting and Validation Issues
- **URL length after rewriting** — ESP tracking URLs are significantly longer than original URLs; verify they don't exceed client URL length limits
- **URL encoding after rewriting** — verify the ESP correctly encodes the destination URL within the tracking URL; double-encoding breaks the final redirect
- **Fragment preservation** — `#section-id` at the end of URLs may be lost during ESP redirect; test with your specific ESP
- **Query parameter conflicts** — if the original URL has parameters AND the ESP tracking URL has parameters, verify they don't conflict
- **HTTPS downgrade** — verify the ESP tracking URL uses HTTPS and the redirect to the final URL preserves HTTPS
- **Redirect HTTP status** — ESPs should use 302 (temporary redirect) not 301 (permanent redirect); 301s may be cached by browsers, skewing click counts

---

## 6. Email Client Link Proxy / Safe Link Systems

### Gmail Link Proxy
- Gmail web may route link clicks through `https://www.google.com/url?q=<encoded_destination>&source=gmail&...`
- Provides phishing/malware protection by checking the destination in real-time
- **Cannot be bypassed** — Gmail controls this at the client level
- **Timing impact:** adds a few milliseconds to click-through
- **Tracking impact:** the ESP still sees the click (it happens before the Gmail proxy)
- **Referrer impact:** destination server sees referrer from Google, not from email client

### Microsoft Safelinks (Outlook/Exchange)
```
https://nam01.safelinks.protection.outlook.com/?url=https%3A%2F%2Fexample.com&data=...&sdata=...&reserved=0
```
- Microsoft 365 / Exchange Online wraps ALL email links in Safelinks URLs
- Links are checked in real-time against Microsoft threat intelligence when clicked
- **URL structure:** the original URL is encoded in the `url=` parameter
- **Visible to recipient:** recipients see the Safelinks URL on hover (not the original URL); this can confuse users
- **Cannot be bypassed** by email developers — it's an organization-level security setting
- **Safelinks may pre-click links** — Microsoft's systems may visit the URL before the user clicks to scan for threats; this can trigger ESP click tracking and inflate click metrics
- **Link expiration:** Safelinks URLs may expire after a period, making old emails' links non-functional

### Outlook ATP (Advanced Threat Protection) Link Detonation
- In addition to Safelinks, ATP may "detonate" links — opening them in a sandboxed environment to check for malware
- **This triggers HTTP requests to your destination URL** from Microsoft's servers before the user clicks
- **Impact on tracking:** can cause phantom clicks in your ESP analytics
- **Impact on single-use links:** if your link is a one-time download or single-use token, ATP detonation may "use" it before the recipient clicks

### Barracuda Link Protection
```
https://linkprotect.cudasvc.com/url?a=<encoded_url>&c=...&p=...
```
- Barracuda email security gateway rewrites links similarly to Safelinks
- Adds its own click-time protection
- Common in enterprise environments

### Proofpoint URL Defense
```
https://urldefense.proofpoint.com/v2/url?u=<encoded_url>&d=...&c=...&r=...
```
- Proofpoint email security wraps links in its URL Defense system
- Very common in large enterprises, universities, and government
- **Multiple encoding versions:** v1, v2, v3 with different URL encoding schemes
- **Can break long URLs** — the Proofpoint encoding adds significant length

### Mimecast URL Protect
```
https://url.emailprotection.link/...
```
- Mimecast's URL protection service
- Similar behavior to Safelinks and Proofpoint
- Common in enterprise environments

### Impact of Link Proxies on Email Development
- **All `href` URLs may be rewritten twice** (once by ESP, once by security proxy) — test with real inboxes, not just code review
- **Link hover preview** shows the proxy URL, not your original URL — this can reduce click confidence
- **Link length grows significantly** after double rewriting — may break in some contexts
- **Pre-click scanning** may trigger tracking events — causing inflated open/click rates; ESPs are developing bot-click detection to compensate
- **One-time-use links** (password resets, download tokens, magic login links) may be "consumed" by pre-click scanning — implement click verification (require a second user action on the landing page)
- **Redirect timing** — multiple redirect hops add latency; test perceived click-through speed

---

## 7. Calendar Link Validation

### Google Calendar Event Link
```html
<a href="https://calendar.google.com/calendar/render?action=TEMPLATE&text=Event+Name&dates=20260315T100000Z/20260315T120000Z&details=Event+description+here&location=123+Main+St&sf=true&output=xml">Add to Google Calendar</a>
```

**Parameters:**
- `action=TEMPLATE` — required; tells Google Calendar to create a new event template
- `text=` — event title (URL-encoded; `+` for spaces)
- `dates=` — start/end datetime in `YYYYMMDDTHHMMSSZ` format (UTC); separated by `/`
- `details=` — event description (URL-encoded)
- `location=` — event location (URL-encoded)
- `sf=true` — show event as free (optional)
- `output=xml` — output format (optional)
- `add=` — additional attendee emails (comma-separated, optional)
- `crm=BUSY` / `crm=AVAILABLE` — show as busy or available (optional)
- `recur=RRULE:FREQ=WEEKLY;BYDAY=MO` — recurring event rule (optional)

**Validation:**
- Date format must be exact: `YYYYMMDDTHHMMSSZ` — no dashes, no colons, trailing `Z` for UTC
- All special characters in text fields must be URL-encoded
- Link opens in browser; user must be logged into Google account

### Outlook.com / Live Calendar Event Link
```html
<a href="https://outlook.live.com/calendar/0/deeplink/compose?subject=Event+Name&startdt=2026-03-15T10:00:00Z&enddt=2026-03-15T12:00:00Z&body=Description&location=123+Main+St&path=%2Fcalendar%2Faction%2Fcompose&rru=addevent">Add to Outlook Calendar</a>
```

**Parameters:**
- `subject=` — event title
- `startdt=` — start datetime in ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`)
- `enddt=` — end datetime
- `body=` — event description
- `location=` — event location
- `path=%2Fcalendar%2Faction%2Fcompose` — required path
- `rru=addevent` — required; tells Outlook this is an add-event action
- `allday=true` / `allday=false` — all-day event flag (optional)

**Validation:**
- Date format: ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`) — different from Google Calendar format
- Requires Outlook.com / Microsoft account login

### Yahoo Calendar Event Link
```html
<a href="https://calendar.yahoo.com/?v=60&title=Event+Name&st=20260315T100000Z&et=20260315T120000Z&desc=Description&in_loc=123+Main+St">Add to Yahoo Calendar</a>
```

**Parameters:**
- `v=60` — required; event type
- `title=` — event title
- `st=` — start time (`YYYYMMDDTHHMMSSZ`)
- `et=` — end time
- `desc=` — description
- `in_loc=` — location
- `dur=` — duration (alternative to end time; format: `HHMM`)

**Validation:**
- Date format same as Google: `YYYYMMDDTHHMMSSZ`
- Requires Yahoo account login

### Apple Calendar (iCal) Link
```html
<a href="webcal://example.com/event.ics">Add to Apple Calendar</a>
<a href="https://example.com/event.ics">Download calendar file</a>
```
- `webcal://` — opens directly in Apple Calendar app (iOS, macOS)
- `https://` pointing to an `.ics` file — downloads the file; the OS handler opens the default calendar app
- The `.ics` file must be a valid iCalendar format

### ICS File Download Link
```html
<a href="https://example.com/events/event-123.ics" download="event.ics">Download .ics file</a>
```
- **`download` attribute** — suggests the file should be downloaded rather than opened in browser
- **Most email clients strip the `download` attribute** — the file will typically open in the browser or calendar app instead
- The `.ics` file must be served with `Content-Type: text/calendar` header for proper handling
- **Alternative:** attach the `.ics` file directly to the email as a MIME attachment (more reliable than a download link)

### Calendar Link Validation Summary
- Different calendar services require different date formats — Google/Yahoo use `YYYYMMDDTHHMMSSZ`, Outlook uses ISO 8601
- All text parameters must be URL-encoded
- Links require the user to be logged into the respective calendar service
- No client-side validation — malformed dates will silently create wrong events
- Always include timezone info (UTC `Z` suffix or explicit offset)
- Test each calendar link individually — the formats are not interchangeable

---

## 8. Unsubscribe Link Validation

### HTML Unsubscribe Link
```html
<a href="https://example.com/unsubscribe?id=abc123&email=user%40example.com" style="color: #999999; text-decoration: underline; font-size: 12px;">Unsubscribe</a>
```

**Validation Requirements:**
- **Must be present** in all bulk/marketing email — required by CAN-SPAM, GDPR, CASL, PECR
- **Must be functional** — the link must actually process the unsubscribe; dead or broken unsubscribe links violate regulations and severely damage sender reputation
- **Must be easy to find** — hidden, disguised, or excessively small unsubscribe links violate CAN-SPAM and anger recipients (who then mark as spam)
- **Must work without login** — requiring the user to log in to unsubscribe violates CAN-SPAM
- **Must process within 10 business days** — CAN-SPAM maximum processing time
- **Should be one-click** — RFC 8058 one-click unsubscribe; Gmail and Yahoo require this for bulk senders as of Feb 2024
- **Link text should be clear:** "Unsubscribe", "Unsubscribe from these emails", "Stop receiving these emails" — not hidden behind "Manage" or "Settings"
- **Token-based identification:** use a secure, unique token in the URL to identify the subscriber — don't put the raw email address in the URL (privacy/security concern)
- **HTTPS required** — unsubscribe endpoints should use HTTPS

### `List-Unsubscribe` Header (Not HTML but Affects Link Rendering)
```
List-Unsubscribe: <https://example.com/unsubscribe?id=abc123>, <mailto:unsubscribe@example.com?subject=unsubscribe>
List-Unsubscribe-Post: List-Unsubscribe=One-Click
```
- **`List-Unsubscribe` header** — provides a URL and/or mailto address for machine-readable unsubscribe; Gmail, Apple Mail, Outlook surface this as a native unsubscribe button
- **`List-Unsubscribe-Post`** — enables RFC 8058 one-click unsubscribe via HTTP POST; required by Gmail and Yahoo for bulk senders
- **Both HTTPS URL and mailto** should be provided for maximum client compatibility
- **The `mailto:` version** is a fallback for clients that don't support HTTP-based unsubscribe
- **Spam score impact:** STRONG positive signal; its absence in bulk email is a negative signal

### Preference Center Link
```html
<a href="https://example.com/preferences?id=abc123" style="color: #999999; text-decoration: underline;">Manage email preferences</a>
```
- Links to a page where users control email frequency, categories, and channels
- Must be distinct from the unsubscribe link — they serve different purposes
- Should use the same secure token-based identification as unsubscribe
- **Not legally required** but strongly recommended for engagement and deliverability

---

## 9. Link Display Text vs `href` Validation (Phishing Detection)

### How Email Clients Detect Phishing Links
Email clients and spam filters compare the visible link text against the actual `href` destination to detect phishing.

### Mismatched Display Text — Phishing Triggers
```html
<!-- SEVERE phishing signal — display text is a URL that doesn't match href -->
<a href="https://evil-site.com/steal-credentials">https://bankofamerica.com</a>

<!-- SEVERE — display text shows one domain, href goes to another -->
<a href="https://totally-legit.xyz/login">Click here to log in at paypal.com</a>

<!-- MODERATE — display shows URL but href is a tracking redirect -->
<a href="https://clicks.esp.com/track/abc123">https://example.com/sale</a>
```

### What Triggers Phishing Detection
- **Display text contains a URL domain** that differs from the `href` domain — SEVERE; the most common phishing technique
- **Display text contains a well-known brand domain** (google.com, paypal.com, bankofamerica.com) but `href` goes elsewhere — SEVERE
- **Display text says "secure" or "verified"** but `href` goes to HTTP or unknown domain — MODERATE
- **Image `alt` text contains a domain** that doesn't match the wrapping `<a href>` domain — MODERATE
- **`title` attribute contains a domain** that doesn't match `href` — MODERATE

### Safe Patterns (Not Flagged)
- **Display text is descriptive action text** ("Shop now", "View order") with any legitimate `href` — SAFE
- **Display text is the sender's brand name** with `href` to sender's domain — SAFE
- **Display text is non-URL text** ("Click here", "Learn more") — not a phishing signal (may be a spam style signal, but not phishing)
- **`href` is an ESP tracking redirect** and display text is action text — SAFE; filters understand ESP tracking patterns
- **`href` contains UTM parameters** and display text is clean — SAFE

### Validation Rules for Link Text
- **Never put a URL in the visible link text** unless it exactly matches the `href` destination domain
- **Never display a well-known brand's domain** in link text if the `href` goes to a different domain
- **If showing a URL in link text, strip tracking parameters** from the display but keep them in the `href`
- **Use descriptive action text** instead of raw URLs wherever possible
- **If the link goes through an ESP tracking redirect**, use action text, not a display URL

---

## 10. Image Links — Linked Image Validation

### Standard Linked Image
```html
<a href="https://example.com/sale" style="text-decoration: none; border: 0;">
  <img src="https://example.com/images/sale-banner.jpg" alt="Winter Sale — 50% off all coats — Shop now" width="600" height="300" style="display: block; border: 0; outline: none; text-decoration: none; max-width: 100%; height: auto;">
</a>
```

### Linked Image Validation Rules
- **`alt` text on linked images must describe the link action/destination** — not just the image content; when images are off, the `alt` text IS the link
- **`border: 0`** on both the `<a>` and the `<img>` — prevents the default blue link border around images
- **`outline: none`** on the `<img>` — prevents focus outline from appearing as a border in some clients
- **`text-decoration: none`** on the `<a>` — prevents underline from appearing under the image
- **`display: block`** on the `<img>` — prevents phantom gap below the image that appears in some email clients
- **`<a>` should have inline `style`** — bare `<a>` wrapping an image may display with unwanted default link styling
- **Image `src` domain should relate to `href` domain** — images from one domain linking to a completely different domain is a slight phishing signal
- **Linked image without `alt` text** — the link has no accessible text; screen readers may announce the full image URL or nothing; also a spam signal

### Image Map Links
```html
<img src="hero.jpg" alt="Sale page" usemap="#salemap" width="600" height="300" style="display: block; border: 0;">
<map name="salemap">
  <area shape="rect" coords="0,0,300,300" href="https://example.com/womens" alt="Women's sale">
  <area shape="rect" coords="300,0,600,300" href="https://example.com/mens" alt="Men's sale">
</map>
```
- **Client support:** Apple Mail, iOS Mail, Outlook desktop, Thunderbird — YES; Gmail apps — NO
- **Each `<area>` must have `alt` text** — accessibility requirement and helps if image maps partially fail
- **Fallback:** always provide text links below the image map for clients that don't support them
- **`shape`** — `rect`, `circle`, `poly`, `default`
- **`coords`** — pixel coordinates defining the clickable area
- **`href`** — destination URL (same validation as regular links)
- **All `<area>` `href` values are subject to the same spam filter, phishing, and tracking validation as regular `<a href>`**

---

## 11. VML Link Validation (Outlook)

### VML `href` Attribute
```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="https://example.com/cta" style="height:44px;v-text-anchor:middle;width:200px;" arcsize="10%" fillcolor="#1a73e8" strokecolor="#1a73e8">
  <w:anchorlock/>
  <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;">Shop Now</center>
</v:roundrect>
<![endif]-->
```
- **`href` on VML elements** — makes the entire VML shape a clickable link in Outlook
- **Same URL validation rules apply** — HTTPS, valid domain, no suspicious patterns
- **The `href` on VML is separate from any `<a href>` in the non-MSO content** — ensure both point to the same destination
- **VML `href` is NOT tracked by ESP click tracking** — ESPs rewrite `<a href>` tags, not VML `href` attributes; you must manually update VML links to match the tracked URL, or your Outlook recipients' clicks won't be tracked
- **This is one of the most common email link validation errors** — the VML button href and the CSS button href go to different URLs because the ESP only rewrites the `<a>` tag

### VML Link Attributes
- `href="https://..."` — the link destination (on `<v:rect>`, `<v:roundrect>`, `<v:oval>`, `<v:shape>`)
- No `target` equivalent on VML — Outlook always opens links in the default browser
- No `title` equivalent on VML
- No `aria-label` on VML
- The link text is whatever is inside the VML `<center>` or `<v:textbox>` content

---

## 12. Outlook Safelinks / Link Preview Interaction

### How Safelinks Modifies Email DOM Links
When an email arrives in a Microsoft 365 / Exchange environment with Safelinks enabled:
1. Every `<a href>` in the email HTML is rewritten to a `safelinks.protection.outlook.com` URL
2. The original URL is encoded in the `url=` parameter
3. The visible link text is NOT changed — only the `href` attribute
4. On click, Safelinks checks the URL against Microsoft's threat database in real-time
5. If safe, the user is redirected to the original destination
6. If flagged, the user sees a warning page

### Safelinks Validation Concerns
- **Your carefully validated link text vs href match is now broken** — Safelinks changes the `href` to its own domain, so the display text and `href` no longer match (but Safelinks is exempt from the client's own phishing detection since it IS the security system)
- **Link hover shows Safelinks URL** — recipients see `safelinks.protection.outlook.com/...` on hover, not your URL; this may confuse less technical users
- **ESP tracking + Safelinks = triple redirect** — ESP tracking redirect → Safelinks redirect → final URL; test for latency and breakage
- **Fragment links may break** — `#section-id` fragments may be lost in the Safelinks rewrite
- **VML `href` is also rewritten** — Safelinks modifies VML links in the MSO conditional content
- **Pre-click scanning** — Safelinks may visit URLs before the user clicks; this can trigger single-use links and inflate click metrics
- **Time-limited links** (e.g., password reset, verification tokens) — Safelinks pre-scanning may consume the token before the user clicks; implement click verification on your landing page
- **Cannot opt out** — email senders cannot prevent Safelinks rewriting; it's controlled by the recipient's organization

---

## 13. Auto-Linking / Auto-Detection by Email Clients

Some email clients automatically convert plain text patterns into clickable links, even without `<a>` tags.

### iOS Mail Auto-Detection
- **Phone numbers** — auto-linked to `tel:` — prevented by `<meta name="format-detection" content="telephone=no">`
- **Email addresses** — auto-linked to `mailto:` — prevented by `content="email=no"`
- **Physical addresses** — auto-linked to Apple Maps — prevented by `content="address=no"`
- **Dates** — auto-linked to Calendar — prevented by `content="date=no"`
- **Tracking numbers** — auto-linked to package tracking (USPS, FedEx, UPS)
- **Flight numbers** — auto-linked to flight tracking
- **Full prevention:** `<meta name="format-detection" content="telephone=no, date=no, address=no, email=no">`

### Gmail Auto-Detection
- **URLs in plain text** — auto-linked (adding `<a href>` tags around detected URLs)
- **Email addresses in plain text** — auto-linked to `mailto:`
- **Tracking numbers** — auto-detected and linked in some contexts
- **No meta tag prevention** — Gmail's auto-detection cannot be turned off via meta tags
- **Workaround:** wrap content in `<a>` tags yourself to control the link destination and styling; if the text is already inside an `<a>`, Gmail won't auto-link it

### Outlook Auto-Detection
- **URLs** — auto-linked in plain text
- **Email addresses** — auto-linked
- **Outlook applies default blue color and underline** to auto-detected links — overridable with `span.MsoHyperlink { color: inherit !important; }` in the MSO `<style>` block

### Auto-Linking Validation Concerns
- **Auto-linked content gets default styling** — blue color, underline; may clash with your email design
- **Auto-linked phone numbers may have wrong formatting** — iOS may misinterpret date strings or order numbers as phone numbers
- **Auto-linked addresses may go to wrong location** — partial addresses may be misgeocoded
- **Auto-linking adds unexpected `<a>` tags to your DOM** — this changes the rendered DOM from what you designed
- **Prevention is the best validation** — use the `format-detection` meta tag and manually link any content you want linked

---

## 14. Link Validation in AMP Email

### AMP Email Link Rules
- **Standard `<a href>` links work in AMP emails** — same validation rules apply
- **AMP prohibits certain link types:**
  - `javascript:` — blocked
  - `data:` — blocked (except `data:image/` in `<amp-img>`)
  - Custom URI schemes — may be blocked depending on the AMP validator
- **`amp-form` action URLs** — form submissions in AMP go to `action-xhr` endpoints:
  ```html
  <form method="post" action-xhr="https://example.com/api/submit">
  ```
  - **`action-xhr`** — the XHR endpoint must be HTTPS
  - **CORS headers required** — the endpoint must return proper `AMP-Access-Control-Allow-Source-Origin` headers
  - **Must be on the sender's domain or an authorized origin** — AMP validates the form submission domain

### AMP Link Validation Tools
- **AMP Validator** — validates all links and URLs in AMP email HTML
- **Gmail AMP Playground** — test AMP email rendering and link behavior
- **AMP for Email spec** requires all resource URLs to be HTTPS

---

## 15. Link Rendering Differences Across Email Clients

### Default Link Styling by Client
- **Gmail (web):** blue (`#1a0dab` or `#1155cc`), underlined
- **Gmail (app):** blue, underlined
- **Outlook desktop:** blue (`#0563C1`), underlined; wraps in `span.MsoHyperlink` that can override your styles
- **Outlook.com:** blue, underlined; adds `MsoHyperlink` span
- **Apple Mail:** blue (`#0000ee`), underlined; respects inline styles most reliably
- **iOS Mail:** blue, underlined; respects inline styles
- **Yahoo Mail:** blue, underlined
- **Thunderbird:** blue, underlined; respects inline styles

### Link Style Override Challenges
- **Outlook `span.MsoHyperlink`** — Outlook wraps links in `<span class="MsoHyperlink">` and applies its own color; override with:
  ```css
  <!--[if mso]>
  <style>
    span.MsoHyperlink { color: inherit !important; mso-style-priority: 99 !important; }
    span.MsoHyperlinkFollowed { color: inherit !important; mso-style-priority: 99 !important; }
  </style>
  <![endif]-->
  ```
- **Gmail class prefixing** — Gmail renames CSS classes with unique prefixes; inline styles on `<a>` tags are the only reliable way to style links in Gmail
- **Yahoo Mail** — may strip or override link colors in some contexts
- **Dark mode link colors** — all clients may modify link colors in dark mode; provide dark mode overrides via `@media (prefers-color-scheme: dark)` and `[data-ogsc]`

### Visited Link Styling
- **Most email clients do NOT apply `:visited` styles** — visited/unvisited distinction is unreliable in email
- Some webmail clients (Gmail web, Yahoo web) may apply `:visited` styling in the browser
- **Do not rely on visited link color to convey information** — design links to look the same visited or not

### Link Underline Control
- **`text-decoration: underline`** — inline on `<a>` for body links
- **`text-decoration: none`** — inline on `<a>` for buttons and navigation links
- **Outlook may add underlines regardless** — use the `MsoHyperlink` override above
- **Gmail may add underlines** — inline `text-decoration: none` generally works
- **Some clients render underlines differently** — some use `text-decoration`, others use `border-bottom`; for precise underline control, some developers use `border-bottom: 1px solid #color` instead of `text-decoration: underline`

---

## 16. Link Testing & Validation Checklist

### Pre-Send Link Validation
- Every `<a href>` has a valid, absolute URL
- All links use HTTPS (no HTTP unless absolutely necessary)
- All links resolve (no 404s, no dead domains)
- No `javascript:` or `data:` URIs in any `href`
- No URL shorteners (bit.ly, t.co, etc.) — use full URLs
- No IP address URLs — use domain names
- No links to domains on blocklists (check SURBL, URIBL, Spamhaus DBL)
- Display text does not contain a URL domain that differs from the `href` domain
- All linked images have descriptive `alt` text (link action, not image description)
- Redundant image + text links are wrapped in a single `<a>` tag
- VML `href` matches the corresponding CSS/HTML `<a href>` (including ESP tracking URLs)
- `mailto:` links have valid email addresses and properly encoded parameters
- `tel:` links use E.164 format with country code
- Calendar links use the correct date format for each service (Google vs Outlook vs Yahoo)
- Unsubscribe link is present, visible, functional, and meets CAN-SPAM/GDPR requirements
- `List-Unsubscribe` and `List-Unsubscribe-Post` headers are present for bulk email
- `<meta name="format-detection" content="telephone=no, date=no, address=no, email=no">` is present to prevent unwanted auto-linking
- Fragment links (`#section-id`) are tested in target email clients
- Deep links / universal links are tested on both iOS and Android
- Links survive ESP click tracking rewrite (test actual delivered email, not source code)
- Links survive Safelinks / Proofpoint / Barracuda rewriting (test in enterprise inboxes)
- Link hover preview shows expected URL (or acceptable ESP tracking URL)
- Single-use links (password reset, verification) have landing page verification to handle pre-click scanning
- All links are keyboard accessible (Tab key reaches them)
- Link focus indicators are visible
- Link touch targets are minimum 44x44px on mobile
- Link color contrast meets 4.5:1 against background
- Link text is descriptive (no "click here" without `aria-label` fallback)

### Link Analytics Validation
- ESP click tracking is working (clicks are logged)
- UTM parameters are present on all marketing links
- UTM parameters are not doubled or conflicting
- Click tracking redirect chain resolves to the correct final URL
- No redirect loops
- Redirect latency is acceptable (under 2 seconds total)
- Bot/pre-click detection is enabled in ESP to filter phantom clicks from Safelinks/ATP

---

*Total email link validation elements, attributes, protocols, patterns, and rules: 400+*
