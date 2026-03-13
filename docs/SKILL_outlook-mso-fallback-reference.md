# Outlook MSO Fallback — Complete Tag & Element Reference

Every Microsoft Office (MSO) conditional tag, VML element, MSO-specific CSS property, and Outlook rendering engine behavior used in HTML email development. These are rendered by Outlook's Word-based rendering engine (Outlook 2007–2021+ on Windows desktop).

---

## 1. MSO Conditional Comments

Outlook desktop (Windows) is the only email client that parses Microsoft conditional comments. These control what HTML Outlook sees vs what every other email client sees.

### Outlook-Only Content (Hidden from All Other Clients)
```html
<!--[if mso]>
  <!-- This content is ONLY rendered by Outlook desktop (Word engine) -->
<![endif]-->
```

### Non-Outlook Content (Hidden from Outlook)
```html
<!--[if !mso]><!-->
  <!-- This content is rendered by EVERYTHING EXCEPT Outlook desktop -->
<!--<![endif]-->
```

### Outlook Version Targeting
```html
<!--[if mso 12]>    Outlook 2007 only                    <![endif]-->
<!--[if mso 14]>    Outlook 2010 only                    <![endif]-->
<!--[if mso 15]>    Outlook 2013 only                    <![endif]-->
<!--[if mso 16]>    Outlook 2016, 2019, 2021, Office 365 <![endif]-->
```

### Outlook Version Range Targeting
```html
<!--[if gte mso 12]>   Outlook 2007 and above            <![endif]-->
<!--[if gte mso 14]>   Outlook 2010 and above            <![endif]-->
<!--[if gte mso 15]>   Outlook 2013 and above            <![endif]-->
<!--[if gte mso 16]>   Outlook 2016 and above            <![endif]-->
<!--[if lte mso 14]>   Outlook 2010 and below            <![endif]-->
<!--[if lte mso 15]>   Outlook 2013 and below            <![endif]-->
<!--[if lt mso 16]>    Below Outlook 2016                 <![endif]-->
<!--[if gt mso 14]>    Above Outlook 2010                 <![endif]-->
```

### Outlook + IE Targeting
```html
<!--[if mso | IE]>
  <!-- Rendered by Outlook desktop AND legacy Internet Explorer -->
<![endif]-->
```

### Conditional Comment Operators
- `mso` — matches any Outlook desktop version
- `mso XX` — matches exact Outlook version (12, 14, 15, 16)
- `gte mso XX` — greater than or equal to version
- `gt mso XX` — greater than version
- `lte mso XX` — less than or equal to version
- `lt mso XX` — less than version
- `!mso` — NOT Outlook (everything else)
- `mso | IE` — Outlook OR Internet Explorer
- `mso & IE` — Outlook AND Internet Explorer context (rare)

### Outlook Version Numbers
- `mso 9` — Outlook 2000
- `mso 10` — Outlook 2002/XP
- `mso 11` — Outlook 2003
- `mso 12` — Outlook 2007 (first Word rendering engine version)
- `mso 14` — Outlook 2010 (skipped 13)
- `mso 15` — Outlook 2013
- `mso 16` — Outlook 2016, 2019, 2021, and Microsoft 365 (all report as version 16)

---

## 2. MSO XML Namespace Declarations

These must be declared in the `<html>` tag or in a conditional `<xml>` block in the `<head>` for VML and Office-specific elements to render.

### On the `<html>` Tag
```html
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns:m="http://schemas.microsoft.com/office/2004/12/omml"
      xmlns:x="urn:schemas-microsoft-com:office:excel">
```

### Namespace Definitions
- `xmlns:v="urn:schemas-microsoft-com:vml"` — Vector Markup Language; required for all VML shapes, background images, rounded buttons
- `xmlns:o="urn:schemas-microsoft-com:office:office"` — Office namespace; required for `o:OfficeDocumentSettings`, `o:AllowPNG`, `o:PixelsPerInch`
- `xmlns:w="urn:schemas-microsoft-com:office:word"` — Word namespace; required for Word-specific rendering controls
- `xmlns:m="http://schemas.microsoft.com/office/2004/12/omml"` — Office Math Markup Language (rarely used in email)
- `xmlns:x="urn:schemas-microsoft-com:office:excel"` — Excel namespace (rarely used in email)

### Conditional XML Namespace Block in `<head>`
```html
<!--[if gte mso 9]>
<xml>
  <o:OfficeDocumentSettings>
    <o:AllowPNG/>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings>
</xml>
<![endif]-->
```

### Office Document Settings Elements
- `<o:OfficeDocumentSettings>` — container for Outlook rendering settings
- `<o:AllowPNG>` — enables PNG rendering in Outlook (without this, some Outlook versions may not render PNGs correctly)
- `<o:PixelsPerInch>96</o:PixelsPerInch>` — sets the DPI for rendering; prevents Outlook from scaling images on high-DPI displays; `96` is standard screen DPI

