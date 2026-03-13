# HTML Email File Size Guidelines — Complete Reference

Every file size limit, threshold, recommendation, clipping rule, and optimization technique for HTML email development. Covers total email size, HTML weight, image sizes, attachment limits, and per-client constraints.

---

## 1. Why File Size Matters in Email

Email file size affects deliverability, rendering, load time, engagement, and spam scoring at every stage of the delivery pipeline.

### What Happens When Emails Are Too Large
- **Spam filter penalties** — bloated HTML increases spam score; SpamAssassin and commercial filters flag oversized emails
- **Email clipping** — Gmail clips emails over ~102KB and hides the rest behind a "View entire message" link; the unsubscribe link, tracking pixel, and footer may be clipped and never seen
- **Slow rendering** — large emails take longer to parse and render in the email client; mobile clients on slow networks are especially affected
- **Slow loading** — image-heavy emails stall on mobile data connections; recipients abandon before content loads
- **Bounce/rejection** — emails exceeding ISP or corporate server size limits are bounced (rejected) entirely
- **Reduced engagement** — every additional second of load time decreases click-through rate; oversized emails have measurably lower engagement
- **Bandwidth costs** — large emails sent to millions of recipients consume significant bandwidth on both sender and recipient infrastructure
- **Mobile data impact** — recipients on metered data connections may resent emails that consume excessive data

---

## 2. Total Email Size Limits

Total email size includes ALL MIME parts: HTML, plain text, headers, AMP part, inline images, and attachments combined.

### ISP / Email Provider Inbound Limits
- **Gmail** — 25MB maximum total email size (inbound)
- **Outlook.com / Hotmail** — 20MB maximum (Microsoft 365 can be configured higher by admins)
- **Yahoo Mail** — 25MB maximum
- **AOL Mail** — 25MB maximum
- **Apple iCloud Mail** — 20MB maximum
- **ProtonMail** — 25MB maximum
- **Zoho Mail** — 20MB maximum (expandable)
- **Exchange Online (Microsoft 365)** — 25MB default (admin-configurable up to 150MB)
- **Exchange On-Premises** — varies by organization; commonly 10–25MB
- **Corporate email gateways** — often 10–15MB; many organizations set restrictive limits
- **Barracuda / Mimecast / Proofpoint** — security appliances may have their own limits, often 10–25MB

### Recommended Total Email Size
- **Marketing/promotional email:** under 100KB total (ideally under 80KB)
- **Transactional email:** under 75KB total
- **Newsletter email:** under 120KB total (newsletters tend to be longer)
- **Absolute maximum for marketing:** 250KB total (pushing it; expect degraded performance)
- **With attachments:** depends on use case; keep under 10MB; prefer hosted links over attachments

### What Counts Toward Total Size
- Email headers (From, To, Subject, DKIM signature, authentication headers, List-Unsubscribe, etc.) — typically 2–10KB
- `text/plain` MIME part — typically 1–10KB
- `text/html` MIME part — the main HTML email; target under 100KB
- `text/x-amp-html` MIME part — AMP version if present; typically 10–50KB
- Inline/embedded images (CID-attached) — counted in full; avoid embedding images when possible
- Regular attachments (PDF, ICS, etc.) — counted in full
- MIME boundary strings and encoding overhead — Base64 encoding increases attachment size by ~33%
- DKIM signature — adds 1–3KB to headers

### Base64 Encoding Overhead
- Email attachments and inline images are Base64-encoded in the MIME structure
- **Base64 increases file size by approximately 33%** — a 750KB image becomes ~1MB in the email
- A 15MB attachment results in ~20MB in the email after Base64 encoding
- Account for this overhead when calculating total email size against provider limits

---

## 3. HTML File Size (The `text/html` MIME Part)

### Gmail Clipping Threshold — The Critical Limit
- **Gmail clips emails at approximately 102KB** of the HTML MIME part
- When clipped, Gmail truncates the rendered HTML and shows "[Message clipped] View entire message" at the bottom
- **What gets clipped:** everything after the ~102KB mark in the HTML source — this typically means:
  - Footer content (unsubscribe link, physical address, legal text)
  - Tracking pixel (open tracking fails for clipped emails)
  - Closing HTML tags (`</body>`, `</html>`)
  - Dark mode CSS (if in a `<style>` block near the bottom)
  - AMP call-to-action elements near the bottom
- **Clipping is measured on the raw HTML source**, not the rendered visual size
- **MSO conditional comments count toward the limit** — `<!--[if mso]>...<![endif]-->` content is included in the HTML source size even though non-Outlook clients don't render it
- **Whitespace, comments, and blank lines count** — every character in the source counts
- **Gmail clipping affects open tracking** — if the tracking pixel is clipped, the open is not recorded; this skews your analytics

