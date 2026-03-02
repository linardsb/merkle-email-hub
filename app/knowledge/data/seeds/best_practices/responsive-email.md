# Responsive Email Design

## Overview

Responsive email design ensures that messages render well across devices ranging from 320px-wide mobile screens to 1920px desktop monitors. Unlike web development, email responsive design must contend with clients that strip `<style>` blocks, ignore media queries, or use non-standard rendering engines. This guide covers the mobile-first approach, the fluid hybrid method, media queries for email, stacking patterns, and practical breakpoint strategies.

## Mobile-First Philosophy

Over 60% of email opens occur on mobile devices. Designing mobile-first means the single-column, stacked layout is your default — then you enhance for wider screens rather than trying to shrink a desktop layout down.

Benefits of mobile-first email design:

- The base layout works even when media queries are stripped (e.g., Gmail app on Android).
- Content hierarchy is clearer when forced into a single column.
- Faster rendering on constrained mobile hardware.
- Smaller payloads when progressive enhancement is used.

## The Fluid Hybrid Method

The fluid hybrid (or spongy) method achieves responsive behavior without relying on media queries. It combines `max-width` on container elements with `display: inline-block` on column divs, allowing content to naturally reflow.

```html
<!-- Fluid hybrid two-column layout -->
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td align="center" style="padding: 20px;">

      <!--[if mso]>
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0">
      <tr>
      <td width="290" valign="top">
      <![endif]-->
      <div style="display: inline-block; width: 100%; max-width: 290px; vertical-align: top;">
        <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding: 10px; font-size: 14px; line-height: 1.5;">
              <h2 style="margin: 0 0 10px;">Feature One</h2>
              <p style="margin: 0;">Description of the first feature with enough text to demonstrate the column behavior.</p>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td>
      <td width="290" valign="top">
      <![endif]-->
      <div style="display: inline-block; width: 100%; max-width: 290px; vertical-align: top;">
        <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding: 10px; font-size: 14px; line-height: 1.5;">
              <h2 style="margin: 0 0 10px;">Feature Two</h2>
              <p style="margin: 0;">Description of the second feature that stacks below on narrow screens.</p>
            </td>
          </tr>
        </table>
      </div>
      <!--[if mso]>
      </td>
      </tr>
      </table>
      <![endif]-->

    </td>
  </tr>
</table>
```

How it works:

1. Each column is a `<div>` with `display: inline-block` and `max-width: 290px`.
2. On screens wider than 600px, both divs sit side by side.
3. On screens narrower than ~580px, the divs cannot fit side by side and stack vertically.
4. Outlook receives a fixed-width table via MSO conditional comments.

## Media Queries in Email

Media queries provide fine-grained responsive control in clients that support `<style>` blocks. They work reliably in Apple Mail, iOS Mail, Outlook.com, Yahoo Mail, and the Gmail app (with `<style>` support).

```css
/* Base styles: mobile-first single column */
.email-container {
  width: 100% !important;
  max-width: 600px !important;
}

.column {
  width: 100% !important;
  display: block !important;
}

/* Tablet and desktop: side-by-side columns */
@media screen and (min-width: 600px) {
  .column {
    width: 50% !important;
    display: inline-block !important;
  }
}

/* Small mobile adjustments */
@media screen and (max-width: 480px) {
  .email-container {
    padding: 10px !important;
  }

  .hero-text {
    font-size: 22px !important;
    line-height: 28px !important;
  }

  .mobile-padding {
    padding-left: 15px !important;
    padding-right: 15px !important;
  }

  .mobile-full-width {
    width: 100% !important;
    height: auto !important;
  }
}
```

### Important Notes on Media Query Support

- **Gmail (non-AMP)**: Supports `<style>` blocks but rewrites class names. Use attribute selectors as a fallback if needed.
- **Outlook desktop**: Ignores all `<style>` blocks and media queries. Always provide MSO conditional fallbacks.
- **`!important`**: Required in email media queries to override inline styles. Without it, the inline `style` attribute wins.

## Column Stacking Patterns

