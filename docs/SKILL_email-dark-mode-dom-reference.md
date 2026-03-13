# HTML Email Dark Mode — Complete DOM Rendering Reference

Every tag, attribute, meta declaration, CSS selector, hack, and technique that email client dark mode engines interact with when rendering HTML emails. Special focus on Outlook's forced dark mode overrides and prevention techniques.

---

## 1. How Email Client Dark Mode Engines Modify the DOM

Email dark mode is NOT like website dark mode. Email clients forcibly rewrite your inline styles and HTML attributes at the DOM level before rendering. Understanding what the dark mode engine touches is critical.

### What Dark Mode Engines Do to Your Email DOM
- Rewrite `color` inline style values on text elements (`<td>`, `<p>`, `<span>`, `<a>`, `<h1>`–`<h6>`, `<li>`, `<b>`, `<strong>`, `<em>`, `<i>`)
- Rewrite `background-color` inline style values on container elements (`<td>`, `<div>`, `<table>`, `<body>`)
- Rewrite `bgcolor` HTML attributes on `<table>`, `<td>`, `<tr>`, `<body>`
- Rewrite `border-color` inline style values
- Rewrite `border` shorthand inline style values (extracting and modifying the color component)
- Rewrite `border-top`, `border-right`, `border-bottom`, `border-left` color components
- Rewrite `outline-color` values
- Rewrite `box-shadow` color values (in clients that support `box-shadow`)
- Invert or replace `background-image` in some clients
- Modify `<img>` rendering (add transparency blending, reduce brightness)
- Apply filter transformations to images (`brightness()`, `invert()`)
- Override `<meta name="color-scheme">` preferences in some clients
- Inject wrapper `<div>` elements with dark background colors around your email content
- Add `data-*` attributes to elements for targeting (Outlook.com)
- Rewrite the `<body>` background color

### Three Types of Email Dark Mode Behavior
1. **No color change** — client offers dark chrome (inbox list, toolbar) but does not modify email HTML colors (rare)
2. **Partial inversion** — client only changes light backgrounds to dark but leaves dark backgrounds and text alone (Apple Mail, iOS Mail default behavior)
3. **Full forced inversion** — client forcibly inverts ALL colors regardless of your design intent (Outlook desktop Windows, Outlook.com, Gmail Android app in some modes)

---

## 2. Meta Tags for Dark Mode Declaration

These `<meta>` tags in the email `<head>` tell email clients that your email supports dark mode and should be rendered using your custom dark styles rather than forced inversion.

### `<meta name="color-scheme">`
```html
<meta name="color-scheme" content="light dark">
```
- Declares that the email supports both light and dark color schemes
- Parsed by: Apple Mail, iOS Mail, macOS Mail
- Effect: tells the client to use your `@media (prefers-color-scheme: dark)` styles instead of auto-inverting
- Without this: Apple Mail may still auto-invert colors even if you have dark mode CSS
- `content="light"` — declares light mode only; client may still force dark mode
- `content="dark"` — declares dark mode only; email always renders in dark style
- `content="light dark"` — declares support for both (recommended)
- `content="only"` — attempts to prevent any dark mode modification (limited support)
- `content="light only"` — attempts to force light mode rendering; works in Apple Mail to prevent dark mode inversion entirely

### `<meta name="supported-color-schemes">`
```html
<meta name="supported-color-schemes" content="light dark">
```
- Legacy/older version of `color-scheme` meta tag
- Parsed by: older versions of Apple Mail, iOS Mail
- Include BOTH meta tags for maximum compatibility
- Same `content` values as `color-scheme`

### `<meta name="color-scheme">` on `<head>` (alternative placement)
```html
<head>
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
</head>
```
- Must be in `<head>`, not `<body>`
- Must appear before `<style>` blocks
- Some clients strip `<head>` content — these meta tags may be lost (Gmail strips them)

---

## 3. CSS `color-scheme` Property

### On `:root` or `<html>`
```css
:root {
  color-scheme: light dark;
}
```
- CSS equivalent of the meta tag
- Parsed by: Apple Mail, iOS Mail
- Placed in the embedded `<style>` block in `<head>`
- Tells the rendering engine the email understands dark mode

### On Specific Elements
```css
.force-light {
  color-scheme: light only;
}
```
- Applied to individual elements to prevent dark mode inversion on that specific element
- `color-scheme: light only` on a `<td>` attempts to keep that cell in light mode
- Limited support: Apple Mail respects this; most other clients ignore it

---

## 4. `@media (prefers-color-scheme: dark)` CSS Block

The primary method for providing custom dark mode styles. Placed in the `<style>` block in `<head>`.

### Basic Structure
```css
@media (prefers-color-scheme: dark) {
  /* Dark mode overrides */
  .email-body { background-color: #1a1a1a !important; }
  .text-primary { color: #ffffff !important; }
  .text-secondary { color: #cccccc !important; }
  .header-bg { background-color: #2d2d2d !important; }
  .button-bg { background-color: #4a9eff !important; }
  .divider { border-color: #444444 !important; }
}
```