### Recommended HTML Size Targets
- **Ideal:** 50–70KB HTML source
- **Acceptable:** 70–90KB HTML source
- **Caution zone:** 90–100KB HTML source (dangerously close to clipping)
- **Clipping risk:** 100KB+ HTML source (expect Gmail clipping)
- **Emergency maximum:** 120KB+ (many recipients will see clipped email)

### What Contributes to HTML Size
- **Inline styles** — every element has full inline CSS; this is the #1 source of HTML bloat in email; a single `<td>` can have 100+ characters of inline styles
- **MSO conditional content** — VML shapes, Outlook ghost tables, MSO-only styles add significant size; this content is invisible to non-Outlook clients but still counts toward the HTML size for ALL clients
- **Embedded `<style>` blocks** — media queries, dark mode CSS, font-face declarations, reset styles
- **Table nesting** — deep table structure with `<table><tr><td>` markup repeated many levels deep
- **Redundant attributes** — `role="presentation"` on every layout table, `cellpadding="0" cellspacing="0" border="0"` on every table, full inline styles on every element
- **Content** — the actual text, headings, product listings, etc.
- **HTML comments** — template comments, MSO conditionals, section markers
- **Whitespace** — indentation, blank lines, spaces between tags
- **Tracking parameters** — long UTM strings on every link add to size
- **Dark mode classes** — additional class attributes on every element for dark mode targeting

### How to Measure HTML Size
- **Check the raw HTML source file size** — not the rendered/visual size
- **In your code editor:** save the HTML file and check the file size in your OS
- **Command line:** `wc -c email.html` (bytes) or `ls -la email.html`
- **ESP preview tools:** most ESPs show the HTML size and warn about clipping
- **Litmus / Email on Acid:** show HTML size and Gmail clipping prediction
- **After ESP processing:** check the size AFTER the ESP has rewritten tracking links (tracked URLs are longer than original URLs, increasing size)

---

## 4. Image File Size Guidelines

### Individual Image Size Recommendations
- **Hero/banner image:** 100–200KB maximum (ideally under 150KB)
- **Product images:** 30–80KB each
- **Logo:** 10–30KB
- **Icons:** 2–10KB each
- **Background images (for VML):** 50–150KB
- **Social media icons:** 2–5KB each
- **Animated GIF:** 200–500KB maximum (ideally under 250KB); under 1MB absolute max
- **Tracking pixel:** <1KB (1x1 transparent GIF or PNG)
- **Retina images:** double the pixel dimensions but same file size target as non-retina (achieved through higher compression)

### Total Image Weight Per Email
- **Recommended total image weight:** 800KB or less for the entire email
- **Ideal total image weight:** 200–500KB
- **Maximum practical total:** 1.5MB (mobile users on slow connections will have issues)
- **Above 2MB total images:** significant load time impact; expect reduced engagement

### Image Dimensions (Pixel Size)
- **Maximum image width:** 600px for full-width images (matching the standard 600px email container)
- **Retina width:** 1200px actual pixels, displayed at 600px via `width="600"` HTML attribute
- **Hero image:** 600px wide × 200–400px tall (or 1200×400–800 for retina)
- **Product thumbnails:** 200–300px wide
- **Logo:** 150–250px wide
- **Social icons:** 24–40px (or 48–80px retina)
- **Avoid images wider than 1200px** — unnecessary file size; email is never displayed wider than ~700px even on desktop
- **Height consideration:** extremely tall images (>1000px rendered height) may be problematic on mobile; consider breaking into multiple images

### Image Format Selection

#### JPEG (.jpg)
- **Best for:** photographs, hero images, product photos, complex images with many colors and gradients
- **Target quality:** 60–80% compression (Photoshop/GIMP quality setting)
- **Progressive JPEG:** load in progressive scans (blurry → sharp); slightly better perceived load time but slightly larger file
- **Standard JPEG:** load top-to-bottom; slightly smaller file
- **Color mode:** RGB only (not CMYK); sRGB color space
- **Recommendation:** use progressive JPEG for hero images (>100KB); standard JPEG for smaller images

#### PNG (.png)
- **Best for:** logos, icons, illustrations with flat colors, images requiring transparency
- **PNG-8:** up to 256 colors; very small file size; good for simple graphics
- **PNG-24:** millions of colors; larger file size; use for transparency with complex images
- **PNG with transparency:** essential for dark mode compatibility (logos, icons)
- **Avoid PNG for photographs** — JPEG is always smaller for photographic content
- **Optimize with tools:** TinyPNG, PNGQuant, OptiPNG reduce PNG size by 50–80%

