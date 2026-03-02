# CSS Selectors in Email

## Overview

CSS selectors determine which elements your styles apply to, and their support in email clients is far more restrictive than in web browsers. Gmail rewrites class names and strips many selector types. Outlook on Windows has its own subset of supported selectors based on the Word rendering engine. Understanding which selectors work -- and which are silently ignored -- is critical for writing email CSS that behaves predictably across clients.

## Basic Selectors

Foundational selectors have broad support, with some caveats in Gmail.

| Selector | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| Element (`p`, `td`) | Yes | Yes | Yes | Yes | Yes | Yes |
| Class (`.my-class`) | Yes* | Yes | Yes | Yes | Yes | Yes |
| ID (`#my-id`) | No | Yes | Yes | Yes | No | Yes |
| Universal (`*`) | No | Yes | Yes | Yes | No | Yes |
| Grouping (`h1, h2`) | Yes | Yes | Yes | Yes | Yes | Yes |

*Gmail renames class selectors by adding a random prefix. Your `.header` class becomes something like `.m_123456_header`. This works transparently, but it means you cannot reference class names from JavaScript or external resources.

Gmail and Yahoo strip ID selectors entirely. Never use ID selectors for email styling -- always use classes.

### Code Example: Safe Selector Usage

```html
<style>
  /* Safe: element selectors */
  td { font-family: Arial, sans-serif; }

  /* Safe: class selectors */
  .email-heading { font-size: 24px; color: #1a1a1a; }

  /* UNSAFE: ID selector -- stripped by Gmail and Yahoo */
  #main-content { padding: 20px; }

  /* UNSAFE: Universal selector -- stripped by Gmail and Yahoo */
  * { margin: 0; padding: 0; }
</style>
```

## Combinators

Combinator selectors have partial support, with significant gaps in Gmail.

| Selector | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| Descendant (`div p`) | Yes | Yes | Yes | Yes | Yes | Yes |
| Child (`div > p`) | Yes | Yes | Yes | Yes | Yes | Yes |
| Adjacent sibling (`h1 + p`) | No | Partial | Yes | Yes | No | Yes |
| General sibling (`h1 ~ p`) | No | No | Yes | Yes | No | Yes |

Gmail strips adjacent sibling (`+`) and general sibling (`~`) selectors. Outlook has limited support for adjacent sibling selectors.

### Code Example: Safe Combinator Usage

```html
<style>
  /* Safe: descendant selector */
  .card-body p {
    margin: 0 0 12px 0;
    font-size: 16px;
    line-height: 24px;
  }

  /* Safe: child selector */
  .nav > td {
    padding: 0 10px;
  }

  /* UNSAFE: adjacent sibling -- stripped by Gmail */
  .heading + .subheading {
    margin-top: 4px;
  }
</style>
```

## Pseudo-Classes

Pseudo-class support varies widely. Interactive pseudo-classes like `:hover` work in more clients than you might expect, but Gmail strips most of them.

| Selector | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `:hover` | No | Partial | Yes | No | No | Yes |
| `:active` | No | No | Yes | Yes | No | Partial |
| `:focus` | No | No | Yes | Yes | No | Partial |
| `:first-child` | No | No | Yes | Yes | No | Yes |
| `:last-child` | No | No | Yes | Yes | No | Yes |
| `:nth-child()` | No | No | Yes | Yes | No | Yes |
| `:nth-of-type()` | No | No | Yes | Yes | No | Partial |
| `:not()` | No | No | Yes | Yes | No | Yes |
| `:visited` | No | No | Partial | Partial | No | No |
| `::before` | No | No | Yes | Yes | No | Yes |
| `::after` | No | No | Yes | Yes | No | Yes |
| `::first-line` | No | Partial | Yes | Yes | No | Yes |
| `::first-letter` | No | Partial | Yes | Yes | No | Yes |

Gmail strips all pseudo-classes and pseudo-elements. Outlook supports `:hover` only on `<a>` elements in some versions.

### Code Example: Hover Effects (Progressive Enhancement)

