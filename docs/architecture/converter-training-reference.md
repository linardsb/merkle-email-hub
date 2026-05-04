# Converter Engine Training Reference — Phase 40

Three real-world campaign HTMLs built from the component library, each showing how generic components are adapted to match a specific Figma design. This document is the learning material for the converter engine: it maps every section of every email back to its source component, lists every modification made, and explains the design reasoning.

> **Important: This is training data, not a specification.**
> The brand names, hex codes, font stacks, copy, and image paths in these examples are **illustrative, not prescriptive**. The converter engine and AI agents must treat them as examples of *transformation patterns* — the types of modifications that happen when a generic component is adapted to match a Figma design. The converter output is **client-agnostic and design-agnostic**: it reads any Figma file, extracts the design tokens (colors, fonts, sizes, spacing, layout), matches sections to the correct base component, and applies overrides dynamically. Never hard-code or memorise the specific brand values from these examples.
>
> **What to learn from these files:**
> - The *categories* of change (color override, font swap, size adjustment, structural adaptation, VML upgrade, mobile reflow pattern)
> - Which base component maps to which visual pattern in a design
> - When a component needs structural changes vs. just style overrides
> - When no single component fits and a bespoke composition is needed
>
> **What NOT to learn:**
> - Specific hex values, font names, or copy text
> - That a heading is always 40px or a button is always a pill
> - That footers are always white or always black
> - Any assumption tied to Starbucks, Mammut, or MAAP specifically

---

## Files in This Folder

| File | Campaign | Brand | Sections | Figma Source |
|------|----------|-------|----------|--------------|
| `starbucks-pumpkin-spice.html` | Starbucks — Pumpkin Now, Peppermint On The Way | Starbucks | 9 | [node-id=2833-1424](https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1424&t=XbSk3G2DSZJWoweH-0) |
| `mammut-duvet-day.html` | Mammut — Grab A Duvet Day | Mammut | 18 | [node-id=2833-1135](https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1135&t=XbSk3G2DSZJWoweH-0) |
| `maap-kask.html` | MAAP x KASK — New Season Collaboration | MAAP | 13 | [node-id=2833-1623](https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1623&t=XbSk3G2DSZJWoweH-0) |

### Figma File

All three campaigns live in the same Figma file:
- **File:** `The Ultimate Email Design System (Community)`
- **File ID:** `VUlWjZGAEVZr3mK1EawsYR`
- **Node IDs:** Starbucks `2833-1424` / Mammut `2833-1135` / MAAP `2833-1623`

---

## How to Read This Document

Each campaign section below is annotated with:
1. **Source component** — the base `.html` file from `email-templates/components/`
2. **Slot fills** — which `data-slot` values were populated
3. **Structural changes** — any modifications to the component's table/td structure
4. **Style overrides** — colors, fonts, sizes, spacing, alignment that differ from defaults
5. **Design reasoning** — why the change was needed to match the Figma

---

## 1. Starbucks — Pumpkin Spice (`starbucks-pumpkin-spice.html`)

### Shell
| Property | Component default | Starbucks override |
|----------|------------------|--------------------|
| Source component | `email-shell.html` | — |
| `color-scheme` | `light dark` | `light dark` (kept) |
| `<title>` | `Email` | `Starbucks — Pumpkin Now, Peppermint On The Way` |
| Preheader text | `Preview text goes here` | `Pumpkin now, peppermint on the way...` |
| Font stack | system stack | `'SoDo Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` |
| Dark mode | `@media (prefers-color-scheme: dark)` | Kept — full component dark mode class system |

### Section 1 — Hero Image
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `full-width-image.html` | — |
| Image src | `placeholder.com/600x300` | `data/debug/6/assets/2833_1425.png` |
| Alt text | `Full width image` | `Starbucks — Pumpkin Spice Latte with whipped cream` |
| Link wrapper | `href="https://example.com"` | `href="#"` (placeholder) |
| Structural | Identical to component | No changes |