### Which Clients Parse This
- Apple Mail (macOS) — full support
- iOS Mail — full support
- Outlook for iOS — partial support
- Outlook for Android — partial support
- Outlook for Mac — full support
- Samsung Mail — partial support (Android 9+)
- Thunderbird — full support
- Hey.com — full support
- Fastmail — full support

### Which Clients IGNORE This (Force Their Own Inversion)
- Outlook desktop (Windows) — ignores `prefers-color-scheme` entirely; applies Word-engine forced inversion
- Outlook.com (webmail) — ignores `prefers-color-scheme`; uses its own `[data-ogsc]`/`[data-ogsb]` system
- Gmail (web) — strips `<style>` blocks in some contexts; does its own inversion
- Gmail (Android) — strips `<style>` blocks; auto-inverts
- Gmail (iOS) — partial; may strip styles
- Yahoo Mail — limited support; may auto-invert instead
- AOL Mail — limited support

### `!important` Requirement
- ALL dark mode CSS declarations must use `!important` — they're overriding inline styles, which have maximum specificity
- Without `!important`, inline styles always win and dark mode classes have no effect

### Targeting Specific Elements
```css
@media (prefers-color-scheme: dark) {
  /* Body/wrapper background */
  .body-bg { background-color: #121212 !important; }
  
  /* Table cell backgrounds */
  .content-bg { background-color: #1e1e1e !important; }
  .card-bg { background-color: #2d2d2d !important; }
  .header-bg { background-color: #1a1a1a !important; }
  .footer-bg { background-color: #0d0d0d !important; }
  
  /* Text colors */
  .text-dark { color: #f0f0f0 !important; }
  .text-light { color: #e0e0e0 !important; }
  .text-muted { color: #999999 !important; }
  .heading-color { color: #ffffff !important; }
  
  /* Link colors */
  .link-color { color: #6ab7ff !important; }
  
  /* Button colors */
  .btn-bg { background-color: #4a9eff !important; }
  .btn-text { color: #ffffff !important; }
  .btn-border { border-color: #4a9eff !important; }
  
  /* Border/divider colors */
  .divider { border-color: #444444 !important; }
  .card-border { border-color: #555555 !important; }
  
  /* Image handling */
  .dark-img { display: block !important; width: auto !important; overflow: visible !important; max-height: inherit !important; }
  .light-img { display: none !important; }
}
```

---

## 5. Dark Mode Image Swap Techniques

### `<picture>` + `<source>` Method (Apple Mail)
```html
<picture>
  <source srcset="https://example.com/logo-dark.png" media="(prefers-color-scheme: dark)">
  <img src="https://example.com/logo-light.png" alt="Company Logo" width="200" height="50" style="display: block; border: 0;">
</picture>
```
- The `<source>` with `media="(prefers-color-scheme: dark)"` is rendered in dark mode
- The `<img>` is the light mode fallback
- Supported by: Apple Mail, iOS Mail only
- All other clients show the `<img>` fallback (they ignore `<picture>` in email)

### CSS Show/Hide Method (Broader Support)
```html
<!-- Light mode logo (shown by default, hidden in dark mode) -->
<img src="https://example.com/logo-light.png" alt="Company Logo" class="light-img" width="200" height="50" style="display: block; border: 0;">

<!-- Dark mode logo (hidden by default, shown in dark mode) -->
<img src="https://example.com/logo-dark.png" alt="" class="dark-img" width="200" height="50" style="display: none; mso-hide: all; overflow: hidden; max-height: 0;">
```

```css
@media (prefers-color-scheme: dark) {
  .light-img { display: none !important; max-height: 0 !important; overflow: hidden !important; }
  .dark-img { display: block !important; max-height: none !important; overflow: visible !important; }
}
```
- Works in any client that supports `@media (prefers-color-scheme: dark)` and embedded `<style>`
- The dark mode image is hidden by default using `display: none; max-height: 0; overflow: hidden;`
- `mso-hide: all` hides it from Outlook desktop rendering
- `alt=""` on the hidden image to prevent screen reader announcement of the duplicate

### Transparent PNG Method (No Code Swap Needed)
- Use logos and icons with transparent backgrounds (PNG-24 or SVG)
- Transparent logos naturally adapt to any background color — light or dark
- No CSS or image swap needed — the simplest dark mode image approach
- Limitation: only works for images that don't have their own background (logos, icons, illustrations)

### Image Opacity/Brightness Reduction
```css
@media (prefers-color-scheme: dark) {
  img { opacity: 0.9; }
  .hero-img { filter: brightness(0.85); }
}
```
- Slightly dims images in dark mode to reduce visual harshness against dark backgrounds
- `opacity: 0.9` — subtle reduction; prevents bright images from being jarring
- `filter: brightness(0.85)` — more control; reduces perceived brightness
- Limited client support (Apple Mail, iOS Mail, Thunderbird)