---

## 3. VML Elements (Vector Markup Language)

VML is the vector graphics language that Outlook's Word rendering engine uses instead of CSS for shapes, backgrounds, and rounded corners. VML is only rendered by Outlook desktop (Windows).

### `<v:rect>` — Rectangle
The most commonly used VML element in email. Primarily used for bulletproof background images on table cells.

```html
<!--[if gte mso 9]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml"
        fill="true"
        stroke="false"
        style="width:600px; height:300px;">
  <v:fill type="tile"
          src="https://example.com/bg-image.jpg"
          color="#cccccc" />
  <v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->
    <!-- HTML content goes here (visible to all clients) -->
<!--[if gte mso 9]>
  </v:textbox>
</v:rect>
<![endif]-->
```

**Attributes:**
- `fill="true"` / `fill="false"` — whether the rectangle has a fill
- `stroke="true"` / `stroke="false"` — whether the rectangle has a border stroke
- `strokecolor="#000000"` — border stroke color
- `strokeweight="1pt"` — border stroke thickness
- `style` — inline CSS for dimensions (`width`, `height`)
- `fillcolor="#cccccc"` — solid fill color (alternative to `<v:fill>` child element)
- `href="https://..."` — makes the entire rectangle a clickable link (useful for bulletproof buttons)
- `coordorigin` — coordinate system origin
- `coordsize` — coordinate system size

### `<v:roundrect>` — Rounded Rectangle
Used for bulletproof rounded buttons in Outlook. Outlook doesn't support CSS `border-radius`, so VML is the only way to achieve rounded corners.

```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
             xmlns:w="urn:schemas-microsoft-com:office:word"
             href="https://example.com/cta"
             style="height:44px; v-text-anchor:middle; width:200px;"
             arcsize="10%"
             strokecolor="#1a73e8"
             strokeweight="1px"
             fillcolor="#1a73e8">
  <w:anchorlock/>
  <center style="color:#ffffff; font-family:Arial,sans-serif; font-size:16px; font-weight:bold;">
    Shop Now
  </center>
</v:roundrect>
<![endif]-->
```

**Attributes:**
- `arcsize="10%"` — corner radius as percentage of the shortest side (e.g., `10%`, `20%`, `50%` for fully rounded pill shape)
- `href="https://..."` — makes the entire rounded rectangle a clickable link
- `fillcolor="#1a73e8"` — button background color
- `strokecolor="#1a73e8"` — button border color
- `strokeweight="1px"` — button border thickness
- `stroke="false"` — removes border entirely
- `style="height:44px; v-text-anchor:middle; width:200px;"` — dimensions and vertical text alignment

### `<v:oval>` — Ellipse/Circle
Used for circular shapes, circular buttons, or circular image masks in Outlook.

```html
<!--[if mso]>
<v:oval xmlns:v="urn:schemas-microsoft-com:vml"
        style="width:100px; height:100px;"
        fillcolor="#1a73e8"
        stroke="false">
  <v:textbox inset="0,0,0,0">
    <center>Text</center>
  </v:textbox>
</v:oval>
<![endif]-->
```

**Attributes:**
- `fillcolor` — fill color
- `strokecolor` — border color
- `strokeweight` — border thickness
- `stroke="false"` — no border
- `style` — dimensions

### `<v:line>` — Line
Used for decorative lines or custom dividers in Outlook.

```html
<!--[if mso]>
<v:line xmlns:v="urn:schemas-microsoft-com:vml"
        from="0,0"
        to="600,0"
        strokecolor="#cccccc"
        strokeweight="1px">
  <v:stroke dashstyle="solid"/>
</v:line>
<![endif]-->
```

**Attributes:**
- `from="x1,y1"` — line start coordinates
- `to="x2,y2"` — line end coordinates
- `strokecolor` — line color
- `strokeweight` — line thickness

### `<v:shape>` — Custom Shape
Used for complex custom shapes, custom paths, and advanced vector graphics.

```html
<!--[if mso]>
<v:shape xmlns:v="urn:schemas-microsoft-com:vml"
         style="width:600px; height:200px;"
         coordorigin="0,0"
         coordsize="600,200"
         path="m 0,0 l 600,0, 600,150, 300,200, 0,150 x e"
         fillcolor="#1a73e8"
         stroke="false">
  <v:textbox inset="0,0,0,0">
    <!-- content -->
  </v:textbox>
</v:shape>
<![endif]-->
```

