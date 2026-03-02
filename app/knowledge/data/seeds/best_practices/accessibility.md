# Email Accessibility

## Overview

Email accessibility ensures that messages are usable by people with disabilities, including those who use screen readers, have low vision, are colorblind, or have motor impairments. While WCAG (Web Content Accessibility Guidelines) was designed for websites, its core principles — perceivable, operable, understandable, and robust — apply directly to email. Accessible emails also tend to perform better overall: clear structure, good contrast, and meaningful content benefit all recipients, not just those with disabilities.

## The lang Attribute

The `lang` attribute is one of the simplest and most impactful accessibility improvements. It tells screen readers which language to use for pronunciation, enabling correct speech synthesis.

```html
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Subject Line</title>
</head>
<body>
  <!-- Email content -->
</body>
</html>
```

For multilingual emails, use the `lang` attribute on specific elements:

```html
<p lang="en">Thank you for your purchase.</p>
<p lang="fr">Merci pour votre achat.</p>
<p lang="de">Vielen Dank f&uuml;r Ihren Einkauf.</p>
```

Without `lang`, screen readers default to the user's system language, which can result in garbled pronunciation when the email content is in a different language.

## Alt Text for Images

Alt text is the single most important image accessibility feature. It provides text alternatives when images are not visible — either because they are blocked by the email client or because the user relies on a screen reader.

### Rules for Writing Alt Text

**Content images** — describe the information the image conveys:

```html
<!-- Product image: describe what the user would see -->
<img src="red-dress.jpg" width="280" height="400"
     alt="Red midi dress with short sleeves and a belted waist, $89"
     style="display: block; width: 100%; height: auto;" />

<!-- Chart or infographic: describe the data -->
<img src="q4-results.png" width="560" height="300"
     alt="Q4 results: Revenue up 23% year-over-year, reaching $4.2M"
     style="display: block; width: 100%; height: auto;" />

<!-- Icon with meaning: describe the function -->
<img src="phone-icon.png" width="20" height="20"
     alt="Call us:" style="display: inline; vertical-align: middle;" />
```

**Decorative images** — use empty alt to signal screen readers to skip:

```html
<!-- Decorative divider line -->
<img src="divider.png" width="600" height="2"
     alt="" role="presentation"
     style="display: block;" />

<!-- Purely decorative background graphic -->
<img src="confetti.png" width="600" height="80"
     alt="" role="presentation"
     style="display: block;" />
```

**Never do this:**
- `alt="image"` or `alt="photo"` — adds noise without information.
- `alt="image123.jpg"` — the filename is not a description.
- Omitting `alt` entirely — screen readers will read the full image URL instead.

## Semantic Table Usage

Email layout relies heavily on tables, but screen readers interpret tables differently depending on their role.

### Layout Tables

All tables used for visual layout must include `role="presentation"`. This instructs screen readers to ignore the table structure and read the content sequentially.

```html
<!-- Layout table: screen readers ignore the table structure -->
<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td>
      <h1>Welcome to Our Newsletter</h1>
      <p>Here is your weekly update.</p>
    </td>
  </tr>
</table>
```

### Data Tables

When presenting actual tabular data (pricing, schedules, comparisons), use proper table semantics so screen readers can navigate cells meaningfully.

```html
<!-- Data table: proper headers for screen reader navigation -->
<table border="1" cellpadding="8" cellspacing="0"
       style="border-collapse: collapse; width: 100%; border-color: #dddddd;">
  <caption style="font-weight: bold; margin-bottom: 10px; text-align: left;">
    Subscription Plans
  </caption>
  <thead>
    <tr style="background-color: #f5f5f5;">
      <th scope="col" style="text-align: left; padding: 10px;">Plan</th>
      <th scope="col" style="text-align: left; padding: 10px;">Price</th>
      <th scope="col" style="text-align: left; padding: 10px;">Features</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px;">Basic</td>
      <td style="padding: 10px;">$9/month</td>
      <td style="padding: 10px;">5 projects, email support</td>
    </tr>
    <tr>
      <td style="padding: 10px;">Pro</td>
      <td style="padding: 10px;">$29/month</td>
      <td style="padding: 10px;">Unlimited projects, priority support</td>
    </tr>
  </tbody>
</table>
```

Key elements for data tables:

- `<caption>` provides a title that screen readers announce before the table.
- `<th scope="col">` identifies column headers.
- `<th scope="row">` identifies row headers (when applicable).
- Do NOT add `role="presentation"` to data tables.

## Color Contrast

Poor color contrast makes text unreadable for users with low vision or colorblindness. WCAG AA requires a minimum contrast ratio of 4.5:1 for normal text and 3:1 for large text (18px+ or 14px+ bold).

### Common Contrast Failures in Email

```css
/* FAIL: light gray on white — 2.3:1 ratio */
color: #999999;
background-color: #ffffff;

/* PASS: dark gray on white — 7.0:1 ratio */
color: #555555;
background-color: #ffffff;

/* FAIL: medium blue on dark blue — 2.1:1 ratio */
color: #6699cc;
background-color: #003366;

/* PASS: white on dark blue — 11.5:1 ratio */
color: #ffffff;
background-color: #003366;
```