---

## 6. Outlook Desktop (Windows) Dark Mode — The Forced Override Engine

Outlook desktop is the most aggressive dark mode renderer. It ignores `@media (prefers-color-scheme: dark)`, ignores `<meta name="color-scheme">`, and forcibly rewrites your colors using its Word rendering engine.

### How Outlook Desktop Dark Mode Modifies the DOM
- Scans every element's `color`, `background-color`, and `bgcolor` values
- Categorizes each color as "light" or "dark" based on luminance
- Inverts light backgrounds to dark (e.g., `#ffffff` → `#1e1e1e` or similar)
- Inverts dark text to light (e.g., `#333333` → `#d4d4d4` or similar)
- Leaves "already dark" backgrounds alone (below a luminance threshold)
- Leaves "already light" text alone (above a luminance threshold)
- May or may not invert mid-range colors — behavior is unpredictable
- Modifies `<img>` rendering: may add a white outline/glow to images with transparent backgrounds
- Ignores VML fill colors (VML backgrounds may become invisible against the inverted background)

### Outlook Desktop Dark Mode Versions
- **Outlook 2019+** and **Microsoft 365** — have dark mode built in
- **Outlook 2016** — no native dark mode (some users use Windows dark mode which affects chrome but not email body)
- **Outlook 2013 and earlier** — no dark mode
- The "new Outlook" for Windows (based on web engine) — different dark mode behavior from classic Outlook desktop; more similar to Outlook.com

### Three Outlook Desktop Dark Mode Rendering Behaviors
1. **No background change** — Outlook keeps your background colors but inverts text colors to maintain contrast
2. **Full background inversion** — Outlook inverts both background and text colors
3. **Partial inversion** — Outlook inverts only certain elements based on its luminance analysis

The user's Outlook dark mode setting determines which behavior applies, and email developers cannot control which mode the recipient uses.

---

## 7. The 1x1 Pixel Background Color Trick (Outlook Dark Mode Prevention)

This is the technique you referenced. It exploits Outlook's dark mode rendering engine behavior.

### How It Works
Outlook's dark mode engine analyzes the `bgcolor` attribute and `background-color` CSS on `<td>` and `<table>` elements to decide whether to invert them. However, when Outlook encounters certain color signals — specifically a small (1x1 pixel) background image or specific color attribute patterns — it may skip inversion on that element.

### The 1x1 Pixel Transparent/Colored GIF Technique
```html
<td style="background-color: #ffffff; background-image: url('https://example.com/1x1-white.gif'); background-repeat: repeat;">
  <!-- Content -->
</td>
```
- A 1x1 pixel GIF (transparent or matching the background color) is set as `background-image`
- Outlook's dark mode engine sees the `background-image` property and may choose NOT to override the `background-color`
- The theory: Outlook's Word engine treats elements with background images differently from those with just background colors — it avoids inverting the background color when a background image is present, to avoid color-clashing with the image
- The 1x1 pixel is invisible to the user but signals to Outlook's rendering engine that this element has "intentional" styling

### Implementation Patterns

#### On `<body>`
```html
<body style="margin: 0; padding: 0; background-color: #ffffff; background-image: url('https://example.com/1x1.gif'); background-repeat: repeat;">
```

#### On Wrapper `<table>`
```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; background-image: url('https://example.com/1x1.gif'); background-repeat: repeat;">
```

#### On Content `<td>` Cells
```html
<td style="background-color: #1a73e8; background-image: url('https://example.com/1x1-blue.gif'); background-repeat: repeat; padding: 20px;">
  <a href="..." style="color: #ffffff; text-decoration: none; font-size: 16px; font-weight: bold;">Shop Now</a>
</td>
```

#### Transparent 1x1 GIF (Universal)
```html
<!-- Base64-encoded 1x1 transparent GIF to avoid external image dependency -->
<td style="background-color: #ffffff; background-image: url(data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7); background-repeat: repeat;">
```

### Color-Matched 1x1 Pixel Variants
- **1x1 white GIF** — for white/light backgrounds you want to preserve
- **1x1 colored GIF** — matching the exact background color of the cell (e.g., blue 1x1 for a blue button background)
- **1x1 transparent GIF** — universal fallback; the background-color remains the visible color
- **Base64-encoded inline** — avoids external image hosting; data URI embedded directly in the `style` attribute

### Limitations of the 1x1 Pixel Trick
- NOT universally reliable — Outlook's dark mode behavior changes between versions and updates
- Microsoft has been known to change the rendering engine behavior, which can break this technique
- Some Outlook builds may ignore the background-image signal entirely
- The base64 data URI approach may not work in all Outlook versions (some strip data URIs)
- Externally hosted 1x1 images require the image to load; if images are blocked, the trick fails
- This trick preserves the BACKGROUND but doesn't prevent Outlook from inverting the TEXT color — you may end up with white text on a white background

