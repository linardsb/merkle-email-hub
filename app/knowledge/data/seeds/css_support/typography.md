# CSS Typography in Email

## Overview

Typography controls are among the better-supported CSS properties in email, but there are still critical gaps. Core properties like `font-family`, `font-size`, `font-weight`, `line-height`, and `color` work reliably across all major clients. The challenges emerge with web fonts (`@font-face`, Google Fonts), advanced text properties (`text-transform`, `letter-spacing`, `word-spacing`), and the infamous default styles that different email clients inject. Understanding these nuances ensures your email typography renders consistently from Gmail to Outlook.

## Font Family

System and web-safe font stacks work universally. Always provide a robust fallback stack because email clients will silently drop fonts they cannot resolve.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `font-family` (system fonts) | Yes | Yes | Yes | Yes | Yes | Yes |
| `font-family` (web-safe) | Yes | Yes | Yes | Yes | Yes | Yes |
| `@font-face` | No | No | Yes | Yes | No | Yes |
| Google Fonts `<link>` | No | No | Yes | Yes | No | Yes |

Gmail, Outlook, and Yahoo all strip `@font-face` declarations and `<link>` tags for external fonts. Only Apple Mail, iOS Mail, and Samsung Email reliably render custom web fonts.

### Code Example: Robust Font Stack

```css
font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
```

```html
<td style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
           font-size: 16px; line-height: 24px; color: #333333;">
  Body text with safe font stack
</td>
```

### Web Font Strategy with Fallbacks

```html
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
</style>

<!-- In your content -->
<td style="font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
           font-size: 16px;">
  Renders Inter in Apple Mail/iOS, falls back to Helvetica in Gmail/Outlook
</td>
```

Note: `@import` for Google Fonts works in Apple Mail and iOS Mail. Gmail, Outlook, and Yahoo will ignore it and use the fallback fonts.

## Font Size and Line Height

`font-size` and `line-height` are universally supported. However, some email clients enforce minimum font sizes or adjust line-height calculations.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `font-size` (px) | Yes | Yes | Yes | Yes | Yes | Yes |
| `font-size` (em/rem) | Yes | No | Yes | Yes | Yes | Yes |
| `line-height` (unitless) | Yes | Yes | Yes | Yes | Yes | Yes |
| `line-height` (px) | Yes | Yes | Yes | Yes | Yes | Yes |

Outlook on Windows does not reliably support `em` or `rem` units. Always use `px` for font sizes in email.

### iOS Font Size Auto-Adjustment

iOS Mail automatically scales up small text to improve readability. To prevent this, add `-webkit-text-size-adjust: 100%` to your body or wrapper styles:

```html
<body style="-webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; margin: 0; padding: 0;">
```

### Minimum Readable Sizes

Use at least 14px for body text. iOS will auto-enlarge text below 13px, and small text creates accessibility issues.

```html
<td style="font-size: 16px; line-height: 1.5;">
  Body text at a comfortable reading size
</td>
<td style="font-size: 13px; line-height: 18px; color: #666666;">
  Fine print / legal text (minimum practical size)
</td>
```

## Font Weight and Style

`font-weight` and `font-style` are well-supported across all major email clients.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `font-weight: bold` | Yes | Yes | Yes | Yes | Yes | Yes |
| `font-weight: 400/700` | Yes | Partial | Yes | Yes | Yes | Yes |
| `font-style: italic` | Yes | Yes | Yes | Yes | Yes | Yes |
| `<b>` / `<strong>` | Yes | Yes | Yes | Yes | Yes | Yes |
| `<i>` / `<em>` | Yes | Yes | Yes | Yes | Yes | Yes |

Outlook on Windows may not support all numeric `font-weight` values (100-900). It reliably supports `normal` (400) and `bold` (700). For intermediate weights like 500 or 600, Outlook may round to the nearest supported value.

### Best Practice: Use HTML Tags for Emphasis

```html
<td style="font-family: Arial, sans-serif; font-size: 16px; line-height: 24px;">
  This is <strong style="font-weight: bold;">important text</strong> and
  this is <em style="font-style: italic;">emphasized text</em>.
</td>
```

Using both the HTML tag and the CSS property ensures rendering in clients that may strip styles.

## Text Decoration

`text-decoration` is widely supported, but link underlines behave differently across clients.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `text-decoration: none` | Yes | Yes | Yes | Yes | Yes | Yes |
| `text-decoration: underline` | Yes | Yes | Yes | Yes | Yes | Yes |
| `text-decoration: line-through` | Yes | Yes | Yes | Yes | Yes | Yes |
| `text-decoration-color` | No | No | Yes | Yes | No | Partial |
| `text-decoration-thickness` | No | No | Yes | Yes | No | No |

### Link Styling

```html
<a href="https://example.com"
   style="color: #1a73e8; text-decoration: underline; font-weight: bold;">
  Click here
</a>

<!-- Removing link underline -->
<a href="https://example.com"
   style="color: #1a73e8; text-decoration: none;">
  No underline link
</a>
```

Note: Some email clients (notably Gmail on Android) may force blue link colors on detected URLs. Use the `color` property inline on the `<a>` tag and avoid relying on `<style>` block rules for link colors.

## Text Transform, Letter Spacing, and Word Spacing

These properties have inconsistent support across email clients.

| Property | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `text-transform` | Yes | Yes | Yes | Yes | Yes | Yes |
| `letter-spacing` | Yes | Partial | Yes | Yes | Yes | Yes |
| `word-spacing` | Yes | Partial | Yes | Yes | Yes | Yes |
| `text-align` | Yes | Yes | Yes | Yes | Yes | Yes |
| `text-indent` | Yes | No | Yes | Yes | Yes | Yes |
| `white-space` | Yes | Partial | Yes | Yes | Yes | Yes |

`text-transform: uppercase` is well-supported and safe to use. `letter-spacing` works in most clients but Outlook may render it with slight inconsistencies, especially with larger values.

### Code Example: Styled Heading

```html
<td style="font-family: Arial, sans-serif; font-size: 12px;
           font-weight: bold; text-transform: uppercase;
           letter-spacing: 2px; color: #666666;">
  Section Header
</td>
```

## Heading Default Styles

Email clients apply default margins and font sizes to `<h1>` through `<h6>` tags. These defaults vary significantly between clients. Always reset heading styles explicitly.

```html
<h1 style="margin: 0 0 16px 0; padding: 0;
           font-family: Arial, sans-serif;
           font-size: 28px; line-height: 34px;
           font-weight: bold; color: #1a1a1a;">
  Email Heading
</h1>
```

## Key Takeaways

- System fonts and web-safe font stacks (`Arial`, `Helvetica`, `Georgia`, `Times New Roman`) work universally across all email clients
- Web fonts (`@font-face`, Google Fonts) only work in Apple Mail, iOS Mail, and Samsung Email -- always provide robust fallback stacks
- Use `px` units for `font-size` in email -- Outlook does not reliably support `em` or `rem`
- Add `-webkit-text-size-adjust: 100%` to prevent iOS from auto-scaling small text
- `font-weight` numeric values (100-900) may not render correctly in Outlook -- prefer `normal` and `bold` keywords or use `<strong>` / `<b>` tags
- `text-transform: uppercase` and `text-align` are safe to use across all clients
- Always reset default margins and padding on heading tags (`<h1>` - `<h6>`)
- Style links inline with both `color` and `text-decoration` -- some clients (Gmail Android) override inherited link styles
- `letter-spacing` works broadly but may render with minor inconsistencies in Outlook