### Section 2 — Heading (PUMPKIN NOW, PEPPERMINT ON THE WAY)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `heading.html` | — |
| `bgcolor` | `#ffffff` | `#F2F0EB` (Starbucks warm cream) |
| Font size | `24px` | `40px` |
| Line height | `28px` | `44px` |
| Color | `#1A1A1A` | `#1e3932` (Starbucks green) |
| Font weight | `<strong>` tag wrapping | `font-weight: 900` inline style |
| Letter spacing | none | `-0.5px` |
| Text align | `left` | `center` |
| Padding top | `0` | `40px` |
| Content | Lorem ipsum | `PUMPKIN NOW, PEPPERMINT ON THE WAY` |
| Removed | `id="vwh"` attribute | Not needed |

### Section 3 — Paragraph (italic body text)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `paragraph.html` | — |
| `bgcolor` | `#ffffff` | `#F2F0EB` |
| Font size | `14px` | `16px` |
| Line height | `21px` | `26px` |
| Color | `#1A1A1A` | `#1e3932` |
| Font style | normal | `italic` |
| Text align | `left` | `center` |
| Padding top | `0` | `20px` |
| Font stack | system stack | SoDo Sans + system stack |
| Removed | `id="vwp"` attribute | Not needed |

### Section 4 — Button (Order your fall favorite)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `button-filled.html` | Completely rewritten |
| **Structural change** | Simple table-based button | VML `v:roundrect` for Outlook + `<a>` fallback for modern clients |
| Width | `170px` | `240px` |
| Height | `35px` | `48px` |
| Border radius | `10px` | `25px` (pill shape) |
| Background color | `#1a1a1a` | `#1e3932` (Starbucks green) |
| Font family | Helvetica | SoDo Sans stack |
| Font size | `15px` | `16px` |
| Font weight | default | `600` (semi-bold) |
| Text transform | `uppercase` | normal case |
| `bgcolor` on wrapper | `#ffffff` | `#F2F0EB` |
| Padding | `0` | `28px top / 40px bottom` |
| **Design reasoning** | Generic button upgraded to bulletproof VML rounded button for Outlook compatibility with pill shape matching Starbucks brand |

### Section 5 — Two-Column Layout (Holiday Countdown)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `column-layout-2.html` | Heavily customized |
| Column widths | `300px / 300px` | `264px / 292px` (asymmetric for image/text balance) |
| Background | `#ffffff` | `#AA1733` (holiday red) |
| Padding | none | `30px 20px` |
| Vertical align | `top` | `middle` (centers content vertically) |
| Col 1 content | text placeholder | `<img>` — calendar countdown image |
| Col 2 content | text placeholder | Heading + paragraph + ghost CTA button |
| Col 2 heading font | system stack | `'Lander Grande', Georgia, 'Times New Roman', serif` (Starbucks serif) |
| Col 2 heading size | — | `28px/32px`, `700 weight` |
| Col 2 body text | — | `14px/20px`, white |
| Col 2 CTA | — | Ghost pill button: `2px solid #ffffff`, `border-radius: 25px`, `221x40`, with VML fallback |
| **Design reasoning** | Base 2-col is equal-width and empty. Starbucks design requires image-heavy left + text-right with a deep brand-color background, asymmetric widths, and a nested ghost CTA — all computed from the Figma layout |

### Section 6 — Four-Column Navigation Bar (APP | ORDER | OFFERS | REWARDS)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `column-layout-4.html` + `navigation-bar.html` | Hybrid — neither component alone |
| **Structural change** | Completely custom: desktop = single `<table>` row with 4 image cells + 3 vertical-divider `<td>` cells. Mobile = separate `<table>` using `show` class for 2x2 grid. Desktop table uses `hide` class. |
| Background | `#ffffff` | `#296042` (Starbucks dark green) |
| Content | text placeholders | Image-based navigation: `nav-app.png`, `nav-order.png`, `nav-offers.png`, `nav-rewards.png` |
| Column widths | `150px` each | `149px` each + `1px` divider cells |
| Dividers | none in base component | `1px` cells with `#5a8a6a` inner table (60px height) |
| Mobile behavior | columns stack | 2x2 grid (two rows of two `<td width="50%">`) |
| **Design reasoning** | Neither `column-layout-4` nor `navigation-bar` handles image-based icon navigation with vertical dividers and a 2x2 mobile reflow. This is a bespoke composition. The converter must recognize image-based navigation patterns and generate the desktop/mobile split. |

