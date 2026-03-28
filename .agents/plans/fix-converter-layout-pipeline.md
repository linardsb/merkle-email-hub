# Fix Design Import → HTML Layout Pipeline

## Context

The Figma-to-email converter (`app/design_sync/converter.py`) produces structurally correct but layout-broken HTML. After 5 fix iterations, centering and images work, but the layout token pipeline still generates:
- Excessive table nesting (5-7 levels deep for simple elements)
- Multi-column ghost tables for inline content (text + small icon)
- Empty visible sections with padding but no content
- Disproportionate column widths in button/nav grids

Root cause: the converter treats **every** horizontal sibling group as a multi-column layout requiring MSO ghost tables, with no heuristics to distinguish inline content from true grid layouts. Additionally, the sanitizer double-wraps `<div>` columns into extra `<table>` elements.

## Fixes (4 changes, ordered by impact)

### Fix 1: Eliminate sanitizer double-wrapping of multi-column `<div>`s

**File:** `converter.py:1172-1177`

**Problem:** `_render_multi_column_row()` outputs `<div class="column" style="display:inline-block;...">` wrapping an inner `<table>`. Then `sanitize_web_tags_for_email()` (line 932) detects `display:inline-block` as layout CSS and converts the `<div>` → `<table><tr><td>`, creating an extra nesting layer around every column.

**Fix:** Replace `<div>` with `<table role="presentation"><tr><td>` directly in `_render_multi_column_row()`, since the sanitizer would do this anyway. Remove the `<div>` entirely — output the inline-block style on the outer `<td>` that's already there. This eliminates 1 table nesting level per column.

Before:
```
<div style="display:inline-block;max-width:272px;...">     ← sanitizer converts to <table><tr><td>
  <table><tr><td>content</td></tr></table>                  ← inner table from renderer
</div>
```

After:
```
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
  <tr><td style="display:inline-block;max-width:272px;width:100%;vertical-align:top;">
    content                                                  ← recurse directly, no extra inner table
  </td></tr>
</table>
```

**Lines to change:** `converter.py:1172-1213` — rewrite the column wrapper output in `_render_multi_column_row()`. Remove the separate inner `<table>` per column since the outer wrapper table already provides the structure. Also remove the child `<tr><td>` wrapping at lines 1206-1209 — the recursive call already produces its own table structure.

---

### Fix 2: Add inline content heuristic for HORIZONTAL frames

**File:** `converter.py:773` (multi-column decision point)

**Problem:** A HORIZONTAL auto-layout frame with [TEXT, small IMAGE] triggers `_render_multi_column_row()` — overkill for nav items like "Man ↗". Every nav row gets a full ghost table with MSO conditionals.

**Fix:** Add `_is_inline_row(row)` heuristic before line 773. When a row consists of TEXT nodes + small images (both dimensions ≤ 30px), render them inline in a single `<td>` instead of as separate multi-column cells.

```python
def _is_inline_row(children: list[DesignNode]) -> bool:
    """Detect rows that should be inline (text + small icons) not multi-column."""
    if len(children) < 2 or len(children) > 4:
        return False
    has_text = any(c.type == DesignNodeType.TEXT for c in children)
    all_small_or_text = all(
        c.type == DesignNodeType.TEXT
        or (c.type == DesignNodeType.IMAGE and (c.width or 0) <= 30 and (c.height or 0) <= 30)
        for c in children
    )
    return has_text and all_small_or_text
```

New `_render_inline_row()` function renders as:
```html
<tr><td>
  <h1 style="...;display:inline;">Man</h1>
  <img src="arrow.png" width="20" height="20" style="display:inline;vertical-align:middle;" />
</td></tr>
```

**Integration point:** `converter.py:773` — check `_is_inline_row(row)` before `len(row) > 1`:
```python
if len(row) > 1 and not _is_inline_row(row):
    # existing multi-column rendering
elif len(row) > 1:
    # new inline rendering
```

---

### Fix 3: Prune empty frame subtrees

**File:** `converter.py:720-724` and `converter_service.py:391-394`

**Problem:** Frames containing only nested empty frames (no text/image descendants) still render as visible padding blocks. The current depth-0 check only catches childless top-level frames — nested empty trees still produce `<table><tr><td>&nbsp;</td></tr></table>` chains.

**Fix:** Add recursive `_has_visible_content(node)` check:

```python
def _has_visible_content(node: DesignNode) -> bool:
    """Check if node or any descendant has visible content (text/image)."""
    if node.type in (DesignNodeType.TEXT, DesignNodeType.IMAGE):
        return True
    return any(_has_visible_content(c) for c in node.children)
```

Apply at two levels:
1. **converter_service.py:391-394** — skip frames with no visible content at section level (already skips childless frames, extend to check descendants)
2. **converter.py:720** — for childless frames beyond depth 0, return empty string instead of `&nbsp;` spacer

---

### Fix 4: Use natural widths for sparse multi-column layouts

**File:** `converter.py:1048-1106` (`_calculate_column_widths`)

**Problem:** Column widths are always distributed proportionally across the full container width. For city buttons (3 buttons in a 552px row), the third button gets disproportionately wide to fill the remaining space. For nav items, a 20px icon column gets stretched.

**Fix:** When total children width is less than 60% of container width, use **natural widths** (actual design dimensions) instead of proportional distribution. This keeps small elements compact instead of stretching them.

```python
total_child_w = sum(w for _, w in known)
if total_child_w > 0 and total_child_w < avail * 0.6:
    # Sparse layout: use natural widths, don't stretch
    for i, w in known:
        widths[i] = round(w)
else:
    # Dense layout: existing proportional distribution
    ...
```

Also set the MSO ghost table `width` to `sum(widths) + total_gap` instead of `container_width` when using natural widths, so the ghost table isn't wider than needed.

---

## Files to modify

| File | Changes |
|------|---------|
| `app/design_sync/converter.py` | Fix 1 (lines 1172-1213), Fix 2 (new functions + line 773), Fix 3 (lines 720-724, new helper), Fix 4 (lines 1048-1106) |
| `app/design_sync/converter_service.py` | Fix 3 (lines 391-394, extend frame skip check) |
| `app/design_sync/tests/test_multi_column.py` | Update tests for new column wrapper structure, add inline row tests |
| `app/design_sync/tests/test_spacing_layout.py` | Update nesting expectations if changed |

## Verification

1. **Unit tests:** `python -m pytest app/design_sync/tests/test_multi_column.py app/design_sync/tests/test_spacing_layout.py -v`
2. **Full design_sync test suite:** `python -m pytest app/design_sync/tests/ -v`
3. **Types:** `make types`
4. **Lint:** `make lint`
5. **Manual:** Re-import the MAAP x KASK Figma design and verify:
   - Nav items (Man↗, Woman↗...) render as single rows without ghost tables
   - Product grid (2 helmets) still renders side-by-side correctly
   - City buttons row is compact, not stretched to full width
   - Empty sections between nav and footer are gone
   - Total table nesting is ≤4 levels for simple elements