### Dark Mode Considerations

Email clients with dark mode (Apple Mail, Outlook.com, Gmail app) may invert colors automatically. Test that your contrast ratios hold in both light and dark modes.

```html
<!-- Provide explicit dark mode colors via meta and media query -->
<meta name="color-scheme" content="light dark" />
<meta name="supported-color-schemes" content="light dark" />

<style>
  @media (prefers-color-scheme: dark) {
    .body-bg { background-color: #1a1a2e !important; }
    .text-primary { color: #e0e0e0 !important; }
    .text-secondary { color: #b0b0b0 !important; }
  }
</style>
```

## Screen Reader Behavior in Email Clients

Different email clients expose content to screen readers in different ways.

- **Apple Mail + VoiceOver**: Full HTML semantics supported. Headings, lists, and landmark roles are navigable.
- **Outlook desktop + JAWS/NVDA**: Limited semantic support. Focus on clear heading hierarchy and `role="presentation"` on layout tables.
- **Gmail web + screen reader**: Wraps email in its own DOM. Some ARIA roles may be stripped. Keep semantic HTML simple.
- **Outlook.com/OWA**: Reasonable screen reader support. Headings and table roles work.

### Best Practices for Screen Reader Compatibility

```html
<!-- Use semantic headings for document structure -->
<h1 style="font-size: 24px; margin: 0 0 16px;">Main Headline</h1>
<h2 style="font-size: 20px; margin: 0 0 12px;">Section Title</h2>
<p style="font-size: 16px; margin: 0 0 16px; line-height: 1.5;">Body text content.</p>

<!-- Use lists for list content -->
<ul style="padding-left: 20px; margin: 0 0 16px;">
  <li style="margin-bottom: 8px;">First benefit</li>
  <li style="margin-bottom: 8px;">Second benefit</li>
  <li style="margin-bottom: 8px;">Third benefit</li>
</ul>
```

Avoid using `<div>` or `<span>` for text that should be a heading. Screen reader users navigate by heading level, and styled divs are invisible to this navigation.

## Link Accessibility

```html
<!-- Good: descriptive link text -->
<a href="https://example.com/privacy" style="color: #1a73e8;">
  Read our privacy policy
</a>

<!-- Bad: ambiguous link text -->
<a href="https://example.com/privacy" style="color: #1a73e8;">
  Click here
</a>

<!-- Good: distinguish links from surrounding text -->
<a href="https://example.com/terms"
   style="color: #1a73e8; text-decoration: underline;">
  Terms of service
</a>
```

Links should be visually distinguishable through both color AND an additional indicator (underline, bold, icon). Relying on color alone fails for colorblind users.

## WCAG Guidelines Applied to Email

| WCAG Criterion | Email Application |
|---------------|-------------------|
| 1.1.1 Non-text Content | Alt text on all content images |
| 1.3.1 Info and Relationships | Semantic headings, `role="presentation"` on layout tables, `<th>` on data tables |
| 1.3.2 Meaningful Sequence | Logical reading order matches visual order |
| 1.4.3 Contrast (Minimum) | 4.5:1 for text, 3:1 for large text |
| 1.4.4 Resize Text | Relative font sizes, fluid widths for mobile |
| 2.4.4 Link Purpose | Descriptive link text, avoid "click here" |
| 3.1.1 Language of Page | `lang` attribute on `<html>` element |
| 3.1.2 Language of Parts | `lang` attribute on foreign-language sections |

## Do's and Don'ts

**Do:**
- Add `lang` attribute to the `<html>` element of every email.
- Write descriptive alt text for all content images.
- Use `alt=""` and `role="presentation"` for decorative images.
- Add `role="presentation"` to every layout table.
- Maintain 4.5:1 minimum contrast ratio for all text.
- Use semantic HTML headings (`<h1>` through `<h6>`) for content structure.
- Underline links in addition to using color differentiation.
- Test with a screen reader (VoiceOver on macOS is free and built-in).

**Don't:**
- Don't omit the `alt` attribute — screen readers will read the raw URL.
- Don't use color as the only means of conveying information.
- Don't use `<div>` tags styled to look like headings — use actual heading elements.
- Don't create emails that only make sense with images enabled.
- Don't use tiny font sizes (below 14px for body text) — they are difficult to read on mobile.
- Don't put meaningful content in `title` attributes — screen reader support is inconsistent.

## Key Takeaways

- The `lang` attribute on `<html>` is the simplest high-impact accessibility improvement.
- Every content image needs descriptive alt text; every decorative image needs `alt=""`.
- Use `role="presentation"` on all layout tables and proper `<th>`/`<caption>` on data tables.
- Maintain 4.5:1 contrast ratio for normal text and 3:1 for large text.
- Use semantic headings for document structure — screen reader users navigate by heading level.
- Make links identifiable by both color and underline, with descriptive text.
- Test with images disabled and with a screen reader to verify the experience.
- Accessible emails perform better for everyone — clear structure and good contrast benefit all users.