**Attributes:**
- `path` — SVG-like path commands for custom shapes (`m` = moveto, `l` = lineto, `c` = curveto, `x` = close, `e` = end)
- `coordorigin` — coordinate origin point
- `coordsize` — coordinate system dimensions
- `fillcolor` — shape fill color
- `strokecolor` — shape border color
- `strokeweight` — shape border thickness
- `style` — dimensions and positioning

### `<v:image>` — Image
Used for images within VML shapes or as standalone VML image elements.

```html
<!--[if mso]>
<v:image xmlns:v="urn:schemas-microsoft-com:vml"
         src="https://example.com/image.jpg"
         style="width:600px; height:300px;" />
<![endif]-->
```

**Attributes:**
- `src` — image URL
- `style` — dimensions
- `alt` — alternative text

### `<v:group>` — Group Container
Groups multiple VML elements together so they can be positioned and transformed as a unit.

```html
<!--[if mso]>
<v:group xmlns:v="urn:schemas-microsoft-com:vml"
         style="width:600px; height:400px;"
         coordorigin="0,0"
         coordsize="600,400">
  <v:rect ... />
  <v:oval ... />
  <v:shape ... />
</v:group>
<![endif]-->
```

**Attributes:**
- `coordorigin` — coordinate system origin for the group
- `coordsize` — coordinate system dimensions
- `style` — group dimensions

### `<v:polyline>` — Polyline
A series of connected line segments. Used for custom decorative shapes.

```html
<!--[if mso]>
<v:polyline xmlns:v="urn:schemas-microsoft-com:vml"
            points="0,0 100,50 200,0 300,50"
            strokecolor="#cccccc"
            strokeweight="2px"
            fill="false">
</v:polyline>
<![endif]-->
```

**Attributes:**
- `points` — series of x,y coordinates
- `strokecolor` — line color
- `strokeweight` — line thickness
- `filled="false"` / `fill="false"` — no fill (outline only)

### `<v:arc>` — Arc
A curved arc segment.

**Attributes:**
- `startangle` — arc start angle in degrees
- `endangle` — arc end angle in degrees
- `style` — dimensions
- `fillcolor` — fill color
- `strokecolor` — border color

### `<v:curve>` — Bezier Curve
A bezier curve shape.

**Attributes:**
- `from` — start point
- `to` — end point
- `control1` — first control point
- `control2` — second control point
- `strokecolor` — curve color
- `strokeweight` — curve thickness

---

## 4. VML Sub-Elements (Child Elements)

These elements are placed inside VML shape elements to control fill, stroke, shadow, text, and other properties.

### `<v:fill>` — Fill Properties
Controls the fill of a VML shape. The primary method for bulletproof background images in Outlook.

```html
<v:fill type="tile"
        src="https://example.com/background.jpg"
        color="#cccccc"
        size="600px,300px"
        aspect="atleast"
        origin="0.5,0.5"
        position="0.5,0.5" />
```

**Attributes:**
- `type` — fill type:
  - `"solid"` — solid color fill
  - `"tile"` — tiled/repeated image fill (most common for email background images)
  - `"frame"` — stretched image fill (scales image to fit shape)
  - `"pattern"` — pattern fill
  - `"gradient"` — gradient fill (see gradient attributes below)
  - `"gradientRadial"` — radial gradient fill
  - `"gradientTitle"` — title gradient
- `src` — image URL for image-based fills
- `color` — primary fill color (also serves as fallback if image fails to load)
- `color2` — secondary fill color (for gradients)
- `size` — image size for fill
- `aspect` — image aspect ratio behavior:
  - `"ignore"` — stretch to fit
  - `"atleast"` — fill at least the shape area (crop if needed)
  - `"atmost"` — fit within the shape area
- `origin` — image origin point (fraction: `"0.5,0.5"` = center)
- `position` — image position within shape (fraction: `"0.5,0.5"` = center)
- `opacity` — fill opacity (`"0"` to `"1"` or `"0%"` to `"100%"`)
- `angle` — gradient angle in degrees (for gradient fills)
- `focus` — gradient focus point (percentage, `"0%"` to `"100%"`)
- `focusposition` — gradient focus position
- `focussize` — gradient focus size
- `colors` — multi-stop gradient color definition (e.g., `"0% #ff0000, 50% #00ff00, 100% #0000ff"`)
- `method` — gradient rendering method (`"linear"`, `"sigma"`, `"any"`, `"none"`)

### `<v:stroke>` — Stroke/Border Properties
Controls the border/outline of a VML shape.

```html
<v:stroke dashstyle="solid"
          color="#cccccc"
          weight="1px"
          opacity="1"
          linestyle="single" />
```

**Attributes:**
- `dashstyle` — line pattern:
  - `"solid"` — solid line
  - `"dot"` — dotted line
  - `"dash"` — dashed line
  - `"dashdot"` — dash-dot pattern
  - `"longdash"` — long dashed line
  - `"longdashdot"` — long dash-dot pattern
  - `"longdashdotdot"` — long dash-dot-dot pattern
  - Custom pattern (space-separated numbers defining dash/gap lengths)
