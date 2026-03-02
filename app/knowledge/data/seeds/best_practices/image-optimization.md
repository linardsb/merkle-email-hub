# Email Image Optimization

## Overview

Images are central to email design but introduce significant challenges: slow load times on mobile networks, image blocking by default in many clients, accessibility concerns for screen reader users, and inconsistent rendering across clients. Optimizing images for email means choosing the right format, sizing for retina displays, providing meaningful alt text, handling background images across clients, and planning for image-blocked scenarios.

## Image Format Selection

Each image format has specific strengths in the email context.

### PNG

Best for graphics with flat colors, logos, icons, and text overlays. Supports transparency (alpha channel). Produces larger file sizes than JPEG for photographic content.

```html
<!-- Logo with transparency -->
<img src="https://cdn.example.com/logo.png" width="180" height="50"
     alt="Company Name" style="display: block; border: 0;" />
```

### JPEG

Best for photographs and complex gradients. No transparency support. Use quality settings between 70-85% for the best balance of file size and visual quality. Below 70%, compression artifacts become visible.

### GIF

Supports animation and simple transparency (1-bit, no alpha). Limited to 256 colors. Use for simple animations (loading indicators, subtle motion). Avoid for complex animations — file sizes grow rapidly with frame count and dimensions.

### WebP

Superior compression (25-35% smaller than JPEG at equivalent quality). Supported in Apple Mail, iOS Mail, Gmail, and most modern clients. Not supported in Outlook desktop. Always provide a JPEG or PNG fallback.

```html
<!-- WebP with fallback using picture element (limited email support) -->
<!-- Safer approach: use WebP as src with server-side content negotiation -->
<img src="https://cdn.example.com/hero.jpg" width="600" height="300"
     alt="Spring collection hero banner" style="display: block; width: 100%; height: auto;" />
```

In practice, most email teams use JPEG for photos and PNG for graphics, since these formats have universal support. WebP can be served via CDN content negotiation where the server detects client support.

## Image Dimensions and Sizing

### Always Set Explicit Dimensions

Outlook requires the HTML `width` attribute on images. Without it, images may render at their natural size, breaking layouts.

```html
<!-- Correct: HTML width attribute + CSS for responsive scaling -->
<img src="hero.jpg" width="600" height="300"
     alt="Hero banner"
     style="display: block; width: 100%; max-width: 600px; height: auto; border: 0;" />
```

```html
<!-- Incorrect: no width attribute — breaks in Outlook -->
<img src="hero.jpg" alt="Hero banner"
     style="display: block; max-width: 100%; height: auto;" />
```

### Standard Dimensions

| Element | Recommended Width | Notes |
|---------|------------------|-------|
| Full-width hero | 600px | Matches standard email width |
| Two-column image | 280-290px | Accounting for gutters |
| Three-column image | 180-190px | Tight spacing |
| Thumbnail | 80-120px | Product grids, avatars |
| Logo | 150-200px | Keep proportional |

## Retina and HiDPI Displays

Most modern devices have 2x or 3x pixel density displays. Images rendered at 1x look blurry on these screens.

### The 2x Strategy

Export images at twice the display dimensions, then constrain with HTML/CSS width attributes.

```html
<!-- Image is 1200x600 actual pixels, displayed at 600x300 -->
<img src="hero@2x.jpg" width="600" height="300"
     alt="Crisp hero image on retina displays"
     style="display: block; width: 100%; max-width: 600px; height: auto; border: 0;" />
```

### File Size Considerations

Retina images are 2-4x larger in file size. Mitigate with:

- JPEG quality at 40-60% for 2x images (the downscaling masks compression artifacts).
- Use tools like `imageoptim`, `squoosh`, or `tinypng` for lossless compression.
- Target a maximum of 200KB per image, 800KB total for the entire email.

## Alt Text Best Practices

Alt text is displayed when images are blocked (Outlook blocks by default, many corporate environments do the same) and is read by screen readers.

### Writing Effective Alt Text