### When to Use the 1x1 Pixel Trick
- On colored CTA button `<td>` cells — preserves the button background color in dark mode
- On branded header/banner background colors — preserves brand colors
- On the email wrapper `<table>` — preserves the white (or custom) email body background
- On any element where forced inversion would destroy the design intent

---

## 8. Other Outlook Dark Mode Prevention Techniques

### `[owa]` and `[data-ogsb]` / `[data-ogsc]` — Outlook.com Dark Mode Selectors

Outlook.com (webmail) adds `data-ogsb` (background) and `data-ogsc` (color) attributes to elements when dark mode is active. You can target these in CSS to override Outlook.com's forced inversions.

```css
/* Outlook.com dark mode overrides */
[data-ogsc] .text-color {
  color: #ffffff !important;
}

[data-ogsb] .bg-color {
  background-color: #1a1a1a !important;
}

[data-ogsc] .heading-color {
  color: #f0f0f0 !important;
}

[data-ogsb] .button-bg {
  background-color: #4a9eff !important;
}

[data-ogsc] .button-text {
  color: #ffffff !important;
}

[data-ogsb] .card-bg {
  background-color: #2d2d2d !important;
}

[data-ogsc] .link-color {
  color: #6ab7ff !important;
}

[data-ogsb] .footer-bg {
  background-color: #0d0d0d !important;
}

[data-ogsc] .footer-text {
  color: #999999 !important;
}
```

#### How `[data-ogsc]` and `[data-ogsb]` Work
- Outlook.com's dark mode engine adds `data-ogsc` to the wrapper when it overrides foreground/text colors
- Outlook.com adds `data-ogsb` to the wrapper when it overrides background colors
- These selectors ONLY work in Outlook.com webmail — they do NOT work in Outlook desktop (Windows)
- They are attribute selectors, not class selectors — they target the injected `data-*` attributes
- They must be in the `<style>` block in `<head>` (Outlook.com preserves `<style>` blocks, unlike Gmail)

### `[data-outlook-cycle]` — Outlook Mobile Dark Mode
```css
[data-outlook-cycle] .dark-override {
  background-color: #1a1a1a !important;
  color: #ffffff !important;
}
```
- Outlook iOS and Android apps may inject this attribute in dark mode
- Limited and inconsistent support — test thoroughly

### `.darkmode` Class Targeting
Some email clients inject a `.darkmode` class on the `<body>` or a wrapper element when dark mode is active.

```css
.darkmode .text-color { color: #ffffff !important; }
.darkmode .bg-color { background-color: #1a1a1a !important; }
```
- Client support varies — not standardized
- Test in specific clients to verify

---

## 9. Outlook Desktop Dark Mode — `<style>` Block Approach (Limited)

Outlook desktop (Windows) does NOT support `@media (prefers-color-scheme: dark)`. However, there is an MSO conditional approach using specific Outlook-targeted styles.

### MSO Conditional Dark Mode Attempt
```html
<!--[if mso]>
<style type="text/css">
  /* These styles are always applied in Outlook desktop — not dark-mode-specific */
  /* But you can set colors that look acceptable in BOTH light and dark mode */
  .mso-safe-text { color: #333333; }
  .mso-safe-bg { background-color: #f5f5f5; }
</style>
<![endif]-->
```

**Important limitation:** MSO conditional comments cannot detect whether Outlook is in dark mode or light mode. You cannot conditionally apply styles based on Outlook's dark mode state. The only approach is to choose colors that work reasonably in both modes.

### Mid-Range Color Strategy for Outlook Desktop
Since you cannot detect Outlook dark mode, choose colors that survive inversion gracefully:
- Avoid pure white (`#ffffff`) backgrounds — Outlook inverts to near-black; use `#f5f5f5` or `#fafafa` instead (sometimes not inverted, or inverted to a slightly lighter dark)
- Avoid pure black (`#000000`) text — Outlook inverts to near-white; use `#333333` or `#222222` instead
- Mid-range gray backgrounds (`#666666` to `#999999`) are in the "unpredictable zone" — Outlook may or may not invert them
- Saturated brand colors (bright blue, red, green) may or may not be inverted — depends on luminance
- Generally: high-luminance colors (light) get inverted; low-luminance colors (dark) are left alone

---

## 10. Element-Level Dark Mode Prevention Attributes

### `background` HTML Attribute (Not Just `bgcolor`)
```html
<table background="https://example.com/1x1.gif" bgcolor="#ffffff" style="background-color: #ffffff;">
```
- The `background` HTML attribute on `<table>` and `<td>` signals a background image
- Combined with `bgcolor` and `background-color` CSS, this triple-declaration approach gives the strongest signal to dark mode engines that the background is intentional
- Some dark mode engines skip inversion when `background` (image) attribute is present