### Section 7 — Social Icons Row
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `footer-social.html` | Stripped down significantly |
| **Structural change** | VW-branded ESP tracking links + "Follow Us" heading + unsubscribe text | Simple icon row: 4 icons (IG, FB, TikTok, X) with `16px` spacing cells |
| Content | VW social links with ESP tokens | Starbucks social icons (local PNG assets) |
| Icon size | `26x26` | `26x26` (same) |
| Removed | "Follow Us" heading, unsubscribe row, ESP tracking URLs, LinkedIn | — |
| Background | `#ffffff` | `#ffffff` (same) |
| Padding | `40px top/bottom` | `30px top / 16px bottom` |
| **Design reasoning** | `footer-social.html` is a VW-branded template with ESP tokens. Starbucks needs a clean, minimal icon bar. The structure (table of icon cells with spacer `<td>`) is preserved, but all brand-specific content is replaced. |

### Section 8 — Footer (legal text)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `footer.html` | Rewritten |
| Background | `#f5f5f5` | `#ffffff` |
| Structure | Single `<p>` with template vars | 7 separate `<tr>` rows for: ref code, email + unsubscribe, contact, address + copyright, card terms, rewards terms, privacy |
| Font family | system stack | SoDo Sans stack |
| Font size | `12px` | `11px` |
| Color | `#666666` | `#707070` |
| Padding | `30px` | `8px top/bottom per row` |
| Inner width | full width | `480px` inner table |
| **Design reasoning** | Starbucks footer has many individual legal lines (each its own row for spacing control). The generic footer is a single paragraph with template variables. |

### Section 9 — Logo Image (Starbucks Rewards)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `image.html` (inline image) wrapped in `heading.html` table structure | — |
| Width | — | `146px` |
| Padding | — | `20px top / 30px bottom` |
| Content | — | `logo.png` (Starbucks Rewards badge) |
| Background | — | `#ffffff` |

---

## 2. Mammut — Duvet Day (`mammut-duvet-day.html`)

### Shell
| Property | Component default | Mammut override |
|----------|------------------|-----------------|
| Source component | `email-shell.html` | — |
| `color-scheme` | `light dark` | `light` only |
| Dark mode CSS | `@media (prefers-color-scheme: dark)` | `.dark-mode` class-based only (opt-in, not auto) |
| Font stack | system stack | system stack (no custom font) |
| `<title>` | `Email` | `Mammut — Grab A Duvet Day` |
| **Extra mobile classes** | standard set | Added `.prod-gutter` (hide gutter on mobile), `.prod-row` (full-width product cards) |

### Section 1 — Hero Image (climber + MAMMUT logo)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `full-width-image.html` | — |
| Image src | placeholder | `data/debug/10/assets/2833_1136.png` |
| Alt text | generic | `Mammut — Climber in orange and blue Eiger Extreme gear on snowy mountain` |
| Structural | Identical | No changes |

### Section 2 — Heading (GRAB A DUVET DAY)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `heading.html` | — |
| `bgcolor` | `#ffffff` | `#E85D26` (Mammut orange) |
| Font size | `24px` | `32px` |
| Line height | `28px` | `38px` |
| Color | `#1A1A1A` | `#ffffff` (white on orange) |
| Font weight | `<strong>` | `font-weight: 800` |
| Text transform | none | `uppercase` |
| Letter spacing | none | `-0.5px` |
| Dark mode class | none | `textblock-heading` added |
| Padding top | `0` | `30px` |

### Section 3 — Paragraph (body text)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `paragraph.html` | — |
| `bgcolor` | `#ffffff` | `#E85D26` |
| Color | `#1A1A1A` | `#ffffff` |
| Line height | `21px` | `22px` |
| Padding top | `0` | `16px` |
| Dark mode class | none | `textblock-body` added |

