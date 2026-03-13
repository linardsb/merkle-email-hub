# HTML Email Image Optimization — Complete DOM Tag Reference

Every tag, attribute, inline style, rendering behavior, fallback technique, and client-specific quirk that affects how images are optimized, loaded, rendered, and displayed in HTML email.

---

## 1. `<img>` Tag — Core Image Element

### Required Attributes for Email Images

#### `src` — Image Source URL (Mandatory)
```html
<img src="https://images.example.com/hero-banner.jpg">
```
- **Must be an absolute URL** — relative paths (`/images/hero.jpg`) don't work in email; email has no base URL context
- **Must use HTTPS** — HTTP image URLs may be blocked by email clients; Gmail, Outlook.com, and Apple Mail increasingly require HTTPS for image loading
- **Must resolve to a live image** — dead URLs result in broken image icons; unlike the web, email images cannot be updated after send (the URL is permanent)
- **Must point to a proper image file** — served with correct `Content-Type` header (`image/jpeg`, `image/png`, `image/gif`)
- **Must not be empty** (`src=""`) — empty `src` causes some clients to make a request to the email's base URL or display an error
- **Must not contain spaces** — spaces in URLs must be encoded as `%20`
- **Must not use `data:` URIs for large images** — Base64-encoded inline images bloat the HTML size; some clients (Gmail) strip large `data:` URIs; acceptable only for tiny images under 2–3KB (e.g., a single-color 1x1 pixel)
- **Domain should match or relate to sender domain** — images from unrelated domains may be flagged by spam filters or blocked by corporate firewalls
- **CDN-hosted recommended** — images on a CDN (Cloudinary, AWS CloudFront, Imgix, ESP image hosting) load faster globally than images on a single-origin server
- **URL must be stable** — once the email is sent, the image URL must remain live permanently; changing or removing the hosted image breaks all previously sent emails

#### `alt` — Alternative Text (Mandatory for Optimization)
```html
<img src="hero.jpg" alt="Winter Sale — 50% off all coats. Shop now.">
```
- **Must be present on every `<img>` tag** — no exceptions; even decorative images need `alt=""`
- **Image-off rendering:** many corporate email clients (Outlook, especially in enterprise environments) block images by default; `alt` text is the ONLY visible content when images are off
- **Alt text IS the content** when images are blocked — it must convey the full message, not just describe the image
- **Product images:** `alt="Blue cotton t-shirt — $29.99"` not just `alt="product photo"`
- **CTA image buttons:** `alt="Shop the sale"` not `alt="button"`
- **Hero/banner images:** `alt="Spring Collection Launch — Free shipping on orders over $50 — Shop now"` — include any text baked into the image
- **Decorative images:** `alt=""` (empty, not missing) — spacers, dividers, decorative borders
- **Tracking pixel:** `alt=""` — must be empty; tracking pixels should be invisible
- **Logo images:** `alt="Company Name"` or `alt="Company Name — visit website"` if linked
- **Social icons:** `alt="Follow us on Instagram"` not `alt="Instagram icon"`
- **Spam filter scanning:** `alt` text is scanned for spam keywords; don't keyword-stuff alt text
- **Character limit:** no technical limit, but keep under ~125 characters for screen reader usability; longer descriptions may be truncated or cause layout issues when displayed as text