### Direction-Aware Stacking

On mobile, columns typically stack top-to-bottom in source order. But sometimes you need the image to appear above the text even when the image is in the second column on desktop. Use `dir="rtl"` to reverse visual column order while maintaining source order for stacking.

```html
<!-- Desktop: Text left, Image right -->
<!-- Mobile: Image stacks on top (because source order is reversed by dir) -->
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" dir="rtl">
  <tr>
    <td width="50%" valign="top" dir="ltr" class="column">
      <img src="feature.jpg" width="280" alt="Feature image" style="display: block; width: 100%;" />
    </td>
    <td width="50%" valign="top" dir="ltr" class="column">
      <h2>Feature Title</h2>
      <p>Feature description text.</p>
    </td>
  </tr>
</table>
```

### Hide/Show Pattern

Use media queries to toggle visibility of mobile-specific or desktop-specific elements.

```html
<!-- Desktop-only element -->
<table role="presentation" class="desktop-only" style="display: table;">
  <tr>
    <td>Detailed navigation bar</td>
  </tr>
</table>

<!-- Mobile-only element -->
<table role="presentation" class="mobile-only" style="display: none; mso-hide: all;">
  <tr>
    <td>Simplified mobile menu</td>
  </tr>
</table>
```

```css
@media screen and (max-width: 480px) {
  .desktop-only {
    display: none !important;
    mso-hide: all !important;
  }

  .mobile-only {
    display: table !important;
    width: 100% !important;
  }
}
```

## Recommended Breakpoints

Email breakpoints differ from web breakpoints because the rendering context is the email client viewport, which is often narrower than the browser.

| Breakpoint | Target | Usage |
|-----------|--------|-------|
| 600px | Standard email width | Main container max-width |
| 480px | Small mobile | Font size increases, single column forced |
| 375px | iPhone SE / compact | Extra padding reduction, CTA full-width |

Keep breakpoints to a maximum of 2-3. Every additional breakpoint adds complexity and increases the risk of rendering inconsistencies across clients. The most impactful single breakpoint is `480px` for mobile optimization.

## Responsive Typography

Font sizes that look fine on desktop become unreadably small on mobile. Apply mobile-specific sizing.

```css
@media screen and (max-width: 480px) {
  /* Increase body text for readability */
  .body-text {
    font-size: 16px !important;
    line-height: 24px !important;
  }

  /* Scale down oversized headings */
  .hero-heading {
    font-size: 26px !important;
    line-height: 32px !important;
  }

  /* Ensure minimum tap target size (44x44px) for links */
  .cta-link {
    display: block !important;
    padding: 14px 20px !important;
    font-size: 16px !important;
  }
}
```

## Do's and Don'ts

**Do:**
- Start with a single-column mobile layout and enhance for desktop.
- Use the fluid hybrid method as your primary responsive strategy.
- Test in Gmail (which may strip `<style>`), Apple Mail, and Outlook.
- Use `!important` in media queries to override inline styles.
- Set images to `width: 100%; height: auto;` in mobile styles.
- Provide MSO conditional tables for Outlook.

**Don't:**
- Don't rely solely on media queries — many clients ignore them.
- Don't use `display: flex` or `display: grid` — no reliable email client support.
- Don't set fixed pixel widths on mobile — use percentage widths.
- Don't forget to test forwarded emails, which often lose `<style>` blocks.
- Don't use more than 3 breakpoints — it increases complexity without proportional benefit.

## Key Takeaways

- Mobile-first is the correct default: design for single-column, then enhance for wider screens.
- The fluid hybrid method (inline-block divs + MSO ghost tables) provides responsive behavior without media queries.
- Media queries enhance the experience in supporting clients but should never be the only responsive mechanism.
- Use `!important` in all media query declarations to beat inline style specificity.
- Limit breakpoints to 480px (mobile) and 600px (container width) for most email designs.
- Test the responsive behavior in Gmail (style stripping), Apple Mail (good support), and Outlook (no CSS support) at minimum.
- Ensure tap targets are at least 44x44px on mobile for accessibility and usability.
