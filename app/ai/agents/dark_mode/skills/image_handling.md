# Dark Mode Image Handling

## Image Swap Pattern (Light -> Dark Logo)

For logos or images that need different versions in dark vs light mode:

```html
<!-- Light mode image (hidden in dark mode) -->
<img class="dark-img-light" src="logo-dark-text.png" alt="Brand Logo"
  width="200" height="50" style="display:block; border:0;">

<!-- Dark mode image (hidden by default, shown in dark mode) -->
<!--[if !mso]><!-->
<div class="dark-img-dark" style="display:none; overflow:hidden; max-height:0; font-size:0;">
  <img src="logo-light-text.png" alt="Brand Logo"
    width="200" height="50" style="display:block; border:0;">
</div>
<!--<![endif]-->
```

CSS to toggle:
```css
@media (prefers-color-scheme: dark) {
  .dark-img-light { display: none !important; }
  .dark-img-dark {
    display: block !important;
    max-height: none !important;
    overflow: visible !important;
    font-size: inherit !important;
  }
}
```

## Transparent PNG Strategy

For images that work on any background:
- Use transparent PNG format for logos and icons
- Ensure the content color works on both light AND dark backgrounds
- If the logo is single-color, consider using a color that meets 4.5:1 on both

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