### `bgcolor` vs `background-color` in Dark Mode
```html
<!-- bgcolor HTML attribute -->
<td bgcolor="#1a73e8">

<!-- background-color CSS -->
<td style="background-color: #1a73e8;">

<!-- Both (belt-and-suspenders for dark mode) -->
<td bgcolor="#1a73e8" style="background-color: #1a73e8;">
```
- Some dark mode engines only modify `background-color` CSS but leave `bgcolor` attribute alone
- Some engines modify `bgcolor` but not `background-color`
- Using BOTH gives the best coverage but can also mean dark mode fails to invert when it should
- In Outlook desktop: both are typically modified by the forced inversion engine

### Inline `color` vs Class-Based `color`
```html
<!-- Inline (dark mode engines directly modify this) -->
<td style="color: #333333;">

<!-- Class-based (can be overridden by @media prefers-color-scheme) -->
<td class="text-dark" style="color: #333333;">
```
- Dark mode engines rewrite inline `style="color: ..."` values directly in the DOM
- Class-based overrides via `@media (prefers-color-scheme: dark)` only work in clients that support embedded `<style>`
- The inline style is what Outlook desktop modifies; the class override is what Apple Mail / iOS Mail use

---

## 11. Dark-Mode-Safe Color Selection

### Colors That Survive Forced Inversion

#### Backgrounds
- Pure white `#ffffff` — always inverted to dark; avoid if you want to preserve background
- Off-white `#f5f5f5` to `#fafafa` — sometimes inverted, sometimes not; less predictable
- Light gray `#e0e0e0` to `#eeeeee` — usually inverted
- Mid-gray `#666666` to `#999999` — unpredictable zone; may or may not invert
- Dark gray `#333333` to `#444444` — usually NOT inverted (already dark)
- Near-black `#1a1a1a` to `#222222` — never inverted (already dark)
- Pure black `#000000` — never inverted

#### Text
- Pure black `#000000` text — always inverted to light/white
- Dark gray `#333333` text — usually inverted to light gray
- Mid-gray `#666666` text — unpredictable
- Light gray `#cccccc` text — usually NOT inverted (already light)
- White `#ffffff` text — never inverted

#### Brand/Accent Colors
- High saturation + high brightness (e.g., `#ffcc00` bright yellow) — likely inverted or muted
- High saturation + medium brightness (e.g., `#1a73e8` blue) — may or may not be inverted
- High saturation + low brightness (e.g., `#0d47a1` dark blue) — usually NOT inverted
- Low saturation colors (pastels like `#e3f2fd` light blue) — likely inverted

### The "Magic" Color Values
Some email developers have discovered that certain specific color values cause Outlook to skip inversion:

- `background-color: #010101` vs `#000000` — Outlook may treat `#000000` differently from `#010101`; some reports suggest near-black values like `#010101` are more reliably left alone
- `color: #fefefe` vs `#ffffff` — similar behavior; near-white may be treated differently from pure white
- These are anecdotal and version-dependent — do not rely on them as the sole strategy

---

## 12. Dark Mode Tags on Specific Email Elements

### `<body>` Dark Mode
```html
<body style="margin: 0; padding: 0; background-color: #ffffff; background-image: url('1x1.gif'); -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
```
- Dark mode engines modify `<body>` background-color
- 1x1 pixel trick on `<body>` may prevent body background inversion in Outlook
- Apple Mail respects `@media (prefers-color-scheme: dark)` targeting `body`

### Wrapper `<table>` Dark Mode
```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" background="https://example.com/1x1.gif" style="background-color: #ffffff; background-image: url('https://example.com/1x1.gif'); background-repeat: repeat;" class="body-bg">
```
- Triple declaration: `bgcolor` attribute + `background-color` CSS + `background-image` (1x1 trick)
- Class `body-bg` for `@media (prefers-color-scheme: dark)` and `[data-ogsb]` overrides

### Content `<td>` Dark Mode
```html
<td bgcolor="#ffffff" style="background-color: #ffffff; padding: 20px;" class="content-bg">
  <p style="color: #333333; font-family: Arial, sans-serif; font-size: 16px; line-height: 1.5;" class="text-dark">
    Email content
  </p>
</td>
```
- `bgcolor` + `background-color` on every `<td>` that has a background color
- CSS class for `@media (prefers-color-scheme: dark)` override
- `color` inline style on all text elements (dark mode engines rewrite these)

