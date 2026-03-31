# Pipeline-Ready: Remaining 10 Non-Fillable Components

## Context

After the anim-* optimization, **79/89** components are design-converter pipeline-ready (HTML structure + `data-slot` attributes). The remaining **10** are CSS fragments, inline style strings, structural glue, or missing slots. This plan makes all 89 pipeline-ready.

## Current State of 10 Components

| Slug | Category | Current Content | Problem |
|------|----------|----------------|---------|
| `text` | content | `font-family: Helvetica, Arial, sans-serif; font-size: 16px; color:#000000; line-height: 22px; mso-line-height-rule: exactly;` | Raw CSS property string, no HTML, no slots |
| `text-left` | content | `font-family: HelveticaNeue-Light, ...; font-size: 16px; line-height: 22px; color:#000000; mso-line-height-rule: exactly; text-decoration: none;` | Raw CSS property string, no HTML, no slots |
| `font-stack` | utility | `font-family: Helvetica, Arial, sans-serif;` | Raw CSS property, no HTML, no slots |
| `font-web` | utility | `@font-face { font-family: 'Open Sans'; ... }` | Raw CSS `@font-face`, no `<style>` wrapper |
| `font-inline` | utility | `<span data-slot="content" style="...">Inline text</span>` | Has slot but no table wrapper |
| `mso-lineheight` | utility | `mso-line-height-rule:exactly; line-height:22px;` | Raw CSS properties, no HTML, no slots |
| `divider` | structure | Full table with MSO conditional, `border-top: 1px solid #e0e0e0` | Has table but **no `data-slot`** for customization |
| `row` | structure | MSO conditional `</td></tr><tr><td width="600">` | Structural glue fragment, no slots |
| `td` | structure | `<td align="center"></td>` | Empty cell, no `data-slot` |
| `editable` | interactive | `elq-edit="true"` | ESP attribute marker, not a standalone component |

## Design Decisions

### Injection Target Classification

Add `inject_target` field to manifest entries. Values:

| Value | Meaning | Converter behavior |
|-------|---------|-------------------|
| `body` | (default) Rendered as body section | Current behavior — slot fill → render into `{sections}` |
| `head_style` | CSS block for `<head>` `<style>` | Extract CSS, merge into `_build_component_style_block()` output |
| `structural` | Composable fragment inside other components | Not rendered standalone — used as building block |
| `attribute` | Attribute snippet applied to other elements | Not rendered standalone — injected as attribute on target element |

### Group A: Body Section Components (5)

Convert to full table-based components with `data-slot` attributes. These become standalone renderable sections.

#### `text` → `email-templates/components/text.html`

```html
<!-- Component: text -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td align="center" style="padding:8px 24px;font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:22px;color:#000000;mso-line-height-rule:exactly;">
      <p data-slot="content" style="margin:0;">Your text content here</p>
    </td>
  </tr>
</table>
```

- Manifest: `inject_target: body` (default, can omit)
- Slots auto-detected: `content`
- Uses `<p>` inside `<td>` per email structure rules

#### `text-left` → `email-templates/components/text-left.html`

```html
<!-- Component: text-left -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td align="left" style="padding:8px 24px;font-family:HelveticaNeue-Light,Helvetica,Arial,sans-serif;font-size:16px;line-height:22px;color:#000000;mso-line-height-rule:exactly;text-decoration:none;">
      <p data-slot="content" style="margin:0;">Your text content here</p>
    </td>
  </tr>
</table>
```

- Same pattern as `text`, left-aligned
- Slots: `content`

#### `divider` → `email-templates/components/divider.html`

```html
<!-- Component: divider -->
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td data-slot="divider_style" style="padding:16px 24px;">
      <div class="divider-line" style="border-top:1px solid #e0e0e0;font-size:1px;line-height:1px;">&nbsp;</div>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->
```

- Preserves existing MSO conditional wrapper
- Adds `data-slot="divider_style"` on the padding `<td>` for token overrides
- Existing dark mode class `.divider-line` preserved
- Slots: `divider_style`

#### `font-inline` → `email-templates/components/font-inline.html`

```html
<!-- Component: font-inline -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td align="center" style="padding:0;">
      <span data-slot="content" style="font-size:16px;line-height:22px;color:#000000;text-transform:none;">Inline text</span>
    </td>
  </tr>
</table>
```

- Wraps existing `<span>` in table cell
- Slots: `content` (already existed, now auto-detected in table context)

#### `td` → `email-templates/components/td.html`

```html
<!-- Component: td -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td data-slot="content" align="center" style="padding:0;"></td>
  </tr>
</table>
```

