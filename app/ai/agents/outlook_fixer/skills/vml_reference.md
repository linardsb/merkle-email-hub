---
version: "1.0.0"
---

<!-- L4 source: docs/SKILL_outlook-mso-fallback-reference.md sections 3-4 -->
<!-- Last synced: 2026-03-13 -->

# VML Reference — Shapes, Fills, Sub-Elements, and Textbox Patterns

VML (Vector Markup Language) is required for advanced Outlook rendering —
background images, rounded buttons, custom shapes. Outlook desktop uses the
Word rendering engine which supports VML natively.

## Required Namespace Declarations

Always add these to the `<html>` tag when using VML:
```html
<html xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word">
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

**Attributes:** `fill`, `stroke`, `strokecolor`, `strokeweight`, `fillcolor`, `href` (clickable), `style` (width/height), `coordorigin`, `coordsize`.

### Fill Types
- `type="frame"` — Stretch image to fill (background-size: cover equivalent)
- `type="tile"` — Repeat image (background-repeat: repeat)
- `type="solid"` — Solid color fill (no image)

## VML Roundrect — Bulletproof Buttons

```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
  xmlns:w="urn:schemas-microsoft-com:office:word"
  href="https://example.com/cta"
  style="height:44px; v-text-anchor:middle; width:200px;"
  arcsize="10%"
  strokecolor="#007bff"
  fillcolor="#007bff">
<w:anchorlock/>
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
<v:stroke dashstyle="solid"/>
</v:line>
<![endif]-->
```

## VML Group — Composite Shapes

Groups multiple VML elements for unified positioning:
```html
<!--[if mso]>
<v:group xmlns:v="urn:schemas-microsoft-com:vml"
  style="width:600px; height:400px;"
  coordorigin="0,0" coordsize="600,400">
  <v:rect ... />
  <v:oval ... />
</v:group>
<![endif]-->
```

## VML Shape — Custom Paths

```html
<!--[if mso]>
<v:shape xmlns:v="urn:schemas-microsoft-com:vml"
  style="width:600px; height:200px;"
  coordorigin="0,0" coordsize="600,200"
  path="m 0,0 l 600,0, 600,150, 300,200, 0,150 x e"
  fillcolor="#1a73e8" stroke="false">
<v:textbox inset="0,0,0,0"><!-- content --></v:textbox>
</v:shape>
<![endif]-->
```
Path commands: `m` = moveto, `l` = lineto, `c` = curveto, `x` = close, `e` = end.

## VML Sub-Elements

### `<v:fill>` — Fill Properties
The primary method for bulletproof background images in Outlook.

```html
<v:fill type="tile" src="https://example.com/bg.jpg"
  color="#cccccc" color2="#6ab7ff"
  size="600px,300px" aspect="atleast"
  origin="0.5,0.5" position="0.5,0.5" />
```

**Key attributes:**
- `type` — `"solid"`, `"tile"` (repeat), `"frame"` (stretch), `"gradient"`, `"gradientRadial"`
- `src` — Image URL for image fills
- `color` — Primary/fallback color
- `color2` — Secondary color (for gradients)
- `angle` — Gradient angle in degrees
- `opacity` — Fill opacity (`"0"` to `"1"`)
- `aspect` — `"ignore"` (stretch), `"atleast"` (fill/crop), `"atmost"` (fit within)
- `origin` / `position` — Image origin/position as fractions (`"0.5,0.5"` = center)
- `colors` — Multi-stop gradient: `"0% #ff0000, 50% #00ff00, 100% #0000ff"`
- `focus` / `focusposition` / `focussize` — Gradient focus control
- `method` — Gradient rendering: `"linear"`, `"sigma"`, `"any"`

### `<v:stroke>` — Border/Outline Properties

```html
<v:stroke dashstyle="solid" color="#cccccc"
  weight="1px" opacity="1" linestyle="single" />
```

**Key attributes:**
- `dashstyle` — `"solid"`, `"dot"`, `"dash"`, `"dashdot"`, `"longdash"`, `"longdashdot"`, or custom pattern
- `linestyle` — `"single"`, `"thinThin"`, `"thinThick"`, `"thickThin"`, `"thickBetweenThin"`
- `endcap` — `"flat"`, `"square"`, `"round"`
- `joinstyle` — `"round"`, `"bevel"`, `"miter"`
- `startarrow` / `endarrow` — `"none"`, `"block"`, `"classic"`, `"diamond"`, `"oval"`, `"open"`
- `startarrowwidth` / `endarrowwidth` — `"narrow"`, `"medium"`, `"wide"`
- `on` — `"true"` / `"false"` to enable/disable

### `<v:shadow>` — Drop Shadow

```html
<v:shadow on="true" type="single"
  color="#333333" opacity="0.5" offset="2px,2px" />
```

- `type` — `"single"`, `"double"`, `"perspective"`, `"emboss"`
- `offset` — Shadow offset (`"x,y"` in pixels)

### `<v:textbox>` — Text Container

```html
<v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
  <!-- HTML content goes here -->
</v:textbox>
```

- `inset` — Padding (`"top,right,bottom,left"` in px/pt). Use this, NOT CSS padding.
- `mso-fit-shape-to-text: true` — Expands shape to fit text (critical for responsive backgrounds)
- `v-text-anchor: top|middle|bottom` — Vertical text alignment

### `<v:imagedata>` — Image Data

```html
<v:imagedata src="https://example.com/image.jpg" o:title="Description" />
```

- `croptop` / `cropright` / `cropbottom` / `cropleft` — Image cropping (fractions)
- `gain` — Brightness, `blacklevel` — Contrast, `gamma` — Gamma correction

### `<w:anchorlock/>` — Prevent Resize

Essential inside VML buttons — prevents shape resize on user interaction:
```html
<v:roundrect ...>
  <w:anchorlock/>
  <center>Button Text</center>
</v:roundrect>
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
6. **Missing `<w:anchorlock/>`** — Buttons without it can be accidentally resized
7. **No fallback color** — Always set `color` on `<v:fill>` as image load fallback