### CTA Button Dark Mode
```html
<!-- Padding-based button -->
<td bgcolor="#1a73e8" background="https://example.com/1x1-blue.gif" style="background-color: #1a73e8; background-image: url('https://example.com/1x1-blue.gif'); background-repeat: repeat; border-radius: 5px; padding: 12px 40px;" class="btn-bg">
  <a href="https://example.com" style="color: #ffffff; text-decoration: none; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; display: inline-block;" class="btn-text">Shop Now</a>
</td>

<!-- VML button with dark mode consideration -->
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="https://example.com" style="height:44px;v-text-anchor:middle;width:200px;" arcsize="10%" fillcolor="#1a73e8" strokecolor="#1a73e8">
  <w:anchorlock/>
  <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">Shop Now</center>
</v:roundrect>
<![endif]-->
```
- 1x1 pixel trick on the button `<td>` to prevent Outlook from inverting the button background
- VML button `fillcolor` — Outlook dark mode MAY still override this; VML colors are not always immune
- `class="btn-bg"` and `class="btn-text"` for CSS dark mode overrides

### Image Dark Mode
```html
<!-- Standard image with dark mode considerations -->
<img src="https://example.com/product.jpg" alt="Product Name" width="600" height="300" style="display: block; border: 0; max-width: 100%; height: auto;" class="img-fluid">

<!-- Logo with dark mode swap -->
<img src="https://example.com/logo-light.png" alt="Company Logo" width="200" height="50" style="display: block; border: 0;" class="light-img">
<img src="https://example.com/logo-dark.png" alt="" width="200" height="50" style="display: none; mso-hide: all; max-height: 0; overflow: hidden;" class="dark-img">
```

```css
@media (prefers-color-scheme: dark) {
  .light-img { display: none !important; max-height: 0 !important; overflow: hidden !important; }
  .dark-img { display: block !important; max-height: none !important; overflow: visible !important; }
  .img-fluid { opacity: 0.9 !important; }
}
```

### Divider/Border Dark Mode
```html
<td style="border-top: 1px solid #e0e0e0; font-size: 1px; line-height: 1px; mso-line-height-rule: exactly;" class="divider">&nbsp;</td>
```

```css
@media (prefers-color-scheme: dark) {
  .divider { border-color: #444444 !important; }
}

[data-ogsc] .divider { border-color: #444444 !important; }
```

### Link Dark Mode
```html
<a href="https://example.com" style="color: #1a73e8; text-decoration: underline;" class="link-color">Link text</a>
```

```css
@media (prefers-color-scheme: dark) {
  .link-color { color: #6ab7ff !important; }
}

[data-ogsc] .link-color { color: #6ab7ff !important; }
```
- Links often need lighter/brighter colors in dark mode for contrast
- Outlook desktop may or may not invert link colors — test both states

### Heading Dark Mode
```html
<h1 style="color: #1a1a1a; font-family: Arial, sans-serif; font-size: 28px; line-height: 1.2; margin: 0;" class="heading-color">Email Title</h1>
```

```css
@media (prefers-color-scheme: dark) {
  .heading-color { color: #ffffff !important; }
}

[data-ogsc] .heading-color { color: #ffffff !important; }
```

---

## 13. Gmail Dark Mode Behavior

Gmail's dark mode is different from both Apple Mail and Outlook.

### Gmail Web (Desktop Browser)
- Strips `<style>` blocks in some contexts (clipped emails, forwarded emails)
- When it does parse `<style>`, it prefixes all class names with a unique string
- Does NOT support `@media (prefers-color-scheme: dark)`
- Uses its own forced inversion algorithm
- Targets: `background-color`, `bgcolor`, `color` inline styles
- Behavior: inverts light backgrounds to dark; inverts dark text to light; may leave colored elements alone
- No developer control — you cannot override Gmail's forced inversion via CSS

### Gmail Android App
- More aggressive forced inversion than web
- Strips `<style>` blocks
- Auto-inverts colors based on luminance
- NO support for `@media (prefers-color-scheme: dark)` or any dark mode CSS
- The 1x1 pixel trick does NOT work in Gmail Android
- Only approach: choose colors that survive forced inversion gracefully

### Gmail iOS App
- Similar to Android but occasionally less aggressive
- Also strips `<style>` blocks
- No dark mode CSS support
- Forced inversion only

### Gmail Dark Mode Strategy
Since Gmail ignores all dark mode CSS, the only approach is defensive:
- Avoid pure `#ffffff` backgrounds — use `#f5f5f5` or slightly off-white
- Avoid pure `#000000` text — use `#333333`
- Use mid-to-dark saturated brand colors that look acceptable whether inverted or not
- Test with Gmail dark mode and accept that you cannot control the output
- Ensure all text meets contrast ratios against BOTH the light mode and the inverted dark mode background

---

## 14. Apple Mail / iOS Mail Dark Mode Behavior

Apple Mail has the best developer control for dark mode.

### Apple Mail Detection and Override
```html
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">

<style>
  :root { color-scheme: light dark; }
  
  @media (prefers-color-scheme: dark) {
    /* Full custom dark mode styles */
  }
</style>
```

