# CTA Buttons in Email

## Overview

Call-to-action buttons are the most important interactive elements in email. They drive clicks, conversions, and engagement. However, buttons in email cannot rely on modern CSS properties — Outlook ignores `border-radius`, `box-shadow`, and other visual enhancements. This guide covers bulletproof button techniques that work across all major email clients, including the padding-based approach, VML buttons for Outlook, border-based fallbacks, and accessibility requirements.

## Why Image Buttons Are Problematic

Using images for buttons introduces several issues:

- **Image blocking**: Many clients block images by default. An image-based CTA disappears entirely.
- **Alt text limitations**: Alt text cannot replicate the visual prominence of a styled button.
- **Load time**: Image buttons add to the total image payload.
- **Accessibility**: Screen readers may not convey button semantics from an image link.
- **Maintenance**: Text changes require re-exporting images rather than editing HTML.

Always use HTML/CSS buttons with live text for CTAs.

## The Padding-Based Bulletproof Button

The most reliable cross-client button technique uses a table cell with padding and a background color. This approach works in every email client, including Outlook.

```html
<!-- Bulletproof button: table-based with padding -->
<table role="presentation" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td align="center" bgcolor="#e63946" style="border-radius: 6px; background-color: #e63946;">
      <a href="https://example.com/shop"
         target="_blank"
         style="display: inline-block; padding: 14px 32px;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 16px; font-weight: bold;
                color: #ffffff; text-decoration: none;
                border-radius: 6px;">
        Shop the Collection
      </a>
    </td>
  </tr>
</table>
```

Key details:

- `bgcolor` on the `<td>` provides the background color for Outlook (which ignores CSS `background-color` on `<a>` tags).
- `background-color` in the inline style provides the color for modern clients.
- `border-radius` on both `<td>` and `<a>` gives rounded corners where supported (ignored by Outlook, which renders square).
- Padding on the `<a>` tag makes the entire button area clickable, not just the text.
- `text-decoration: none` removes the default link underline.

## VML Button for Full Outlook Support

For pixel-perfect buttons in Outlook — including rounded corners and background colors — use VML (Vector Markup Language) wrapped in MSO conditional comments.

```html
<!-- Full bulletproof button with VML for Outlook -->
<div style="text-align: center;">
  <!--[if mso]>
  <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
               xmlns:w="urn:schemas-microsoft-com:office:word"
               href="https://example.com/signup"
               style="height: 48px; v-text-anchor: middle; width: 220px;"
               arcsize="12%"
               strokecolor="#1a73e8"
               fillcolor="#1a73e8">
    <w:anchorlock/>
    <center style="color: #ffffff; font-family: Arial, sans-serif;
                   font-size: 16px; font-weight: bold;">
      Sign Up Free
    </center>
  </v:roundrect>
  <![endif]-->

  <!--[if !mso]><!-->
  <a href="https://example.com/signup"
     target="_blank"
     style="display: inline-block; padding: 14px 40px;
            background-color: #1a73e8; color: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 16px; font-weight: bold;
            text-decoration: none; border-radius: 6px;">
    Sign Up Free
  </a>
  <!--<![endif]-->
</div>
```

How it works:

- Outlook renders the `<v:roundrect>` VML element with a clickable link, rounded corners (`arcsize`), and fill color.
- All other clients render the standard `<a>` tag with CSS styling.
- The `<!--[if !mso]><!-->` and `<!--<![endif]-->` comments hide the modern version from Outlook.

## The Border-Based Approach

An alternative technique that avoids VML complexity by using thick borders on the `<a>` tag to simulate padding. This works because Outlook respects `border` on inline elements.

```html
<!-- Border-based bulletproof button -->
<a href="https://example.com/learn-more"
   target="_blank"
   style="display: inline-block;
          background-color: #2d6a4f;
          color: #ffffff;
          font-family: Arial, Helvetica, sans-serif;
          font-size: 16px;
          font-weight: bold;
          text-decoration: none;
          padding: 14px 32px;
          border: 1px solid #2d6a4f;
          border-radius: 6px;">
  Learn More
</a>
```

For Outlook specifically, thick borders can replace padding:

```html
<!-- Border-as-padding for Outlook compatibility -->
<a href="https://example.com/learn-more"
   target="_blank"
   style="display: inline-block;
          background-color: #2d6a4f;
          color: #ffffff;
          font-family: Arial, Helvetica, sans-serif;
          font-size: 16px;
          font-weight: bold;
          text-decoration: none;
          border-top: 14px solid #2d6a4f;
          border-bottom: 14px solid #2d6a4f;
          border-left: 32px solid #2d6a4f;
          border-right: 32px solid #2d6a4f;">
  Learn More
</a>
```

