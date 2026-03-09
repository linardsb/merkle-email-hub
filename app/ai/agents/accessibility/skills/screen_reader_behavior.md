# Screen Reader Behavior in Email Clients

## Screen Reader + Email Client Matrix

| Screen Reader | Platform | Email Client | Notes |
|--------------|----------|-------------|-------|
| VoiceOver | macOS | Apple Mail | Best support, reads role="article" |
| VoiceOver | iOS | Mail app | Good support, reads semantic markup |
| NVDA | Windows | Outlook desktop | Reads tables as data by default |
| JAWS | Windows | Outlook desktop | Similar to NVDA, respects role="presentation" |
| NVDA | Windows | Outlook web | Web rendering, good support |
| TalkBack | Android | Gmail app | Limited, basic structure reading |

## Table Reading Behavior

### Without `role="presentation"` (BAD)
```
NVDA: "Table with 3 rows and 2 columns. Row 1, Column 1: Header..."
```
Screen reader announces grid structure, confusing for layout tables.

### With `role="presentation"` (GOOD)
```
NVDA: "Header text. Content text..."
```
Screen reader treats table as layout, reads content linearly.

### Critical Rule
ALL layout tables MUST have `role="presentation"`:
```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
```

## Heading Navigation

Screen reader users navigate by headings (H key in NVDA/JAWS).
Proper heading hierarchy enables efficient scanning:

```html
<h1>Summer Sale</h1>                    <!-- Main topic -->
  <h2>Women's Collection</h2>            <!-- Section -->
    <h3>Dresses</h3>                     <!-- Subsection -->
    <h3>Accessories</h3>                 <!-- Subsection -->
  <h2>Men's Collection</h2>             <!-- Section -->
```

**Never skip levels:** h1 -> h3 (skipping h2) breaks navigation expectations.

## MSO Conditional Content

### VoiceOver Behavior with MSO Comments
VoiceOver (Apple Mail) ignores MSO conditional content — reads only non-MSO content.
NVDA/JAWS (Outlook) reads MSO content — ignores non-MSO fallbacks.

This means both versions need proper alt text and semantic markup:
```html
<!--[if mso]>
<v:roundrect ...>
<center style="...">Shop Now</center>
</v:roundrect>
<![endif]-->
<!--[if !mso]><!-->
<a href="..." role="button" style="...">Shop Now</a>
<!--<![endif]-->
```

Both the VML center text and the `<a>` text should convey the same action.

## VML Accessibility

VML elements (`<v:rect>`, `<v:roundrect>`, etc.) have limited screen reader support:
- Text inside `<v:textbox>` IS read by NVDA/JAWS in Outlook
- VML shapes themselves are NOT announced
- Alt text on VML elements is NOT reliably read

**Best practice:** Ensure all VML content has equivalent text in `<v:textbox>` or `<center>`.

## Email-Level ARIA

### Recommended ARIA for Email
```html
<html lang="en">
<body>
  <div role="article" aria-roledescription="email" aria-label="Email from Brand Name">
    <!-- All email content -->
  </div>
</body>
</html>
```

### ARIA on Decorative Elements
```html
<img src="spacer.gif" alt="" role="presentation" aria-hidden="true">
<hr role="presentation" aria-hidden="true">
```

## Reading Order

Screen readers follow DOM order, not visual order.
In multi-column email layouts:
- Source order should be: left column content -> right column content
- On mobile (stacked), this becomes top-to-bottom
- Ensure the reading order makes sense in both layouts
