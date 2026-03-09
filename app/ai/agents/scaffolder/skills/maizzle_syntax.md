# Maizzle Template Syntax Reference

## Frontmatter

Every Maizzle template starts with YAML frontmatter between `---` delimiters:

```yaml
---
title: "Campaign Name"
preheader: "Preview text shown in inbox"
bodyClass: "bg-gray-100"
---
```

Common frontmatter variables:
- `title` — Email subject line / template name
- `preheader` — Preview text (40-130 chars, complements subject)
- `bodyClass` — Tailwind classes applied to `<body>`

## Template Inheritance

Templates extend a layout and fill named blocks:

```html
<extends src="src/layouts/main.html">
  <block name="content">
    <!-- All email content goes here -->
  </block>
</extends>
```

## Components

Reusable components included via `<component>`:

```html
<component src="src/components/button.html"
  href="https://example.com"
  text="Shop Now"
  bg-color="#007bff"
  text-color="#ffffff" />
```

Component files use `<content>` for slot content and `{{ prop }}` for props.

## Outlook Conditional Tag

Maizzle provides `<outlook>` and `<not-outlook>` tags:

```html
<outlook>
  <table width="600" cellpadding="0" cellspacing="0" role="presentation">
    <tr><td>
</outlook>

<!-- Content visible in all clients -->

<outlook>
    </td></tr>
  </table>
</outlook>
```

Compiles to `<!--[if mso]>...<![endif]-->`.

`<not-outlook>` compiles to `<!--[if !mso]><!-->...<![endif]-->`.

## Tailwind CSS Utilities (Email-Safe)

Maizzle uses Tailwind with email-safe utilities:

### Spacing
- `p-4` -> `padding: 16px` (inlined)
- `px-6` -> `padding-left: 24px; padding-right: 24px`
- `mt-4` -> `margin-top: 16px`

### Typography
- `text-lg` -> `font-size: 18px; line-height: 28px`
- `font-bold` -> `font-weight: 700`
- `text-center` -> `text-align: center`
- `leading-6` -> `line-height: 24px`

### Colors
- `text-gray-800` -> `color: #1f2937`
- `bg-white` -> `background-color: #ffffff`

### Width
- `w-full` -> `width: 100%`
- `max-w-xl` -> `max-width: 600px`

### Display
- `block` -> `display: block`
- `inline-block` -> `display: inline-block`
- `hidden` -> `display: none`

## Maizzle Build Process

Maizzle processes templates in this order:
1. Parse frontmatter variables
2. Resolve `<extends>` and `<block>` inheritance
3. Resolve `<component>` includes
4. Process Tailwind CSS -> inline styles
5. Process `<outlook>` / `<not-outlook>` -> MSO conditionals
6. Minify (production only)

## Environment-Specific Config

Production builds (`maizzle build production`):
- CSS inlining enabled
- Unused CSS purged
- HTML minified
- Attributes shortened

Development builds (`maizzle build`):
- CSS inlining enabled but no purging
- HTML not minified
- Faster builds for preview