The border color matches the background color, creating the visual appearance of padding. This approach is simpler than VML but results in square corners in Outlook.

## Button Design Guidelines

### Sizing

- **Minimum height**: 44px (Apple's Human Interface Guidelines for touch targets).
- **Minimum width**: 120px for single-word CTAs; expand to fit text with padding.
- **Padding**: 12-16px vertical, 24-40px horizontal.
- **Font size**: 14-18px. Avoid going below 14px for readability.

### Color and Contrast

- **Contrast ratio**: Minimum 4.5:1 between button text and background color (WCAG AA).
- **Visual weight**: The primary CTA should be the most visually prominent element in the email.
- **Hover states**: Not reliable in email. Do not depend on hover for information or affordance.

### Copy

- Use action verbs: "Shop Now", "Get Started", "Download Guide".
- Keep text concise: 2-4 words maximum.
- Avoid generic text: "Click Here" and "Learn More" perform worse than specific CTAs.

## Multiple CTAs

When an email has multiple CTAs, establish a clear visual hierarchy.

```html
<!-- Primary CTA: solid background, prominent -->
<table role="presentation" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td align="center" bgcolor="#1a73e8" style="border-radius: 6px;">
      <a href="https://example.com/primary"
         target="_blank"
         style="display: inline-block; padding: 14px 40px;
                font-family: Arial, sans-serif; font-size: 16px;
                font-weight: bold; color: #ffffff; text-decoration: none;">
        Start Free Trial
      </a>
    </td>
  </tr>
</table>

<!-- Spacer -->
<div style="height: 12px; line-height: 12px; font-size: 1px;">&nbsp;</div>

<!-- Secondary CTA: outlined/ghost style -->
<table role="presentation" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td align="center" style="border: 2px solid #1a73e8; border-radius: 6px;">
      <a href="https://example.com/secondary"
         target="_blank"
         style="display: inline-block; padding: 12px 32px;
                font-family: Arial, sans-serif; font-size: 14px;
                font-weight: bold; color: #1a73e8; text-decoration: none;">
        View Pricing
      </a>
    </td>
  </tr>
</table>
```

## Accessibility Requirements

Buttons must be accessible to keyboard users, screen readers, and users with visual impairments.

```html
<!-- Accessible button with ARIA label -->
<table role="presentation" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td align="center" bgcolor="#e63946" style="border-radius: 6px;">
      <a href="https://example.com/shop"
         target="_blank"
         role="link"
         aria-label="Shop the spring collection at example.com"
         style="display: inline-block; padding: 14px 32px;
                font-family: Arial, sans-serif; font-size: 16px;
                font-weight: bold; color: #ffffff; text-decoration: none;">
        Shop Now
      </a>
    </td>
  </tr>
</table>
```

Accessibility checklist for CTA buttons:

- **Color contrast**: 4.5:1 minimum between text and background.
- **Don't rely on color alone**: Underline or bold button text for users who cannot distinguish colors.
- **Descriptive link text**: Avoid "Click Here". Use specific text that describes the destination.
- **Touch target size**: Minimum 44x44px on mobile devices.
- **`aria-label`**: Add when the visible text is very short or ambiguous (e.g., "Go" or an icon-only button).

## Do's and Don'ts

**Do:**
- Use HTML/CSS buttons with live text — never image-based buttons.
- Use the padding-based table approach as the reliable baseline.
- Add VML for Outlook when rounded corners are required.
- Ensure 4.5:1 color contrast ratio.
- Make buttons at least 44px tall for mobile touch targets.
- Center-align buttons for the strongest visual impact.

**Don't:**
- Don't use `<button>` elements — email clients do not support form elements.
- Don't rely on `hover` states — they are inconsistent across email clients.
- Don't use CSS gradients on buttons without a solid `background-color` fallback.
- Don't make buttons too small — anything below 44px height is difficult to tap on mobile.
- Don't use more than 2-3 CTAs per email — it dilutes focus and reduces click rates.

## Key Takeaways

- The padding-based table button is the most reliable technique across all email clients.
- Use VML (`<v:roundrect>`) wrapped in MSO conditionals for pixel-perfect Outlook buttons with rounded corners.
- The border-based approach offers a simpler alternative to VML at the cost of square corners in Outlook.
- Always use live HTML text in buttons, never images.
- Maintain at least 4.5:1 contrast ratio and 44px minimum touch target height.
- Write specific, action-oriented button copy ("Start Free Trial" not "Click Here").
- Establish a clear visual hierarchy when using multiple CTAs — one primary, others secondary.
