<!-- L4 source: docs/SKILL_email-dark-mode-dom-reference.md section 5 -->
<!-- Last synced: 2026-03-13 -->

# Dark Mode Image Handling

## Image Swap Techniques

### Method 1: `<picture>` + `<source>` (Apple Mail Only)
```html
<picture>
  <source srcset="https://example.com/logo-dark.png" media="(prefers-color-scheme: dark)">
  <img src="https://example.com/logo-light.png" alt="Company Logo"
    width="200" height="50" style="display: block; border: 0;">
</picture>
```
- The `<source>` with `media="(prefers-color-scheme: dark)"` renders in dark mode
- The `<img>` is the light mode fallback
- **Apple Mail / iOS Mail only** — all other clients show the `<img>` fallback (they ignore `<picture>` in email)
- Simplest markup but narrowest client support

### Method 2: CSS Show/Hide (Broader Support)
```html
<!-- Light mode logo (shown by default, hidden in dark mode) -->
<img src="logo-light.png" alt="Brand Logo" class="dark-img-light"
  width="200" height="50" style="display:block; border:0;">

<!-- Dark mode logo (hidden by default, shown in dark mode) -->
<!--[if !mso]><!-->
<div class="dark-img-dark" style="display:none; overflow:hidden; max-height:0; font-size:0; mso-hide:all;">
  <img src="logo-dark.png" alt="Brand Logo"
    width="200" height="50" style="display:block; border:0;">
</div>
<!--<![endif]-->
```

CSS to toggle:
```css
@media (prefers-color-scheme: dark) {
  .dark-img-light { display: none !important; max-height: 0 !important; overflow: hidden !important; }
  .dark-img-dark {
    display: block !important;
    max-height: none !important;
    overflow: visible !important;
    font-size: inherit !important;
  }
}
```

Key details:
- Works in any client that supports `@media (prefers-color-scheme: dark)` and embedded `<style>`
- `mso-hide: all` hides the dark image from Outlook desktop rendering
- `alt=""` on the hidden image prevents screen reader announcement of the duplicate
- `max-height: 0; overflow: hidden` ensures the hidden image takes no space even in clients that ignore `display: none`

### Method 3: Transparent PNG (Simplest — No Swap Needed)
- Use logos and icons with transparent backgrounds (PNG-24 or SVG)
- Transparent logos naturally adapt to any background color
- No CSS or image swap required
- **Limitation:** Only works for images without their own background (logos, icons, illustrations)
- Check that content colors meet contrast on both light AND dark backgrounds

## Image Brightness/Opacity Reduction

```css
@media (prefers-color-scheme: dark) {
  img { opacity: 0.9; }
  .hero-img { filter: brightness(0.85); }
}
```
- Slightly dims images to reduce visual harshness against dark backgrounds
- `opacity: 0.9` — subtle reduction; prevents bright images from being jarring
- `filter: brightness(0.85)` — more precise control over perceived brightness
- **Limited client support:** Apple Mail, iOS Mail, Thunderbird only

## Image Border Technique

When an image has a white background that blends into light mode but looks
awkward in dark mode:

```css
@media (prefers-color-scheme: dark) {
  .img-bordered {
    border: 1px solid #2d2d50 !important;
    border-radius: 4px !important;
  }
}

[data-ogsb] .img-bordered {
  border: 1px solid #2d2d50 !important;
}
```

## Product Images on White Backgrounds

Product photos typically have white backgrounds. In dark mode:
1. **Best:** Add subtle border (1-2px) in dark mode
2. **Good:** Use a slightly lighter dark background (#252540) for product sections
3. **Avoid:** Don't try to remove/change the white background

```css
@media (prefers-color-scheme: dark) {
  .product-img { border: 1px solid rgba(255,255,255,0.1) !important; }
  .product-cell { background-color: #252540 !important; }
}
```

## Icon Handling

For simple icons (social media, feature icons):
- Use SVG with `currentColor` where supported (Apple Mail)
- Use white icons for dark backgrounds, dark icons for light backgrounds
- Implement swap pattern for email clients that don't support SVG

## Background Image Dark Mode

Background images in dark mode need overlay treatment:

```css
@media (prefers-color-scheme: dark) {
  .hero-bg {
    background-color: #1a1a2e !important;
    /* Darken the background image */
    background-blend-mode: multiply !important;
  }
}
```

Note: `background-blend-mode` has limited email client support. Fallback: use
a darker version of the background image via the image swap pattern.

## Outlook VML Image Dark Mode

VML `<v:fill>` images don't respond to dark mode CSS. For VML backgrounds:
- Use images that work on both light and dark backgrounds
- Or use a neutral/dark image that won't clash with dark mode
- Cannot swap VML fill images via CSS -- accept this limitation