```html
<!-- Good: descriptive and actionable -->
<img src="sale-banner.jpg" width="600" height="200"
     alt="Summer Sale: 40% off all items. Shop now through August 31."
     style="display: block; width: 100%; height: auto;" />

<!-- Good: functional description for UI elements -->
<img src="facebook-icon.png" width="32" height="32"
     alt="Follow us on Facebook"
     style="display: inline-block;" />

<!-- Bad: redundant or useless -->
<img src="banner.jpg" alt="banner" />
<img src="spacer.gif" alt="spacer image" />
<img src="hero.jpg" alt="image" />

<!-- Correct: decorative images get empty alt -->
<img src="divider-line.png" width="600" height="2"
     alt="" role="presentation"
     style="display: block;" />
```

### Styled Alt Text

When images are blocked, you can style the alt text to maintain some visual hierarchy.

```html
<img src="hero.jpg" width="600" height="300"
     alt="Welcome to Our Spring Collection"
     style="display: block; width: 100%; height: auto;
            font-family: Arial, sans-serif; font-size: 24px;
            font-weight: bold; color: #333333;
            background-color: #f0f0f0;" />
```

## Background Images

Background images allow text overlays on images — a common design pattern. Support varies widely across email clients.

### VML Background for Outlook

Outlook does not support CSS `background-image`. Use VML (Vector Markup Language) for Outlook compatibility.

```html
<td valign="middle" style="background-image: url('https://cdn.example.com/bg.jpg');
    background-size: cover; background-position: center; padding: 60px 40px;">

  <!--[if gte mso 9]>
  <v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
          style="width:600px; height:300px;">
    <v:fill type="frame" src="https://cdn.example.com/bg.jpg" />
    <v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true">
  <![endif]-->

  <div style="font-family: Arial, sans-serif; font-size: 28px; color: #ffffff; text-align: center;">
    <h1 style="margin: 0; font-size: 32px;">Headline Over Image</h1>
    <p style="margin: 15px 0 0; font-size: 16px;">Supporting copy beneath the headline.</p>
  </div>

  <!--[if gte mso 9]>
    </v:textbox>
  </v:rect>
  <![endif]-->

</td>
```

## Planning for Image Blocking

Design emails that remain functional when images are not displayed.

**Strategies:**

- Use styled alt text on all content-bearing images.
- Never put critical information (coupon codes, dates, CTAs) only in images.
- Use HTML/CSS for buttons instead of image-based buttons.
- Set a background color on image containers so the layout does not collapse.
- Test your email with images disabled to verify readability.

```html
<!-- Image container with fallback background color -->
<td style="background-color: #003366; text-align: center; padding: 20px;">
  <img src="promo-banner.jpg" width="540" height="200"
       alt="SAVE30 — Use code at checkout for 30% off your order"
       style="display: block; width: 100%; max-width: 540px; height: auto;
              font-family: Arial, sans-serif; font-size: 20px;
              color: #ffffff; font-weight: bold;" />
</td>
```

## Do's and Don'ts

**Do:**
- Set HTML `width` (and optionally `height`) attributes on every image.
- Use `style="display: block; border: 0;"` to prevent gaps and blue borders in links.
- Compress images aggressively — aim for under 200KB per image.
- Provide descriptive alt text for content images and empty alt for decorative images.
- Use 2x resolution images for retina displays with constrained display dimensions.
- Host images on a CDN with HTTPS URLs.

**Don't:**
- Don't use SVG in email — support is minimal and inconsistent.
- Don't use `<picture>` or `srcset` — email client support is negligible.
- Don't embed images as base64 data URIs — most clients strip them, and they bloat file size.
- Don't rely on images for critical text content — always have an HTML text fallback.
- Don't use animated GIFs larger than 500KB — they cause rendering delays and may be stripped.

## Key Takeaways

- Use JPEG for photographs (70-85% quality) and PNG for graphics with transparency.
- Always set explicit `width` and `height` attributes on images for Outlook compatibility.
- Export images at 2x display dimensions for retina sharpness, using lower JPEG quality (40-60%) to offset file size.
- Write descriptive, actionable alt text — it is the primary fallback when images are blocked.
- Use VML for background images in Outlook; CSS `background-image` for other clients.
- Design and test your email with images disabled to ensure it remains readable and functional.
- Keep total email image payload under 800KB for acceptable mobile load times.