- `color` — stroke color
- `weight` — stroke thickness
- `opacity` — stroke opacity
- `linestyle` — line style:
  - `"single"` — single line
  - `"thinThin"` — double thin lines
  - `"thinThick"` — thin then thick line
  - `"thickThin"` — thick then thin line
  - `"thickBetweenThin"` — thick line between two thin lines
- `endcap` — line end style (`"flat"`, `"square"`, `"round"`)
- `joinstyle` — line join style (`"round"`, `"bevel"`, `"miter"`)
- `startarrow` — arrow at line start (`"none"`, `"block"`, `"classic"`, `"diamond"`, `"oval"`, `"open"`)
- `endarrow` — arrow at line end (same values)
- `startarrowwidth` — start arrow size (`"narrow"`, `"medium"`, `"wide"`)
- `endarrowwidth` — end arrow size (same values)
- `startarrowlength` — start arrow length (`"short"`, `"medium"`, `"long"`)
- `endarrowlength` — end arrow length (same values)
- `on="true"` / `on="false"` — enable/disable stroke

### `<v:shadow>` — Shadow Properties
Adds drop shadow to VML shapes.

```html
<v:shadow on="true"
          type="single"
          color="#333333"
          opacity="0.5"
          offset="2px,2px" />
```

**Attributes:**
- `on="true"` / `on="false"` — enable/disable shadow
- `type` — shadow type:
  - `"single"` — simple drop shadow
  - `"double"` — double shadow
  - `"perspective"` — perspective shadow
  - `"emboss"` — embossed shadow
- `color` — shadow color
- `opacity` — shadow opacity
- `offset` — shadow offset (`"x,y"` in pixels)
- `origin` — shadow origin point
- `matrix` — transformation matrix for perspective shadows

### `<v:textbox>` — Text Container
Contains HTML text content inside a VML shape. This is how text is overlaid on VML background images.

```html
<v:textbox inset="0,0,0,0"
           style="mso-fit-shape-to-text:true;">
  <!-- HTML content goes here -->
</v:textbox>
```

**Attributes:**
- `inset` — text padding inside the shape (`"top,right,bottom,left"` or `"all"`) — in pixels or points (e.g., `"10px,20px,10px,20px"` or `"0,0,0,0"`)
- `style` — MSO-specific CSS properties:
  - `mso-fit-shape-to-text: true` — expands the VML shape to fit the text content height; critical for responsive background images that need to grow with content
  - `v-text-anchor: top` / `middle` / `bottom` — vertical text alignment within the shape

### `<v:imagedata>` — Image Data
Alternative to `<v:fill>` for embedding image data in a VML shape.

```html
<v:imagedata src="https://example.com/image.jpg"
             o:title="Description" />
```

**Attributes:**
- `src` — image URL
- `o:title` — image title/alt text
- `croptop` / `cropright` / `cropbottom` / `cropleft` — image cropping (fraction values)
- `gain` — image brightness
- `blacklevel` — image contrast/black level
- `gamma` — image gamma correction

### `<v:formulas>` — Shape Formulas
Mathematical formulas used to define custom shape paths dynamically.

```html
<v:formulas>
  <v:f eqn="sum width 0 #0"/>
  <v:f eqn="prod #0 1 2"/>
  <v:f eqn="sum height 0 #1"/>
</v:formulas>
```

### `<v:path>` — Path Definition
Defines the shape's path as a child element (alternative to the `path` attribute on `<v:shape>`).

```html
<v:path v="m 0,0 l 600,0, 600,200, 0,200 x e"
        textboxrect="0,0,600,200" />
```

**Attributes:**
- `v` — path commands (same syntax as `path` attribute)
- `textboxrect` — defines the area within the shape where text content is placed
- `limo` — defines the stretch points of the shape
- `fillok="true"` / `"false"` — whether path can be filled
- `strokeok="true"` / `"false"` — whether path can be stroked
- `shadowok="true"` / `"false"` — whether path can have a shadow

### `<v:handles>` and `<v:h>` — Shape Adjustment Handles
Define interactive adjustment handles for shapes (rarely used in email, but part of VML spec).

### `<v:extrusion>` — 3D Extrusion
Adds 3D depth to VML shapes (rarely used in email).

---

## 5. Office/Word Sub-Elements (`o:` and `w:` namespace)

### `<o:OfficeDocumentSettings>` — Document-Level Settings
```html
<o:OfficeDocumentSettings>
  <o:AllowPNG/>
  <o:PixelsPerInch>96</o:PixelsPerInch>
  <o:TargetScreenSize>1024x768</o:TargetScreenSize>
</o:OfficeDocumentSettings>
```