- Full table wrapper (single cell can't be a standalone section)
- Slots: `content`

### Group B: Injectable `<style>` Blocks (3)

Wrap CSS in `<style>` tags. These get injected into `<head>` style block when the design requires them (e.g., web font detected in design tokens).

#### `font-web` → `email-templates/components/font-web.html`

```html
<!-- Component: font-web -->
<style>
@font-face {
  font-family: 'Open Sans';
  font-style: normal;
  font-weight: 400;
  src: local('Open Sans'), local('OpenSans'), url(http://themes.googleusercontent.com/static/fonts/opensans/v6/cJZKeOuBrn4kERxqtaUH3bO3LdcAZYWl9Si6vvxL-qU.woff) format('woff');
}
</style>
```

- Manifest: `inject_target: head_style`
- No `data-slot` — font URL/family come from design tokens, not slot filling
- Converter integration: when `tokens.typography.body_font` or `heading_font` is a web font, inject this block into `_build_component_style_block()` output

#### `font-stack` → `email-templates/components/font-stack.html`

```html
<!-- Component: font-stack -->
<style>
.font-stack { font-family: Helvetica, Arial, sans-serif; }
</style>
```

- Manifest: `inject_target: head_style`
- Reusable CSS class — elements can reference `.font-stack` class
- Converter integration: inject when design tokens don't specify a custom font

#### `mso-lineheight` → `email-templates/components/mso-lineheight.html`

```html
<!-- Component: mso-lineheight -->
<style>
.mso-lh { mso-line-height-rule: exactly; line-height: 22px; }
</style>
```

- Manifest: `inject_target: head_style`
- Reusable CSS class for Outlook line-height fix
- Converter integration: inject into style block; elements that need precise line-height add `class="mso-lh"`

### Group C: Structural Composables (2)

Keep as fragments but properly classify in manifest. These are building blocks used inside other components, not standalone sections.

#### `row` → `email-templates/components/row.html`

Keep as-is (MSO conditional row break). No HTML restructuring needed.

```html
<!-- Component: row -->
<!--[if (gte mso 9)|(IE)]>
</td>
</tr>
<tr>
<td width="{{ width || '600' }}" valign="top">
<![endif]-->
```

- Manifest: `inject_target: structural`
- Used inside multi-column layouts to break MSO ghost table rows
- Not rendered standalone by the converter

#### `editable` → `email-templates/components/editable.html`

Keep as-is (ESP attribute marker). No HTML restructuring needed.

```html
<!-- Component: editable -->
elq-edit="true"
```

- Manifest: `inject_target: attribute`
- Applied as HTML attribute on elements for Eloqua ESP editability
- Not rendered standalone by the converter

## Manifest Changes

File: `app/components/data/component_manifest.yaml`

Add `inject_target` field to the 10 components. Existing 79 body components don't need changes (default is `body`).

```yaml
# ── Content ──
- slug: text
  name: Text
  description: "Centered text paragraph with configurable font, size, color, and line-height."
  category: content
  compatibility: full

- slug: text-left
  name: Text Left
  description: "Left-aligned text paragraph with light-weight font stack."
  category: content
  compatibility: full

# ── Structure ──
- slug: row
  name: Row
  description: "MSO conditional row break snippet for Outlook ghost table columns."
  category: structure
  compatibility: full
  inject_target: structural

- slug: td
  name: Table Cell
  description: "Single table cell section with content slot."
  category: structure
  compatibility: full

- slug: divider
  name: Divider
  description: "Horizontal line separator with MSO conditional wrapper and customizable style."
  category: structure
  compatibility: full

# ── Interactive ──
- slug: editable
  name: Editable
  description: "Snippet attribute to mark ESP-editable regions (Eloqua elq-edit)."
  category: interactive
  compatibility: full
  inject_target: attribute

# ── Utility ──
- slug: font-inline
  name: Font Inline
  description: "Inline text span in table cell with configurable font size, line-height, and color."
  category: utility
  compatibility: utility

- slug: font-stack
  name: Font Stack
  description: "Safe system font-family stack as injectable CSS class."
  category: utility
  compatibility: utility
  inject_target: head_style

- slug: font-web
  name: Font Web
  description: "@font-face declaration for embedding a web font (Open Sans example)."
  category: utility
  compatibility: partial_outlook
  inject_target: head_style

- slug: mso-lineheight
  name: MSO Line Height
  description: "Outlook-safe mso-line-height-rule:exactly as injectable CSS class."
  category: utility
  compatibility: utility
  inject_target: head_style
```

## File Loader Impact

File: `app/components/data/file_loader.py`

Add `inject_target` to the loaded dict (line ~97-108):

```python
results.append(
    {
        "name": entry["name"],
        "slug": slug,
        "description": entry["description"],
        "category": entry["category"],
        "html_source": html_source,
        "css_source": entry.get("css_source"),
        "compatibility": resolve_compatibility(entry["compatibility"]),
        "slot_definitions": slot_definitions,
        "default_tokens": entry.get("default_tokens"),
        "inject_target": entry.get("inject_target", "body"),  # NEW
    }
)
```

No other loader changes needed — the field is optional with default `"body"`.

## Converter Integration (Future)

The converter (`app/design_sync/converter_service.py`) currently treats all components as body sections. Future work to support `inject_target`:

1. **`head_style` components**: In `_build_component_style_block()`, after building the base style block, check if any matched components have `inject_target: head_style`. If so, extract their `<style>` content and merge into the head block. This enables web font injection, MSO line-height classes, etc.

2. **`structural` / `attribute` components**: These are not matched by the converter — they're composable pieces referenced by other components or added manually. No converter changes needed.

3. **Renderer awareness**: `ComponentRenderer.render_section()` could skip rendering for non-body components, or the matcher could filter them out of results.

This converter integration is **not required for this plan** — the components are pipeline-ready in their file format. The converter changes can be done in a separate phase.

## Test Landscape

**Key test files:**
| File | Role |
|------|------|
| `app/components/tests/test_file_loader.py` | Manifest loading, seed structure, slot auto-detect |
| `app/design_sync/tests/test_component_matcher.py` | Section → slug matching, slot fill rate |
| `app/design_sync/tests/test_component_renderer.py` | Template filling, token overrides, dark mode |
| `app/design_sync/tests/test_builder_annotations.py` | data-slot-name, data-section-id annotations |

**Existing fixtures:** `make_component()`, `make_version()` in `app/components/tests/conftest.py`; `make_design_node()`, `make_file_structure()` in `app/design_sync/tests/conftest.py`.

**Hardcoded assertion — MUST UPDATE:**
- `test_file_loader.py:69` — `assert len(COMPONENT_SEEDS) == 90` (unchanged — 89 file + 1 inline, no new components added)

**Seed dict required keys** (`test_file_loader.py:14`): `name, slug, description, category, html_source, css_source, compatibility, slot_definitions, default_tokens`. Adding `inject_target` means updating `_REQUIRED_SEED_KEYS` or keeping it optional (not in required set).

## Type Check Baseline

| Directory | Pyright Errors | Pyright Warnings | Mypy Errors |
|-----------|---------------|-----------------|-------------|
| `app/components/` | 7 | 21 | 0 |
| `app/design_sync/` | 225 | 278 | 0 |

Mypy clean for both. Pyright errors are pre-existing (test-related types). New work must not increase these counts.

## Implementation Steps

1. **Write 8 HTML files** (5 body + 3 head_style; row and editable stay as-is)
2. **Update 10 manifest entries** (add `inject_target` where needed, update descriptions)
3. **Update `file_loader.py:97-108`** — add `"inject_target": entry.get("inject_target", "body")` to results dict
4. **Update `test_file_loader.py`** — add `"inject_target"` to `_REQUIRED_SEED_KEYS` set (line 14), or add a dedicated test for the new field
5. **Verify**: Run `load_file_components()` — all 89 should load, 87 with slots (row + editable have none by design)
6. **Run tests**: `pytest app/components/tests/test_file_loader.py app/design_sync/tests/test_component_matcher.py app/design_sync/tests/test_component_renderer.py -x`

## Preflight Warnings

- `test_file_loader.py:69` asserts `len(COMPONENT_SEEDS) == 90` — count stays at 90 (no new components, just HTML rewrites), but clear `_load_manifest` LRU cache in tests if HTML changes cause load failures
- `test_file_loader.py:76-88` checks `_REQUIRED_SEED_KEYS` — if `inject_target` is added to required set, all 89 file seeds must include it (they will via `entry.get("inject_target", "body")`)
- `_load_manifest()` uses `@lru_cache(maxsize=1)` — tests that patch manifest data must call `_load_manifest.cache_clear()`
- Slot auto-detection via `_DATA_SLOT_RE` regex scans full HTML — the 3 `head_style` components (font-web, font-stack, mso-lineheight) wrapped in `<style>` tags won't have `data-slot` attrs, so `slot_definitions: []` is correct for them

## Security Checklist

No new endpoints introduced. Changes are limited to static HTML files, YAML manifest, and the file loader. No user input paths affected.

## Expected Result

| Metric | Before | After |
|--------|--------|-------|
| Total components | 89 | 89 |
| Pipeline-ready (body, with slots) | 79 | 84 (+ text, text-left, divider, font-inline, td) |
| Injectable head CSS | 0 | 3 (font-web, font-stack, mso-lineheight) |
| Structural composables | 0 (unlabeled) | 2 (row, editable — labeled in manifest) |
| **Total classified** | **79** | **89** |

## Files Modified

| File | Change |
|------|--------|
| `email-templates/components/text.html` | Rewrite: CSS string → table + `<p>` + slot |
| `email-templates/components/text-left.html` | Rewrite: CSS string → table + `<p>` + slot |
| `email-templates/components/divider.html` | Add `data-slot="divider_style"` to `<td>` |
| `email-templates/components/font-inline.html` | Wrap `<span>` in table cell |
| `email-templates/components/td.html` | Rewrite: bare `<td>` → full table + slot |
| `email-templates/components/font-web.html` | Wrap `@font-face` in `<style>` tags |
| `email-templates/components/font-stack.html` | Convert to CSS class in `<style>` block |
| `email-templates/components/mso-lineheight.html` | Convert to CSS class in `<style>` block |
| `app/components/data/component_manifest.yaml` | Add `inject_target` to 5 entries (3 head_style + 1 structural + 1 attribute) |
| `app/components/data/file_loader.py` | Add `inject_target` field to loaded dict (1 line) |

`row.html` and `editable.html` are **not modified** — only their manifest entries get `inject_target`.
