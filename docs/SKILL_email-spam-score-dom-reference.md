# HTML Email Spam Score — Complete DOM Element Reference

Every HTML tag, attribute, inline style, structural pattern, and content signal in the email DOM that spam filters analyze when calculating spam score. Covers SpamAssassin, Gmail, Microsoft (Outlook/Hotmail/Exchange), Yahoo, and commercial spam filter engines.

---

## 1. How Spam Filters Parse Email HTML DOM

Spam filters don't just scan text — they parse the full HTML DOM tree and analyze structural patterns, tag usage, attribute values, CSS properties, image-to-text ratios, and link behavior. The HTML structure of your email is scored alongside authentication headers, sender reputation, and engagement metrics.

### What Spam Filters Analyze in the DOM
- Tag-to-text ratio (how much HTML markup vs actual readable text)
- Image-to-text ratio (how much of the email is images vs live text)
- Link density (number of links relative to content length)
- HTML complexity (nesting depth, table count, tag count)
- Specific tag presence/absence (e.g., `<form>`, `<script>`, `<iframe>`)
- Inline style patterns (hidden text, tiny fonts, color-matching-background)
- URL patterns in `href` attributes (redirects, shortened URLs, suspicious domains)
- HTML validity and well-formedness
- Character encoding declarations
- Content structure (presence of headers, body, proper nesting)
- Hidden content techniques (display: none, visibility: hidden, font-size: 0)
- Accessibility attributes (their presence or absence can signal legitimacy)

---

## 2. Document Structure Tags — Spam Score Impact

### `<!DOCTYPE>` Declaration
- **Present:** Slight positive signal — indicates a properly crafted email from a legitimate sender
- **Missing:** Minor negative signal — many spam templates omit DOCTYPE
- **Wrong/malformed DOCTYPE:** Negative signal — indicates sloppy or auto-generated spam HTML
- **Recommended:** `<!DOCTYPE html>` or XHTML 1.0 Transitional

### `<html>` Tag
- **Present with `lang` attribute:** Positive signal — legitimate senders declare language
- **Missing `lang`:** Neutral to slightly negative — not a strong signal alone
- **Multiple `<html>` tags:** Negative signal — malformed HTML, common in spam
- **Excessive namespace declarations:** Neutral — legitimate for Outlook VML emails, but unusual volume may be flagged

### `<head>` Section
- **Present and well-formed:** Positive signal — structured email from legitimate sender
- **Missing entirely:** Negative signal — many spam emails are body-only HTML fragments
- **Empty `<head>`:** Slight negative — indicates minimal effort or auto-generation
- **Excessive content in `<head>`:** Neutral — legitimate for email with embedded styles, dark mode meta, etc.

### `<meta charset="UTF-8">`
- **Present:** Positive signal — proper character encoding declaration
- **Missing:** Slight negative — may indicate auto-generated or legacy spam
- **Conflicting charset declarations:** Negative — multiple or contradictory charset declarations suggest obfuscation
- **Unusual charset (e.g., charset="windows-1251"):** May flag for further scrutiny in non-Cyrillic-context emails

### `<meta name="viewport">`
- **Present:** Positive signal — indicates mobile-optimized email from professional sender
- **Missing:** Neutral — many legitimate emails still don't include this

### `<title>` Tag
- **Present with descriptive text:** Positive signal — professionalism indicator
- **Empty `<title></title>`:** Neutral to slightly negative
- **Missing:** Neutral — common in both legitimate and spam emails
- **`<title>` containing spam keywords:** Negative — filters scan title text for spam phrases

### `<body>` Tag
- **Present with inline styles:** Normal — expected in email
- **Missing:** Negative signal — bare HTML fragments without `<body>` are common in spam
- **`<body>` with `onload` or event handlers:** Strong negative — JavaScript event handlers are a phishing/spam signal
- **Multiple `<body>` tags:** Negative — malformed HTML

---

## 3. Forbidden/High-Risk Tags — Strong Spam Signals

These tags, when present in email HTML, trigger strong negative spam scoring or outright rejection by most spam filters.

### `<script>` — JavaScript
- **Spam impact:** SEVERE negative — almost guaranteed spam/phishing flag
- **Why:** Email should never contain JavaScript; its presence indicates malicious intent
- **Behavior:** Most email clients strip `<script>` tags, but spam filters flag the email before the client even renders it
- **Includes:** `<script>`, `<script src="...">`, `<script type="...">`, inline `<script>` blocks
- **Also flagged:** `javascript:` protocol in `href` attributes (e.g., `<a href="javascript:...">`)

### `<iframe>` — Inline Frame
- **Spam impact:** SEVERE negative — strong phishing/spam indicator
- **Why:** Iframes can load external malicious content; no legitimate email uses iframes
- **Includes:** `<iframe>`, `<iframe src="...">`, `<iframe srcdoc="...">`

### `<object>` — Embedded Object
- **Spam impact:** SEVERE negative — used to embed Flash, Java, or other executable content
- **Includes:** `<object>`, `<object data="...">`, `<object type="...">`

### `<embed>` — Embedded Content
- **Spam impact:** SEVERE negative — similar to `<object>`; embeds executable or media content
- **Includes:** `<embed>`, `<embed src="...">`

### `<applet>` — Java Applet
- **Spam impact:** SEVERE negative — deprecated tag for Java applets; strong malware signal

