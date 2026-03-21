# Plan: Figma Node-Walk Color & Typography Extraction

## Context

Community Figma templates (e.g., Emailify) apply colors and fonts directly on nodes without publishing them as reusable Figma styles. The current `_parse_colors()` and `_parse_typography()` in `FigmaDesignSyncService` only iterate `file_data["styles"]` (published style metadata), so both return `[]` for these files.

Spacing extraction already works for all files because `_parse_spacing()` walks the full document tree. This plan replicates that pattern for colors and typography.

## Files to Modify

| File | Change |
|------|--------|
| `app/design_sync/figma/service.py` | Add `_walk_for_colors`, `_walk_for_typography`; update `_parse_colors`, `_parse_typography` |
| `app/design_sync/tests/test_service.py` | Add `TestNodeWalkExtraction` class with 11 tests |

**No changes to:** `protocol.py` (dataclasses sufficient), routes, schemas, repository, or API contract.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Color naming (node-walked) | Hex value as name (`"#3366CC"`) | Deterministic, dedup-friendly. Published styles already have human names and take priority. |
| Noise filtering (white/black) | Include all colors | Downstream `resolve_color_map()` and `BrandRepair` already handle palette selection. Filtering here risks losing legitimate brand whites/blacks. |
| Stroke extraction | Yes, include strokes | Border colors are valid design tokens (dividers, button outlines). |
| Sort order | Published styles first, then node-walked | Published styles have intentional names; node-walked fills in the gaps. |
| Color dedup key | Hex string | Two fills with same RGB but different alpha produce same hex; first occurrence wins. |
| Typography dedup key | `(family, weight, size)` tuple | Line height excluded from dedup — same font at same size may have different line heights; first occurrence is sufficient. |
| Gradient/image fills | Skip (only `SOLID` type) | Non-solid fills don't map to single hex tokens. |
| Transparent fills | Skip (`alpha < 0.01`) | Invisible fills are not design tokens. |
| `lineHeightPx` fallback | `size * 1.2` | Figma omits it when set to "auto"; CSS default is `line-height: 1.2`. |

## Implementation Steps

### Step 1: Add `_walk_for_colors()` — new method

Insert after `_walk_for_spacing()` (~line 283). Follows identical recursive pattern:

```python
def _walk_for_colors(
    self,
    node: Any,
    colors: list[ExtractedColor],
    seen_hex: set[str],
) -> None:
    """Recursively extract SOLID fill/stroke colors from every node."""
    if not isinstance(node, dict):
        return
    node_d = cast(dict[str, Any], node)

    for prop in ("fills", "strokes"):
        raw_list = node_d.get(prop)
        if not isinstance(raw_list, list):
            continue
        for fill in cast(list[Any], raw_list):
            if not isinstance(fill, dict):
                continue
            fill_d = cast(dict[str, Any], fill)
            if fill_d.get("type") != "SOLID":
                continue
            color_raw = fill_d.get("color")
            if not isinstance(color_raw, dict):
                continue
            c = cast(dict[str, Any], color_raw)
            alpha = float(c.get("a", 1.0))
            if alpha < 0.01:
                continue
            hex_val = _rgba_to_hex(
                float(c.get("r", 0)),
                float(c.get("g", 0)),
                float(c.get("b", 0)),
            )
            if hex_val in seen_hex:
                continue
            seen_hex.add(hex_val)
            colors.append(ExtractedColor(name=hex_val, hex=hex_val, opacity=alpha))

    for child in cast(list[Any], node_d.get("children", [])):
        self._walk_for_colors(child, colors, seen_hex)
```

### Step 2: Add `_walk_for_typography()` — new method

Insert after `_walk_for_colors()`:

```python
def _walk_for_typography(
    self,
    node: Any,
    typography: list[ExtractedTypography],
    seen_keys: set[tuple[str, str, float]],
) -> None:
    """Recursively extract typography from TEXT nodes."""
    if not isinstance(node, dict):
        return
    node_d = cast(dict[str, Any], node)

    if str(node_d.get("type", "")) == "TEXT":
        style = node_d.get("style")
        if isinstance(style, dict):
            s = cast(dict[str, Any], style)
            family = str(s.get("fontFamily", ""))
            weight = str(s.get("fontWeight", "400"))
            size = float(s.get("fontSize", 0))
            if family and size > 0:
                key = (family, weight, size)
                if key not in seen_keys:
                    seen_keys.add(key)
                    line_height = float(s.get("lineHeightPx", size * 1.2))
                    name = f"{family} {weight} {int(size)}px"
                    typography.append(
                        ExtractedTypography(
                            name=name, family=family, weight=weight,
                            size=size, line_height=line_height,
                        )
                    )

    for child in cast(list[Any], node_d.get("children", [])):
        self._walk_for_typography(child, typography, seen_keys)
```

### Step 3: Update `_parse_colors()` — two-phase merge

Replace lines 190-225. The key change: track `seen_hex` during Phase 1 (published styles), then pass it to Phase 2 (node walk) so duplicates are skipped automatically.

```python
def _parse_colors(
    self,
    file_data: dict[str, Any],
    styles_data: dict[str, Any],  # noqa: ARG002
) -> list[ExtractedColor]:
    """Extract colour tokens from published styles + node walk fallback."""
    colors: list[ExtractedColor] = []
    seen_hex: set[str] = set()

    # Phase 1: Published styles (better names, take priority)
    raw_styles = file_data.get("styles", {})
    if isinstance(raw_styles, dict):
        styles = cast(dict[str, Any], raw_styles)
        for style_id, style_meta in styles.items():
            # ... existing published style logic, but add seen_hex.add(hex_val) ...

    # Phase 2: Node walk (picks up unstyled colors, skips duplicates via seen_hex)
    self._walk_for_colors(file_data.get("document", {}), colors, seen_hex)

    return colors
```

### Step 4: Update `_parse_typography()` — two-phase merge

Same pattern. Track `seen_keys: set[tuple[str, str, float]]` during Phase 1, pass to Phase 2.

### Step 5: Add tests — `TestNodeWalkExtraction` class

11 test cases in `app/design_sync/tests/test_service.py`:

| # | Test | Asserts |
|---|------|---------|
| 1 | Colors from node fills, no published styles | 1 color extracted, name = hex |
| 2 | Colors from strokes | Stroke colors extracted |
| 3 | Transparent fills skipped | `alpha < 0.01` → 0 colors |
| 4 | Gradient fills skipped | Only SOLID extracted |
| 5 | Published style takes priority over node-walked | Same hex → published name wins, count = 1 |
| 6 | Typography from node walk, no published styles | Family/weight/size/line_height correct |
| 7 | Typography dedup by (family, weight, size) | Same combo → count = 1 |
| 8 | Non-TEXT nodes' style ignored | FRAME with style property → 0 typography |
| 9 | Mixed published + node-walked colors | Both sources, no duplicates, published first |
| 10 | Empty document → empty lists | Edge case |
| 11 | Deeply nested colors extracted | 3+ levels deep |

## Verification

```bash
# Run the specific test class
pytest app/design_sync/tests/test_service.py::TestNodeWalkExtraction -v

# Run all design_sync tests
pytest app/design_sync/tests/ -v

# Type checking
make types

# Full check
make check
```

Manual verification: connect the Emailify community template (`sV1UnG6Tv6SvaJCHVaLGtc`) and confirm Colors and Typography counts are > 0.