### Section 4 — Button Ghost (SHOP THE COLLECTION)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `button-ghost.html` | Rewritten for VML + modern |
| Width | `170px` | `220px` |
| Height | `35px` | `40px` |
| Border | `1px solid #1a1a1a` | `1px solid #ffffff` |
| Background | transparent | `#ffffff` fill (inverted ghost — white on orange) |
| Text color | `#1a1a1a` | `#1a1a1a` (dark on white) |
| Font size | `15px` | `12px` |
| Text transform | `uppercase` | `uppercase` (same) |
| Letter spacing | none | `1px` |
| Border radius | none | `0%` (sharp corners — Mammut brand) |
| VML | none | Full `v:roundrect` with `arcsize="0%"` |
| `bgcolor` on wrapper | `#ffffff` | `#E85D26` |
| **Design reasoning** | Mammut uses sharp-cornered, small-text, uppercase buttons — very different from the rounded default. White fill on orange background inverts the typical ghost pattern. |

### Section 5 — Button Ghost (DISCOVER EIGER EXTREME 6.0)
Same as Section 4 with:
- Width: `260px` (wider for longer text)
- Padding bottom: `30px` (closes the orange section)

### Section 6 — Hero Image (layering system — 4 people)
Same pattern as Section 1, src: `2833_1154.png`

### Section 7 — Heading (A LAYERING SYSTEM FOR LIFE IN THE EXTREMES)
Same pattern as Section 2 with:
- `bgcolor`: `#0252B5` (Mammut blue)
- Font size: `28px` / line-height: `34px`

### Section 8 — Paragraph (layering body text)
Same pattern as Section 3 with `bgcolor: #0252B5`

### Section 9 — Text Link (BUILD YOUR LAYERS)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `text-link.html` | Wrapped in heading/paragraph table structure |
| **Structural change** | Bare `<a>` tag | Wrapped in `600px` table + `520px` inner table + padding |
| Color | `#444444` | `#ffffff` |
| Font size | `14px` | `13px` |
| Text transform | none | `uppercase` |
| Letter spacing | none | `0.5px` |
| Arrow | none | ` &nbsp;&rarr;` appended |
| `bgcolor` on wrapper | — | `#0252B5` |
| Padding | — | `16px top / 30px bottom` |
| **Design reasoning** | `text-link.html` is just an `<a>` tag. Mammut needs it wrapped in the standard table structure (like heading/paragraph) with the blue background section continuing. The converter must handle "text link as standalone section" by wrapping it. |

### Section 10 — Spacer
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `spacer.html` | — |
| Height | `20px` | `30px` |
| Structural | Identical | No changes |

### Section 11 — Heading (LAYER SMARTER)
Same pattern as Section 2 with: `bgcolor: #ffffff`, color: `#1a1a1a`, font-size: `24px/28px`, padding: `0 top / 20px bottom`

### Sections 12-13 — Product Grid (2x2 — four products)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `column-layout-2.html` | Heavily customized |
| **Structural change** | Equal `300px` columns with `div.column` | Asymmetric `268px / 16px gutter / 268px` using `<td>` cells (not `<div>`) |
| Column wrapper | `<div class="column">` | `<td class="prod-row">` |
| Gutter | none | `<td class="prod-gutter" width="16">` (hidden on mobile) |
| Content per cell | text placeholder | Image + product name (bold 13px) + description (12px) + "SHOP NOW &rarr;" link |
| Font family | Arial | system stack + `'Courier New'` for "SHOP NOW" links |
| Outer padding | none | `0 24px` on wrapper `<td>` |
| Mobile | `div` stacks via `.column` | `<td class="prod-row">` → `display: block; width: 100%` |
| Gutter mobile | — | `display: none` via `.prod-gutter` |
| **Design reasoning** | Product grids need gutter control (collapses on mobile) and structured content per card (image + name + desc + CTA). The base `column-layout-2` uses `<div>` inline-block which doesn't support gutters. Mammut uses `<td>` cells for reliable Outlook rendering of product cards. |

### Section 14 — Spacer (between product rows)
Height: `24px`

