# Plan: Extract Sublime Snippets into Hub Components

**Status:** Done
**Created:** 2026-03-19

## Objective

Extract pure HTML email structural patterns from ~386 Sublime snippets, strip all brand prefixes (`au*`, `vw*`, `cu*`, `se*`, `sk*`, `sp*`, `h*`, `r*`), deduplicate down to ~15 reusable generic components, and upgrade each with the hub's advanced rendering techniques (VML, MSO validation, dark mode, slots, design tokens).

## Source Analysis

### Brand Prefix Map (to be stripped)

| Prefix | Brand | Example | Generic Target |
|--------|-------|---------|----------------|
| `au*` | Audi | `au2col` | `column-layout-2` |
| `vw*` | Volkswagen | `vwhero` | `hero-section` |
| `cu*` | Custom | `cuart1` | `article-card` |
| `se*` | Sales Enablement | `se2col` | `column-layout-2` |
| `sk*` | Sketch | `skhero` | `hero-section` |
| `sp*` | Spark | `sp2col` | `column-layout-2` |
| `h*` | HTML/Hybrid | `h2col` | `column-layout-2` |
| `r*` | Responsive | `r2col20` | `column-layout-2` |
| (none) | Generic | `2col` | `column-layout-2` |

### What Gets Dropped (not components)

- **Font stacks** (28 snippets: `arial`, `helv`, `calibri`, `georgia`, `tahoma`, `times`, `verdana`, `webfont`) — handled by design system `typography` tokens
- **Text style snippets** (`stxt`, `ltxt`, `nkltxt`, `hsbctxt`, `etxt`) — inline via design tokens
- **Base templates** (`base2`, `hbase`, `jbase`, `sbase`, `spbase`, `aubase`, `sebase`, `vwbase`) — already covered by `email-templates/src/layouts/main.html`
- **Animations** (28 snippets: `ani*`, `carousel`, `hotspot`, `accordion`) — too complex for component abstraction; keep as standalone reference
- **Brand-specific duplicates** — one generic component replaces N branded copies
- **Editor utilities** (`eedit`, `edelete`, `evalname`, `dummytxt`, `readme`) — editor tooling

---

## Component Inventory (15 components)

### Existing (5) — Upgrade In-Place

These already exist in `seeds.py`. They will be upgraded with snippet patterns where the snippets have better structural techniques.

| # | Slug | Current State | Upgrade Needed |
|---|------|--------------|----------------|
| 1 | `spacer` | MSO + div split | Add `mso-line-height-rule:exactly` from snippet pattern, add `slot_definitions` for height token |
| 2 | `divider` | Basic `border-top` div | Good as-is |
| 3 | `cta-button` | VML `v:roundrect` + HTML fallback | Add ghost button variant (transparent/outline) from `buttont` snippet, add `slot_definitions` |
| 4 | `hero-block` | VML `v:rect` background + overlay | Add `slot_definitions` + `default_tokens` |
| 5 | `image-block` | MSO ghost table + caption | Add responsive class `.bannerimg` from snippets |

### New (10) — Create From Scratch

| # | Slug | Category | Source Snippets | Description |
|---|------|----------|----------------|-------------|
| 6 | `column-layout-2` | structure | `2col`, `h2col`, `h2col_space`, `r2col20` | Hybrid responsive 2-column (MSO ghost table + inline-block divs) |
| 7 | `column-layout-3` | structure | `3col`, `h3col`, `h3colspace`, `r3col20` | Hybrid responsive 3-column |
| 8 | `column-layout-4` | structure | `h4col`, `h4col_space`, `r4col20` | Hybrid responsive 4-column |
| 9 | `reverse-column` | structure | `hrev` | RTL-trick reverse stacking for mobile (image right, text left on desktop; text first on mobile) |
| 10 | `full-width-image` | content | `hone`, `simg`, `spimg` | Responsive full-width image with MSO fixed-width wrapper |
| 11 | `preheader` | structure | `hprehead` | Hidden preheader text + "View in browser" link |
| 12 | `article-card` | content | `auart1-4`, `cuart1-2`, `seart1-4`, `vwart1-4` (deduplicated) | Image + heading + body + CTA in 2-column layout with configurable image position |
| 13 | `image-grid` | content | `aufwimg`, `cuimgrid`, `vwimgrid` patterns | 2-column responsive image grid using hybrid pattern |
| 14 | `logo-header` | structure | `aulogo`, `culogo`, `selogo` patterns | Centered logo with optional tagline |
| 15 | `navigation-bar` | structure | `aunav`, `cunav`, `vwcvnav` patterns | Horizontal nav links, hidden on mobile |

---

## Hub Upgrades Applied to Every Component

Each component gets these enhancements over the raw snippet HTML:

### 1. MSO Ghost Table Wrapper
```html
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
  {component content}
<!--[if mso]>
</td></tr></table>
<![endif]-->
```

