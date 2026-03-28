# Plan: Universal Figma-to-Email Converter (Any Client, Any Design)

**Status:** planned
**Phase:** 34 (Universal Design Sync)
**Depends on:** Phase 33 converter pipeline, conversion-diagnostic-pipeline plan

## Context

The current converter only works well with designs that use specific naming ("hero", "header", "footer"). The MAAP x KASK Figma file uses `mj-*` MJML naming — and the converter classifies every section as UNKNOWN with 0.7 confidence. This isn't a one-off: every client will have different Figma conventions. We need the converter to work for ANY client email-hub serves, not just designs that happen to match our hardcoded patterns.

**Three root problems:**
1. **Naming is hardcoded** — `_SECTION_PATTERNS` only has 10 patterns. `mj-*`, agency conventions, generic "Frame 1" names all fail
2. **Structure is flattened** — content extractors dump texts, images, buttons into flat lists. Which image pairs with which caption in which column is LOST
3. **No client-specific config** — no way to tell the converter "this client uses mj-* naming" or "this client's buttons are always named btn-*"

## What Clients Must Provide (Figma API Requirements)

### Required from Every Client

| What | Where | Why |
|------|-------|-----|
| **Figma file key** | URL: `figma.com/design/{FILE_KEY}/...` | Identifies the file |
| **Figma access token** | Personal Access Token or OAuth | Authenticates API calls |
| **File URL** | Full Figma URL | For display/linking back |

These are already captured in `DesignConnection` model (`file_ref`, `encrypted_token`, `file_url`).

### What the Figma API Returns (and what we need)

The Figma REST API (`GET /v1/files/{key}`) returns the **full node tree**. Our `sync_tokens_and_structure()` already fetches it with **NO depth limit**. The `_MAX_PARSE_DEPTH=30` safety ceiling is far more than needed (designs rarely exceed ~15 levels).

**Critical Figma node properties we already extract:**

| Property | Extracted | Used For |
|----------|-----------|----------|
| `name` | Yes → `DesignNode.name` | Section classification |
| `type` | Yes → `DesignNode.type` | Node type detection |
| `children[]` | Yes → recursed to depth 30 | Tree structure |
| `absoluteBoundingBox` | Yes → `x, y, width, height` | Position-based layout |
| `layoutMode` | Yes → `layout_mode` | Auto-layout detection |
| `itemSpacing` | Yes → `item_spacing` | Gap between children |
| `paddingTop/Right/Bottom/Left` | Yes | Section padding |
| `fills[].color` (SOLID) | Yes → `fill_color` | Background colors |
| `style.fontFamily/Size/Weight` | Yes (TEXT only) | Typography |
| `characters` | Yes (TEXT only) → `text_content` | Text content |

**Critical properties we DON'T extract (need to add):**

| Property | Currently | Need For | Impact |
|----------|-----------|----------|--------|
| `fills[].imageRef` | Ignored on FRAME | Background images on hero/section frames | Hero bg always placeholder |
| `fills[].scaleMode` | Ignored | Image sizing (FILL/FIT/CROP) | Wrong image dimensions |
| `componentProperties` | Ignored | Component variant overrides | Losing customization |
| `primaryAxisAlignItems` | Ignored | Content alignment (center/start/end) | Wrong text alignment |
| `counterAxisAlignItems` | Ignored | Cross-axis alignment | Wrong vertical alignment |
| `layoutAlign` | Ignored | Child alignment within auto-layout | Wrong stretching |
| `constraints` | Ignored | Responsive behavior | Wrong mobile stacking |

### Optional Client Configuration (NEW — per-connection)

Add a `config_json` column to `DesignConnection` for clients to specify hints:

```python
{
  "naming_convention": "auto" | "mjml" | "descriptive" | "generic",
  "section_name_map": {           # Optional custom overrides
    "my-hero-banner": "hero",
    "email-nav": "nav"
  },
  "button_name_hints": ["btn-", "cta-", "action-"],
  "image_fill_as_background": true,  # Extract IMAGE fills on frames as bg images
  "container_width": 600             # Override auto-detected width
}
```