### `<form>` — HTML Form
- **Spam impact:** HIGH negative — forms in email are a phishing indicator
- **Why:** Phishing emails use forms to capture credentials directly in the email
- **Includes:** `<form>`, `<form action="...">`, `<form method="...">`
- **Related tags also flagged:** `<input>`, `<select>`, `<textarea>`, `<button type="submit">` when inside a `<form>`
- **Exception:** AMP emails have their own form handling (`amp-form`) which is separate from HTML `<form>` and handled differently by Gmail's spam engine
- **Note:** `<input>` and `<label>` used for CSS-only interactivity (checkbox hack) without a `<form>` wrapper are generally not flagged as heavily, but some filters may still flag any `<input>` presence

### `<meta http-equiv="refresh">` — Auto-Redirect
- **Spam impact:** SEVERE negative — auto-redirecting the email page is a phishing technique
- **Includes:** `<meta http-equiv="refresh" content="0; url=...">`

### `<base>` — Base URL
- **Spam impact:** HIGH negative — changes the base URL for all relative links; used in phishing to disguise link destinations
- **Includes:** `<base href="...">`

### `<link>` — External Stylesheet
- **Spam impact:** MODERATE negative — loading external resources is suspicious
- **Why:** External stylesheets can be used for tracking, or changed after delivery to alter email appearance
- **Includes:** `<link rel="stylesheet" href="...">`
- **Also:** `<link rel="import">`, `<link rel="preload">`

### `<style>` with `@import`
- **Spam impact:** MODERATE negative — `@import url(...)` loads external CSS; same concern as `<link>`
- **The `<style>` block itself is fine** — embedded styles are expected in email; it's the `@import` within it that's flagged

### `<marquee>` — Scrolling Text
- **Spam impact:** MODERATE negative — scrolling text is a classic spam visual technique
- **Outdated and suspicious in modern email context**

### `<blink>` — Blinking Text
- **Spam impact:** MODERATE negative — deprecated; associated with spam aesthetics

### `<bgsound>` — Background Sound
- **Spam impact:** HIGH negative — auto-playing audio is spam behavior

### `<video autoplay>` and `<audio autoplay>`
- **Spam impact:** MODERATE negative — auto-playing media is suspicious
- **Without `autoplay`:** Lower impact — `<video>` in email is unusual but Apple Mail supports it

---

## 4. Link Tags (`<a href>`) — Spam Score Signals

Links are one of the most heavily analyzed elements in email spam scoring. Every `href` attribute is parsed and evaluated.

### Link URL Patterns — Negative Signals
- **URL shorteners** (`bit.ly`, `t.co`, `goo.gl`, `tinyurl.com`, `ow.ly`, etc.) — MODERATE to HIGH negative; hides the true destination; heavily associated with spam and phishing
- **IP address URLs** (`http://192.168.1.1/...`) — HIGH negative; legitimate websites use domain names, not raw IPs
- **Numeric/hex-encoded URLs** (`http://%68%65%6C%6C%6F.com`) — SEVERE negative; URL obfuscation is a phishing technique
- **Mismatched display text and href** (display says "bankofamerica.com" but href goes to "evil-site.com") — SEVERE negative; the #1 phishing signal
- **`href` containing `@` symbol** (`http://legit-domain.com@evil-site.com`) — SEVERE negative; URL authority confusion attack
- **Excessively long URLs** (200+ characters) — MODERATE negative; unusual and potentially obfuscated
- **Multiple redirects in URL** (`http://redirect1.com/redirect2.com/redirect3.com/...`) — MODERATE negative
- **URLs with suspicious TLDs** (`.xyz`, `.top`, `.click`, `.link`, `.club`, `.buzz`, `.gq`, `.tk`, `.ml`, `.ga`, `.cf`) — MODERATE negative; these TLDs are disproportionately used in spam
- **URLs with suspicious path patterns** (`/wp-admin/`, `/phishing/`, `/login/`, `/verify/`, `/account/update/`) — MODERATE negative
- **URLs with unusual ports** (`http://example.com:8080/...`) — MODERATE negative
- **`data:` URIs in `href`** (`<a href="data:text/html,...">`) — SEVERE negative; can execute code
- **`javascript:` protocol in `href`** — SEVERE negative (covered above but also applies to links)
- **Mixed HTTP and HTTPS links** (some links HTTP, others HTTPS in the same email) — SLIGHT negative; inconsistency suggests carelessness or manipulation

### Link URL Patterns — Positive Signals
- **HTTPS links** — Slight positive; indicates modern, secure destinations
- **Consistent sender domain** (links match the `From` domain) — Positive; indicates legitimacy
- **Known ESP tracking domain** (e.g., Mailchimp, SendGrid, HubSpot tracking URLs) — Neutral to positive; recognized infrastructure
- **Unsubscribe link with clear destination** — Positive; required by law; its presence signals compliance
- **mailto: links** — Neutral to positive; common in legitimate business emails

### Link Density — Scoring Rules
- **Too many links relative to text** — Negative; spam often has excessive links
- **SpamAssassin rule:** More than ~10–15 links in a short email may trigger scoring
- **All-link email** (just images with links, no real text) — HIGH negative
- **Single link emails** — Neutral (common in notifications) to slight negative (if combined with other signals)
- **Links in alt text** — Not directly a link issue, but alt text containing URLs is unusual and may be flagged
- **Multiple links to the same domain** — Neutral (normal for internal links) vs. **multiple links to different suspicious domains** — Negative