- `<o:AllowPNG/>` — enables PNG image support in Outlook
- `<o:PixelsPerInch>96</o:PixelsPerInch>` — sets DPI to standard 96; prevents high-DPI scaling that distorts email layout
- `<o:TargetScreenSize>` — target display resolution (rarely used)

### `<w:anchorlock/>` — Anchor Lock
Prevents the VML shape from being resized or moved when the user interacts with it in Outlook. Essential inside VML buttons.

```html
<v:roundrect ...>
  <w:anchorlock/>
  <center>Button Text</center>
</v:roundrect>
```

### `<o:lock>` — Element Lock
Locks specific properties of a VML element.

```html
<o:lock v:ext="edit"
        aspectratio="true"
        shapetype="true" />
```

**Attributes:**
- `aspectratio="true"` — locks aspect ratio
- `shapetype="true"` — locks shape type
- `selection="true"` — prevents selection
- `text="true"` — locks text editing

### `<o:column>` and `<o:row>` — Table Helpers
Office-specific table structure helpers (rarely used directly in email HTML).

---

## 6. MSO-Specific CSS Properties

These CSS properties are only understood by Outlook's Word rendering engine. They are placed in inline `style` attributes and are ignored by all other email clients.

### Table & Layout Properties
- `mso-table-lspace: 0pt` — removes default left spacing on tables; Outlook adds extra space around tables by default
- `mso-table-rspace: 0pt` — removes default right spacing on tables
- `mso-table-anchor-horizontal: column` — horizontal anchor point for table positioning
- `mso-table-anchor-vertical: paragraph` — vertical anchor point for table positioning
- `mso-table-bspace: 0pt` — bottom spacing on tables
- `mso-table-tspace: 0pt` — top spacing on tables
- `mso-cellspacing: 0` — cell spacing override
- `mso-padding-alt: 0` — alternative padding value (overrides CSS `padding` for Outlook)
- `mso-padding-top-alt: 10px` — Outlook-specific top padding override
- `mso-padding-right-alt: 10px` — Outlook-specific right padding override
- `mso-padding-bottom-alt: 10px` — Outlook-specific bottom padding override
- `mso-padding-left-alt: 10px` — Outlook-specific left padding override
- `mso-border-alt: solid #000000 1px` — alternative border shorthand for Outlook (overrides CSS `border`)
- `mso-border-top-alt` — top border override
- `mso-border-right-alt` — right border override
- `mso-border-bottom-alt` — bottom border override
- `mso-border-left-alt` — left border override

### Text & Font Properties
- `mso-line-height-rule: exactly` — forces Outlook to render exact line-height values instead of approximating; without this, Outlook may add extra vertical space
- `mso-line-height-rule: at-least` — minimum line height (Outlook default)
- `mso-text-raise: 10px` — raises text vertically within its container; used for fine-tuning vertical alignment in table cells
- `mso-font-width: 100%` — controls font width/scaling; prevents Outlook from auto-adjusting font width
- `mso-ansi-font-size: 16px` — ANSI character set font size
- `mso-bidi-font-size: 16px` — bidirectional text font size
- `mso-font-alt: Arial` — alternative font for Outlook
- `mso-generic-font-family: swiss` — generic font family hint (`swiss`, `roman`, `modern`, `script`, `decorative`)
- `mso-font-charset: 0` — character set number
- `mso-font-pitch: variable` — font pitch (`variable`, `fixed`)
- `mso-font-signature: ...` — font signature (Unicode range support)
- `mso-ansi-language: EN-US` — language for ANSI text
- `mso-bidi-language: AR-SA` — language for bidirectional text
- `mso-fareast-language: JA` — language for Far East text
- `mso-text-indent-alt: 0` — alternative text indent value
- `mso-char-indent-count: 0` — character indent count
- `mso-char-indent-size: 0` — character indent size
- `mso-ascii-font-family: Arial` — font for ASCII characters
- `mso-hansi-font-family: Arial` — font for high-ANSI characters
- `mso-bidi-font-family: Arial` — font for bidirectional characters
- `mso-fareast-font-family: "MS Gothic"` — font for Far East characters