### 2. Dark Mode CSS
```html
<style>
  @media (prefers-color-scheme: dark) {
    .component-class { background-color: #1a1a2e !important; }
    .component-text { color: #e0e0e0 !important; }
  }
  [data-ogsc] .component-class { background-color: #1a1a2e !important; }
  [data-ogsb] .component-text { color: #e0e0e0 !important; }
</style>
```

### 3. VML Fallbacks (where applicable)
- Buttons: `<v:roundrect>` with `<w:anchorlock/>`
- Background images: `<v:rect>` with `<v:fill type="frame">`

### 4. Slot Annotations
```html
<img data-slot="hero_image" src="..." />
<h1 data-slot="headline">...</h1>
<a data-slot="cta_url" href="...">...</a>
```

### 5. Accessibility
- `role="presentation"` on all layout tables
- `alt` text on all images
- Semantic heading hierarchy

### 6. Responsive Classes
- `.bannerimg` — full-width responsive image
- `.column` — inline-block column (stacks on mobile)
- `.wf` — width-full on mobile
- `.hide` — display:none on mobile
- `.db` — display:block on mobile

### 7. MSO-Specific CSS
- `mso-line-height-rule: exactly` on spacers
- `mso-table-lspace: 0pt; mso-table-rspace: 0pt` on tables
- `border-collapse: collapse` on all tables

---

## Detailed Component Specs

### 6. `column-layout-2` (NEW)

**Source pattern:** `h2col` hybrid responsive
**Base width:** 600px (hub standard) — NOT 640px from snippets
**Column width:** 300px each (50/50 split)

**Slots:**
| slot_id | slot_type | selector | required |
|---------|-----------|----------|----------|
| `col_1` | body | `[data-slot='col_1']` | true |
| `col_2` | body | `[data-slot='col_2']` | true |

**Default tokens:**
```json
{
  "colors": { "background": "#ffffff", "dark_background": "#1a1a2e" },
  "spacing": { "column_gap": "0", "padding": "0" }
}
```

**Structure:**
```
<tr>
  <td font-size:0; text-align:center>
    <!--[if mso]> <table width="600"> <tr> <td width="300"> <![endif]-->
    <div class="column" max-width:300px; display:inline-block>
      <table width="100%">
        <td data-slot="col_1"> ... </td>
      </table>
    </div>
    <!--[if mso]> </td><td width="300"> <![endif]-->
    <div class="column" max-width:300px; display:inline-block>
      <table width="100%">
        <td data-slot="col_2"> ... </td>
      </table>
    </div>
    <!--[if mso]> </td></tr></table> <![endif]-->
  </td>
</tr>
```

### 7. `column-layout-3` (NEW)

Same hybrid pattern. **Column width:** 200px each (600/3).

**Slots:** `col_1`, `col_2`, `col_3`

### 8. `column-layout-4` (NEW)

Same hybrid pattern. **Column width:** 150px each (600/4).

**Slots:** `col_1`, `col_2`, `col_3`, `col_4`

### 9. `reverse-column` (NEW)

**Source pattern:** `hrev` — uses `dir="rtl"` on parent, `dir="ltr"` on children.
Desktop: image right, text left. Mobile: text stacks first (natural reading order).

**Slots:**
| slot_id | slot_type | selector | required |
|---------|-----------|----------|----------|
| `primary_content` | body | `[data-slot='primary_content']` | true |
| `secondary_content` | body | `[data-slot='secondary_content']` | true |

### 10. `full-width-image` (NEW)

**Source pattern:** `hone` — MSO fixed-width + fluid `max-width` inner table.

**Slots:**
| slot_id | slot_type | selector | required |
|---------|-----------|----------|----------|
| `image_url` | image | `[data-slot='image_url']` | true |
| `image_alt` | body | `[data-slot='image_alt']` | true |
| `link_url` | cta | `[data-slot='link_url']` | false |

### 11. `preheader` (NEW)

**Source pattern:** `hprehead` — hidden text column (`.hide` on mobile) + "View in browser" link.

**Slots:**
| slot_id | slot_type | selector | required |
|---------|-----------|----------|----------|
| `preheader_text` | body | `[data-slot='preheader_text']` | true |
| `view_online_url` | cta | `[data-slot='view_online_url']` | false |

### 12. `article-card` (NEW)

**Source pattern:** Deduplicated from `auart1-4` variants. Uses hybrid 2-column: image on one side, text on the other.

**Slots:**
| slot_id | slot_type | selector | required |
|---------|-----------|----------|----------|
| `image_url` | image | `[data-slot='image_url']` | true |
| `image_alt` | body | `[data-slot='image_alt']` | true |
| `heading` | headline | `[data-slot='heading']` | true |
| `body_text` | body | `[data-slot='body_text']` | true |
| `cta_text` | cta | `[data-slot='cta_text']` | false |
| `cta_url` | cta | `[data-slot='cta_url']` | false |

**Default tokens:**
```json
{
  "colors": {
    "heading": "#333333", "body": "#555555", "cta": "#0066cc", "cta_text": "#ffffff",
    "dark_heading": "#e0e0e0", "dark_body": "#cccccc"
  },
  "fonts": { "heading": "Arial, sans-serif", "body": "Arial, sans-serif" },
  "font_sizes": { "heading": "20px", "body": "14px" },
  "spacing": { "image_width": "280px", "text_padding": "20px" }
}
```