### Apple Mail Auto-Inversion Rules
- If `color-scheme: light dark` is declared AND `@media (prefers-color-scheme: dark)` styles are present: Apple Mail uses YOUR dark mode styles (no auto-inversion)
- If `color-scheme: light dark` is declared but NO dark mode CSS is present: Apple Mail applies partial auto-inversion (changes light backgrounds to dark, adjusts text)
- If NO `color-scheme` meta is present: Apple Mail applies its own full auto-inversion
- If `color-scheme: light only` is declared: Apple Mail attempts to render the email in light mode regardless of system setting (may still partially invert in some versions)

### Apple Mail `<picture>` Dark Mode Image Swap
```html
<picture>
  <source srcset="dark-logo.png" media="(prefers-color-scheme: dark)">
  <img src="light-logo.png" alt="Logo" style="display: block; border: 0;">
</picture>
```
- Apple Mail only — the only email client that supports `<picture>` with `<source media="(prefers-color-scheme: dark)">`

### Apple Mail Transparent Image Behavior
- In dark mode, Apple Mail may add a subtle white background/glow behind images with transparency
- This can make transparent PNGs look odd on dark backgrounds
- Workaround: use images with very slight dark edges or a subtle shadow baked into the image file

---

## 15. Samsung Mail Dark Mode