### Spacing & Margin Properties
- `mso-margin-top-alt: 0` — Outlook-specific top margin override
- `mso-margin-bottom-alt: 0` — Outlook-specific bottom margin override
- `mso-para-margin: 0` — paragraph margin override
- `mso-para-margin-top: 0` — paragraph top margin
- `mso-para-margin-right: 0` — paragraph right margin
- `mso-para-margin-bottom: 0` — paragraph bottom margin
- `mso-para-margin-left: 0` — paragraph left margin
- `mso-element: para-border-div` — paragraph border container
- `mso-element-frame-width: 600px` — frame element width
- `mso-element-wrap: around` — text wrap around element
- `mso-element-anchor-vertical: paragraph` — vertical anchor
- `mso-element-anchor-horizontal: column` — horizontal anchor
- `mso-element-top: 0` — top position
- `mso-element-left: 0` — left position
- `mso-height-rule: exactly` — forces exact height rendering (similar to line-height-rule)
- `mso-width-source: auto` — width calculation source
- `mso-width-alt: 6000` — alternative width value in twentieths of a point (1/20 pt)

### Visibility & Display Properties
- `mso-hide: all` — hides the element from Outlook rendering; does NOT hide from screen readers; the element is invisible in Outlook but other clients render it normally
- `mso-special-character: line-break` — forces a line break
- `mso-special-character: column-break` — forces a column break
- `mso-break-type: section-break` — forces a section break
- `mso-column-break-before: always` — column break before element

### Style/Appearance Properties
- `mso-style-name: "Normal"` — applies a named Word style
- `mso-style-type: export-only` — style is for export only
- `mso-style-link: "Heading 1 Char"` — links character style to paragraph style
- `mso-style-priority: 99` — style priority
- `mso-style-unhide: no` — whether style is visible
- `mso-style-parent: ""` — parent style inheritance
- `mso-outline-level: 1` — outline level for headings
- `mso-list: l0 level1 lfo1` — list formatting (level, format override)
- `mso-shading: white` — background shading color
- `mso-pattern: solid` — background pattern type

### VML Style Properties (Used inside VML `style` attributes)
- `v-text-anchor: top` / `middle` / `bottom` — vertical text alignment within VML shapes
- `mso-fit-shape-to-text: true` — expands VML shape height to fit contained text; critical for responsive VML background images
- `mso-width-percent: 1000` — width as percentage (1000 = 100%)
- `mso-height-percent: 0` — height as percentage
- `mso-width-relative: margin` — width relative to margin/page/etc.
- `mso-height-relative: margin` — height relative to margin/page/etc.
- `mso-position-horizontal: center` — horizontal position
- `mso-position-horizontal-relative: page` — horizontal position reference
- `mso-position-vertical: center` — vertical position
- `mso-position-vertical-relative: page` — vertical position reference
- `mso-wrap-style: square` — text wrap style
- `mso-wrap-distance-left: 0` — left wrap distance
- `mso-wrap-distance-right: 0` — right wrap distance
- `mso-wrap-distance-top: 0` — top wrap distance
- `mso-wrap-distance-bottom: 0` — bottom wrap distance
- `rotation: 45` — shape rotation in degrees

---

## 7. MSO Conditional `<style>` Block Properties

These are placed in a conditional `<style>` block in the `<head>` targeting Outlook only.

```html
<!--[if mso]>
<style type="text/css">
  /* Outlook-only CSS */
  body { ... }
  table { ... }
  td { ... }
  a { ... }
  h1, h2, h3 { ... }
  p { ... }
  .outlook-fallback { ... }
</style>
<![endif]-->
```

### Common MSO `<style>` Block Resets
- `body { margin: 0; padding: 0; }` — reset Outlook body defaults
- `table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }` — remove Outlook table gaps
- `td { border-collapse: collapse; }` — consistent cell rendering
- `img { -ms-interpolation-mode: bicubic; }` — smooth image scaling in Outlook
- `a { color: #1a73e8; text-decoration: underline; }` — consistent link styles (Outlook may override)
- `p { margin: 0; padding: 0; mso-line-height-rule: exactly; }` — reset paragraph defaults
- `h1, h2, h3, h4, h5, h6 { margin: 0; padding: 0; }` — reset heading defaults
- `span.MsoHyperlink { color: inherit !important; mso-style-priority: 99 !important; }` — prevents Outlook from overriding link colors with its default blue
- `span.MsoHyperlinkFollowed { color: inherit !important; mso-style-priority: 99 !important; }` — prevents Outlook from applying visited link purple color
- `.ExternalClass { width: 100%; }` — forces Outlook.com to honor full width
- `.ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div { line-height: 100%; }` — fixes Outlook.com line-height bug

### Image Rendering Property
- `-ms-interpolation-mode: bicubic` — forces smooth bicubic image scaling in Outlook instead of default nearest-neighbor; prevents pixelated images when Outlook resizes them

---

## 8. Outlook-Specific HTML Workarounds

These are standard HTML elements and attributes that behave differently in Outlook or are specifically required for Outlook rendering.