### Link Tracking and UTM Parameters
- **ESP click tracking redirects** (links rewritten through `clicks.example-esp.com`) — Neutral when from known ESPs; negative when from unknown redirect domains
- **UTM parameters** (`utm_source`, `utm_medium`, etc.) — Neutral to slightly positive; indicates professional marketing practices
- **Excessive URL parameters** (very long query strings) — SLIGHT negative; looks like tracking overload or obfuscation

### Unsubscribe Link Presence
- **Present and functional:** POSITIVE signal — compliance with CAN-SPAM, GDPR; indicates legitimate bulk sender
- **Missing:** NEGATIVE signal — spam filters specifically check for unsubscribe mechanism in bulk/marketing emails
- **Disguised or hard-to-find:** May not be flagged by automated filters but hurts sender reputation when users mark as spam instead of unsubscribing
- **`List-Unsubscribe` header + HTML unsubscribe link:** STRONG positive — double unsubscribe mechanism signals maximum legitimacy

---

## 5. Image Tags (`<img>`) — Spam Score Signals

### Image-to-Text Ratio
- **All-image email** (one giant image, no text) — HIGH negative; classic spam technique to avoid text-based content filters
- **Mostly-image email** (>60% image, <40% text) — MODERATE negative
- **Balanced email** (40–60% images, 40–60% text) — Neutral to positive
- **Text-heavy email** (<20% images) — Positive; easy for filters to scan content
- **SpamAssassin rule:** `HTML_IMAGE_RATIO_02` — email is 0–20% text (high image ratio triggers this)
- **SpamAssassin rule:** `HTML_IMAGE_RATIO_04` — email is 20–40% text
- **SpamAssassin rule:** `HTML_IMAGE_RATIO_06` — email is 40–60% text
- **SpamAssassin rule:** `HTML_IMAGE_RATIO_08` — email is 60–80% text
- **Recommended:** At least 60% text content, 40% or less images

### Image Tag Attributes
- **`<img>` without `alt` attribute:** SLIGHT negative — indicates careless/auto-generated email; spam often omits alt text
- **`<img>` with empty `alt=""`:** Neutral — acceptable for decorative images
- **`<img>` with keyword-stuffed `alt` text:** Negative — `alt="BUY NOW CHEAP DISCOUNT SALE"` is a spam signal
- **`<img>` without `width` and `height`:** SLIGHT negative — unprofessional; legitimate senders set dimensions
- **`<img>` with `width="0"` or `height="0"`:** MODERATE negative — hidden image; used for tracking but excessive zero-sized images are suspicious
- **`<img>` with `width="1"` and `height="1"`:** Neutral to slight negative — recognized as tracking pixel; one is normal, many are suspicious
- **Multiple tracking pixels** (several 1x1 images from different domains) — MODERATE negative; indicates multiple third-party trackers
- **`<img>` with `display: none`:** MODERATE negative — hidden image; why include an invisible image? Signals deception
- **`<img>` with `visibility: hidden`:** Same as above
- **`<img src="">` (empty source):** Negative — malformed; indicates auto-generated or broken HTML

### Image Source URLs
- **Images hosted on sender's domain:** Positive — consistent infrastructure
- **Images hosted on known CDN** (Cloudflare, AWS S3, Cloudinary, ESP image hosting) — Neutral to positive
- **Images hosted on free hosting** (Imgur, Photobucket, free web hosts) — MODERATE negative; legitimate brands host their own images
- **Images from suspicious or unknown domains:** MODERATE negative
- **Images with IP address URLs:** HIGH negative — same as link URL issue
- **Images with excessively long filenames:** SLIGHT negative — may indicate auto-generated content
- **Base64-encoded inline images** (`src="data:image/..."`) — MODERATE negative for large images; small base64 images (icons) are less suspicious but still unusual in email
- **Broken image URLs** (404/dead images) — SLIGHT negative — indicates abandoned or poorly maintained campaign
- **Mismatched image domains** (images from many different unrelated domains) — SLIGHT negative

### Image Content Analysis (Advanced Filters)
- Some advanced spam filters (Gmail, Microsoft) use image recognition/OCR to scan text within images
- **Text-as-image** (critical content baked into images to avoid text scanning) — negative when detected; defeats the purpose of text-based filtering
- **Known spam image patterns** (pill images, adult content, fake logos) — SEVERE negative when recognized by image classifiers
- **QR codes in images** — MODERATE negative in recent years; QR code phishing ("quishing") has increased filter scrutiny

---

## 6. Text Formatting Tags — Spam Score Signals

### Font Tags and Attributes
- **`<font>` tag:** SLIGHT negative — deprecated tag; indicates outdated or auto-generated HTML; modern email uses inline CSS on `<span>`, `<td>`, `<p>`
- **`<font color="..." face="..." size="...">`:** Deprecated attributes; same signal as above
- **Excessive font changes** (many different fonts, sizes, colors in a short email) — MODERATE negative; looks like spam trying to evade pattern matching
- **Very small font sizes** (`font-size: 1px`, `font-size: 0`, `font-size: 2px`) — HIGH negative; hidden text technique
- **`font-size: 0`:** SEVERE negative — text exists in the DOM but is invisible; classic spam obfuscation
- **Very large font sizes** (`font-size: 72px+` for non-heading text) — MODERATE negative; aggressive/shouting appearance associated with spam
- **Text color matching background color** (white text on white background, or `color` matching `background-color`) — SEVERE negative; hidden text is one of the strongest spam signals
- **Near-matching colors** (`color: #fefefe` on `background-color: #ffffff`) — HIGH negative; spam filters calculate color difference and flag near-invisible text
- **`color: transparent`:** HIGH negative — invisible text