```html
<style>
  /* Hover effect -- works in Apple Mail, Samsung; ignored elsewhere */
  .cta-link:hover {
    background-color: #0d47a1 !important;
    text-decoration: underline !important;
  }
</style>

<a href="https://example.com" class="cta-link"
   style="display: inline-block; background-color: #1a73e8;
          color: #ffffff; padding: 12px 28px;
          font-family: Arial, sans-serif; font-size: 16px;
          font-weight: bold; text-decoration: none;
          border-radius: 4px;">
  Call to Action
</a>
```

Hover effects should always be progressive enhancements. The base design must look complete without them.

## Attribute Selectors

Attribute selectors are stripped by Gmail and Yahoo but work in most other clients.

| Selector | Gmail | Outlook (Win) | Apple Mail | iOS Mail | Yahoo | Samsung |
|---|---|---|---|---|---|---|
| `[attr]` | No | Partial | Yes | Yes | No | Yes |
| `[attr="value"]` | No | Partial | Yes | Yes | No | Yes |
| `[attr^="value"]` | No | No | Yes | Yes | No | Yes |
| `[attr$="value"]` | No | No | Yes | Yes | No | Yes |
| `[attr*="value"]` | No | No | Yes | Yes | No | Yes |

Attribute selectors are primarily useful for dark mode targeting in Outlook.com and other specific clients.

### Code Example: Outlook.com Dark Mode Targeting

```html
<style>
  /* Outlook.com dark mode uses data-ogsb and data-ogsc attributes */
  [data-ogsc] .dark-text {
    color: #e0e0e0 !important;
  }
  [data-ogsb] .dark-bg {
    background-color: #1a1a2e !important;
  }
</style>
```

See the dark-mode-css guide for more on this technique.

## Specificity Considerations in Email

Email CSS specificity rules still apply, but several factors change the practical considerations:

### Gmail Class Prefixing

Gmail rewrites `.my-class` to `.m_xyz_my-class`, which changes the effective specificity chain. When writing overrides in media queries, always use `!important` to ensure your styles take precedence.

```html
<style>
  @media screen and (max-width: 600px) {
    /* !important required to override Gmail's prefixed specificity */
    .mobile-full-width {
      width: 100% !important;
      max-width: 100% !important;
    }
  }
</style>
```

### Inline Styles Always Win

Inline styles have the highest specificity (outside of `!important`). Since many email clients strip or limit `<style>` blocks, the most reliable approach is inline styles for critical visual properties and `<style>` blocks for responsive overrides and progressive enhancements.

```html
<!-- Inline for guaranteed rendering + class for responsive override -->
<td class="mobile-full-width"
    style="width: 300px; padding: 10px; font-family: Arial, sans-serif;">
  Content
</td>
```

### Recommended Specificity Strategy

1. **Inline styles** for all critical visual properties (colors, fonts, padding, widths)
2. **Class selectors in `<style>`** for responsive media queries and dark mode
3. **Element selectors** for CSS resets (`p { margin: 0; }`)
4. **Avoid** ID selectors, attribute selectors, and pseudo-classes for core styling

## Key Takeaways

- Use class selectors (`.class`) for all `<style>` block rules -- Gmail and Yahoo strip ID selectors
- Gmail rewrites class names with random prefixes, but class-based styling still works transparently
- Descendant (`div p`) and child (`div > p`) combinators are safe across all clients
- Adjacent sibling (`+`) and general sibling (`~`) selectors are stripped by Gmail and Yahoo
- Pseudo-classes (`:hover`, `:nth-child`, `:not`) are stripped by Gmail -- use them only as progressive enhancements
- `::before` and `::after` pseudo-elements do not work in Gmail or Outlook -- never use them for essential content
- Attribute selectors (`[data-ogsc]`, `[data-ogsb]`) are useful specifically for Outlook.com dark mode targeting
- Always use `!important` in media query declarations to override Gmail's class name prefixing specificity
- Rely on inline styles for all critical visual properties; reserve `<style>` blocks for responsive and enhancement layers
- The universal selector (`*`) is stripped by Gmail and Yahoo -- do not use it for CSS resets in email