### Table Attributes Required for Outlook
- `cellpadding="0"` — must be set as HTML attribute, not just CSS padding
- `cellspacing="0"` — must be set as HTML attribute, not just CSS
- `border="0"` — must be set as HTML attribute
- `width="600"` — numeric pixel value as HTML attribute; Outlook may ignore CSS `width` on tables
- `align="center"` — HTML attribute for centering; Outlook may ignore CSS `margin: 0 auto`
- `bgcolor="#ffffff"` — HTML attribute for background color; more reliable than CSS `background-color` in Outlook
- `valign="top"` — HTML attribute for vertical alignment; more reliable than CSS `vertical-align` in Outlook

### Image Attributes Required for Outlook
- `width="600"` — HTML attribute (number only, no `px`); Outlook requires this to size images correctly
- `height="300"` — HTML attribute; prevents Outlook from collapsing images to 0 height
- `border="0"` — prevents blue borders on linked images in Outlook
- `style="display: block;"` — prevents Outlook from adding gaps below images
- `style="-ms-interpolation-mode: bicubic;"` — smooth scaling

### Outlook-Specific Line Breaks
- `<!--[if mso]>&nbsp;<![endif]-->` — MSO-specific spacer to force height in empty cells
- `&#8203;` (zero-width space) — prevents Outlook from collapsing empty table cells while remaining invisible

### Outlook Ghost Table Pattern
The most common MSO conditional pattern: wrapping fluid/hybrid content in a fixed-width table for Outlook while other clients get the fluid layout.

```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" align="center">
<tr>
<td width="300" valign="top">
<![endif]-->
  <div style="display: inline-block; width: 100%; max-width: 300px; vertical-align: top;">
    <!-- Column 1 content -->
  </div>
<!--[if mso]>
</td>
<td width="300" valign="top">
<![endif]-->
  <div style="display: inline-block; width: 100%; max-width: 300px; vertical-align: top;">
    <!-- Column 2 content -->
  </div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

### Outlook-Specific Spacer Patterns
```html
<!-- Fixed-height spacer for Outlook -->
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
<tr><td style="height: 20px; font-size: 1px; line-height: 1px;">&nbsp;</td></tr>
</table>
<![endif]-->
```

### Outlook DPI Scaling Fix
```html
<!--[if gte mso 9]>
<xml>
  <o:OfficeDocumentSettings>
    <o:AllowPNG/>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings>