### Text Content Tags
- **`<b>`, `<strong>`, `<i>`, `<em>`:** Normal — expected in email; no spam signal
- **Excessive bold/all-caps** (entire email in bold or uppercase) — SLIGHT negative; aggressive tone associated with spam
- **`<u>` (underline) on non-links:** SLIGHT negative — can mislead users into thinking underlined text is a link (deceptive pattern)
- **`<s>`, `<strike>`, `<del>` (strikethrough):** Neutral — commonly used for sale pricing; no spam signal
- **`<sup>`, `<sub>`:** Neutral — used in legitimate content (trademarks, footnotes)
- **`<pre>`, `<code>`:** Neutral in tech emails; unusual in marketing email context
- **`<blockquote>`:** Neutral — used in legitimate reply/quote formatting

### Heading Tags
- **Proper heading hierarchy** (`<h1>` through `<h6>`): Positive — indicates structured, professional content
- **Multiple `<h1>` tags:** SLIGHT negative — improper structure
- **Heading tags with spam keywords** (`<h1>FREE VIAGRA CLICK NOW</h1>`): Negative — but the keywords are the issue, not the tag
- **Headings styled as hidden** (`<h1 style="display: none">`): HIGH negative — hidden heading text

---

## 7. Table Tags — Spam Score Signals

### Table Structure
- **Clean, well-nested tables:** Positive — indicates professionally built email template
- **Deeply nested tables** (10+ levels) — SLIGHT negative — excessive complexity can indicate auto-generated or obfuscated HTML
- **Malformed table nesting** (unclosed tags, `<td>` outside `<tr>`, etc.) — SLIGHT negative — indicates sloppy generation
- **Missing `cellpadding`, `cellspacing`, `border` attributes:** Neutral — not a spam signal, but indicates less professional template
- **`role="presentation"` on tables:** Neutral to slight positive — indicates accessibility awareness; professional sender signal
- **Empty tables** (tables with no content) — SLIGHT negative — may be used for spacing tricks or to pad HTML complexity

### Table-Based Hidden Content
- **`<td>` with `display: none`:** MODERATE negative if it contains text content (hidden text)
- **`<td>` with `font-size: 0` and content:** HIGH negative — hiding text in table cells
- **`<td>` with matching `color` and `bgcolor`:** HIGH negative — invisible text in table cell
- **`<tr>` with `height: 0` and `overflow: hidden` containing text:** MODERATE negative — hidden row
- **`<td>` with `width: 0` containing text:** MODERATE negative — zero-width cell with content

---

## 8. Inline CSS Styles — Spam Score Signals

Spam filters parse inline `style` attributes on every element and analyze specific CSS properties.

### Hidden Content CSS — Strong Negative Signals
- `display: none` on text-containing elements — HIGH negative
- `visibility: hidden` on text-containing elements — HIGH negative
- `opacity: 0` on text-containing elements — HIGH negative
- `font-size: 0` / `font-size: 0px` — SEVERE negative
- `font-size: 1px` — HIGH negative (near-invisible)
- `line-height: 0` on text — HIGH negative (collapses text to invisible)
- `max-height: 0; overflow: hidden` on text — MODERATE negative (hidden preheader uses this legitimately, but excessive use is suspicious)
- `color: #ffffff` on `background-color: #ffffff` (or any matching pair) — SEVERE negative
- `color: transparent` — HIGH negative
- `text-indent: -9999px` — HIGH negative — pushes text off-screen (a web SEO spam technique that email filters also detect)
- `position: absolute; left: -9999px` — HIGH negative — positions text off-screen
- `clip: rect(0,0,0,0)` on text — MODERATE negative (legitimately used for screen-reader-only text, but filters may flag it)
- `height: 0; width: 0; overflow: hidden` on text-containing elements — HIGH negative
- `z-index: -1` on text behind other content — MODERATE negative

### Legitimate Hidden Content vs Spam
Spam filters attempt to distinguish legitimate hidden content from spam obfuscation:

- **Hidden preheader text** (`max-height: 0; overflow: hidden; mso-hide: all`) — LEGITIMATE; single instance expected at the top of the email; filters generally recognize this pattern
- **Mobile-only / desktop-only show/hide** (`display: none` in media queries) — LEGITIMATE; responsive email technique
- **Spacer cells with `font-size: 1px; line-height: 1px`** — LEGITIMATE; standard email spacing technique
- **`&nbsp;` in spacer cells** — LEGITIMATE; prevents cell collapse
- **Image-off alt text** — LEGITIMATE; styled alt text is a standard email technique

**The difference:** Legitimate hidden content is structural (spacing, responsive show/hide, preheader), while spam hidden content is textual (keyword stuffing, invisible sales copy, hidden links). Filters analyze what content is hidden, not just that something is hidden.