### Section 15 — Hero Image (gift section — two hikers)
Same pattern as Section 1, src: `2833_1222.png`

### Section 16 — Heading + Paragraph + Text Link (Gift Guide section)
Same patterns as Sections 2/3/9 with `bgcolor: #ffffff`, body text color `#555555`

### Section 17 — Navigation Bar (MEN / WOMEN / EQUIPMENT)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `navigation-bar.html` | Rewritten — vertical list variant |
| **Structural change** | Horizontal inline `<a>` links in one `<td>` | Vertical: each link is its own `<tr>` with a nested 2-cell table (label left, arrow right) |
| Layout | horizontal, centered | vertical list, left-aligned |
| Separator | none | `1px solid #e0e0e0` border-top/bottom on `<td>` |
| Font size | `14px` | `22px` |
| Font weight | normal | `800` |
| Text transform | none | `uppercase` |
| Arrow indicator | none | `&#8599;` (north-east arrow) in `#e2001a` (Mammut red) |
| Class `hide` | present on nav bar | removed (visible on all devices) |
| Items | Home, Products, About, Contact | MEN, WOMEN, EQUIPMENT |
| **Design reasoning** | Mammut's Figma shows a stacked vertical nav with bold category names and red arrow icons — a completely different pattern from the inline horizontal default. The converter must detect vertical navigation layouts in Figma and switch to this row-per-link pattern. |

### Section 18 — Footer (Mammut logo + social as composite image)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `full-width-image.html` (NOT `footer.html`) | — |
| **Design reasoning** | Mammut's footer is a single composite image containing logo, social icons, legal text, and address. Instead of building it from `footer.html` + `footer-social.html`, the Figma design exported it as one image. The converter must recognize when footer content is an image block vs structured HTML. |

---

## 3. MAAP x KASK (`maap-kask.html`)

### Shell
| Property | Component default | MAAP override |
|----------|------------------|---------------|
| Source component | `email-shell.html` | — |
| `color-scheme` | `light dark` | `light` only |
| Dark mode CSS | `@media (prefers-color-scheme: dark)` | `.dark-mode` class-based only (opt-in) |
| `<title>` | `Email` | `MAAP x KASK — New Season Collaboration` |
| Preheader | `Preview text goes here` | `Now Live: The KASK Protone Icon by MAAP in exclusive shades of Opal and Loam.` |

### Section 1 — Hero Image
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `full-width-image.html` | — |
| Link wrapper | present | Removed (no `<a>` wrapper — image only) |
| Image src | placeholder | `data/debug/5/assets/2833_1628.png` |

### Section 2 — Heading (subtitle — "New Season Collaboration")
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `heading.html` used as subtitle | — |
| Font size | `24px` | `12px` |
| Line height | `28px` | `18px` |
| Color | `#1A1A1A` | `#555555` |
| Dark mode class | none | `textblock-body` (body class, not heading — because it looks like body text) |
| Padding top | `0` | `16px` |
| **Design reasoning** | MAAP uses the heading component at tiny size as a category label above the main title. The converter must detect "small text above large heading" patterns and emit a heading component with subtitle sizing. |

### Section 3 — Heading (main title — "MAAP x KASK")
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `heading.html` | — |
| Font size | `24px` | `36px` |
| Line height | `28px` | `42px` |
| Color | `#1A1A1A` | `#101828` |
| Font weight | `<strong>` | `font-weight: 800` |
| Padding top | `0` | `8px` (tight to subtitle above) |
| Dark mode class | none | `textblock-heading` |

### Section 4 — Paragraph (body text)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `paragraph.html` | — |
| Font size | `14px` | `16px` |
| Line height | `21px` | `26px` |
| Color | `#1A1A1A` | `#555555` |
| Padding top | `0` | `12px` |
| Dark mode class | none | `textblock-body` |