Default: `{"naming_convention": "auto"}` — auto-detect from the node names.

## Research Summary

### The Full Pipeline (6 stages)

```
Figma API → _parse_node() → DesignFileStructure
         → analyze_layout() → DesignLayoutDescription (sections, texts, images, buttons)
         → match_all() → list[ComponentMatch] (slug, slots, overrides)
         → ComponentRenderer → list[RenderedSection] (per-section HTML)
         → COMPONENT_SHELL assembly → full HTML
         → sanitize_web_tags_for_email() → email-safe HTML
```

### Key Finding: Full Tree IS Fetched

`sync_tokens_and_structure()` (`figma/service.py:275`) sends **NO depth parameter** to Figma API — gets the entire tree. Then `_parse_node()` recurses with `max_depth=None` → ceiling of 30. The depth cap is NOT the problem.

### Key Finding: Structure IS Flattened

All three content extractors (`_extract_texts`, `_extract_images`, `_extract_buttons`) fully recurse but dump results into **flat lists**. `EmailSection` stores `texts: list[TextBlock]` — no column grouping. `_build_column_fills()` then uses **round-robin modulo** to distribute content across columns.

### Key Finding: Column Detection is Position-Only

`_detect_column_layout()` groups children by Y-position (±10px tolerance) at the **immediate child level only**. It detects "this section has 2 columns" but doesn't track which content is in which column. The actual `mj-column` frames with their children are invisible to this.

### Naming Conventions Across Clients

| Convention | Example Names | Detection Strategy |
|-----------|--------------|-------------------|
| **MJML** | `mj-section`, `mj-column`, `mj-image`, `mj-button`, `mj-wrapper` | Prefix: `mj-` |
| **Descriptive** | "Hero Section", "Header", "Footer Area", "Product Card" | Substring match (current `_SECTION_PATTERNS`) |
| **Generic Figma** | "Frame 1", "Group 2", "Rectangle 3" | No name signal — use position/structure heuristics |
| **Agency/Builder** | "bee-row", "stripo-container", "edm-header" | Configurable prefix map |
| **Custom** | "Section_01", "Block_Hero", "CTA_Primary" | Per-connection `section_name_map` |

**The universal approach:** Try strategies in order: (1) auto-detect convention from names, (2) apply matching strategy, (3) fall back to structural heuristics.

## Files to Create/Modify

| File | Change |
|------|--------|
| `app/design_sync/figma/layout_analyzer.py` | **Major** — add `_detect_naming_convention()`, expand `_SECTION_PATTERNS` with mj-* and builder prefixes, add `ColumnGroup` dataclass to preserve per-column content, rewrite `_detect_column_layout()` to use structure-aware detection |
| `app/design_sync/figma/service.py` | **Minor** — extract `imageRef` from IMAGE fills on FRAMEs, extract `primaryAxisAlignItems`/`counterAxisAlignItems` |
| `app/design_sync/protocol.py` | **Minor** — add `image_ref`, `alignment` fields to `DesignNode` |
| `app/design_sync/component_matcher.py` | **Moderate** — use `ColumnGroup` data for column fills instead of round-robin, improve article-card image/caption pairing |
| `app/design_sync/models.py` | **Minor** — add `config_json` column to `DesignConnection` |
| `app/design_sync/schemas.py` | **Minor** — add `config` field to connection request/response |
| `alembic/versions/xxx_add_connection_config.py` | **New** — migration for config_json column |
| `app/design_sync/tests/test_naming_conventions.py` | **New** — tests for all naming strategies |
| `app/design_sync/tests/test_column_grouping.py` | **New** — tests for structure-aware column detection |

## Implementation Steps

### Step 1: Auto-Detect Naming Convention (`layout_analyzer.py`)

Add a function that scans top-level frame names and determines the naming convention:

```python
class NamingConvention(StrEnum):
    MJML = "mjml"           # mj-section, mj-column, mj-image, etc.
    DESCRIPTIVE = "descriptive"  # hero, header, footer, etc.
    GENERIC = "generic"      # Frame 1, Group 2, etc.
    CUSTOM = "custom"        # Per-connection map

# MJML → EmailSectionType mapping
_MJ_SECTION_MAP: dict[str, EmailSectionType] = {
    "mj-section": EmailSectionType.CONTENT,   # generic section
    "mj-wrapper": EmailSectionType.CONTENT,   # full-width wrapper
    "mj-hero": EmailSectionType.HERO,
    "mj-navbar": EmailSectionType.NAV,
}

# MJML → content role mapping (not section type, but what the node IS)
_MJ_CONTENT_ROLES: dict[str, str] = {
    "mj-image": "image",
    "mj-text": "text",
    "mj-button": "button",
    "mj-column": "column",
    "mj-section": "section",
    "mj-wrapper": "wrapper",
    "mj-divider": "divider",
    "mj-spacer": "spacer",
    "mj-social": "social",
    "mj-navbar": "nav",
}

def _detect_naming_convention(candidates: list[DesignNode]) -> NamingConvention:
    """Auto-detect which naming convention the design uses."""
    names = []
    for c in candidates:
        names.append(c.name.lower())
        for child in c.children:
            names.append(child.name.lower())

    mj_count = sum(1 for n in names if n.startswith("mj-"))
    pattern_count = sum(
        1 for n in names
        for patterns in _SECTION_PATTERNS.values()
        for p in patterns
        if p in n
    )
    generic_count = sum(1 for n in names if _is_generic_name(n))

    total = len(names) or 1
    if mj_count / total > 0.3:
        return NamingConvention.MJML
    if pattern_count / total > 0.2:
        return NamingConvention.DESCRIPTIVE
    return NamingConvention.GENERIC

def _is_generic_name(name: str) -> bool:
    """Check if name is Figma auto-generated (Frame 1, Group 2, etc.)."""
    import re
    return bool(re.match(r"^(frame|group|rectangle|ellipse|vector|text)\s*\d*$", name.strip()))
```

### Step 2: Expand `_SECTION_PATTERNS` for `mj-*` and Builder Conventions

```python
_SECTION_PATTERNS: dict[EmailSectionType, list[str]] = {
    EmailSectionType.PREHEADER: ["preheader", "pre-header", "preview"],
    EmailSectionType.HEADER: ["header", "top-bar", "topbar", "logo-bar", "logo-header"],
    EmailSectionType.HERO: ["hero", "banner", "masthead", "feature", "mj-hero"],
    EmailSectionType.CONTENT: ["content", "body", "main", "article", "text", "product"],
    EmailSectionType.CTA: ["cta", "call-to-action", "button", "action"],
    EmailSectionType.FOOTER: ["footer", "bottom", "legal", "unsubscribe"],
    EmailSectionType.SOCIAL: ["social", "follow", "connect", "mj-social"],
    EmailSectionType.DIVIDER: ["divider", "separator", "hr", "line", "mj-divider"],
    EmailSectionType.SPACER: ["spacer", "gap", "padding", "mj-spacer"],
    EmailSectionType.NAV: ["nav", "navigation", "menu", "links", "mj-navbar"],
}
```

### Step 3: Structure-Aware Column Detection (`layout_analyzer.py`)

Add a `ColumnGroup` dataclass that preserves which content is in which column:

```python
@dataclass(frozen=True)
class ColumnGroup:
    """Content grouped by column, preserving structure."""
    column_idx: int
    node_id: str
    node_name: str
    texts: list[TextBlock]
    images: list[ImagePlaceholder]
    buttons: list[ButtonElement]
    width: float | None = None
```

Rewrite `_detect_column_layout()` to detect columns structurally first, position-based second:

```python
def _detect_column_layout(
    node: DesignNode,
    convention: NamingConvention = NamingConvention.GENERIC,
) -> tuple[ColumnLayout, int, list[ColumnGroup]]:
    """Detect column layout using structure first, position fallback.

    Returns (layout_type, column_count, column_groups).
    column_groups preserves which content is in which column.
    """
    # Strategy 1: MJML — look for mj-column children
    if convention == NamingConvention.MJML:
        columns = _detect_mj_columns(node)
        if columns:
            return _layout_from_count(len(columns)), len(columns), columns

    # Strategy 2: Auto-layout — HORIZONTAL layout_mode means children are columns
    if node.layout_mode == "HORIZONTAL":
        frame_children = [c for c in node.children
                         if c.type in _FRAME_TYPES and c.width and c.width > 40]
        if len(frame_children) >= 2:
            columns = _build_column_groups(frame_children)
            return _layout_from_count(len(columns)), len(columns), columns

    # Strategy 3: Position-based — group by Y-position (existing logic)
    columns = _detect_position_columns(node)
    return _layout_from_count(len(columns)), len(columns), columns


def _detect_mj_columns(node: DesignNode) -> list[ColumnGroup]:
    """Find mj-column children and extract their content."""
    columns = []
    # Walk one level to find mj-section, then its mj-column children
    section_node = node
    for child in node.children:
        if child.name.lower().startswith("mj-section"):
            section_node = child
            break

    col_idx = 0
    for child in section_node.children:
        if child.name.lower().startswith("mj-column"):
            col_idx += 1
            columns.append(ColumnGroup(
                column_idx=col_idx,
                node_id=child.id,
                node_name=child.name,
                texts=_extract_texts(child),
                images=_extract_images(child),
                buttons=_extract_buttons(child),
                width=child.width,
            ))
    return columns
```

### Step 4: MJML-Aware Section Classification

When naming convention is MJML, classify sections using the `mj-*` structure instead of heuristics:

```python
def _classify_mj_section(node: DesignNode) -> EmailSectionType:
    """Classify a section using MJML naming conventions."""
    name = node.name.lower().strip()

    # Direct mj-* type mapping
    if name in _MJ_SECTION_MAP:
        return _MJ_SECTION_MAP[name]

    # Walk children to infer type from content roles
    child_roles = set()
    for child in _walk_mj_children(node):
        role = _get_mj_role(child.name)
        if role:
            child_roles.add(role)

    # Inference rules:
    # Single large image with no text → full-width image (header/hero)
    if child_roles == {"image"} and _has_large_image_child(node):
        return EmailSectionType.HERO

    # Image + text + button → content section
    if "image" in child_roles and "text" in child_roles and "button" in child_roles:
        return EmailSectionType.CONTENT

    # Only text + button → CTA or content
    if "button" in child_roles and "text" in child_roles and "image" not in child_roles:
        return EmailSectionType.CONTENT

    # Social icons
    if "social" in child_roles:
        return EmailSectionType.SOCIAL

    # Navigation
    if "nav" in child_roles:
        return EmailSectionType.NAV

    # Divider/spacer
    if "divider" in child_roles:
        return EmailSectionType.DIVIDER
    if "spacer" in child_roles:
        return EmailSectionType.SPACER

    return EmailSectionType.CONTENT  # Default for mj-wrapper/mj-section


def _get_mj_role(name: str) -> str | None:
    """Get content role from mj-* name (checking both exact and -Frame suffix)."""
    lower = name.lower().strip()
    # Try direct match: "mj-image"
    if lower in _MJ_CONTENT_ROLES:
        return _MJ_CONTENT_ROLES[lower]
    # Try frame-suffix match: "mj-image-Frame" → "image"
    for prefix, role in _MJ_CONTENT_ROLES.items():
        if lower.startswith(prefix):
            return role
    return None
```

### Step 5: Update `EmailSection` to Include Column Groups

```python
@dataclass(frozen=True)
class EmailSection:
    """A detected email section with its content."""
    # ... existing fields ...
    column_groups: list[ColumnGroup] = field(default_factory=list)  # NEW
```