### Layout CSS — Neutral to Positive
- `padding`, `margin` — Normal email layout
- `border`, `border-collapse` — Normal table styling
- `text-align`, `vertical-align` — Normal alignment
- `background-color` with visible content — Normal
- `font-family`, `font-size`, `line-height` (reasonable values) — Normal
- `width`, `max-width`, `height` — Normal layout control

### Suspicious CSS Properties
- `position: absolute` / `relative` / `fixed` — MODERATE negative in email context; no legitimate reason for positioned elements in email (doesn't even work in most clients)
- `float` — SLIGHT negative in email; unreliable in email rendering; legitimate senders don't use float
- `overflow: auto` / `scroll` — MODERATE negative; scrollable regions in email are unusual and suspicious
- `cursor: pointer` on non-link elements — SLIGHT negative; trying to make non-links look clickable
- `user-select: none` — SLIGHT negative; preventing text selection is suspicious

---

## 9. Content Encoding & Character Tags — Spam Score Signals

### Character Encoding Issues
- **Mixed character encodings** (some content in UTF-8, some in ISO-8859-1) — MODERATE negative; indicates cobbled-together content
- **Missing charset declaration** — SLIGHT negative
- **Unicode obfuscation** (using lookalike Unicode characters to replace Latin letters: "Ⅴіаgrа" instead of "Viagra") — SEVERE negative; one of the most common text obfuscation techniques
- **Zero-width characters in text** (`&zwnj;`, `&zwj;`, `&#8203;` scattered through words) — HIGH negative when inserted within words to break up spam keywords (e.g., "V&#8203;i&#8203;a&#8203;g&#8203;r&#8203;a"); legitimate when used for spacing/direction control
- **HTML entities used to spell spam words** (`&#86;&#105;&#97;&#103;&#114;&#97;` = "Viagra") — SEVERE negative; entity encoding to evade text filters
- **Excessive HTML entities** (encoding normal characters that don't need encoding) — MODERATE negative; suggests obfuscation attempt
- **Base64-encoded text blocks** in the HTML body — HIGH negative; obfuscation technique

### Invisible Unicode Characters
- `U+200B` (zero-width space) — Legitimate in small quantities (preheader, spacing); suspicious when scattered through content text
- `U+200C` (zero-width non-joiner `&zwnj;`) — Legitimate in preheader padding; suspicious within words
- `U+200D` (zero-width joiner `&zwj;`) — Legitimate in emoji sequences; suspicious within text content
- `U+FEFF` (byte order mark) — Legitimate at document start; suspicious elsewhere
- `U+00AD` (soft hyphen) — Legitimate for word breaking; suspicious when used to split spam keywords
- `U+2060` (word joiner) — Rarely legitimate in email; suspicious
- `U+034F` (combining grapheme joiner) — Very suspicious; almost never legitimate in email

---

## 10. MIME Structure Tags — Spam Score Signals

These aren't HTML tags but are part of the email's MIME structure that spam filters analyze alongside the HTML DOM.

### `text/plain` MIME Part
- **Present:** POSITIVE signal — legitimate senders include a plain text alternative
- **Missing:** MODERATE negative — HTML-only emails are a spam indicator; SpamAssassin rule `MIME_HTML_ONLY` specifically flags this
- **Plain text matches HTML content:** Positive — content consistency indicates legitimacy
- **Plain text wildly different from HTML:** MODERATE negative — mismatched MIME parts suggest deception (showing one thing in text, another in HTML)
- **Empty plain text part:** MODERATE negative — worse than no plain text at all; indicates minimal effort to appear legitimate

### Content-Type Headers
- **`Content-Type: text/html; charset=UTF-8`:** Normal — expected
- **`Content-Type: multipart/alternative`:** Positive — indicates both text and HTML versions
- **`Content-Type: multipart/mixed`:** Neutral — indicates attachments (evaluated separately)
- **`Content-Type: multipart/related`:** Neutral — indicates inline images
- **Missing Content-Type:** Negative — malformed email

### `text/x-amp-html` MIME Part
- **Present alongside `text/html`:** Neutral — AMP email; recognized by Gmail, Yahoo
- **Present without `text/html` fallback:** SLIGHT negative — every AMP email should have an HTML fallback

---

## 11. HTML Validity & Well-Formedness — Spam Score Signals

### Malformed HTML
- **Unclosed tags** (`<td>` without `</td>`, `<p>` without `</p>`) — SLIGHT negative per instance; cumulative effect increases
- **Improperly nested tags** (`<b><i></b></i>`) — SLIGHT negative
- **Duplicate `<html>`, `<head>`, `<body>` tags:** Negative — indicates concatenated or injected content
- **Missing closing tags throughout:** MODERATE negative — indicates auto-generated or sloppy HTML
- **Tag soup** (completely unstructured HTML) — MODERATE to HIGH negative
- **SpamAssassin rule:** `HTML_TAG_BALANCE_BODY` — mismatched opening/closing tags in body
- **SpamAssassin rule:** `HTML_TAG_BALANCE_HEAD` — mismatched tags in head

### Excessive HTML
- **Very large HTML** (100KB+ for a simple email) — SLIGHT negative; bloated HTML may indicate obfuscated content or hidden text
- **Extremely small HTML** (<200 bytes) — SLIGHT negative; too short to be a legitimate email
- **SpamAssassin rule:** `HTML_SHORT_LINK_IMG_1` — very short HTML with image and link (classic spam pattern)

### HTML Comments
- **Normal HTML comments** (`<!-- section header -->`) — Neutral; common in templates
- **Excessive comments** (large blocks of commented-out text) — SLIGHT negative; may be padding to change email hash/fingerprint
- **MSO conditional comments** (`<!--[if mso]>`) — Neutral; recognized as legitimate Outlook targeting
- **Comments containing spam keywords** — MODERATE negative; some spammers hide keywords in comments thinking filters don't scan them (they do)
- **Random character strings in comments** — MODERATE negative; hash-busting technique to make each email unique

---

## 12. `<style>` Block Content — Spam Score Signals

### Embedded CSS
- **Normal embedded `<style>` block with email CSS:** Positive — professional email
- **`@import url(...)` in `<style>`:** MODERATE negative — loading external resources
- **`@media` queries:** Neutral to positive — responsive email technique
- **`@font-face`:** Neutral — web font loading; used in legitimate email
- **Excessive `!important` declarations:** Neutral in email (required for dark mode overrides, media query overrides)

### CSS Content Property
- **`content: "..."` in CSS `::before` / `::after`:** MODERATE negative — injecting text via CSS to evade text-based content scanning
- **Not commonly supported in email clients anyway**, but filters still flag it

### CSS Expressions (Legacy IE)
- **`expression(...)` in CSS:** SEVERE negative — CSS expression execution; phishing/malware vector
- **`behavior: url(...)` in CSS:** SEVERE negative — legacy IE behavior binding; malware vector
- **`-moz-binding: url(...)`:** SEVERE negative — Firefox XBL binding; malware vector

---

## 13. Specific SpamAssassin HTML Rules

SpamAssassin has specific rules that score HTML DOM patterns. Here are the ones directly related to HTML structure.

### Image/Text Ratio Rules
- `HTML_IMAGE_RATIO_02` — 0–20% text (mostly images) — Negative score
- `HTML_IMAGE_RATIO_04` — 20–40% text — Slight negative
- `HTML_IMAGE_RATIO_06` — 40–60% text — Neutral
- `HTML_IMAGE_RATIO_08` — 60–80% text — Neutral to positive
- `HTML_IMAGE_ONLY_04` — email has 0–400 bytes of text with images — Negative
- `HTML_IMAGE_ONLY_08` — email has 400–800 bytes of text with images — Negative
- `HTML_IMAGE_ONLY_12` — email has 800–1200 bytes of text with images — Slight negative
- `HTML_IMAGE_ONLY_16` — email has 1200–1600 bytes of text with images — Slight negative
- `HTML_IMAGE_ONLY_20` — email has 1600–2000 bytes of text with images — Neutral

### HTML Structure Rules
- `MIME_HTML_ONLY` — email has HTML part but no text/plain part — Negative
- `HTML_MISSING_CTYPE` — missing Content-Type meta/header — Negative
- `HTML_TAG_BALANCE_BODY` — unbalanced tags in body — Negative
- `HTML_TAG_BALANCE_HEAD` — unbalanced tags in head — Negative
- `HTML_TAG_EXIST_BGSOUND` — `<bgsound>` tag exists — Negative
- `HTML_FONT_SIZE_TINY` — very small font size detected — Negative
- `HTML_FONT_SIZE_LARGE` — excessively large font size — Slight negative
- `HTML_FONT_LOW_CONTRAST` — text color too close to background color — Negative
- `HTML_FONT_FACE_BAD` — suspicious font-face declaration — Slight negative
- `HTML_SHORT_LINK_IMG_1` — short HTML with image and link — Negative
- `HTML_SHORT_LINK_IMG_2` — very short HTML with image and link — More negative
- `HTML_SHORT_LINK_IMG_3` — extremely short HTML, just image and link — Strong negative
- `HTML_EMBEDS` — embedded objects (`<embed>`, `<object>`) present — Negative
- `HTML_EXTRA_CLOSE` — extra closing tags — Slight negative
- `HTML_BADTAG_40_50` / `HTML_BADTAG_50_60` / `HTML_BADTAG_60_70` etc. — percentage of bad/unknown HTML tags — Progressive negative scoring
- `HTML_OBFUSCATE_05_10` / `HTML_OBFUSCATE_10_20` etc. — percentage of HTML that appears to be obfuscated — Progressive negative scoring
- `HTML_COMMENT_8BITS` — 8-bit characters in HTML comments — Slight negative (hash-busting detection)
- `HTML_COMMENT_SAVED_URL` — URL saved in HTML comment — Slight negative

### Link-Related SpamAssassin Rules
- `HTML_LINK_CLICK_HERE` — link text is "click here" — Slight negative (spam cliché)
- `URI_HEX` — URI contains hex-encoded characters — Negative
- `URI_NOVOWEL` — URI with no vowels (randomized domain) — Negative
- `URI_ONLY_MSGID_IN_BODY` — body contains only a message ID-style URI — Negative
- `URIBL_*` rules — URI appears on real-time block lists (SURBL, URIBL, DBL) — SEVERE negative
- `RCVD_IN_MSPIKE_*` — sender IP in Cloudmark reputation lists — Variable

---

## 14. Authentication-Adjacent DOM Signals

While authentication (SPF, DKIM, DMARC) is not part of the HTML DOM, certain HTML patterns interact with authentication checks.

### `List-Unsubscribe` Header Presence (Signaled in DOM)
- **HTML unsubscribe link present AND `List-Unsubscribe` header present:** STRONG positive — double compliance signal
- **HTML unsubscribe link only:** Moderate positive
- **Neither present in bulk email:** STRONG negative
- **RFC 8058 one-click unsubscribe (`List-Unsubscribe-Post`):** Additional positive — required by Gmail and Yahoo for bulk senders since Feb 2024; its absence in bulk email is increasingly penalized

### BIMI (Brand Indicators)
- **Proper BIMI implementation (SVG logo, VMC certificate, DMARC pass):** Positive — brand verification signals legitimacy
- **Not a DOM element**, but the presence of brand-consistent visual elements (logo, colors) in the HTML that match the BIMI logo reinforces authenticity signals

### `From` Domain Consistency with Link Domains
- **Links in email HTML match the `From` header domain:** Positive — consistent infrastructure
- **Links in email HTML all go to different domains from `From`:** MODERATE negative — looks like spoofed sender
- **Tracking link domains that resolve to the sender's ESP:** Neutral — recognized pattern

---

## 15. Email Size & Complexity — DOM-Level Signals

### HTML Size
- **Under 15KB HTML:** Slight positive — clean, efficient email
- **15–100KB HTML:** Normal range — typical marketing email
- **100–150KB HTML:** Slight negative — bloated; approaching Gmail clipping threshold
- **Over 102KB total email size:** Gmail clips the email (adds "View entire message" link) — not a direct spam signal but reduces engagement which indirectly hurts deliverability
- **Over 150KB HTML:** MODERATE negative — unusually large; may contain hidden content or excessive code
- **Over 500KB HTML:** HIGH negative — extreme bloat; strong indicator of hidden content or poor generation

### Tag Count
- **Reasonable tag count** (50–500 tags) — Normal email range
- **Excessive tag count** (1000+ tags in a short email) — MODERATE negative — indicates hidden content, excessive nesting, or obfuscation
- **Very few tags** (<10) with lots of text — Neutral — could be a plain/simple email

### Nesting Depth
- **3–8 levels of table nesting:** Normal for email
- **10–15+ levels of nesting:** SLIGHT negative — overly complex; may indicate auto-generated or obfuscated HTML
- **20+ levels:** MODERATE negative — unusual complexity

---

## 16. Content Patterns in DOM Elements — Spam Keyword Signals

Spam filters scan the text content within every DOM element. These patterns apply to text inside `<td>`, `<p>`, `<span>`, `<h1>`–`<h6>`, `<a>`, `alt` attributes, `<title>`, and all other text-carrying elements.

### High-Risk Spam Phrases in DOM Text
- "Act now", "Limited time", "Urgent", "Expires", "Only X left" — SLIGHT negative per instance; cumulative
- "Free", "100% free", "No cost", "No obligation" — SLIGHT to MODERATE negative depending on density
- "Click here", "Click below", "Click now" — SLIGHT negative (SpamAssassin `HTML_LINK_CLICK_HERE`)
- "Buy now", "Order now", "Shop now" — SLIGHT negative when overused
- "Guaranteed", "No risk", "Risk-free" — SLIGHT negative
- "Winner", "Congratulations", "You've been selected", "You've won" — MODERATE to HIGH negative
- "Unsubscribe" in subject or prominent heading — Neutral (it's required in the footer, but prominent placement is unusual)
- ALL CAPS text blocks — SLIGHT negative per instance; SpamAssassin has specific rules for excessive capitalization
- Excessive exclamation marks (!!! or !!!!!!) — SLIGHT negative
- Excessive dollar signs or currency symbols ($$$, €€€) — SLIGHT negative
- Emoji spam (excessive emoji, especially 🔥💰🎉💵 in subject lines or headings) — SLIGHT negative in some filters

### Phishing-Related DOM Text
- "Verify your account", "Confirm your identity", "Update your information" — HIGH negative in combination with suspicious links
- "Your account has been suspended/compromised/locked" — HIGH negative
- "Enter your password/SSN/credit card" — SEVERE negative
- "Dear Customer" (generic greeting instead of personalized) — SLIGHT negative; legitimate senders personalize
- "Dear [blank]" or "Dear {FIRST_NAME}" (unfilled merge tag) — MODERATE negative; broken template indicates mass mailing

### Content in `alt` Attributes
- **`alt` text containing spam keywords:** Negative — filters scan alt text
- **`alt` text that is the entire email message** (hiding real content in alt tags) — MODERATE negative
- **`alt` text stuffed with invisible keywords:** MODERATE negative

---

## 17. Tracking Pixel Tags — Spam Score Signals

### Open Tracking Pixel
```html
<img src="https://track.esp.com/open/abc123" width="1" height="1" border="0" style="display: block;" alt="">
```
- **Single tracking pixel from known ESP:** Neutral — standard practice; filters recognize this pattern
- **Single tracking pixel from unknown domain:** SLIGHT negative
- **Multiple tracking pixels from different domains:** MODERATE negative — indicates multiple third-party trackers; unusual for legitimate email
- **Tracking pixel without `width="1"` and `height="1"`:** More suspicious — a 1x1 pixel is the recognized convention
- **Tracking pixel with `display: none`:** SLIGHT negative — hiding the tracking pixel more aggressively than necessary
- **Tracking pixel at the top of the email vs bottom:** Top placement is unusual; bottom placement is standard

### Conversion Tracking Pixels
- **Known advertising/analytics pixel** (Facebook pixel, Google conversion tracking) — Neutral when single; slight negative when multiple from different networks
- **Unknown third-party pixel:** SLIGHT to MODERATE negative

---

## 18. CSS Class Names & IDs — Spam Score Signals

Some spam filters analyze CSS class names and IDs for suspicious patterns.

### Suspicious Class/ID Patterns
- **Random string class names** (`.xk3j2m`, `.a1b2c3d4`) — SLIGHT negative — indicates auto-generated HTML
- **Class names containing spam keywords** (`.free-offer`, `.buy-now`, `.discount-special`) — Neutral to slight negative — filters primarily scan content, not class names, but some analyzers check
- **Excessive class names per element** — SLIGHT negative — bloated HTML
- **No class names at all** (all inline styles) — Neutral — common in email due to Gmail stripping classes

### Email Client-Generated Classes
- `.ExternalClass` — Outlook.com generated; recognized as legitimate
- `[data-ogsc]`, `[data-ogsb]` — Outlook.com dark mode; recognized as legitimate
- Gmail class prefix (`m_-xxxx`) — Gmail generated; recognized as legitimate
- These client-generated patterns are NOT spam signals

---

## 19. Attachment-Related DOM Signals

While attachments aren't HTML DOM elements, certain HTML patterns that reference or simulate attachments are flagged.

### HTML Patterns Mimicking Attachments
- **Fake "attachment" images** (images styled to look like attachment previews with file icons) — MODERATE negative when combined with phishing link
- **HTML links to `.exe`, `.zip`, `.bat`, `.scr`, `.pif`, `.com` files:** SEVERE negative — malware delivery
- **Links to `.pdf`, `.doc`, `.xls` on suspicious domains:** MODERATE negative — document-based phishing
- **Links to cloud storage (Google Drive, Dropbox, OneDrive):** Neutral when from legitimate sender; suspicious when combined with urgency language

---

## 20. Positive Spam Score Signals in the DOM

Elements and patterns that REDUCE spam score (improve deliverability).

### Structural Positives
- Well-formed `<!DOCTYPE html>` declaration
- Complete `<head>` with `<meta charset>`, `<meta viewport>`, `<title>`
- Clean, properly nested table structure
- `role="presentation"` on layout tables (indicates accessibility-aware, professional sender)
- `lang` attribute on `<html>`
- Balanced image-to-text ratio (60%+ text)
- `text/plain` MIME alternative present and matching HTML content

### Content Positives
- Personalized greeting (merge tags resolved: "Hi Sarah" not "Hi {FNAME}")
- Physical mailing address in footer
- Unsubscribe link in footer
- `List-Unsubscribe` and `List-Unsubscribe-Post` headers
- Privacy policy link
- Company name and registration info
- Reply-to address that accepts replies
- Links to sender's own domain (consistent with `From` address)
- `alt` text on meaningful images

### Authentication Positives (Not DOM but Affects DOM Rendering)
- Valid SPF record
- Valid DKIM signature
- DMARC alignment pass
- BIMI logo displayed
- ARC chain valid (for forwarded email)
- Sender reputation score (based on historical engagement)

---

## 21. DOM Testing & Spam Score Validation

### Tools That Analyze Email HTML for Spam Signals
- **Mail-Tester (mail-tester.com)** — sends a test email, analyzes SpamAssassin score, shows which HTML rules triggered
- **GlockApps** — tests email deliverability and shows spam filter HTML analysis
- **Litmus Spam Testing** — tests against multiple spam filters and shows HTML-level triggers
- **Email on Acid Spam Testing** — similar multi-filter testing
- **SpamAssassin directly** — install locally and test HTML files against the rule set
- **MXToolbox** — tests email headers and some content analysis
- **Google Postmaster Tools** — shows Gmail-specific delivery metrics (not HTML-level, but engagement-based)
- **Microsoft SNDS** — shows Outlook/Hotmail delivery metrics

### Pre-Send HTML Checklist for Spam Score
- `<!DOCTYPE>` present
- `<html lang="...">` present
- `<head>` with `<meta charset>` and `<title>` present
- `<body>` present and properly formed
- No forbidden tags (`<script>`, `<iframe>`, `<form>`, `<embed>`, `<object>`, `<applet>`)
- No `<meta http-equiv="refresh">`
- No `<base href>`
- No `@import` in `<style>`
- No `javascript:` in any `href`
- No hidden text (color matching background, font-size: 0, display: none on text)
- Image-to-text ratio: 60%+ text
- All images have `alt` attributes
- All links use HTTPS
- No URL shorteners in links
- No IP address URLs
- Link display text matches actual destination (no phishing mismatch)
- Unsubscribe link present in footer
- Physical address present
- `text/plain` MIME part present
- Single tracking pixel only (from known ESP)
- HTML under 100KB total
- Properly closed/nested HTML tags
- No excessive comments or whitespace padding
- No Unicode obfuscation in text content
- No zero-width characters scattered through words
- Merge tags resolved (no unfilled `{FIRST_NAME}` placeholders)
- Links resolve (no 404s or dead URLs)

---

*Total spam-score-related DOM elements, attributes, patterns, and signals: 350+*
