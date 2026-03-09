# VML Reference — Shapes, Fills, and Textbox Patterns

VML (Vector Markup Language) is required for advanced Outlook rendering —
background images, rounded buttons, custom shapes. Outlook desktop uses the
Word rendering engine which supports VML natively.

## Required Namespace Declarations

Always add these to the `<html>` tag when using VML:
```html
<html xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office">
```

## VML Rect — Background Images

```html
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml"
  fill="true" stroke="false"
  style="width:600px; height:300px;">
<v:fill type="frame" src="https://placehold.co/600x300" color="#333333" />
<v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->
<!-- Non-Outlook content with CSS background-image -->
<!--[if mso]>
</v:textbox>
</v:rect>
<![endif]-->
```

### Fill Types
- `type="frame"` — Stretch image to fill (background-size: cover equivalent)
- `type="tile"` — Repeat image (background-repeat: repeat)
- `type="solid"` — Solid color fill (no image)

### Fill Attributes
- `src` — Image URL
- `color` — Fallback solid color (shown while image loads)
- `opacity` — Fill opacity (0.0 to 1.0)

## VML Roundrect — Bulletproof Buttons

```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
  href="https://example.com/cta"
  style="height:44px; v-text-anchor:middle; width:200px;"
  arcsize="10%"
  strokecolor="#007bff"
  fillcolor="#007bff">
<center style="color:#ffffff; font-family:Arial,sans-serif;
  font-size:16px; font-weight:bold;">
  Button Text
</center>
</v:roundrect>
<![endif]-->
```

### Roundrect Attributes
- `arcsize` — Corner radius as percentage (e.g., `10%`, `50%` for pill shape)
- `fillcolor` — Background color
- `strokecolor` — Border color (set same as fillcolor for no visible border)
- `stroke="false"` — Remove border entirely
- `href` — Makes the entire VML shape a link

### Text Inside VML
Use `<center>` tag (not `<div>`) for text centering inside VML shapes.
Style text inline on the `<center>` element.

## VML Oval — Circular Elements

```html
<!--[if mso]>
<v:oval xmlns:v="urn:schemas-microsoft-com:vml"
  style="width:100px; height:100px;"
  fillcolor="#007bff" stroke="false">
<v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:false;">
<center style="color:#ffffff; font-family:Arial,sans-serif; font-size:24px;">
  1
</center>
</v:textbox>
</v:oval>
<![endif]-->
```

## VML Line — Decorative Separators

```html
<!--[if mso]>
<v:line xmlns:v="urn:schemas-microsoft-com:vml"
  from="0,0" to="600,0"
  strokecolor="#cccccc" strokeweight="1px">
</v:line>
<![endif]-->
```

## VML Textbox Best Practices

1. Always use `inset` attribute for internal padding: `inset="10px,10px,10px,10px"`
2. Use `mso-fit-shape-to-text:true` to auto-size VML container to content
3. Never use CSS `padding` inside VML — use `inset` instead
4. Content inside `<v:textbox>` is regular HTML — tables, text, images all work
5. Set `style="v-text-anchor:middle"` on parent shape for vertical centering

## Common VML Mistakes

1. **Missing closing tags** — All `<v:*>` elements must be explicitly closed
2. **Missing namespace** — VML without `xmlns:v` on `<html>` renders as text
3. **VML outside conditionals** — VML MUST be inside `<!--[if mso]>` blocks
4. **CSS padding in textbox** — Use `inset`, not CSS `padding`
5. **Incorrect fill type** — `type="frame"` for background images, not `type="tile"`