### Section 5 — Button Ghost (Discover)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `button-ghost.html` | Rewritten for VML + modern |
| Width | `170px` | `140px` (compact) |
| Height | `35px` | `40px` |
| Border | `1px solid #1a1a1a` | `1px solid #222222` |
| Border radius | none | `25px` (pill shape) |
| Font size | `15px` | `14px` |
| Font weight | default | `bold` |
| Text transform | `uppercase` | normal case |
| Content | `Button` | `Discover &rarr;` |
| VML | none | Full `v:roundrect` with `arcsize="50%"` |
| Padding | — | `16px top/bottom` |
| **Design reasoning** | MAAP uses a rounded pill ghost button — similar to Starbucks but in the brand's monochrome palette. |

### Section 6 — Two-Column Product Images
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `column-layout-2.html` | — |
| Column widths | `300px` | `272px` each (with calc(50% - 4px) for sub-pixel handling) |
| Gutter | none | `4px` padding on inner cells + MSO `8px` spacer `<td>` |
| Content | text placeholder | Image + `<p>` caption per column |
| Background | `#ffffff` | `#ffffff` (same) |
| Padding on wrapper | none | `16px 24px` |
| **Design reasoning** | Product images with captions need a slight gutter. MAAP uses CSS `calc()` for non-MSO and an explicit `<td width="8">` for Outlook. |

### Section 7 — Divider
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `divider.html` | — |
| Border color | `#F1F1F1` | `#e0e0e0` |
| Padding | `16px top/bottom` | `34px top/bottom` |
| Structural | Identical | No changes |

### Section 8 — Navigation Bar (Man / Woman / Accessories / Collections / Collaborations / Stories)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `navigation-bar.html` | Rewritten — vertical list variant |
| Layout | horizontal inline | vertical rows |
| Font size | `14px` | `26px` |
| Font weight | normal | `800` |
| Arrow | none | `&#8599;` superscript (16px) inside the link |
| Class `hide` | present | removed |
| Items | 4 generic links | 6 branded categories |
| Separator | none | none (MAAP uses whitespace, not borders) |
| **Design reasoning** | Similar to Mammut's vertical nav but without border separators. The arrow is inside the `<a>` tag as a `<span>` with `vertical-align:super` instead of in a separate `<td>`. |

### Section 9 — Divider
Same as Section 7 with `24px` bottom padding

### Section 10 — Store Locator (Stores label + pill buttons)
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `paragraph.html` + custom CTA grid | Composite — no single component |
| Label | — | "Stores ( LaB )" in `12px #555555` using paragraph pattern |
| Buttons | — | 7 city pills in 2 rows: `table > tr > td` per button, each is a `<table>` with `border-radius:25px`, `bgcolor="#222222"`, `12px` white text |
| **Design reasoning** | No component exists for "tag cloud" / "pill button grid". The converter must detect multiple small same-styled buttons in a row and generate this table-of-tables pattern. This is a composite of paragraph (label) + custom button grid. |

### Section 11 — Three-Column Feature Icons
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `column-layout-3.html` | — |
| Background | `#ffffff` | `#f7f7f7` |
| Content | text placeholder | Image per column (Free Shipping, Free Returns, Crash Replacement) |
| Padding | none | `16px` per cell |
| Text align | left | `center` |
| Structural | Identical | No changes |

### Section 12 — Footer
| Property | Component default | Override |
|----------|------------------|----------|
| Source component | `footer.html` | Rewritten |
| Background | `#f5f5f5` | `#000000` (black) |
| Text color | `#666666` | `#666666` (body) / `#cccccc` (links) |
| Structure | single `<p>` with template vars | `<td>` with two `<p>` tags: links row + unsubscribe text |
| Links | Unsubscribe + Preferences | Contact Us, Instagram, Facebook, Strava + unsubscribe |
| Padding | `30px` | `40px 44px` |
| Dark mode class | none | `footer-bg`, `footer-link`, `footer-text` |
| **Design reasoning** | MAAP uses a dark footer with social links inline (not as icons). Very different from the generic light footer. |

---

## Component Usage Summary

### Components used across all three campaigns