When `column_groups` is populated, the component matcher uses it instead of the flat lists + round-robin.

### Step 6: Update Component Matcher to Use Column Groups

```python
def _build_column_fills(section: EmailSection) -> list[SlotFill]:
    """Build slot fills using actual column structure when available."""
    # NEW: Use column_groups when available (structure-aware)
    if section.column_groups:
        return _build_column_fills_from_groups(section.column_groups)

    # FALLBACK: Existing round-robin logic for designs without structure
    # ... existing code ...


def _build_column_fills_from_groups(groups: list[ColumnGroup]) -> list[SlotFill]:
    """Build column fills from actual column groups (preserves design structure)."""
    fills: list[SlotFill] = []
    for group in groups:
        col_parts: list[str] = []
        # Images first (design order)
        for img in group.images:
            col_parts.append(
                f'<img src="/api/v1/design-sync/assets/{img.node_id}.png" '
                f'alt="{html.escape(img.node_name)}" '
                f'style="display:block;width:100%;height:auto;border:0;" />'
            )
        # Texts in order
        for text in group.texts:
            col_parts.append(_safe_text(text.content))
        # Buttons
        for btn in group.buttons:
            col_parts.append(_safe_text(btn.text))

        if col_parts:
            fills.append(SlotFill(f"col_{group.column_idx}", "\n".join(col_parts)))
    return fills
```

### Step 7: Extract IMAGE Fills on Frames (`figma/service.py`)

Add detection of IMAGE fills on FRAME nodes (hero/section backgrounds):

```python
# In _parse_node(), after the fills loop (line ~1097):
image_ref: str | None = None
for fi_d in reversed(cast(list[Any], raw_fills)):
    if not isinstance(fi_d, dict):
        continue
    if not fi_d.get("visible", True):
        continue
    fill_type = fi_d.get("type")
    if fill_type == "IMAGE":
        image_ref = fi_d.get("imageRef")  # Figma image reference hash
        break
```

Add `image_ref: str | None = None` field to `DesignNode` in `protocol.py`.

Then in `_walk_for_images()`, detect FRAME nodes with `image_ref`:

```python
# After the existing IMAGE node check:
elif node.type == DesignNodeType.FRAME and node.image_ref:
    # Frame with IMAGE fill → treat as background image
    results.append(ImagePlaceholder(
        node_id=node.id,
        node_name=node.name,
        width=node.width,
        height=node.height,
        is_background=True,  # NEW field
    ))
    # Still recurse into children (frame has content over the bg)
    for child in node.children:
        _walk_for_images(child, results)
```

### Step 8: Per-Connection Config (`models.py`, `schemas.py`)

Add `config_json` to `DesignConnection`:

```python
# models.py
config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
```

Add to connection create/update schemas:

```python
# schemas.py
class ConnectionConfigRequest(BaseModel):
    naming_convention: str = "auto"  # auto|mjml|descriptive|generic
    section_name_map: dict[str, str] | None = None
    button_name_hints: list[str] | None = None
    container_width: int | None = None
```

Thread `config_json` through `import_service.py` → `converter_service.py` → `layout_analyzer.py`.

### Step 9: Smart Section Type Inference for Generic Names

When names are generic ("Frame 1", "Group 2"), enhance position + content heuristics:

```python
def _classify_by_content(
    node: DesignNode,
    texts: list[TextBlock],
    images: list[ImagePlaceholder],
    buttons: list[ButtonElement],
    index: int,
    total: int,
) -> EmailSectionType:
    """Infer section type from content when names are unhelpful."""
    has_images = len(images) > 0
    has_texts = len(texts) > 0
    has_buttons = len(buttons) > 0
    has_large_image = _has_large_image_child(node)

    # Full-width image near top → hero
    if has_large_image and not has_texts and index <= 1:
        return EmailSectionType.HERO

    # Text + button but no images near top → hero (text-based)
    if has_texts and has_buttons and not has_images and index <= 2:
        heading_sizes = [t.font_size for t in texts if t.font_size and t.font_size > 20]
        if heading_sizes:
            return EmailSectionType.HERO

    # Many small texts with arrows/links → navigation
    if len(texts) >= 4 and all(len(t.content) < 30 for t in texts):
        link_indicators = sum(1 for t in texts if any(c in t.content for c in "→↗►▸"))
        if link_indicators >= 3:
            return EmailSectionType.NAV

    # Small text at bottom → footer
    if index >= total - 2 and has_texts:
        avg_size = sum(t.font_size or 14 for t in texts) / len(texts)
        if avg_size <= 13:
            return EmailSectionType.FOOTER

    # Many small boxes at similar Y → stores/grid
    # (detected by column layout > 3)

    # Default: use existing position heuristic
    return _classify_by_position(node, index, total, has_large_image)
```

## How This Works for Any Client

### Client A: Uses MJML naming (like MAAP x KASK)
1. Auto-detection sees >30% `mj-*` names → `NamingConvention.MJML`
2. `_classify_mj_section()` maps sections precisely
3. `_detect_mj_columns()` finds `mj-column` children → preserves grouping
4. `_get_mj_role()` identifies images, buttons, text by name
5. Result: high-confidence matching, correct column content

### Client B: Uses descriptive naming ("Hero", "Products Grid")
1. Auto-detection finds matches in `_SECTION_PATTERNS` → `NamingConvention.DESCRIPTIVE`
2. Existing `_classify_by_name()` works as before
3. Column detection uses auto-layout mode or Y-position
4. Result: works same as current (but with better column grouping via auto-layout)

### Client C: Generic Figma names ("Frame 1", "Frame 2")
1. Auto-detection finds no name signals → `NamingConvention.GENERIC`
2. `_classify_by_content()` infers from dimensions, child content, position
3. Column detection uses auto-layout or Y-position
4. Result: best-effort with enhanced content heuristics

### Client D: Custom agency naming
1. Sets `config_json.section_name_map: {"edm-hero": "hero", "edm-footer": "footer"}`
2. Custom map checked first before pattern matching
3. Result: exact match using client-provided mapping

## Verification

1. **Tests with mj-* fixture:**
   ```bash
   pytest app/design_sync/tests/test_naming_conventions.py -v
   ```
   Build test structure matching the MAAP x KASK Figma tree. Assert:
   - Convention detected as MJML
   - All sections classified correctly (not UNKNOWN)
   - Column groups populated with correct content
   - Hero image detected (even if IMAGE fill on frame)

2. **Tests with descriptive naming:**
   Existing `test_penpot_converter.py` + `test_e2e_pipeline.py` still pass.

3. **Tests with generic naming:**
   Build structure with "Frame 1", "Frame 2" names. Assert content-based classification.

4. **Column grouping tests:**
   ```bash
   pytest app/design_sync/tests/test_column_grouping.py -v
   ```
   Assert: image in column 1 stays in column 1, not round-robin shuffled.

5. **Full pipeline test:**
   Run converter with mj-* structure → verify HTML output has correct sections, images in right columns, buttons with right text.

6. **Regression:** All 712 existing design_sync tests pass.

## Implementation Order

1. `protocol.py` — add `image_ref` to `DesignNode`, `is_background` to `ImagePlaceholder`
2. `figma/service.py` — extract `imageRef` from IMAGE fills on frames
3. `layout_analyzer.py` — `NamingConvention`, `ColumnGroup`, `_detect_naming_convention()`, `_classify_mj_section()`, `_detect_mj_columns()`, expanded `_SECTION_PATTERNS`, enhanced `_classify_by_content()`
4. `component_matcher.py` — use `ColumnGroup` in `_build_column_fills()`
5. `models.py` + migration — `config_json` column
6. `schemas.py` — connection config request/response
7. `import_service.py` + `converter_service.py` — thread config through pipeline
8. Tests — naming conventions, column grouping, regression
