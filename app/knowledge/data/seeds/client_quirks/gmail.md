# Gmail Rendering Quirks

## Overview

Gmail is one of the most widely used email clients globally, but its rendering behavior is fragmented across multiple platforms: Gmail webmail (desktop browser), Gmail Android app, Gmail iOS app, and Gmail within third-party apps via IMAP. Each variant handles HTML and CSS differently, making Gmail one of the trickiest clients to develop for despite its modern browser-based rendering. The core challenge is Gmail's aggressive CSS sanitization, which strips or rewrites styles to prevent emails from breaking the Gmail UI.

Gmail's rendering is powered by a custom HTML/CSS sanitizer rather than a standard browser engine limitation. The sanitizer operates on a whitelist basis, removing anything it does not explicitly allow.

## CSS Stripping and Sanitization

Gmail's sanitizer is the primary source of rendering quirks. It processes CSS in specific ways:

**Embedded `<style>` blocks**: Gmail webmail and Gmail apps support `<style>` tags, but only when placed in the `<head>`. Style blocks in the `<body>` are stripped entirely.

```html
<!-- Supported: style in head -->
<head>
  <style>
    .heading { font-size: 24px; color: #333333; }
  </style>
</head>

<!-- NOT supported: style in body -->
<body>
  <style>
    .heading { font-size: 24px; } /* This will be removed */
  </style>
</body>
```

**Inline styles**: Gmail preserves most inline styles, making inline CSS the most reliable approach for Gmail compatibility. However, some properties are still stripped.

Properties stripped from inline styles include:
- `position` (all values)
- `float`
- `display: flex` and `display: grid`
- `overflow` (in some contexts)
- CSS custom properties (`--variable-name`)

## Class Name Rewriting

Gmail rewrites all CSS class names by prepending a unique, auto-generated prefix. A class like `.header-text` becomes something like `.m_-2846123456789 .header-text` or is prefixed with a hash-based identifier. This means:

- Class names in `<style>` blocks are rewritten to match
- Class-based selectors generally work, but descendant selectors may break
- ID selectors (`#myId`) are completely stripped
- Attribute selectors (`[data-type="header"]`) are not supported

```html
<!-- This works in Gmail -->
<style>
  .btn { background-color: #0066cc; padding: 12px 24px; }
</style>
<a class="btn" href="https://example.com">Click here</a>

<!-- This does NOT work -->
<style>
  #main-btn { background-color: #0066cc; }
  [data-role="button"] { padding: 12px; }
</style>
```

## Responsive Design in Gmail

Gmail's responsive email support varies significantly by platform:

**Gmail webmail (desktop)**: Supports `<style>` in `<head>` and media queries. Responsive designs work.

**Gmail Android app**: Supports `<style>` in `<head>` and media queries since late 2016. Responsive designs work.

**Gmail iOS app**: Supports `<style>` in `<head>` and media queries. Responsive designs work.

**Gmail IMAP (third-party apps)**: Strips all `<style>` blocks. Only inline styles are preserved. This is the most restrictive Gmail variant. Fluid/hybrid layouts using `max-width` with inline styles are the only reliable responsive approach.

```html
<!-- Hybrid/fluid approach that works even when <style> is stripped -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td>
      <!--[if mso]>
      <table role="presentation" cellpadding="0" cellspacing="0" width="600">
      <tr><td width="300">
      <![endif]-->
      <div style="display: inline-block; width: 100%; max-width: 300px;
                  vertical-align: top;">
        <table role="presentation" width="100%">
          <tr>
            <td style="padding: 10px;">Column 1</td>
          </tr>
        </table>
      </div>
      <!--[if mso]></td><td width="300"><![endif]-->
      <div style="display: inline-block; width: 100%; max-width: 300px;
                  vertical-align: top;">
        <table role="presentation" width="100%">
          <tr>
            <td style="padding: 10px;">Column 2</td>
          </tr>
        </table>
      </div>
      <!--[if mso]></td></tr></table><![endif]-->
    </td>
  </tr>
</table>
```

## Image Proxying

Gmail proxies all images through its own servers (`googleusercontent.com`). This has several implications:

- Original image URLs are not directly requested from the sender's server, which means open tracking pixels may be delayed or cached
- Images are cached aggressively; updating an image at the same URL may not reflect immediately
- Image dimensions should be specified in HTML attributes and CSS to prevent layout shifts during proxy loading
- WebP images are supported in Gmail

```html
<img src="https://example.com/banner.jpg"
     width="600" height="200"
     alt="Campaign banner"
     style="display: block; max-width: 100%; height: auto;"
/>
```

## AMP for Email

Gmail supports AMP for Email (AMP4Email), which enables interactive email experiences like carousels, accordions, forms, and real-time content. However, AMP emails have strict requirements:

- Must include a valid MIME part with `text/x-amp-html` content type
- The sender must be registered and verified with Google
- AMP content expires after 30 days, falling back to the HTML version
- AMP emails must include a regular HTML fallback

```html
<!-- AMP component example (in AMP MIME part) -->
<amp-accordion>
  <section>
    <h3>Section Title</h3>
    <div>
      <p>Expandable content here.</p>
    </div>
  </section>
</amp-accordion>
```

AMP4Email is not relevant to most marketing emails but is valuable for transactional flows (order updates, forms, real-time data).

## The 102KB Clipping Issue

Gmail clips emails that exceed approximately 102KB in HTML file size. When clipped, Gmail displays a "[Message clipped] View entire message" link, and the remainder of the email (including the footer with unsubscribe links) is hidden behind an extra click.

```html
<!-- Check your compiled HTML size -->
<!-- If over 102KB, consider:
  - Removing redundant inline styles
  - Minifying HTML output
  - Reducing nested table depth
  - Using shorthand CSS properties
  - Moving repeating styles to <style> block -->
```

The 102KB limit applies to the raw HTML source, not the rendered size. Heavily inlined emails can hit this limit quickly.

## Dark Mode Behavior

Gmail's dark mode behavior differs by platform:

- **Gmail webmail**: No automatic dark mode color inversion. Emails appear as designed.
- **Gmail Android app**: Applies partial dark mode. Light backgrounds may be darkened, and text colors may be inverted. The behavior is inconsistent and not fully controllable.
- **Gmail iOS app**: Similar partial inversion to Android, with some differences in which elements are affected.

To provide hints for Gmail's dark mode:

```css
/* In <style> block */
@media (prefers-color-scheme: dark) {
  .dark-bg { background-color: #1a1a2e !important; }
  .dark-text { color: #e0e0e0 !important; }
}

/* Meta tag for color scheme support */
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
```

## Key Takeaways

- Gmail's CSS sanitizer strips styles on a whitelist basis; always use inline styles as the baseline
- Place `<style>` blocks in `<head>` only; `<body>` style blocks are removed
- Class names are rewritten with auto-generated prefixes; ID selectors and attribute selectors are stripped
- Gmail IMAP (third-party apps) strips all `<style>` blocks, requiring fluid/hybrid layouts with inline styles
- Images are proxied through Google servers, affecting tracking and caching behavior
- Keep HTML under 102KB to avoid Gmail clipping, which hides footer content including unsubscribe links
- Gmail dark mode varies by platform: webmail has none, Android and iOS apply partial automatic inversion
- Responsive media queries work in Gmail webmail and native apps, but not in IMAP/third-party contexts
- AMP for Email enables interactivity but requires sender verification and includes a 30-day expiry