### Samsung Mail (Android 9+)
- Supports `@media (prefers-color-scheme: dark)` — one of the few Android email clients that does
- Samsung's dark mode engine applies BOTH your custom dark styles AND its own partial inversion
- This can cause double-inversion issues (your dark style + Samsung's inversion = unexpected results)
- Workaround: use `!important` on all dark mode declarations and test specifically in Samsung Mail

---

## 16. Complete Dark Mode CSS Template

```css
/* === EMBEDDED IN <head> <style> BLOCK === */

/* Root declaration */
:root {
  color-scheme: light dark;
}

/* Outlook.com dark mode overrides */
[data-ogsc] .dm-text-primary { color: #f0f0f0 !important; }
[data-ogsc] .dm-text-secondary { color: #cccccc !important; }
[data-ogsc] .dm-text-muted { color: #999999 !important; }
[data-ogsc] .dm-heading { color: #ffffff !important; }
[data-ogsc] .dm-link { color: #6ab7ff !important; }
[data-ogsc] .dm-btn-text { color: #ffffff !important; }

[data-ogsb] .dm-body-bg { background-color: #121212 !important; }
[data-ogsb] .dm-content-bg { background-color: #1e1e1e !important; }
[data-ogsb] .dm-card-bg { background-color: #2d2d2d !important; }
[data-ogsb] .dm-header-bg { background-color: #1a1a1a !important; }
[data-ogsb] .dm-footer-bg { background-color: #0d0d0d !important; }
[data-ogsb] .dm-btn-bg { background-color: #4a9eff !important; }

[data-ogsc] .dm-divider { border-color: #444444 !important; }

/* Apple Mail / iOS Mail / Thunderbird / Samsung dark mode */
@media (prefers-color-scheme: dark) {
  /* Backgrounds */
  .dm-body-bg { background-color: #121212 !important; }
  .dm-content-bg { background-color: #1e1e1e !important; }
  .dm-card-bg { background-color: #2d2d2d !important; }
  .dm-header-bg { background-color: #1a1a1a !important; }
  .dm-footer-bg { background-color: #0d0d0d !important; }
  .dm-btn-bg { background-color: #4a9eff !important; }
  
  /* Text */
  .dm-text-primary { color: #f0f0f0 !important; }
  .dm-text-secondary { color: #cccccc !important; }
  .dm-text-muted { color: #999999 !important; }
  .dm-heading { color: #ffffff !important; }
  .dm-link { color: #6ab7ff !important; }
  .dm-btn-text { color: #ffffff !important; }
  
  /* Borders */
  .dm-divider { border-color: #444444 !important; }
  .dm-card-border { border-color: #555555 !important; }
  
  /* Image swap */
  .dm-light-img { display: none !important; max-height: 0 !important; overflow: hidden !important; }
  .dm-dark-img { display: block !important; max-height: none !important; overflow: visible !important; width: auto !important; }
  
  /* Image dimming */
  .dm-img-dim { opacity: 0.9 !important; }
}
```

---

## 17. Dark Mode Class Application on HTML Elements

### Full Element Example with Dark Mode Classes
```html
<body style="margin: 0; padding: 0; background-color: #ffffff;" class="dm-body-bg">

  <!-- Outer wrapper -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" background="https://example.com/1x1.gif" style="background-color: #ffffff; background-image: url('https://example.com/1x1.gif'); background-repeat: repeat;" class="dm-body-bg">
    <tr>
      <td align="center" valign="top">

        <!-- Inner container -->
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center" bgcolor="#ffffff" style="background-color: #ffffff;" class="dm-content-bg">

          <!-- Header -->
          <tr>
            <td bgcolor="#1a1a1a" style="background-color: #1a1a1a; padding: 20px; text-align: center;" class="dm-header-bg">
              <!-- Dark header: already dark, less likely to be inverted -->
              <img src="logo-white.png" alt="Company" width="150" height="40" style="display: block; border: 0; margin: 0 auto;" class="dm-light-img">
              <img src="logo-dark-bg.png" alt="" width="150" height="40" style="display: none; mso-hide: all; max-height: 0; overflow: hidden; margin: 0 auto;" class="dm-dark-img">
            </td>
          </tr>

          <!-- Hero -->
          <tr>
            <td bgcolor="#ffffff" style="background-color: #ffffff; padding: 40px 20px;" class="dm-content-bg">
              <h1 style="color: #1a1a1a; font-family: Arial, sans-serif; font-size: 28px; line-height: 1.2; margin: 0;" class="dm-heading">Big Announcement</h1>
              <p style="color: #555555; font-family: Arial, sans-serif; font-size: 16px; line-height: 1.5; margin: 16px 0 0 0;" class="dm-text-secondary">Supporting text here.</p>
            </td>
          </tr>

          <!-- CTA Button -->
          <tr>
            <td style="padding: 0 20px 40px 20px;" bgcolor="#ffffff" class="dm-content-bg">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
                <tr>
                  <td bgcolor="#1a73e8" background="https://example.com/1x1-blue.gif" style="background-color: #1a73e8; background-image: url('https://example.com/1x1-blue.gif'); background-repeat: repeat; border-radius: 5px; padding: 14px 40px;" class="dm-btn-bg">
                    <a href="https://example.com" style="color: #ffffff; text-decoration: none; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; display: inline-block;" class="dm-btn-text">Shop Now</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="border-top: 1px solid #e0e0e0; font-size: 1px; line-height: 1px; mso-line-height-rule: exactly;" class="dm-divider">&nbsp;</td>
          </tr>

          <!-- Footer -->
          <tr>
            <td bgcolor="#f5f5f5" style="background-color: #f5f5f5; padding: 20px; text-align: center;" class="dm-footer-bg">
              <p style="color: #999999; font-family: Arial, sans-serif; font-size: 12px; line-height: 1.5; margin: 0;" class="dm-text-muted">
                <a href="https://example.com/unsubscribe" style="color: #999999; text-decoration: underline;" class="dm-text-muted">Unsubscribe</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
```

---

## 18. Summary: Dark Mode Tags by Email Client

### Apple Mail / iOS Mail
- `<meta name="color-scheme" content="light dark">` ✅ Parsed
- `<meta name="supported-color-schemes" content="light dark">` ✅ Parsed
- `color-scheme: light dark` CSS property ✅ Parsed
- `@media (prefers-color-scheme: dark)` ✅ Full support
- `<picture><source media="(prefers-color-scheme: dark)">` ✅ Supported
- CSS show/hide image swap ✅ Supported
- `color-scheme: light only` (prevent dark mode) ✅ Works

### Outlook.com (Webmail)
- `<meta name="color-scheme">` ❌ Ignored
- `@media (prefers-color-scheme: dark)` ❌ Ignored
- `[data-ogsc]` foreground color targeting ✅ Supported
- `[data-ogsb]` background color targeting ✅ Supported
- `span.MsoHyperlink` color override ✅ Supported
- Forced color inversion ✅ Active (overridable via `[data-ogsc]`/`[data-ogsb]`)

### Outlook Desktop (Windows)
- `<meta name="color-scheme">` ❌ Ignored
- `@media (prefers-color-scheme: dark)` ❌ Ignored
- `[data-ogsc]` / `[data-ogsb]` ❌ Not applicable (not webmail)
- MSO conditional styles ⚠️ Cannot detect dark mode state
- VML `fillcolor` ⚠️ May or may not be inverted
- 1x1 pixel background trick ⚠️ May prevent background inversion (version-dependent)
- `bgcolor` HTML attribute ⚠️ Usually inverted
- `background-color` CSS ⚠️ Usually inverted
- `color` CSS ⚠️ Usually inverted
- Forced color inversion ✅ Active (cannot be overridden by developer)

### Gmail (All Versions)
- `<meta name="color-scheme">` ❌ Stripped
- `@media (prefers-color-scheme: dark)` ❌ Stripped with `<style>` block
- `[data-ogsc]` / `[data-ogsb]` ❌ Not applicable
- 1x1 pixel trick ❌ Does not prevent inversion
- Forced color inversion ✅ Active (cannot be overridden by developer)
- Only approach: defensive color choices

### Samsung Mail (Android 9+)
- `@media (prefers-color-scheme: dark)` ✅ Supported (but may double-invert)
- Forced partial inversion ✅ Also active alongside your CSS

### Thunderbird
- `@media (prefers-color-scheme: dark)` ✅ Full support
- `color-scheme` CSS property ✅ Supported

### Yahoo Mail / AOL Mail
- `@media (prefers-color-scheme: dark)` ⚠️ Limited/inconsistent
- May apply own forced inversion

---

*Total dark mode-specific tags, selectors, attributes, properties, techniques, and patterns: 200+*