#### GIF (.gif)
- **Best for:** simple animations, very simple graphics (<256 colors)
- **Animated GIF size:** keep under 500KB; ideally under 250KB
- **Frame count:** fewer frames = smaller file; 10–30 frames is typical
- **Frame dimensions:** smaller pixel dimensions dramatically reduce GIF size
- **Color reduction:** reducing from 256 to 64 or 32 colors can halve the file size
- **Dithering:** Floyd-Steinberg dithering maintains perceived quality at lower color counts
- **Loop count:** limit loops to 3–5 for non-essential animations (reduces cognitive load; doesn't affect file size)
- **GIF optimization tools:** Gifsicle, EZGIF, ImageOptim

#### WebP (.webp)
- **Smaller than JPEG and PNG** at equivalent quality (25–35% smaller)
- **Email client support:** Apple Mail (macOS Ventura+), iOS 14+, Gmail (web and app), Thunderbird, some Samsung Mail versions
- **NOT supported by:** Outlook desktop (any version), older iOS, older Apple Mail, some Yahoo Mail
- **Recommendation:** do NOT use WebP as the sole format in email; always provide JPEG/PNG fallback
- **Can be used in `<picture>` tags** with JPEG/PNG fallback — but `<picture>` only works in Apple Mail
- **Current status:** not recommended as primary email image format due to Outlook and legacy client support gaps

#### AVIF (.avif)
- **Even smaller than WebP** at equivalent quality
- **Email client support:** extremely limited; not recommended for email use
- **Future potential:** may become viable as client support grows

#### SVG (.svg)
- **Inline SVG:** very limited email client support (Apple Mail, some Thunderbird); Outlook and Gmail strip inline SVG
- **SVG as `<img src="file.svg">`:** slightly better support but still risky
- **Recommendation:** convert SVG to PNG for email; use SVG only as a progressive enhancement with PNG fallback
- **File size:** typically very small for simple vector graphics (1–10KB)

### Image Optimization Techniques
- **Lossy compression:** reduce JPEG quality to 60–75%; visually acceptable with significant size savings
- **Lossless compression:** strip metadata (EXIF, color profiles, thumbnails) from images; saves 10–30% without quality loss
- **Resize to actual display size:** never serve a 2000px image that displays at 300px; serve at 600px (or 600px retina at 1200px)
- **Crop tightly:** remove unnecessary whitespace and background from product images
- **Color reduction:** reduce PNG palette from 256 to the minimum colors needed
- **Tools:** TinyPNG/TinyJPG, ImageOptim, Squoosh, ShortPixel, Kraken.io
- **CDN image optimization:** Cloudinary, Imgix, and similar services can serve optimized images at the correct size dynamically
- **Image sprites:** combine multiple small images (icons) into a single sprite sheet to reduce HTTP requests (rarely used in email now due to background-position limitations in Outlook)

### Image Caching and Hosting
- **Host images on a CDN** (Content Delivery Network) — faster delivery worldwide; reduces load time
- **Use consistent image URLs** — changing image URLs between sends prevents caching
- **Set proper cache headers** — `Cache-Control: public, max-age=31536000` on image server; images are cached in the client after first load
- **Dedicated image hosting domain** — `images.yourdomain.com` or ESP-provided image hosting
- **HTTPS required** — serve all images over HTTPS; HTTP images may be blocked or show security warnings
- **Avoid hotlinking** — don't link to images on third-party domains that you don't control; they may change or disappear
- **Image server reliability** — if your image server goes down, your email displays broken images indefinitely (unlike web pages, emails are not re-downloaded)

---

## 5. Plain Text MIME Part Size

### Size Guidelines
- **Recommended:** 5–20KB for the `text/plain` part
- **Should be proportional to HTML content** — a 50KB HTML email should have at least a 5–10KB plain text version
- **Minimum:** include at least the key message, primary CTA URL, and unsubscribe link
- **Maximum:** no hard limit, but excessively long plain text adds to total email size

### What to Include in Plain Text
- All meaningful text content from the HTML version
- All link URLs written out in full (including UTM parameters if tracking is needed)
- Unsubscribe link URL
- Physical mailing address
- A note about viewing the HTML version ("View this email in your browser: [URL]")
- Simplified formatting (dashes for dividers, asterisks for emphasis, manual line breaks at ~70 characters)

---

## 6. AMP MIME Part Size

### AMP HTML Size Limits
- **AMP for Email spec limit:** 200KB maximum for the `text/x-amp-html` MIME part
- **Gmail's AMP processing limit:** 200KB
- **Recommended:** under 100KB for the AMP part
- **AMP CSS limit:** `<style amp-custom>` must be under 75KB (AMP spec requirement)
- **AMP boilerplate:** `<style amp4email-boilerplate>` adds ~1KB (mandatory; cannot be reduced)
- **AMP JavaScript:** only the AMP runtime and declared components; no custom JavaScript; the `<script>` tags add to size

### AMP Image Handling
- AMP images (`<amp-img>`) are loaded lazily by default — improves perceived performance
- AMP image size recommendations are the same as regular HTML email images
- AMP layouts (`responsive`, `fixed`, `fill`) manage image rendering without extra CSS

---

## 7. Attachment Size Guidelines

### When to Use Attachments vs Hosted Links
- **Prefer hosted links over attachments** — attachments increase email size, may trigger spam filters, and may be stripped by corporate gateways
- **Use attachments for:** ICS calendar files (small), critical PDFs that must be delivered (invoices, tickets), documents the recipient specifically requested
- **Use hosted links for:** large PDFs, videos, images, downloadable files, documents that may be updated

### Attachment Size Limits
- **ICS calendar files:** typically 1–5KB; always safe to attach
- **PDF attachments:** keep under 2MB; ideally under 500KB
- **Image attachments:** avoid; host images externally and link via `<img src>`
- **Total attachments per email:** keep under 5MB total (accounting for Base64 encoding overhead)
- **Maximum practical attachment size:** 10MB (after Base64 encoding becomes ~13MB; approaches many ISP limits)
- **Video attachments:** NEVER attach video files to email; host on YouTube/Vimeo/your server and link

### Attachment Spam Considerations
- **Executable attachments** (`.exe`, `.bat`, `.scr`, `.pif`, `.com`, `.cmd`, `.vbs`, `.js`) — BLOCKED by virtually all email providers; will not be delivered
- **Compressed archives** (`.zip`, `.rar`, `.7z`) — often blocked or quarantined, especially if they contain executables
- **Office documents** (`.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`) — may trigger scanning; macro-enabled files (`.docm`, `.xlsm`) are frequently blocked
- **PDF** (`.pdf`) — generally accepted but scanned for malware
- **Calendar files** (`.ics`) — generally accepted; low spam signal
- **Image files** (`.jpg`, `.png`, `.gif`) — generally accepted as attachments but increase size unnecessarily
- **Password-protected archives** — often blocked because the scanner can't inspect contents

### Inline/Embedded Images (CID)
```html
<img src="cid:logo-image-001">
```
- **CID (Content-ID) images** are embedded directly in the email as MIME attachments referenced by ID
- **Pros:** images display immediately without requiring external HTTP request; work offline; no image blocking
- **Cons:** dramatically increase email file size; every CID image adds its full Base64-encoded size to the email
- **Recommendation:** avoid CID-embedded images for marketing email; use external hosting
- **Acceptable use:** small logos in transactional email where guaranteed display is critical
- **Size impact:** a 50KB logo embedded via CID becomes ~67KB (Base64) in the email; three product images at 100KB each add ~400KB
- **Gmail handling:** Gmail may strip CID images; external hosting is more reliable

---

## 8. `<style>` Block Size

### Embedded CSS Size
- **Recommended:** under 20KB for the entire `<style>` block
- **Includes:** reset styles, responsive media queries, dark mode `@media (prefers-color-scheme)`, Outlook.com dark mode (`[data-ogsc]`/`[data-ogsb]`), `@font-face` declarations, MSO conditional styles
- **Gmail `<style>` limit:** Gmail supports embedded `<style>` up to a certain complexity (no hard documented limit, but very large/complex `<style>` blocks may be stripped)
- **Gmail class name mangling:** Gmail renames all CSS classes, which adds overhead

### Reducing `<style>` Block Size
- Minify CSS (remove whitespace, comments, unnecessary semicolons)
- Combine duplicate selectors
- Use shorthand properties where supported (`padding: 10px 20px` vs separate `padding-top`, `padding-right`, etc.)
- Remove unused CSS rules (responsive styles for elements that don't exist in the email)
- Critical CSS only — email `<style>` blocks should only contain styles that need class/selector targeting (dark mode, responsive, resets); all other styles go inline

---

## 9. Subject Line and Preheader Size

### Subject Line
- **Maximum characters displayed:** varies by client and device:
  - Gmail (desktop): ~70 characters
  - Gmail (mobile): ~40 characters
  - Outlook (desktop): ~60 characters
  - Outlook (mobile): ~40 characters
  - Apple Mail (desktop): ~60–70 characters
  - iOS Mail: ~35–40 characters
  - Yahoo (desktop): ~45 characters
  - Yahoo (mobile): ~35 characters
- **Recommended length:** 30–50 characters (sweet spot for most clients and devices)
- **Maximum practical:** 60 characters before truncation risk
- **Emoji in subject lines:** emoji are 2–4 bytes in UTF-8; one emoji counts as ~2 characters of display space; some clients may not render all emoji
- **Subject line byte size:** relevant for MIME header encoding; keep under 998 bytes per RFC 5322; extremely long subjects may be folded across multiple header lines

### Preheader / Preview Text
- **Visible preview text length:** varies by client:
  - Gmail (desktop): ~110–120 characters (subject + preheader combined)
  - Gmail (mobile): ~60–90 characters
  - Outlook (desktop): ~50–60 characters
  - Outlook (mobile): ~40–50 characters
  - Apple Mail (desktop): ~80–100 characters
  - iOS Mail: ~50–75 characters
  - Yahoo: ~40–60 characters
- **Recommended preheader length:** 40–100 characters of meaningful text
- **Preheader padding:** the `&zwnj;&nbsp;` whitespace padding after hidden preheader text (to push trailing HTML content out of the preview window) adds ~200–300 bytes; acceptable overhead
- **Hidden preheader HTML overhead:** the hidden preheader `<div>` with its inline styles (`display: none; max-height: 0; overflow: hidden; mso-hide: all;`) adds ~100–200 bytes

---

## 10. Email Header Size

### MIME Headers
- **Typical email header size:** 2–10KB
- **Headers include:** From, To, Subject, Date, Message-ID, MIME-Version, Content-Type, Content-Transfer-Encoding, List-Unsubscribe, List-Unsubscribe-Post, DKIM-Signature, Authentication-Results, Received chains, X-headers, and more
- **DKIM signature:** adds 1–3KB per signature (some senders apply multiple DKIM signatures)
- **ARC headers:** add 1–3KB if present (forwarded email authentication)
- **Received chain:** each hop adds ~200–500 bytes; emails passing through multiple servers accumulate several KB
- **Custom X-headers:** each custom header (X-Mailer, X-Campaign-ID, etc.) adds 50–200 bytes
- **Not directly controllable** by email developers — header size is determined by the ESP and receiving infrastructure

### Header Impact on Total Size
- Headers are counted in the total email size against ISP limits
- A 10KB header block means your content budget is 10KB less than the maximum
- **ARC-heavy forwarded emails** may have 5–10KB of ARC headers alone

---

## 11. Web Font File Size in Email

### `@font-face` File Size
- **Font file downloads** are initiated by the email client when `@font-face` is declared in the `<style>` block
- **The font file itself is NOT part of the email** — it's downloaded separately from the font server
- **WOFF2 format:** recommended; smallest web font format (30–50% smaller than WOFF)
- **WOFF format:** acceptable fallback
- **TTF/OTF format:** larger; use as last resort
- **Recommended individual font file:** under 100KB per weight/style
- **Total font downloads per email:** keep under 300KB total (loading 3–4 font files max)
- **Subset fonts:** strip unused characters from font files to reduce size; if your email is English-only, remove CJK, Cyrillic, Greek character sets
- **Only Apple Mail, iOS Mail, Samsung Mail, and Thunderbird download web fonts** — all other clients ignore `@font-face` and use the fallback font; the font download overhead only affects these clients

### Font Loading Impact
- Fonts load AFTER the email HTML renders — text appears in the fallback font first, then reflows when the web font loads (FOUT — Flash of Unstyled Text)
- Large font files cause noticeable text reflow
- On slow connections, web fonts may not load at all; the fallback font is what most recipients see

---

## 12. Video and Media Size in Email

### `<video>` in Email
- **Only supported in Apple Mail and iOS Mail** — all other clients show the fallback `<img>` poster
- **Video file is NOT embedded in the email** — it's loaded from an external server via `<video src="...">`
- **Recommended video file size:** under 5MB (loaded on demand, not sent with the email)
- **Poster image** (`poster="..."` attribute): serves as the fallback image in non-supporting clients; size guidelines match regular images (100–200KB)
- **Format:** MP4 with H.264 encoding for broadest compatibility
- **Autoplay:** `autoplay muted playsinline` — Apple Mail supports autoplay only when muted
- **Do not embed video in the email MIME structure** — it would make the email 10–100MB+

### Animated GIF as Video Alternative
- **GIFs are the primary animation format in email** — supported by all clients except Outlook desktop (which shows first frame)
- **Size target:** under 500KB per GIF; ideally under 250KB
- **Techniques to reduce GIF size:**
  - Reduce frame count (drop every other frame for a slight speed-up)
  - Reduce pixel dimensions (smaller = dramatically smaller file)
  - Reduce color count (64 or 32 colors instead of 256)
  - Crop to only the animated portion (static background can be a separate image)
  - Use lossy GIF compression (Gifsicle `--lossy=80`)
  - Limit animation duration (3–5 seconds)
  - Use a tool like EZGIF to optimize
- **Animated GIF load time:** a 500KB GIF on a 3G connection takes ~3 seconds to load; on slow connections, the user sees a blank space or partially loaded animation

### Live Countdown Timer Images
- **Server-generated animated GIF** created at open time
- **Typical size:** 50–200KB depending on design complexity and duration
- **Generated per-open** — each open creates a new image request; the server generates the current countdown dynamically
- **Size is not part of the email** — it's an external image loaded on demand

---

## 13. ESP-Specific Size Limits and Considerations

### Mailchimp
- **Maximum HTML size:** 200KB per campaign
- **Maximum total email size:** 25MB
- **Image hosting:** unlimited on Mailchimp's CDN
- **Individual image upload limit:** 10MB per image
- **Recommended HTML size:** under 100KB

### SendGrid
- **Maximum total email size:** 30MB (API limit)
- **Recommended HTML size:** under 100KB
- **No explicit HTML size limit** but larger emails have lower deliverability

### HubSpot
- **Maximum email size:** no published hard limit
- **Image upload limit:** 6MB per image (on HubSpot CMS)
- **Recommended HTML size:** under 100KB
- **Email editor warns** about large email sizes

### Salesforce Marketing Cloud
- **Maximum total email size:** 5MB (with attachments)
- **Maximum HTML size:** no published limit
- **Recommended HTML size:** under 100KB
- **Image hosting:** via Content Builder; varies by license

### Campaign Monitor
- **Maximum total email size:** 25MB
- **Maximum HTML size:** 800KB
- **Recommended HTML size:** under 100KB
- **Image hosting:** provided via Campaign Monitor CDN

### Klaviyo
- **Maximum email size:** no published hard limit
- **Recommended HTML size:** under 100KB
- **Image hosting:** included on Klaviyo CDN

### Braze
- **Maximum email size:** no published hard limit
- **Maximum HTML size:** 100KB hard limit (to prevent Gmail clipping)
- **Inline CSS and minification recommended**

### General ESP Recommendations
- **Check your ESP's documentation** for current limits — they change
- **Test with your ESP's preview/analysis tool** for size warnings
- **Account for ESP overhead:** ESPs add tracking pixels, click tracking URL rewrites, and header modifications that increase the final sent email size beyond your source HTML size

---

## 14. Performance Benchmarks

### Load Time Targets
- **Total email load time:** under 3 seconds on 3G mobile connection
- **Image load time:** each image should load within 1–2 seconds on 3G
- **3G speed reference:** ~750 Kbps (kilobits per second) download
- **4G/LTE speed reference:** ~12 Mbps download
- **At 3G speeds:**
  - 100KB email HTML: ~1 second
  - 500KB total images: ~5 seconds
  - 1MB total images: ~11 seconds
  - 2MB total images: ~22 seconds
- **At 4G speeds:**
  - 100KB email HTML: <0.1 seconds
  - 500KB total images: ~0.3 seconds
  - 1MB total images: ~0.7 seconds
  - 2MB total images: ~1.3 seconds

### Engagement Impact of Size
- **Each additional 100KB** of total email size correlates with measurable decrease in engagement
- **Emails under 100KB total** have the highest open-to-click ratios
- **Emails over 1MB total** have significantly lower click rates compared to optimized emails
- **Mobile opens** (60%+ of all opens) are most affected by size — mobile devices on cellular connections load images slower

---

## 15. Size Optimization Techniques

### HTML Source Optimization
- **Minify HTML** — remove whitespace, line breaks, and comments; saves 10–30%
  - Tools: HTMLMinifier, email-specific minifiers in ESPs
  - **Preserve MSO conditional comments** — minifiers must not break `<!--[if mso]>` syntax
  - **Preserve preheader hidden text** — minifier should not remove the preheader `<div>`
- **Inline CSS efficiently** — use shorthand properties (`padding: 10px 20px` vs four separate padding declarations)
- **Remove unused CSS** — from the `<style>` block; only include rules that are actually referenced
- **Remove redundant attributes** — if a value is the default, it may not need to be declared (but test in email clients; defaults vary)
- **Use abbreviated hex colors** — `#fff` instead of `#ffffff`; `#333` instead of `#333333`; saves 3 bytes per color (adds up across hundreds of elements)
- **Remove HTML comments** — except MSO conditionals and preheader structure
- **Consolidate inline styles** — remove duplicate properties; use `font: 16px/1.5 Arial` shorthand where supported (caution: some clients don't support CSS shorthand)
- **Reduce table nesting depth** — flatten the structure where possible; each table layer adds `<table><tr><td></td></tr></table>` overhead
- **Limit MSO conditional content** — VML and Outlook ghost tables are verbose; use them only where necessary (background images, rounded buttons, column layout)
- **Use semantic HTML** — `<p>` instead of `<td>` containing text where possible; fewer wrapping elements means less markup
- **Limit dark mode class attributes** — only add dark mode classes to elements that actually need color overrides; not every element needs `.dm-text` and `.dm-bg`

### Image Optimization
- **Compress all images** before upload — TinyPNG, ImageOptim, Squoosh
- **Serve at exact display dimensions** — not larger; scale retina images to 2x display width, not 3x or 4x
- **Choose the right format** — JPEG for photos, PNG for transparency/flat graphics, GIF for animation
- **Lazy loading consideration** — email clients do not support `loading="lazy"`; all images load immediately
- **Image CDN** — Cloudinary, Imgix, or similar services can auto-optimize and serve correctly sized images based on the request
- **Remove metadata** — strip EXIF data, ICC color profiles, and thumbnails from images
- **Progressive JPEG** — for large hero images; provides faster perceived loading

### Link Optimization
- **Shorten UTM parameters** — use abbreviated campaign names; `utm_source=mc` instead of `utm_source=mailchimp_campaign_spring_2026`
- **Reduce link count** — fewer links means less tracking URL overhead (each tracked link adds 100–200 bytes of tracking URL)
- **Consider untracked links** — some links (unsubscribe, physical address) may not need click tracking; excluding them saves bytes

### Template Architecture Optimization
- **Modular design** — reusable content blocks with consistent structure reduce per-email custom code
- **Template compression** — some ESPs compress the HTML before sending
- **Test template size before content** — measure the empty template size; a 40KB empty template leaves only 60KB for content before Gmail clipping
- **Account for ESP additions** — click tracking, tracking pixel, header additions, and wrapper HTML added by the ESP; request the final sent size from your ESP

---

## 16. Size Budget Template

A practical allocation for a standard marketing email under the 102KB Gmail clipping limit.

### Total Budget: ~95KB HTML Source (Leaving 7KB Buffer)
- **Email headers (not in HTML):** ~5KB (managed by ESP)
- **`<head>` section:** ~5–10KB
  - `<meta>` tags: ~500 bytes
  - `<title>`: ~50 bytes
  - MSO XML namespace block: ~300 bytes
  - `<style>` block (responsive + dark mode + resets): ~5–8KB
  - MSO conditional `<style>`: ~1KB
- **Preheader (hidden):** ~500 bytes
- **Header section (logo, navigation):** ~2–3KB
- **Hero section:** ~3–5KB (text overlay, background image reference, CTA button)
- **Body content (the actual email content):** ~40–50KB
  - This is your largest variable section
  - Product grids, article excerpts, feature blocks
  - Inline styles on every element eat into this budget
- **CTA sections:** ~2–3KB per CTA block
- **Footer:** ~5–8KB (unsubscribe, address, legal, social icons, preference center)
- **MSO conditional content (VML, ghost tables):** ~10–15KB
  - VML background images: ~2–3KB each
  - Ghost table column wrappers: ~1–2KB each
  - VML buttons: ~1KB each
- **Tracking pixel:** ~200 bytes
- **Closing tags:** ~50 bytes

### Budget Warnings
- **6+ product grid items** in a single email push the body content well over 50KB
- **Multiple VML background sections** (hero + midpage + CTA) can add 10KB+ of MSO conditional content
- **Long article excerpts or full blog post content** can push past 100KB easily; link to the full content on the web instead
- **Personalized content blocks** (dynamic/conditional content) may result in different email sizes per recipient; test the largest variant

---

## 17. Quick Reference Size Table

| Component | Recommended | Maximum | Critical Limit |
|---|---|---|---|
| Total email size | Under 100KB | 250KB | 25MB (ISP reject) |
| HTML source (`text/html`) | 50–70KB | 95KB | ~102KB (Gmail clips) |
| Plain text (`text/plain`) | 5–20KB | 50KB | No hard limit |
| AMP part (`text/x-amp-html`) | Under 100KB | 200KB | 200KB (spec limit) |
| `<style>` block | Under 20KB | 40KB | No hard limit |
| AMP `<style amp-custom>` | Under 50KB | 75KB | 75KB (spec limit) |
| Individual hero image | 100–150KB | 200KB | None (but load time) |
| Individual product image | 30–80KB | 150KB | None |
| Individual animated GIF | Under 250KB | 500KB | ~1MB practical |
| Logo image | 10–30KB | 50KB | None |
| Icon image | 2–10KB | 20KB | None |
| Total images per email | 200–500KB | 800KB | ~1.5MB practical |
| Web font file (WOFF2) | Under 50KB | 100KB | None (external load) |
| Total font downloads | Under 200KB | 300KB | None |
| ICS attachment | 1–5KB | 10KB | None |
| PDF attachment | Under 500KB | 2MB | 10MB practical |
| Total attachments | Under 2MB | 5MB | 10MB practical |
| Subject line | 30–50 chars | 60 chars | ~200 chars (truncated) |
| Preheader text | 40–100 chars | 150 chars | ~250 chars (varies) |
| Email headers | 2–5KB | 10KB | Not controllable |
| Tracking pixel | <1KB | 1KB | None |
| UTM parameter string | Under 100 chars | 200 chars | Adds to URL length |

---

## 18. Testing File Size

### Pre-Send Size Checks
- Check raw HTML file size in code editor or OS file browser
- Check HTML size AFTER ESP processing (tracked links, added pixels, wrapper HTML)
- Use ESP's built-in size/clipping warnings
- Use Litmus or Email on Acid Gmail clipping prediction
- Send a test email to a Gmail account and verify no clipping occurs
- Send a test email on a mobile device on cellular data and time the image load
- Check total email size (including headers) in an email client's "message source" view
- Verify all images load on first open (no broken images, no excessive delay)

### Size Monitoring Over Time
- Track average email size per campaign
- Alert if email size exceeds 90KB HTML (approaching Gmail clipping)
- Monitor image CDN response times
- Track email load time metrics if your ESP provides them
- Review size impact when adding new template sections or features

---

---

## 19. QA Check Rule Mapping

The QA engine validates file size via 8 automated rules in `app/qa_engine/rules/file_size.yaml`. Each rule maps to a configurable deduction against the check's 1.0 base score.

### Group A: Client Thresholds
| Rule ID | Client | Threshold | Default Deduction | Severity |
|---------|--------|-----------|-------------------|----------|
| `fs-gmail-clip` | Gmail | 102KB | -0.30 | Critical — email truncated |
| `fs-outlook-perf` | Outlook Desktop | 100KB | -0.20 | Rendering performance |
| `fs-yahoo-clip` | Yahoo Mail | 75KB | -0.10 | Conservative clip risk |
| `fs-braze-limit` | Braze ESP | 100KB | -0.15 | Hard rejection |

### Group B: Content Distribution
| Rule ID | Condition | Threshold | Default Deduction |
|---------|-----------|-----------|-------------------|
| `fs-inline-css-bloat` | Inline `style=""` bytes > X% of total | 40% | -0.05 |
| `fs-mso-bloat` | MSO conditional bytes > X% of total | 25% | -0.05 |

### Group C: Compression Efficiency
| Rule ID | Condition | Threshold | Default Deduction |
|---------|-----------|-----------|-------------------|
| `fs-gzip-ratio` | Gzip reduction < X% (on files > 20KB) | 50% | -0.05 |

### Group D: Summary
| Rule ID | Purpose | Deduction |
|---------|---------|-----------|
| `fs-size-summary` | Informational breakdown (raw, gzip, category percentages) | 0.00 |

### Score Impact Examples
- **50KB email**: Score 1.0 — all thresholds met
- **80KB email**: Score 0.90 — Yahoo threshold exceeded (-0.10)
- **101KB email**: Score 0.55 — Yahoo (-0.10) + Outlook (-0.20) + Braze (-0.15)
- **105KB email**: Score 0.25 — all 4 client thresholds exceeded (-0.75)
- **105KB with 45% inline CSS**: Score 0.20 — above + CSS bloat (-0.05)

### Configuration Override
All thresholds configurable in `defaults.yaml` under `file_size.params` or per-project via `qa_profile`:
```yaml
file_size:
  params:
    gmail_threshold_kb: 102    # Adjust per project
    outlook_threshold_kb: 100
    yahoo_threshold_kb: 75
    braze_threshold_kb: 100
    inline_css_max_pct: 40     # Content distribution thresholds
    mso_conditional_max_pct: 25
    gzip_min_reduction_pct: 50
```

---

*Total file size guidelines, limits, recommendations, and optimization techniques: 300+*