</xml>
<![endif]-->
```

---

## 9. Outlook.com / Hotmail Specific (Not MSO Conditional)

Outlook.com (webmail) is NOT the same as Outlook desktop. It does NOT use the Word rendering engine and does NOT parse MSO conditional comments or VML. However, it has its own quirks.

### Outlook.com Dark Mode Selectors
- `[data-ogsc]` — Outlook.com dark mode: overrides foreground/text colors
- `[data-ogsb]` — Outlook.com dark mode: overrides background colors
- These can be used in the `<style>` block to target Outlook.com dark mode specifically

```html
<style>
  [data-ogsc] .dark-text { color: #ffffff !important; }
  [data-ogsb] .dark-bg { background-color: #1a1a1a !important; }
</style>
```

### Outlook.com Specific CSS Fixes
- `.ExternalClass { width: 100%; }` — forces Outlook.com wrapper to full width
- `.ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div { line-height: 100%; }` — fixes Outlook.com line-height inheritance bug where it adds extra spacing

### Outlook.com MsoHyperlink Override
```html
<style>
  span.MsoHyperlink { color: inherit !important; }
  span.MsoHyperlinkFollowed { color: inherit !important; }
</style>
```
- Outlook.com wraps links in `<span class="MsoHyperlink">` and forces its own blue color; these overrides prevent that

---

## 10. MSO Conditional Pattern Library

### Bulletproof VML Background Image
```html
<!--[if gte mso 9]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:300px;">
  <v:fill type="frame" src="https://example.com/bg.jpg" color="#cccccc" />
  <v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->
<div style="background-image: url('https://example.com/bg.jpg'); background-color: #cccccc; background-size: cover;">
  <!-- Content here (visible in all clients) -->
</div>
<!--[if gte mso 9]>
  </v:textbox>
</v:rect>
<![endif]-->
```

### Bulletproof VML Rounded Button
```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="https://example.com" style="height:44px;v-text-anchor:middle;width:200px;" arcsize="10%" strokecolor="#1a73e8" fillcolor="#1a73e8">
  <w:anchorlock/>
  <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">Shop Now</center>
</v:roundrect>
<![endif]-->
<!--[if !mso]><!-->
<a href="https://example.com" style="display: inline-block; padding: 12px 40px; background-color: #1a73e8; color: #ffffff; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; text-decoration: none; border-radius: 5px;">Shop Now</a>
<!--<![endif]-->
```

### Outlook Fixed-Width Column Fallback
```html
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center">
<tr>
<td width="290" valign="top">
<![endif]-->
<div style="display:inline-block; max-width:290px; width:100%; vertical-align:top;">
  <!-- Column content -->
</div>
<!--[if mso]>
</td>
<td width="20"></td>
<td width="290" valign="top">
<![endif]-->
<div style="display:inline-block; max-width:290px; width:100%; vertical-align:top;">
  <!-- Column content -->
</div>
<!--[if mso]>
</td>
</tr>
</table>
<![endif]-->
```

### Outlook Max-Width Fallback
Outlook doesn't support CSS `max-width`. This pattern provides a fixed-width fallback.

```html
<!--[if mso]>
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center"><tr><td>
<![endif]-->
<div style="max-width: 600px; margin: 0 auto;">
  <!-- Email content -->
</div>
<!--[if mso]>
</td></tr></table>
<![endif]-->
```

### Outlook Image Scaling Fix
```html
<!--[if gte mso 9]>
<style type="text/css">
  img { -ms-interpolation-mode: bicubic; }
</style>
<![endif]-->
```

### Outlook VML Gradient Background
```html
<!--[if gte mso 9]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:200px;">
  <v:fill type="gradient" color="#1a73e8" color2="#6ab7ff" angle="90" />
  <v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:true;">
<![endif]-->
<div style="background: linear-gradient(90deg, #1a73e8, #6ab7ff);">
  <!-- Content -->
</div>
<!--[if gte mso 9]>
  </v:textbox>
</v:rect>
<![endif]-->
```

### Outlook-Only Spacer Row
```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
<td style="height:30px; font-size:1px; line-height:1px; mso-line-height-rule:exactly;">&nbsp;</td>
</tr></table>
<![endif]-->
```

### Outlook-Only Horizontal Rule
```html
<!--[if mso]>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" align="center"><tr>
<td style="border-top:1px solid #cccccc; font-size:1px; line-height:1px; height:1px; mso-line-height-rule:exactly;">&nbsp;</td>
</tr></table>
<![endif]-->
```

### Full MSO Namespace Setup
```html
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office"
      lang="en" dir="ltr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Email Title</title>
  <!--[if gte mso 9]>
  <xml>
    <o:OfficeDocumentSettings>
      <o:AllowPNG/>
      <o:PixelsPerInch>96</o:PixelsPerInch>
    </o:OfficeDocumentSettings>
  </xml>
  <![endif]-->
  <!--[if mso]>
  <style type="text/css">
    body, table, td, a, p { font-family: Arial, Helvetica, sans-serif; }
    table { border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    img { -ms-interpolation-mode: bicubic; border: 0; outline: none; }
    p { margin: 0; padding: 0; mso-line-height-rule: exactly; }
    span.MsoHyperlink { color: inherit !important; }
    span.MsoHyperlinkFollowed { color: inherit !important; }
  </style>
  <![endif]-->
</head>
```

---

## 11. Properties Outlook Ignores (Requiring MSO Fallbacks)

These standard CSS properties do NOT work in Outlook desktop, which is why MSO fallbacks exist.

- `max-width` — ignored; use MSO conditional fixed-width table
- `min-width` — ignored
- `border-radius` — ignored; use VML `<v:roundrect>` with `arcsize`
- `background-image` (CSS) — ignored on most elements; use VML `<v:rect>` with `<v:fill>`
- `background-size` — ignored; VML `<v:fill>` with `type="frame"` or `type="tile"`
- `background-position` — ignored; VML `<v:fill>` with `origin` and `position`
- `background` shorthand — partially ignored; `background-color` works but image properties don't
- `box-shadow` — ignored; use VML `<v:shadow>`
- `text-shadow` — ignored; no VML equivalent
- `opacity` — ignored on HTML elements; VML shapes support opacity on `<v:fill>` and `<v:stroke>`
- `rgba()` colors — ignored; use hex colors
- `linear-gradient()` — ignored; use VML `<v:fill type="gradient">`
- `radial-gradient()` — ignored; use VML `<v:fill type="gradientRadial">`
- `display: flex` — ignored; use table layout
- `display: grid` — ignored; use table layout
- `float` — unreliable; use table `align` attribute or VML
- `position: absolute/relative/fixed` — ignored; use table-based positioning
- `margin` on `<div>` — often ignored; use table cell padding
- `padding` on `<div>` — often ignored; use `<td>` padding or MSO padding-alt
- `calc()` — ignored
- `object-fit` — ignored
- `clip-path` — ignored
- `@media` queries — ignored; Outlook renders the base inline styles only
- `animation` / `@keyframes` — ignored
- `transition` — ignored
- `transform` — ignored
- `:hover` — ignored
- `line-height` (sometimes unreliable) — use `mso-line-height-rule: exactly` to force correct rendering

---

*Total MSO/Outlook-specific elements, attributes, properties, and patterns: 300+*