#### `width` — Display Width (Mandatory in Email)
```html
<img src="hero.jpg" alt="Sale" width="600">
```
- **Must be set as an HTML attribute** (not just CSS) — Outlook desktop requires the HTML `width` attribute to size images correctly; Outlook ignores CSS `width` on `<img>` in many contexts
- **Value is a number without units** — `width="600"` not `width="600px"`; the HTML attribute expects a plain integer
- **Prevents layout collapse** — without `width`, email clients may render the image at its natural pixel dimensions, breaking the layout; if the image fails to load, the container collapses to 0 width
- **Controls retina display** — a 1200px-wide image with `width="600"` displays at 600px but uses the extra pixels for retina sharpness
- **Must match the intended display width** — not the natural image file dimensions (unless they're the same)
- **Responsive images:** set `width` to the desktop display width; use CSS `max-width: 100%` in the `<style>` block to scale down on mobile

#### `height` — Display Height (Mandatory in Email)
```html
<img src="hero.jpg" alt="Sale" width="600" height="300">
```
- **Must be set as an HTML attribute** — same reason as `width`; Outlook requires it
- **Prevents layout jump/collapse** — reserves vertical space while the image loads; without it, the email layout reflows when the image appears, causing visual instability
- **Value is a number without units** — `height="300"` not `height="300px"`
- **Must match the expected display height** — if the image is 1200×600 retina and displayed at 600×300, use `height="300"`
- **Interaction with responsive scaling:** when the image scales down on mobile via `max-width: 100%`, the height must auto-adjust; set `height="auto"` in the CSS but keep the HTML `height` attribute for the desktop/Outlook rendering

#### `border` — Image Border (Mandatory in Email)
```html
<img src="hero.jpg" alt="Sale" width="600" height="300" border="0">
```
- **Must be set to `"0"`** — older email clients and some Outlook versions add a visible blue border around linked images; `border="0"` removes it
- **HTML attribute, not CSS** — while `style="border: 0;"` also works, the HTML attribute provides maximum backward compatibility
- **Must be on every `<img>` tag** — not just linked images; some clients add borders to all images

#### `style` — Inline CSS (Mandatory in Email)
```html
<img src="hero.jpg" alt="Sale" width="600" height="300" border="0" style="display: block; border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic;">
```
Required inline style properties for every email image:

- **`display: block`** — removes the phantom 2–4px gap that appears below images in email clients; this gap is caused by the inline rendering context treating the image as inline text with a descender line; `display: block` eliminates it
- **`border: 0`** — CSS reinforcement of the HTML `border="0"` attribute
- **`outline: none`** — prevents a focus outline/border from appearing around linked images when clicked or focused
- **`text-decoration: none`** — prevents underline from appearing under/around linked images (inherited from the parent `<a>` tag)
- **`-ms-interpolation-mode: bicubic`** — forces Outlook desktop to use smooth bicubic interpolation when scaling images; without it, Outlook uses nearest-neighbor scaling which makes resized images pixelated
- **`line-height: 0`** (optional) — additional gap prevention; set on images that still show gaps after `display: block` in some clients
- **`font-size: 0`** (optional, on the parent `<td>`) — further gap prevention in some clients; the gap is related to font-size inheritance on the inline image context

### Optional Image Attributes

#### `class` — CSS Class for Responsive/Dark Mode
```html
<img src="hero.jpg" class="img-fluid dm-img-dim light-img" style="display: block; border: 0; ...">
```
- **`img-fluid`** — for responsive sizing via `<style>` block:
  ```css
  @media only screen and (max-width: 600px) {
    .img-fluid { width: 100% !important; height: auto !important; }
  }
  ```
- **`dm-img-dim`** — for dark mode image dimming:
  ```css
  @media (prefers-color-scheme: dark) {
    .dm-img-dim { opacity: 0.9 !important; }
  }
  ```
- **`light-img` / `dark-img`** — for dark mode image swapping (see Section 9)
- **Gmail strips/renames classes** — inline styles are the baseline; classes are progressive enhancement

#### `loading` — Lazy Loading
```html
<img src="hero.jpg" loading="lazy">
```
- **NOT supported by email clients** — the `loading` attribute is a web browser feature; email client rendering engines ignore it
- **Do not rely on `loading="lazy"` in email** — all email images load immediately (or not at all, if images are blocked)
- **Including it is harmless** — clients that don't understand it simply ignore it

#### `srcset` — Responsive Image Sources
```html
<img src="hero-600.jpg" srcset="hero-1200.jpg 2x, hero-600.jpg 1x">
```
- **NOT supported by most email clients** — `srcset` is a web standard; only Apple Mail and iOS Mail support it
- **Do not rely on `srcset` for email image optimization** — use the retina technique (serve 2x image, constrain with `width` attribute) instead
- **Harmless to include** — non-supporting clients fall back to `src`

#### `decoding` — Image Decoding Hint
```html
<img src="hero.jpg" decoding="async">
```
- **NOT supported by email clients** — web browser feature; email clients ignore it
- **No effect in email** — harmless to include but provides no optimization benefit

#### `fetchpriority` — Fetch Priority Hint
```html
<img src="hero.jpg" fetchpriority="high">
```
- **NOT supported by email clients** — web browser resource prioritization hint; email clients ignore it

---

## 2. Styled `alt` Text — Image-Off Optimization

When images are blocked (common default in Outlook enterprise, many corporate environments), the `alt` text renders visually. Email allows you to STYLE this alt text — a technique unique to email.

### Alt Text Styling Properties
```html
<img src="hero.jpg"
     alt="Winter Sale — 50% off"
     width="600" height="300" border="0"
     style="display: block; border: 0;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 24px;
            font-weight: bold;
            color: #1a73e8;
            line-height: 1.4;
            text-align: center;
            background-color: #f0f4ff;">
```

#### `font-family` on `<img>`
- Sets the font for the alt text when the image is not displayed
- **Use web-safe fonts** — Arial, Helvetica, Georgia, Verdana, Tahoma
- **Must be inline** — alt text styling cannot come from a `<style>` block
- **Client support:** Outlook desktop, Apple Mail, iOS Mail, Thunderbird, Yahoo — YES; Gmail — partial (may not display all alt text styles)

#### `font-size` on `<img>`
- Controls the size of the alt text
- **Match the visual importance** — hero image alt text should be larger (20–28px); product image alt text can be smaller (14–16px)
- **Don't use `font-size: 0`** — that hides the alt text entirely (defeats the purpose)

#### `font-weight` on `<img>`
- `font-weight: bold` makes alt text stand out
- Use for CTA image buttons and hero text
- `font-weight: normal` for regular content images

#### `color` on `<img>`
- Sets the alt text color
- **Use brand colors** — alt text is a branding opportunity when images are off
- **Must meet contrast requirements** — 4.5:1 against the `background-color`
- **Dark mode consideration:** dark mode may invert the `color` value; choose colors that survive inversion

#### `background-color` on `<img>`
- Sets the background behind the alt text
- **Fills the image placeholder space** — instead of a blank white box, show a branded background color
- **Creates a visual block** — even without the image, the colored rectangle with styled text maintains the email's visual structure
- **Match or complement the image's dominant color** — so the layout doesn't visually break when images load

#### `text-align` on `<img>`
- Centers or aligns the alt text within the image placeholder
- `text-align: center` for hero images and CTA buttons
- `text-align: left` for content images

#### `line-height` on `<img>`
- Controls the spacing of multi-line alt text
- Set to `1.3`–`1.5` for readability
- Without `line-height`, multi-line alt text may be cramped or excessively spaced depending on the client

#### `padding` on `<img>` (Limited Support)
- Some clients allow padding on `<img>` to give the alt text breathing room
- **Inconsistent support** — Outlook respects it; Gmail may not
- **Alternative:** add padding to the parent `<td>` instead

### Alt Text Best Practices for Image-Off Optimization
- Write alt text as if it's the only content the recipient will see (because it may be)
- Include key information: product names, prices, discount percentages, CTA text
- For hero images with text overlay: the alt text should contain the overlay text verbatim
- For image-only CTAs: alt text IS the call-to-action
- Keep alt text under 125 characters per image for screen reader usability
- Don't duplicate surrounding text content — if the heading above says "Winter Sale", the image alt doesn't need to repeat it
- Test every email with images off to verify the email is fully functional

---

## 3. Image Container `<td>` Optimization

The `<td>` wrapping an image needs specific attributes and styles to prevent rendering issues.

### Container `<td>` Required Styles
```html
<td align="center" valign="top" style="padding: 0; margin: 0; line-height: 0; font-size: 0; mso-line-height-rule: exactly;">
  <img src="hero.jpg" alt="Sale" width="600" height="300" border="0" style="display: block; border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic;">
</td>
```

#### `line-height: 0` on `<td>`
- Eliminates the extra space below the image caused by the inline formatting context
- Some email clients add space below images based on the parent `<td>`'s line-height value
- `line-height: 0` collapses this space to zero
- Works in conjunction with `display: block` on the `<img>`

#### `font-size: 0` on `<td>`
- Further prevents the ghost space below images
- The space is related to font descender height; setting `font-size: 0` removes it
- **Must be reset on any text elements within the same `<td>`** — if you have text alongside the image, `font-size: 0` on the `<td>` will hide that text; only use on image-only cells

#### `mso-line-height-rule: exactly` on `<td>`
- Forces Outlook desktop to use the exact line-height value (in this case `0`) instead of its default "at-least" rule
- Without this, Outlook may add extra vertical space even with `line-height: 0`
- **Outlook-only MSO property** — ignored by all other clients

#### `padding: 0` on `<td>`
- Removes any default cell padding that could create unwanted space around the image
- Must be inline; client defaults vary

#### `margin: 0` on `<td>`
- Removes any default margin
- Outlook may add margins to `<td>` elements

#### `align="center"` on `<td>`
- Centers the image horizontally within the cell
- HTML attribute for maximum email client compatibility
- Use `align="left"` for left-aligned images

#### `valign="top"` on `<td>`
- Vertically aligns the image to the top of the cell
- Prevents vertical centering that can create unexpected space in cells taller than the image
- HTML attribute; more reliable than CSS `vertical-align` in Outlook

#### `bgcolor` on `<td>` (Image Fallback Background)
```html
<td bgcolor="#1a73e8" style="background-color: #1a73e8;">
  <img src="blue-banner.jpg" alt="Sale banner" ...>
</td>
```
- Sets a fallback background color visible when the image is off
- **Should approximate the image's dominant color** — so the layout doesn't show jarring white boxes when images are blocked
- Both `bgcolor` attribute and `background-color` CSS for maximum client coverage

---

## 4. Responsive Image Optimization

### CSS Fluid Image Scaling
```css
/* In the <style> block in <head> */
@media only screen and (max-width: 600px) {
  .img-fluid {
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
  }
}
```
```html
<img src="hero.jpg" alt="Sale" width="600" height="300" border="0" class="img-fluid" style="display: block; border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic; max-width: 100%; height: auto;">
```

#### `max-width: 100%` on `<img>` (Inline)
- Prevents the image from exceeding its container width on smaller screens
- Inline `max-width` works in most clients except Outlook desktop (which ignores `max-width`)
- The inline version is a baseline; the media query version with `!important` overrides the HTML `width` attribute on mobile

#### `height: auto` on `<img>` (Inline and Media Query)
- Maintains the image's aspect ratio when width is scaled down
- Without `height: auto`, a responsive image may distort (the HTML `height` attribute forces a fixed height while the width changes)
- **Must be in both inline style AND media query** — inline for clients that support it; media query with `!important` to override the HTML `height` attribute

#### `width: 100% !important` in Media Query
- Forces the image to fill its container width on mobile
- `!important` is required to override the inline HTML `width` attribute
- Only applied within the media query (mobile screens)

### Outlook Fixed-Width Image Fallback
```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600"><tr><td>
<![endif]-->
<img src="hero.jpg" alt="Sale" width="600" height="300" border="0" class="img-fluid" style="display: block; border: 0; max-width: 100%; height: auto; -ms-interpolation-mode: bicubic;">
<!--[if mso]>
</td></tr></table>
<![endif]-->
```
- Outlook ignores `max-width` — the MSO conditional wrapper table with `width="600"` constrains the image for Outlook
- All other clients use the `max-width: 100%` CSS for responsive scaling
- This is the standard pattern for responsive images in email

### Mobile Image Sizing Overrides
```css
@media only screen and (max-width: 600px) {
  .img-full { width: 100% !important; height: auto !important; }
  .img-half { width: 50% !important; height: auto !important; }
  .img-hide { display: none !important; max-height: 0 !important; overflow: hidden !important; mso-hide: all; }
  .img-show { display: block !important; max-height: none !important; overflow: visible !important; width: auto !important; }
}
```
- **`.img-full`** — image fills the full mobile width
- **`.img-half`** — image takes half the mobile width (for side-by-side mobile layouts)
- **`.img-hide`** — hides a desktop-only image on mobile (e.g., large decorative images that waste mobile data)
- **`.img-show`** — shows a mobile-only image (e.g., a mobile-optimized version of a complex desktop image)

### Mobile-Specific Image Swapping
```html
<!-- Desktop image (hidden on mobile) -->
<img src="desktop-hero.jpg" alt="Sale" width="600" height="300" class="img-hide" style="display: block; border: 0;">

<!-- Mobile image (hidden on desktop, shown on mobile) -->
<img src="mobile-hero.jpg" alt="Sale" width="320" height="200" class="img-show" style="display: none; mso-hide: all; max-height: 0; overflow: hidden;">
```
- Serve different images for desktop and mobile — different aspect ratios, different content, different file sizes
- Mobile image can be smaller file size, better cropped for portrait orientation
- **Hidden image still downloads** in most clients — the `display: none` image may still be fetched; this is a trade-off (extra download vs better mobile experience)
- **`mso-hide: all`** on the mobile image prevents Outlook from showing both images

---

## 5. Retina / HiDPI Image Optimization

### The Retina Technique for Email
```html
<img src="hero-1200x600.jpg" alt="Sale" width="600" height="300" border="0" style="display: block; border: 0; -ms-interpolation-mode: bicubic;">
```
- **Serve image at 2x pixel dimensions** — a 600×300 display area gets a 1200×600 image
- **Constrain with `width` and `height` HTML attributes** — `width="600" height="300"` forces the image to display at half its natural size
- **The extra pixels provide sharpness on retina displays** — iPhones, iPads, MacBooks, modern Android devices
- **Non-retina displays simply downscale** — no visual penalty; the browser/client renders at the specified display dimensions
- **File size trade-off:** a 2x image is larger than a 1x image at the same quality; increase JPEG compression to 60–70% to offset the larger pixel count
- **A well-compressed 1200×600 JPEG can be smaller than a lightly-compressed 600×300 JPEG** — the key is finding the right compression level

### Retina Image Compression Strategy
- **1x image at 80% JPEG quality** — sharp on standard displays; baseline quality
- **2x image at 60% JPEG quality** — the extra pixels compensate for the compression artifacts; the result looks sharp on retina and acceptable on standard displays
- **Result:** the 2x image at lower quality is often similar in file size to the 1x image at higher quality, but looks better on retina screens
- **Test visually** — the optimal quality setting depends on the image content; images with fine text need higher quality than photographs

### When NOT to Use Retina Images
- **Animated GIFs** — doubling the dimensions of a GIF quadruples the pixel count per frame, massively increasing file size; use 1x GIFs
- **Decorative images** — spacers, dividers, simple color blocks don't benefit from retina
- **Very large hero images** — if the 2x image exceeds 200KB, consider serving 1x with higher compression instead
- **Outlook desktop** — Outlook's Word rendering engine doesn't do retina rendering; serving 2x images to Outlook wastes bandwidth with no benefit

---

## 6. Image Format Optimization Tags

### JPEG Optimization
```html
<img src="https://images.example.com/hero.jpg" alt="Sale" width="600" height="300" border="0" style="display: block; border: 0;">
```
- Save as **progressive JPEG** for images over 10KB — loads in progressive scans (blurry → sharp) for better perceived performance
- **Color space:** save in sRGB (not Adobe RGB or ProPhoto) — email clients and screens use sRGB; other color spaces may render with incorrect colors
- **Strip metadata:** remove EXIF data, ICC profiles, thumbnails — saves 10–30% file size with zero quality impact
- **Compression level:** 60–75% for email (lower than web; email images are smaller and viewed at lower attention)
- **Chroma subsampling:** 4:2:0 is standard and provides the best compression; 4:4:4 is only needed for images with fine colored text (rare in email)

### PNG Optimization
```html
<img src="https://images.example.com/logo.png" alt="Company Logo" width="200" height="50" border="0" style="display: block; border: 0;">
```
- **PNG-8** (indexed, up to 256 colors) — use for logos, icons, simple graphics; dramatically smaller than PNG-24
- **PNG-24** (truecolor) — use only when transparency with complex edges is needed (e.g., product on transparent background)
- **PNG with alpha transparency** — essential for dark mode compatibility; logos and icons should be transparent PNG
- **Color palette reduction:** reduce to the minimum colors needed; a 2-color logo doesn't need 256 colors
- **Optimization tools:** TinyPNG (lossy PNG-24 compression), PNGQuant, OptiPNG, PNGCrush — can reduce PNG size by 50–80%
- **Interlaced PNG:** loads progressively (like progressive JPEG); slightly larger file; not commonly used in email

### GIF Optimization
```html
<img src="https://images.example.com/animation.gif" alt="Product demo animation" width="600" height="300" border="0" style="display: block; border: 0;">
```
- **Frame reduction:** remove duplicate or near-duplicate frames; every frame adds to file size
- **Color reduction:** reduce from 256 to 64, 32, or even 16 colors — each halving of colors significantly reduces size
- **Dithering:** Floyd-Steinberg dithering maintains perceived quality at lower color counts; pattern dithering produces smaller files but visible patterns
- **Frame dimensions:** reduce the pixel dimensions of each frame; a 300px-wide GIF is ~25% the size of a 600px-wide GIF
- **Frame disposal method:** `RestorePrevious` vs `RestoreBackground` vs `DoNotDispose` — use the optimal disposal method to avoid storing unchanged portions of each frame
- **Lossy GIF compression:** Gifsicle `--lossy=80` — introduces minor artifacts but significant file reduction
- **Loop count:** `loop=0` (infinite) vs `loop=3` (three times) — doesn't affect file size but affects user experience and accessibility
- **Consider replacing GIFs with static images + play button** — links to an externally hosted video/animation page; dramatically smaller
- **Outlook first frame:** Outlook desktop shows only the first frame; design the first frame to convey the full message

---

## 7. VML Background Image Optimization (Outlook)

Outlook desktop cannot render CSS `background-image` on HTML elements. VML provides the Outlook-specific fallback.

### Bulletproof Background Image Pattern
```html
<!--[if gte mso 9]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:300px;">
  <v:fill type="frame" src="https://images.example.com/hero-bg.jpg" color="#1a73e8" />
  <v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->

<div style="background-image: url('https://images.example.com/hero-bg.jpg'); background-color: #1a73e8; background-size: cover; background-position: center center; background-repeat: no-repeat;">
  <!--[if mso]><table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tr><td style="padding: 40px 20px;"><![endif]-->
  <div style="padding: 40px 20px;">
    <h1 style="color: #ffffff;">Hero Text</h1>
  </div>
  <!--[if mso]></td></tr></table><![endif]-->
</div>

<!--[if gte mso 9]>
  </v:textbox>
</v:rect>
<![endif]-->
```

### VML Fill Type Optimization
- **`type="frame"`** — stretches the image to fill the VML shape; equivalent to `background-size: cover`; best for hero background images
- **`type="tile"`** — tiles/repeats the image; equivalent to `background-repeat: repeat`; best for patterns and textures
- **Both types:** the `src` image should be optimized at the exact VML shape dimensions for `frame`, or at a small tile size for `tile`

### `<v:fill>` Image Attributes
- **`src`** — background image URL; same optimization rules as regular `<img src>`; HTTPS, CDN-hosted, properly compressed
- **`color`** — fallback solid color if the image fails to load; should approximate the image's dominant color
- **`size`** — image display size within the VML shape (optional; defaults to shape dimensions)
- **`aspect`** — `"atleast"` (fill, crop overflow), `"atmost"` (fit within, may letterbox), `"ignore"` (stretch to fit)
- **`origin`** and `position`** — control image positioning within the shape; `"0.5,0.5"` centers the image

### VML Background Image Size Optimization
- Serve the background image at the VML shape dimensions (e.g., 600×300 for a 600×300 `<v:rect>`)
- Outlook does not scale VML images smoothly — avoid relying on VML fill scaling
- Use the same image URL for both the CSS `background-image` and the VML `src` — don't serve separate images unless Outlook needs a different size or format
- JPEG is preferred for VML background images (smaller file size than PNG for photographic content)
- PNG with transparency does NOT work as expected in VML `<v:fill>` — the transparency may render incorrectly or show a black background

---

## 8. `<picture>` and `<source>` — Art Direction (Apple Mail Only)

### Dark Mode Image Swap
```html
<picture>
  <source srcset="https://images.example.com/logo-dark-mode.png" media="(prefers-color-scheme: dark)">
  <img src="https://images.example.com/logo-light-mode.png" alt="Company Logo" width="200" height="50" style="display: block; border: 0;">
</picture>
```
- **Only Apple Mail and iOS Mail render `<picture>` in email** — all other clients ignore `<picture>` and `<source>`, rendering only the `<img>` fallback
- **Image optimization:** prepare two versions of the image — light mode and dark mode
- **Dark mode version:** light-colored logo/icon on transparent background; colors that look good on dark backgrounds
- **Light mode version:** dark-colored logo/icon on transparent background (or on the light background)
- Both images should be individually optimized for file size
- **Both images may be downloaded** by Apple Mail even if only one is displayed — accounts for ~2x image download in Apple Mail

### Responsive Art Direction (Apple Mail Only)
```html
<picture>
  <source srcset="https://images.example.com/hero-mobile.jpg" media="(max-width: 600px)">
  <img src="https://images.example.com/hero-desktop.jpg" alt="Sale" width="600" height="300" style="display: block; border: 0;">
</picture>
```
- Serve different image crops/compositions for mobile vs desktop
- Mobile image can be portrait-oriented, cropped tighter, smaller file size
- **Apple Mail only** — all other clients get the `<img>` fallback

---

## 9. Dark Mode Image Optimization

### Transparent PNG Strategy
```html
<img src="https://images.example.com/logo-transparent.png" alt="Company Logo" width="200" height="50" style="display: block; border: 0;">
```
- **Transparent backgrounds** adapt to any background color — light mode white, dark mode black/gray
- **No code swap needed** — simplest dark mode image strategy
- Works in ALL email clients without any CSS or conditional logic
- **Optimization:** use PNG-8 with alpha transparency if possible (smaller than PNG-24); ensure transparent edges are clean (no white fringe)
- **Limitation:** only works for images that can have a transparent background (logos, icons, illustrations); doesn't work for photographs

### CSS Show/Hide Image Swap
```html
<!-- Light mode image (shown by default) -->
<img src="logo-on-white.png" alt="Company Logo" width="200" height="50" class="light-img" style="display: block; border: 0;">

<!-- Dark mode image (hidden by default) -->
<div class="dark-img" style="display: none; mso-hide: all; max-height: 0; overflow: hidden; font-size: 0;">
  <img src="logo-on-dark.png" alt="" width="200" height="50" style="display: block; border: 0;">
</div>
```
```css
@media (prefers-color-scheme: dark) {
  .light-img { display: none !important; max-height: 0 !important; overflow: hidden !important; }
  .dark-img { display: block !important; max-height: none !important; overflow: visible !important; font-size: inherit !important; }
}
```

#### Optimization for hidden images
- **Both images download regardless of which is displayed** — the hidden image still loads in most clients; this doubles the image bandwidth for clients with dark mode
- **Optimize both versions aggressively** — since you're serving two images, each should be as small as possible
- **`alt=""` on the dark mode image** — prevents screen readers from announcing the duplicate
- **`mso-hide: all`** on the dark mode wrapper — prevents Outlook (which doesn't support the CSS swap) from showing both images
- **`max-height: 0; overflow: hidden; font-size: 0`** — multiple hiding techniques stacked for maximum cross-client concealment

### Dark Mode Image Dimming
```css
@media (prefers-color-scheme: dark) {
  .dm-dim { opacity: 0.85 !important; }
  .dm-brightness { filter: brightness(0.8) !important; }
}
```
- **`opacity: 0.85`** — slightly dims all images to reduce glare against dark backgrounds; subtle but effective
- **`filter: brightness(0.8)`** — more targeted brightness reduction
- **Client support:** Apple Mail, iOS Mail, Thunderbird; other clients ignore these CSS properties
- **No additional image download** — pure CSS; no extra bandwidth
- **Apply selectively** — dim photographs and product images; don't dim logos or icons

### Dark Mode Image Halo/Glow Prevention
- Apple Mail dark mode may add a subtle white halo/glow around images with transparency
- **Workaround:** add a very subtle dark drop shadow baked into the image file (1px, low opacity)
- **Workaround:** add a thin (1–2px) border matching the dark mode background color around the image
- **Workaround:** use images with very slightly expanded edges that fade to transparent (feathered edges)
- These workarounds are pre-applied to the image file, not CSS

---

## 10. Tracking Pixel Optimization

### Standard Open Tracking Pixel
```html
<img src="https://track.esp.com/open/campaign123/user456" alt="" width="1" height="1" border="0" style="display: block; border: 0; height: 1px; width: 1px; overflow: hidden;">
```

#### Required Attributes
- **`alt=""`** — empty alt text; tracking pixel should be invisible to screen readers and invisible when images are off
- **`width="1"` and `height="1"`** — HTML attributes set to 1px; recognized convention for tracking pixels
- **`border="0"`** — no visible border
- **`style="display: block;"`** — prevents phantom gap
- **`style="height: 1px; width: 1px;"`** — CSS reinforcement of 1x1 size
- **`style="overflow: hidden;"`** — ensures no content overflows the 1px boundary

#### Placement Optimization
- **Place at the bottom of the email** — just before `</body>` or the closing wrapper `</table>`
- **Bottom placement reason:** if Gmail clips the email (at ~102KB), the tracking pixel is clipped first; to mitigate this, some developers place it near the top instead
- **Top placement trade-off:** some spam filters view a tracking pixel at the very top as suspicious
- **Recommended:** place in the footer section, but ABOVE any content that would push the email past 102KB

#### Tracking Pixel File Optimization
- **Transparent 1x1 GIF:** 43 bytes — the smallest possible tracking image
- **Transparent 1x1 PNG:** 67–80 bytes — slightly larger than GIF but also fine
- **The pixel is typically generated dynamically by the ESP** — the file size is controlled by the ESP, not the developer
- **Single pixel only** — one tracking pixel per email; multiple tracking pixels from different services increases spam score

#### Gmail Clipping and Tracking
- If the email is clipped by Gmail, the tracking pixel doesn't load, and the open is not recorded
- **Mitigation:** keep total HTML under 102KB; place tracking pixel in the first half of the email if size is borderline
- **Apple Mail Privacy Protection:** Apple pre-loads all images (including tracking pixels) through a proxy, registering "opens" for all Apple Mail users regardless of actual viewing; tracking pixel data from Apple Mail is unreliable

---

## 11. Image Preloading and Caching Behavior

### How Email Clients Load Images

#### Image Blocking (Default Off)
- **Outlook desktop (corporate):** images blocked by default in many enterprise configurations; user must click "Download Pictures" to load images
- **Outlook desktop (personal):** images may load by default or be blocked depending on settings
- **Gmail:** images proxied through Google's image cache; loaded automatically for most users
- **Apple Mail:** images loaded automatically by default
- **iOS Mail:** images loaded automatically; Apple Privacy Protection may pre-load all images through a proxy
- **Yahoo Mail:** images loaded automatically for trusted senders; may be blocked for unknown senders
- **Thunderbird:** images may be blocked by default; depends on configuration

#### Gmail Image Proxy
```
Original: https://images.example.com/hero.jpg
Proxied:  https://ci3.googleusercontent.com/proxy/...
```
- Gmail proxies ALL images through its own servers (`googleusercontent.com`)
- **Purpose:** privacy (hides recipient's IP from the sender's image server), security (scans images for malware), caching (reduces repeat loads)
- **Impact on tracking:** the first open loads the image from the sender's server (recording the open); subsequent views load from Gmail's cache (not recorded as new opens)
- **Impact on dynamic images:** real-time/open-time images (countdown timers, live content) are cached by Gmail after the first load; subsequent opens show the cached version, not a new dynamic render
- **Cache duration:** images may be cached for days or weeks; you cannot force Gmail to refresh a cached image
- **Cannot opt out** — Gmail image proxying is mandatory for all emails

#### Apple Mail Privacy Protection
- **Pre-loads ALL images** (including tracking pixels) through Apple's proxy servers at email delivery time, regardless of whether the user opens the email
- **Hides the recipient's IP address** from the sender's image server
- **Impact on open tracking:** every email delivered to Apple Mail registers as "opened" (even if the user never reads it); open rate data from Apple Mail is unreliable
- **Impact on open-time dynamic images:** the image is fetched at delivery time, not at actual open time; the "live" content is frozen at the time of delivery
- **Impact on geolocation:** Apple's proxy servers are in various locations; IP-based geolocation from image requests is useless for Apple Mail users

### Image Caching Headers
```
Cache-Control: public, max-age=31536000
ETag: "abc123"
Last-Modified: Mon, 01 Jan 2026 00:00:00 GMT
```
- **Set long cache durations** on your image server — email images don't change after send; caching saves bandwidth and improves load time for subsequent views
- **Gmail caches aggressively** regardless of your cache headers
- **Apple Mail Privacy Protection pre-caches** at delivery time
- **Outlook may re-download images** each time the email is opened (depending on configuration)
- **Cache-busting:** if you need to update an image after send (rare; fix a typo in a hero image), you must change the image URL entirely (e.g., add a query parameter `?v=2`); the old URL will remain cached

---

## 12. Image `<a>` Wrapper Optimization

### Linked Image Pattern
```html
<a href="https://example.com/sale" style="text-decoration: none; border: 0; outline: none; display: block;" target="_blank">
  <img src="hero.jpg" alt="Winter Sale — Shop now" width="600" height="300" border="0" style="display: block; border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic;">
</a>
```

#### `<a>` Wrapper Required Styles
- **`text-decoration: none`** — prevents underline from appearing under/around the image
- **`border: 0`** — prevents link border around the image (especially in older Outlook)
- **`outline: none`** — prevents focus outline around the linked image on click
- **`display: block`** — on the `<a>` tag itself; helps prevent gaps in some clients when the `<a>` wraps a block-level image

#### Redundant Image + Text Link Optimization
```html
<!-- BAD: two separate links to the same URL — double tab stop, double screen reader announcement -->
<a href="https://example.com/product"><img src="product.jpg" alt="Blue T-Shirt" ...></a>
<a href="https://example.com/product">Blue T-Shirt — $29.99</a>

<!-- GOOD: single link wrapping both image and text -->
<a href="https://example.com/product" style="text-decoration: none; color: #333333; border: 0;">
  <img src="product.jpg" alt="" width="200" height="200" border="0" style="display: block; border: 0;">
  <span style="display: block; padding: 10px 0; font-family: Arial, sans-serif; font-size: 16px; color: #333333;">Blue T-Shirt — $29.99</span>
</a>
```
- **`alt=""`** on the image when text provides the link description — prevents double reading by screen readers
- **Single `<a>` wrapper** — one tab stop, one screen reader announcement, one link for the entire product card
- **The text describes the link** — the image is treated as decorative within the linked block

---

## 13. Image Spacing and Gap Prevention

### The Phantom Gap Problem
Email clients can render an unwanted 2–4px gap below images due to the inline formatting context. Multiple techniques must be combined.

### Complete Gap Prevention Stack
```html
<td style="padding: 0; margin: 0; line-height: 0; font-size: 0; mso-line-height-rule: exactly; border-collapse: collapse;">
  <img src="image.jpg" alt="" width="600" height="300" border="0" style="display: block; border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic; vertical-align: bottom; line-height: 0;">
</td>
```

#### On the `<img>` tag
- `display: block` — primary fix; removes the inline baseline gap
- `vertical-align: bottom` — secondary fix; aligns image to the bottom of the line box, eliminating descender space
- `line-height: 0` — tertiary fix; collapses the line box height

#### On the parent `<td>`
- `line-height: 0` — collapses the cell's line box
- `font-size: 0` — removes font-based spacing (only on image-only cells)
- `mso-line-height-rule: exactly` — forces Outlook to respect the exact `line-height: 0`
- `padding: 0; margin: 0` — removes default cell spacing
- `border-collapse: collapse` — ensures table borders don't add space

#### On the parent `<table>`
- `cellpadding="0" cellspacing="0" border="0"` — HTML attributes to zero out all table spacing
- `border-collapse: collapse` — CSS to collapse table border model
- `mso-table-lspace: 0pt; mso-table-rspace: 0pt` — Outlook-specific removal of default table spacing

### Spacer Image Pattern
```html
<tr>
  <td style="font-size: 1px; line-height: 1px; height: 20px; mso-line-height-rule: exactly;" height="20">
    &nbsp;
  </td>
</tr>
```
- **Use `<td>` height instead of spacer images** — spacer GIFs are legacy; CSS height on `<td>` is more reliable and adds no image weight
- **`&nbsp;`** prevents the cell from collapsing in Outlook (empty cells may collapse to 0 height)
- **`font-size: 1px; line-height: 1px`** — prevents the `&nbsp;` from creating space larger than intended
- **Both HTML `height` attribute and CSS `height`** — for maximum compatibility

---

## 14. CID / Embedded Image Optimization

### Content-ID (CID) Embedded Images
```html
<img src="cid:logo-001" alt="Company Logo" width="200" height="50" border="0" style="display: block; border: 0;">
```
- CID images are embedded as MIME attachments within the email and referenced by Content-ID
- **Pros:** display immediately without external HTTP request; no image blocking; work offline
- **Cons:** dramatically increase email MIME size (Base64 encoding adds ~33%); may be stripped by some clients (Gmail); defeat the purpose of CDN caching and image optimization
- **When to use:** small logos in critical transactional emails (invoices, receipts) where guaranteed display outweighs size cost
- **When to avoid:** marketing emails, newsletters, any email with multiple images
- **Size limit:** keep individual CID images under 50KB (which becomes ~67KB in the MIME after Base64)
- **Total CID budget:** under 200KB total embedded images per email
- **Format:** JPEG or PNG; PNG-8 preferred for logos (smallest file size with transparency)
- **Outlook behavior:** Outlook generally renders CID images well
- **Gmail behavior:** Gmail may strip CID images or convert them to hosted images; test specifically

---

## 15. Image Accessibility Optimization

### Screen Reader Image Optimization
- **Meaningful images:** descriptive `alt` text conveying purpose and content
- **Decorative images:** `alt=""` plus `role="presentation"` plus `aria-hidden="true"`
- **Linked images:** `alt` describes the link destination/action, not the image content
- **Image maps:** each `<area>` has descriptive `alt`
- **Animated GIFs:** `alt` describes the content/message, not the animation itself; mention that it's animated if relevant
- **SVG in email:** `role="img"` plus `aria-label` or `<title>` inside the SVG; fallback `<img>` with `alt`
- **Tracking pixel:** `alt=""` plus `aria-hidden="true"` — completely invisible to assistive technology
- **Spacer images:** `alt=""` plus `aria-hidden="true"`

### Image-Off Content Strategy
- Design every email to be fully readable and actionable with all images disabled
- Use bulletproof HTML/CSS buttons instead of image-based CTA buttons
- Critical text content must be in live HTML text, not baked into images
- Styled `alt` text on every meaningful image as a fallback content strategy
- Fallback background colors on every image container `<td>` to maintain visual structure

---

## 16. Image Optimization Checklist

### Per-Image Checklist
- `src` is absolute HTTPS URL on a CDN or reliable host
- `alt` is present, descriptive, and under 125 characters
- `width` HTML attribute set to exact display width (number only, no `px`)
- `height` HTML attribute set to exact display height
- `border="0"` HTML attribute present
- `style="display: block; border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic;"` inline
- Image file is compressed (JPEG: 60–75%, PNG: optimized, GIF: color-reduced)
- Image is served at correct dimensions (1x for standard, 2x for retina with constrained `width`/`height`)
- Image format is correct (JPEG for photos, PNG for transparency/flat, GIF for animation)
- Image metadata is stripped (EXIF, ICC profiles, thumbnails)
- Image file size is within budget (hero: <200KB, product: <80KB, icon: <10KB)
- Image alt text is styled with font-family, font-size, color, background-color for image-off rendering
- Parent `<td>` has gap-prevention styles (line-height: 0, font-size: 0, mso-line-height-rule: exactly)
- Responsive class is applied (`.img-fluid`) with corresponding media query
- Dark mode class is applied if needed (`.dm-dim`, `.light-img`, `.dark-img`)
- Linked images have `text-decoration: none; border: 0; outline: none` on the `<a>` wrapper
- VML background image (if used) has matching CSS background-image and fallback color

### Per-Email Image Checklist
- Total image weight under 800KB (ideally under 500KB)
- Image-to-text ratio: at least 60% text, 40% images
- All images load over HTTPS from a reliable CDN
- Email is fully readable and functional with all images disabled
- Retina images are served at 2x dimensions with appropriate compression
- Dark mode image strategy is implemented (transparent PNGs, CSS swap, or dimming)
- Tracking pixel is present, 1x1, with empty `alt`, near the bottom
- Animated GIFs have meaningful first frames (for Outlook)
- Animated GIFs are under 500KB each
- No image-only CTAs (use bulletproof HTML buttons)
- MSO conditional VML background images match their CSS counterparts
- Mobile responsive images scale correctly (`max-width: 100%; height: auto`)
- Outlook MSO conditional table wrapper constrains images to fixed width
- All images tested with Gmail image proxy (verify proxy doesn't break image)
- All images tested with Apple Mail Privacy Protection (verify dynamic images are acceptable when cached at delivery)

---

*Total image optimization DOM elements, attributes, properties, techniques, and rules: 350+*