### 13. `image-grid` (NEW)

2-column responsive image grid using hybrid pattern. Each cell is a linked image.

**Slots:** `image_1`, `image_2`, `link_1`, `link_2` (all image/cta type)

### 14. `logo-header` (NEW)

Centered logo image with MSO wrapper. Simpler than `email-header` (no nav links).

**Slots:**
| slot_id | slot_type | selector | required |
|---------|-----------|----------|----------|
| `logo_url` | image | `[data-slot='logo_url']` | true |
| `logo_alt` | body | `[data-slot='logo_alt']` | true |
| `logo_width` | body | — | true |

### 15. `navigation-bar` (NEW)

Horizontal inline links, hidden on mobile via `.hide` class (mobile users get hamburger or simplified nav).

**Slots:**
| slot_id | slot_type | selector | required |
|---------|-----------|----------|----------|
| `nav_links` | body | `[data-slot='nav_links']` | true |

---

## File Changes

### New Files

| File | Description |
|------|-------------|
| `email-templates/components/column-layout-2.html` | 2-column hybrid responsive |
| `email-templates/components/column-layout-3.html` | 3-column hybrid responsive |
| `email-templates/components/column-layout-4.html` | 4-column hybrid responsive |
| `email-templates/components/reverse-column.html` | RTL reverse-stack layout |
| `email-templates/components/full-width-image.html` | Full-width responsive image |
| `email-templates/components/preheader.html` | Hidden preheader + view online |
| `email-templates/components/article-card.html` | Image + text article layout |
| `email-templates/components/image-grid.html` | 2-column image grid |
| `email-templates/components/logo-header.html` | Centered logo header |
| `email-templates/components/navigation-bar.html` | Horizontal nav links |

### Modified Files

| File | Change |
|------|--------|
| `app/components/data/seeds.py` | Add 10 new component seeds with `slot_definitions` + `default_tokens`; upgrade 5 existing seeds |
| `app/seed_demo.py` | Change seeder from skip-if-exists to upsert-by-slug (add missing components without dropping existing) |

### Files NOT Modified

- No migration needed (components table schema unchanged)
- No route/service/repository changes (generic CRUD handles new seeds)
- No frontend changes (visual builder already renders any component from DB)

---

## Implementation Order

### Phase 1: Seeder Upgrade (prerequisite)
1. Modify `_seed_components()` in `seed_demo.py` to upsert by slug instead of skipping when components exist
2. Test: run `make seed-demo` twice — second run should add missing, skip existing

### Phase 2: Structural Components (foundation)
3. Create `spacer` upgrade (add `mso-line-height-rule:exactly`, `slot_definitions`)
4. Create `column-layout-2.html` + seed entry
5. Create `column-layout-3.html` + seed entry
6. Create `column-layout-4.html` + seed entry
7. Create `reverse-column.html` + seed entry
8. Create `full-width-image.html` + seed entry

### Phase 3: Navigation Components
9. Create `preheader.html` + seed entry
10. Create `logo-header.html` + seed entry
11. Create `navigation-bar.html` + seed entry

### Phase 4: Content Components
12. Create `article-card.html` + seed entry
13. Create `image-grid.html` + seed entry
14. Upgrade existing `cta-button` (add ghost variant, `slot_definitions`)
15. Upgrade existing `hero-block` (add `slot_definitions`, `default_tokens`)
16. Upgrade existing `image-block` (add `.bannerimg` class)

### Phase 5: Validation
17. Run `make seed-demo` on fresh DB — verify all 15 components created
18. Run `make seed-demo` on existing DB — verify upsert adds only new
19. Verify HTML passes MSO parser: `validate_mso_conditionals()` on each component
20. Spot-check: section adapter can convert each component to `SectionBlock`

---

## Naming Conventions (Hub Standard)

- **Slugs:** kebab-case, descriptive, no brand prefix (`column-layout-2` not `h2col`)
- **Categories:** `structure`, `content`, `action`, `social`, `commerce`
- **Slot IDs:** snake_case (`hero_image`, `cta_url`, `col_1`)
- **CSS classes:** kebab-case with component prefix (`col2-bg`, `col2-cell`) — unique per component to avoid collisions
- **Dark mode classes:** same name with `-dark` suffix in `@media (prefers-color-scheme)` and `[data-ogsc]`/`[data-ogsb]` selectors

## Compatibility Target

All components target `_COMPAT_FULL` (gmail, outlook_365, outlook_2019, apple_mail, ios_mail, yahoo, samsung_mail, outlook_com) except:
- `reverse-column` → `_COMPAT_PARTIAL_SAMSUNG` (Samsung Mail has inconsistent RTL handling)
- Components using `border-radius` → `_COMPAT_PARTIAL_SAMSUNG` (Samsung strips in some versions)

## Base Width

Hub standard is **600px** (not the 640px used in some snippets). All column math and MSO ghost table widths use 600px.