| Component | Starbucks | Mammut | MAAP | Notes |
|-----------|-----------|--------|------|-------|
| `email-shell.html` | Yes | Yes | Yes | Always the base — shell is always modified |
| `full-width-image.html` | 1x | 3x | 1x | Most reusable component — minimal changes needed |
| `heading.html` | 1x | 4x | 2x | Always customized: size, color, weight, bgcolor |
| `paragraph.html` | 1x | 3x | 1x | Always customized: color, size, bgcolor |
| `button-filled.html` | 1x | — | — | Heavily rewritten with VML roundrect |
| `button-ghost.html` | — | 2x | 1x | Always rewritten with VML roundrect |
| `column-layout-2.html` | 1x | 2x | 1x | Always customized: widths, content, sometimes `<td>` cells instead of `<div>` |
| `column-layout-3.html` | — | — | 1x | Minimal changes needed |
| `column-layout-4.html` | — | — | — | Referenced in Starbucks nav but replaced with bespoke pattern |
| `navigation-bar.html` | — | 1x | 1x | Always rewritten: vertical instead of horizontal |
| `footer-social.html` | 1x | — | — | Stripped down from VW template |
| `footer.html` | 1x | — | 1x | Always rewritten for brand |
| `spacer.html` | — | 3x | — | Minimal changes (height only) |
| `text-link.html` | — | 2x | — | Wrapped in table structure |
| `divider.html` | — | — | 2x | Color + padding changes |
| `image.html` | 1x | — | — | Used for logo image |

### Bespoke patterns (no matching component)
| Pattern | Campaign | Description |
|---------|----------|-------------|
| Image-based 4-col nav with desktop/mobile split | Starbucks | 4 icon images + vertical dividers, 2x2 grid on mobile |
| Product card grid with gutters | Mammut | `<td>` cells with collapsible gutter, structured card content |
| Pill button tag cloud | MAAP | Multiple small rounded buttons in a grid |
| Composite image footer | Mammut | Entire footer as single image |
| Subtitle + title heading pair | MAAP | Small text + large heading as two consecutive heading components |

---

## Key Observations for the Converter Engine

### 1. The Shell is Always Modified
Every campaign customizes: `<title>`, preheader, font stack, `color-scheme`, and dark mode strategy. The converter must extract these from the Figma metadata or infer them.

### 2. Every Component Gets Brand-Colored
No component is used at its default colors. The converter must extract the brand palette from the Figma design and apply it to every component's `bgcolor`, text `color`, link `color`, and border `color`.

### 3. Buttons Are Always VML-Upgraded
The base `button-filled.html` and `button-ghost.html` are too simple. Every campaign rewrites them with `v:roundrect` for Outlook + `<a>` fallback. The converter should always emit the bulletproof VML pattern.

### 4. Column Widths Are Always Asymmetric
The base layouts use equal widths (300/300, 200/200/200). Real campaigns use asymmetric widths computed from the Figma layout (264/292, 268/gutter/268, 272/272). The converter must calculate column widths from the design.

### 5. Navigation Bars Are Vertical
Both Mammut and MAAP use vertical navigation lists, not the horizontal default. The converter must detect whether navigation is horizontal or vertical from the Figma layout and emit the correct pattern.

### 6. Text Links Need Table Wrappers
`text-link.html` is a bare `<a>` tag but is always used wrapped in the standard `600px > 520px` table structure with padding and background color. The converter should always wrap text links in sections.

### 7. Product Grids Need Gutters
Real product grids use `<td>` cells with explicit gutter columns (hidden on mobile), not `<div>` inline-block. The converter must detect product grids and use the `<td>` pattern.

### 8. Dark Mode Classes Are Semantic
Components get semantic dark mode classes (`textblock-heading`, `textblock-body`, `footer-text`, `navbar-link`) based on their role, not their visual appearance. The converter must assign classes based on semantic role.

### 9. Composite Image Sections Happen
Sometimes a Figma section that looks structured (footer with logo + social icons + legal text) is actually a single exported image. The converter must handle this gracefully.

### 10. Padding Is the Primary Layout Tool
Between sections: `spacer.html`. Within sections: `padding-top` and `padding-bottom` on the `<td>`. The converter must extract spacing from the Figma design and apply it to padding values.
