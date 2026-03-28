# Fix Converter Layout Bugs

**Status:** planned
**Phase:** 33 (Design Token Pipeline)
**Files:** `converter.py`, `layout_analyzer.py`

## Problem

Imported Figma designs render with broken layout:
- Two-column product grids stack vertically
- Navigation items ("Man", "Woman", "Accessories") render as oversized CTA buttons
- Empty spacer sections with no content
- Invalid HTML nesting (`<td><td>`) causes browser error recovery

## Root Causes

### Bug 1 — Invalid `<td><td>` nesting (critical)

`_render_button()` (`converter.py:427-465`) returns `<td align="center">…</td>`.
Two call sites wrap non-TEXT children in an **outer** `<td>`, creating double nesting:

| Call site | Line | Wrapping |
|-----------|------|----------|
| Flat/no-layout path | `converter.py:704-705` | `<tr><td>{child_html}</td></tr>` |
| Row-based path | `converter.py:837-839` | `<td>{child_html}</td>` |

Result: `<tr><td><td align="center">…</td></td></tr>` — invalid HTML.

TEXT nodes already skip the outer wrapper (lines 706-707, 840-841). Buttons need the same treatment.

**Fix:** At both sites, check `button_ids` — if child is a button, skip outer `<td>` wrapper.

```python
# converter.py:704-707 — flat path
is_button = bool(button_ids and child.id in button_ids)
if child.type != DesignNodeType.TEXT and not is_button:
    flat_lines.append(f"{pad}<tr><td>{child_html}</td></tr>")
else:
    flat_lines.append(f"{pad}<tr>{child_html}</tr>")
```

```python
# converter.py:822-841 — row path
is_button = bool(button_ids and child.id in button_ids)
if child.type != DesignNodeType.TEXT and not is_button:
    # existing <td> wrapper logic ...
else:
    lines.append(child_html)
```

### Bug 2 — Navigation items misclassified as buttons

`_walk_for_buttons()` (`layout_analyzer.py:411-442`) matches any frame with:
- 1 TEXT child, text <= 30 chars, height <= 80px, **width <= 300px**

This is too broad — "Man" (40px frame), "Accessories" (200px frame), etc. all match.

**Fix:** Replace `width <= 300` fallback with `fill_color` check. Real buttons have a visible background fill; nav items are transparent.

```python
# layout_analyzer.py:425-430
has_fill = bool(
    node.fill_color
    and node.fill_color.upper() not in ("#FFFFFF", "#FFF", "")
)
if is_button_name or has_fill:
    # ... detect as button
```

### Bug 3 — Empty padding-only sections

`converter.py:719-723` — childless frames with padding render as `<tr><td style="padding:…">&nbsp;</td></tr>`, creating visible blank rows.

**Fix:** Skip the `&nbsp;` filler for childless frames **only at section level** (`_depth == 0`). Nested childless frames (e.g. multi-column cells) still need the existing `&nbsp;` behavior for column structure.

```python
# converter.py:719-723
if not node.children:
    if _depth == 0:
        return ""  # top-level empty section → skip entirely
    if has_padding:
        lines.append(f'{pad}  <tr><td style="{padding_css}">&nbsp;</td></tr>')
    else:
        lines.append(f"{pad}  <tr><td>&nbsp;</td></tr>")
```

## Changes Summary

| File | Lines | What |
|------|-------|------|
| `converter.py` | 704-707 | Skip `<td>` wrapper for button nodes (flat path) |
| `converter.py` | 822-841 | Skip `<td>` wrapper for button nodes (row path) |
| `converter.py` | 719-723 | Skip childless frames at section level only |
| `layout_analyzer.py` | 425-430 | Replace `width<=300` with `fill_color` check |

## Risks

- **Bug 1 fix:** Safe — buttons already emit `<td>`, removing double-wrap is correct
- **Bug 2 fix:** Could under-detect buttons if a real CTA has white/no fill in Figma. Mitigated by `name_hints` primary check remaining
- **Bug 3 fix:** Only skips at `_depth == 0`. Nested childless frames keep `&nbsp;` — existing tests pass

## Preflight Findings

### Tests Assessed (Safe — No Fix Needed)

| File | Line | Pattern | Why Safe |
|------|------|---------|----------|
| `test_layout_analyzer.py` | 127 | button uses `name="button-cta"` | Name hint matches — unaffected by fill_color change |
| `test_semantic_html.py` | 133 | `fill_color="#0066cc"` on button | Has fill — passes both old and new heuristic |
| `test_builder_annotations.py` | 116 | `fill_color="#0066cc"` on button | Same |
| `test_penpot_converter.py` | 320 | `test_props_map_padding()` childless frame | Direct call `_depth=0` — see caution below |
| `test_penpot_converter.py` | 253 | `test_props_map_bg_color()` childless frame | Same |
| `test_multi_column.py` | 139 | `html.count("<tr>") >= 2` | Uses `>=`, tolerant |
| `test_e2e_pipeline.py` | 370 | `sections_count == 4` | Unchanged |
| `test_builder_annotations.py` | 230 | `count('data-slot-name="body"') == 2` | Text slots unchanged |

### Caution: Bug 3 and direct `node_to_email_html()` calls

`test_props_map_padding` and `test_props_map_bg_color` call `node_to_email_html()` directly with `_depth=0` default. If Bug 3 returns `""` at `_depth == 0` for childless frames, these break. **Safest approach:** only skip empty sections in `converter_service.py` (the section loop) rather than inside `node_to_email_html()`. This avoids touching the internal function's contract.

### Pyright Baseline

- Target files: **1 error** (pre-existing `reportUnknownVariableType` in `layout_analyzer.py:104`)
- After implementation: `uv run pyright app/design_sync/converter.py app/design_sync/figma/layout_analyzer.py` — new errors above 1 are regressions

## Testing

- Run existing test suite: `make test -- -k design_sync` (514 tests)
- Verify the MAAP x KASK email renders correctly after fixes
- Check multi-column sections have valid `<tr><td>` nesting (no `<td><td>`)
- Check nav items render as text, not CTA buttons
