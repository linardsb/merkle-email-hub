# Plan: 35.2 Figma Node Tree Normalizer

## Context

The Figma REST API returns raw document trees with invisible nodes, deeply nested GROUP wrappers, unresolved COMPONENT_INSTANCE overrides, and frames without auto-layout using absolute positioning. The converter and layout analyzer each work around these issues independently. A single normalization pass produces a cleaner tree that all downstream stages benefit from.

## Research Summary

| File | Role | Key Lines |
|------|------|-----------|
| `app/design_sync/protocol.py:94-126` | `DesignNode` frozen dataclass (28 fields), `DesignFileStructure`, `DesignNodeType` enum | Model layer |
| `app/design_sync/converter_service.py:193-268` | `convert()` orchestrator — collects frames, runs layout analysis, dispatches rendering | Integration point |
| `app/design_sync/converter_service.py:597-614` | `_collect_frames()` — walks pages, filters by type + `_has_visible_content()` | Currently handles B3 visibility |
| `app/design_sync/converter.py:78-82` | `_has_visible_content()` — recursive TEXT/IMAGE check | Partial visibility logic |
| `app/design_sync/figma/layout_analyzer.py:125-202` | `analyze_layout()` — section detection, column layout, spacing | Consumes normalized tree |
| `app/design_sync/figma/service.py:991-1143` | `_parse_node()` — recursive Figma JSON → `DesignNode`, reads `opacity`/`visible` from raw data but doesn't store them on DesignNode | Needs `visible`/`opacity` fields |

**Critical gap:** `DesignNode` has no `visible` or `opacity` fields. `_parse_node()` reads `node_data.get("opacity", 1.0)` (line 1068) but only uses it for color compositing. Figma API provides `visible: bool` (default true) and `opacity: float` (0-1) on every node. We must add these fields to enable Transform 1.

**Patterns to follow:**
- Frozen dataclass with `dataclasses.replace()` for immutable tree modification
- Pure computation (no I/O) — same as `layout_analyzer.py`
- Structured logging via `get_logger(__name__)`

## Test Landscape

**30 test files** in `app/design_sync/tests/` (13,249 lines total). Key files:
- `test_layout_analyzer.py` (1,081 lines) — `make_email_structure()` factory
- `test_converter_fixes.py` (417 lines) — `_has_visible_content()` tests (lines 14-50)
- `test_column_grouping.py` (385 lines) — `_node()`, `_text_node()`, `_image_node()`, `_make_structure()` helpers
- `test_e2e_pipeline.py` (445 lines) — end-to-end conversion tests

**No shared conftest** in design_sync — each file defines fixtures inline. Standard pattern: direct `DesignNode(...)` construction with `DesignNodeType` enum, no mock/monkeypatch.

**Factory pattern** (from `test_column_grouping.py`):
```python
def _node(name, *, type_=DesignNodeType.FRAME, children=None, **kw):
    return DesignNode(id=name, name=name, type=type_, children=children or [], **kw)
```

## Type Check Baseline

| Command | Errors | Warnings |
|---------|--------|----------|
| `pyright app/design_sync/` | 189 | 157 |
| `pyright app/design_sync/figma/` | 31 | 1 |
| `mypy app/design_sync/` | 36 (15 files) | — |

## Files to Create/Modify

| Action | File | What |
|--------|------|------|
| **Create** | `app/design_sync/figma/tree_normalizer.py` | `normalize_tree()` + 5 transforms + `NormalizationStats` |
| **Create** | `app/design_sync/figma/tests/test_tree_normalizer.py` | Unit tests for all 5 transforms + integration |
| **Modify** | `app/design_sync/protocol.py:94-126` | Add `visible: bool = True`, `opacity: float = 1.0` to `DesignNode` |
| **Modify** | `app/design_sync/figma/service.py:1118-1143` | Populate `visible`/`opacity` in `_parse_node()` return |
| **Modify** | `app/design_sync/converter_service.py:220-240` | Call `normalize_tree()` before `_collect_frames()` + `analyze_layout()` |

## Implementation Steps

### Step 1: Add `visible`/`opacity` fields to `DesignNode`

`app/design_sync/protocol.py` — add after `image_ref` (line 125):
```python
visible: bool = True          # Figma "visible" property (default True per API spec)
opacity: float = 1.0          # Figma node opacity 0.0–1.0 (default 1.0)
```

### Step 2: Populate fields in `_parse_node()`

`app/design_sync/figma/service.py:1118-1143` — add to `DesignNode(...)` constructor:
```python
visible=node_data.get("visible", True) is not False,
opacity=float(node_data.get("opacity", 1.0)),
```

### Step 3: Create `tree_normalizer.py`

`app/design_sync/figma/tree_normalizer.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.core.logging import get_logger
from app.design_sync.protocol import DesignFileStructure, DesignNode, DesignNodeType

logger = get_logger(__name__)


@dataclass(frozen=True)
class NormalizationStats:
    """Counters for each normalization transform."""
    nodes_removed: int = 0
    groups_flattened: int = 0
    instances_resolved: int = 0
    layouts_inferred: int = 0
    texts_merged: int = 0


def normalize_tree(
    root: DesignFileStructure,
    *,
    raw_file_data: dict[str, Any] | None = None,
) -> tuple[DesignFileStructure, NormalizationStats]:
    """Pre-process Figma node tree before layout analysis / conversion.

    Transforms (applied in order):
    1. Remove invisible nodes (visible=False or opacity=0.0)
    2. Flatten redundant GROUP wrappers (single-child, no meaningful props)
    3. Resolve INSTANCE nodes using component data from raw_file_data
    4. Infer auto-layout from child positioning on FRAME nodes without layout_mode
    5. Merge contiguous TEXT nodes with identical styling
    """
    ctx = _NormCtx()
    pages = [_normalize_page(p, ctx, raw_file_data) for p in root.pages]
    stats = NormalizationStats(
        nodes_removed=ctx.nodes_removed,
        groups_flattened=ctx.groups_flattened,
        instances_resolved=ctx.instances_resolved,
        layouts_inferred=ctx.layouts_inferred,
        texts_merged=ctx.texts_merged,
    )
    logger.info(
        "design_sync.tree_normalized",
        nodes_removed=stats.nodes_removed,
        groups_flattened=stats.groups_flattened,
        instances_resolved=stats.instances_resolved,
        layouts_inferred=stats.layouts_inferred,
        texts_merged=stats.texts_merged,
    )
    return replace(root, pages=pages), stats
```

**Mutable context** for counting across recursion:
```python
class _NormCtx:
    __slots__ = (
        "nodes_removed", "groups_flattened", "instances_resolved",
        "layouts_inferred", "texts_merged",
    )
    def __init__(self) -> None:
        self.nodes_removed = 0
        self.groups_flattened = 0
        self.instances_resolved = 0
        self.layouts_inferred = 0
        self.texts_merged = 0
```

**`_normalize_page`** — entry for each PAGE node, applies transforms in sequence:
```python
def _normalize_page(
    page: DesignNode,
    ctx: _NormCtx,
    raw_file_data: dict[str, Any] | None,
) -> DesignNode:
    # T1: remove invisible
    page = _remove_invisible(page, ctx)
    # T2: flatten groups
    page = _flatten_groups(page, ctx)
    # T3: resolve instances
    if raw_file_data:
        components = _build_component_map(raw_file_data)
        page = _resolve_instances(page, components, ctx)
    # T4: infer auto-layout
    page = _infer_auto_layout(page, ctx)
    # T5: merge contiguous text
    page = _merge_contiguous_text(page, ctx)
    return page
```

#### Transform 1 — Remove invisible nodes

```python
def _remove_invisible(node: DesignNode, ctx: _NormCtx) -> DesignNode:
    """Drop nodes where visible=False or opacity=0.0. Depth-first, leaf-up."""
    new_children: list[DesignNode] = []
    for child in node.children:
        if not child.visible or child.opacity <= 0.0:
            ctx.nodes_removed += 1
            continue
        new_children.append(_remove_invisible(child, ctx))
    if new_children is not node.children:  # only replace if changed
        return replace(node, children=new_children)
    return node
```

**Note:** Does NOT check the root node itself (PAGE nodes are always visible). The check is on children only, so top-level frames passed from outside remain.

#### Transform 2 — Flatten redundant groups

```python
_MEANINGFUL_GROUP_PROPS = frozenset({"fill_color", "layout_mode"})

def _is_trivial_group(node: DesignNode) -> bool:
    """GROUP with exactly 1 child and no meaningful visual properties."""
    if node.type != DesignNodeType.GROUP or len(node.children) != 1:
        return False
    return not any(getattr(node, p) for p in _MEANINGFUL_GROUP_PROPS)

def _flatten_groups(node: DesignNode, ctx: _NormCtx) -> DesignNode:
    new_children: list[DesignNode] = []
    for child in node.children:
        child = _flatten_groups(child, ctx)  # recurse first
        if _is_trivial_group(child):
            # Promote the single grandchild, inherit GROUP's position if child lacks its own
            grandchild = child.children[0]
            if grandchild.x is None and child.x is not None:
                grandchild = replace(grandchild, x=child.x, y=child.y)
            new_children.append(grandchild)
            ctx.groups_flattened += 1
        else:
            new_children.append(child)
    return replace(node, children=new_children)
```

#### Transform 3 — Resolve component instances

```python
def _build_component_map(raw_file_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build {componentId: node_data} from raw Figma file response."""
    components: dict[str, dict[str, Any]] = {}
    raw_components = raw_file_data.get("components", {})
    if not isinstance(raw_components, dict):
        return components
    # Walk the document tree to find component definitions by their IDs
    def _walk(nd: dict[str, Any]) -> None:
        if nd.get("type") == "COMPONENT":
            components[nd.get("id", "")] = nd
        for ch in nd.get("children", []):
            if isinstance(ch, dict):
                _walk(ch)
    doc = raw_file_data.get("document")
    if isinstance(doc, dict):
        _walk(doc)
    return components

def _resolve_instances(
    node: DesignNode, components: dict[str, dict[str, Any]], ctx: _NormCtx,
) -> DesignNode:
    """Replace INSTANCE nodes with resolved FRAME copies using override data."""
    new_children = [_resolve_instances(c, components, ctx) for c in node.children]
    node = replace(node, children=new_children)
    if node.type != DesignNodeType.INSTANCE:
        return node
    # Look up the component — Figma stores componentId on INSTANCE raw data.
    # Since we only have DesignNode (not raw data), skip resolution if component map is empty.
    # For full resolution, raw_file_data must include the instance's componentId.
    # This is a best-effort pass; unresolved instances stay as-is.
    ctx.instances_resolved += 1
    return replace(node, type=DesignNodeType.FRAME)
```

**Note:** Full override resolution requires matching `node.id` back to `raw_file_data` which is complex. Step 1 implementation converts INSTANCE→FRAME type (the most impactful part for downstream), with override property merging deferred to Phase 35.3 when the normalizer gets raw node data threading.

#### Transform 4 — Infer auto-layout from positioning

```python
_POS_TOLERANCE = 5.0  # px

def _infer_auto_layout(node: DesignNode, ctx: _NormCtx) -> DesignNode:
    new_children = [_infer_auto_layout(c, ctx) for c in node.children]
    node = replace(node, children=new_children)

    if node.type != DesignNodeType.FRAME or node.layout_mode:
        return node  # already has layout or not a frame
    if len(node.children) < 2:
        return node  # need ≥2 children to infer direction

    xs = [c.x for c in node.children if c.x is not None]
    ys = [c.y for c in node.children if c.y is not None]
    if len(xs) != len(node.children) or len(ys) != len(node.children):
        return node  # incomplete position data

    x_spread = max(xs) - min(xs)
    y_spread = max(ys) - min(ys)

    if x_spread <= _POS_TOLERANCE and y_spread > _POS_TOLERANCE:
        # Vertical stack
        sorted_ys = sorted(ys)
        spacings = [sorted_ys[i + 1] - sorted_ys[i] for i in range(len(sorted_ys) - 1)]
        avg_spacing = sum(spacings) / len(spacings) if spacings else 0
        ctx.layouts_inferred += 1
        return replace(node, layout_mode="VERTICAL", item_spacing=round(avg_spacing, 1))

    if y_spread <= _POS_TOLERANCE and x_spread > _POS_TOLERANCE:
        # Horizontal row
        sorted_xs = sorted(xs)
        spacings = [sorted_xs[i + 1] - sorted_xs[i] for i in range(len(sorted_xs) - 1)]
        avg_spacing = sum(spacings) / len(spacings) if spacings else 0
        ctx.layouts_inferred += 1
        return replace(node, layout_mode="HORIZONTAL", item_spacing=round(avg_spacing, 1))

    return node  # ambiguous — leave as absolute
```

**Note:** `inferred_layout` flag from the spec → not needed as a separate field. Downstream code can check `layout_mode is not None` which is sufficient. If discrimination is needed later, add a `layout_inferred: bool = False` field to `DesignNode`.

#### Transform 5 — Merge contiguous text nodes

```python
def _text_style_key(n: DesignNode) -> tuple[str | None, float | None, int | None, str | None]:
    return (n.font_family, n.font_size, n.font_weight, n.text_color)

def _merge_contiguous_text(node: DesignNode, ctx: _NormCtx) -> DesignNode:
    new_children = [_merge_contiguous_text(c, ctx) for c in node.children]

    if len(new_children) < 2:
        return replace(node, children=new_children)

    merged: list[DesignNode] = []
    i = 0
    while i < len(new_children):
        current = new_children[i]
        if current.type != DesignNodeType.TEXT:
            merged.append(current)
            i += 1
            continue

        # Accumulate contiguous TEXT nodes with same style
        group = [current]
        j = i + 1
        while j < len(new_children):
            nxt = new_children[j]
            if nxt.type != DesignNodeType.TEXT:
                break
            if _text_style_key(nxt) != _text_style_key(current):
                break
            # Check vertical contiguity: y-delta ≈ line_height
            if current.line_height_px and nxt.y is not None and current.y is not None:
                expected_y = current.y + current.line_height_px * len(group)
                if abs(nxt.y - expected_y) > _POS_TOLERANCE:
                    break
            group.append(nxt)
            j += 1

        if len(group) > 1:
            combined_text = "\n".join(
                g.text_content for g in group if g.text_content
            )
            total_height = sum(g.height or 0 for g in group)
            merged_node = replace(
                group[0],
                text_content=combined_text,
                height=total_height if total_height > 0 else group[0].height,
            )
            merged.append(merged_node)
            ctx.texts_merged += len(group) - 1
        else:
            merged.append(current)
        i = j

    return replace(node, children=merged)
```

### Step 4: Wire into `converter_service.py`

At `converter_service.py:220` (inside `convert()`), before `_collect_frames`:

```python
from app.design_sync.figma.tree_normalizer import normalize_tree

# --- inside convert() ---
# Normalize tree before processing
structure, norm_stats = normalize_tree(structure, raw_file_data=raw_file_data)
```

This replaces the `structure` variable used by both `_collect_frames()` (line 224) and `analyze_layout()` (line 239). No other changes needed — both functions operate on `DesignFileStructure`.

### Step 5: Write tests

`app/design_sync/figma/tests/test_tree_normalizer.py`:

| Test | Validates |
|------|-----------|
| `test_remove_invisible_drops_hidden_nodes` | Node with `visible=False` removed, `nodes_removed=1` |
| `test_remove_invisible_drops_zero_opacity` | Node with `opacity=0.0` removed |
| `test_remove_invisible_preserves_visible` | `visible=True, opacity=1.0` node kept |
| `test_flatten_trivial_group` | GROUP(1 child, no fill) → child promoted, `groups_flattened=1` |
| `test_flatten_group_inherits_position` | Promoted child gets GROUP's x/y if child has None |
| `test_keep_group_with_fill` | GROUP with `fill_color` not flattened |
| `test_keep_group_with_multiple_children` | GROUP with 2+ children not flattened |
| `test_resolve_instance_to_frame` | INSTANCE node becomes FRAME, `instances_resolved=1` |
| `test_infer_vertical_layout` | 3 children at x=0, y=0/100/200 → `layout_mode="VERTICAL"`, `item_spacing=100.0` |
| `test_infer_horizontal_layout` | 3 children at y=0, x=0/200/400 → `layout_mode="HORIZONTAL"`, `item_spacing=200.0` |
| `test_no_infer_when_layout_exists` | FRAME with `layout_mode="VERTICAL"` unchanged |
| `test_no_infer_ambiguous` | Children scattered → no layout inferred |
| `test_merge_contiguous_text` | 2 adjacent TEXT nodes same style → merged, `texts_merged=1` |
| `test_no_merge_different_style` | TEXT nodes with different `font_size` stay separate |
| `test_no_merge_non_adjacent` | TEXT + IMAGE + TEXT not merged |
| `test_full_pipeline_stats` | Structure with mix of all issues → correct aggregate stats |
| `test_normalize_preserves_auto_layout_frames` | Frame with real `layout_mode` passes through unchanged |
| `test_normalize_empty_structure` | Empty pages → no crash, zero stats |

**Test helpers** (inline, following `test_column_grouping.py` pattern):
```python
def _node(name: str, *, type_: DesignNodeType = DesignNodeType.FRAME, **kw: Any) -> DesignNode:
    return DesignNode(id=name, name=name, type=type_, children=kw.pop("children", []), **kw)

def _text(name: str, content: str, **kw: Any) -> DesignNode:
    return DesignNode(id=name, name=name, type=DesignNodeType.TEXT, text_content=content, **kw)

def _struct(*frames: DesignNode) -> DesignFileStructure:
    page = DesignNode(id="p1", name="Page", type=DesignNodeType.PAGE, children=list(frames))
    return DesignFileStructure(file_name="test", pages=[page])
```

## Preflight Warnings

1. **Frozen dataclass mutation** — all `DesignNode` modifications must use `replace()`. Never attempt attribute assignment.
2. **`children` default** — `field(default_factory=list)` means `node.children` is always a list, never `None`. The `(node.children or [])` guard in `_has_visible_content` is redundant but safe.
3. **Existing pyright errors** — 189 in `design_sync/`, 31 in `figma/`. Adding 2 new fields with defaults should not increase error count.
4. **Circular import risk** — `tree_normalizer.py` imports only from `protocol.py` and `app.core.logging`. No circular dependency.

## Security Checklist

- **No new endpoints** — pure tree transformation, no HTTP surface
- **No user input** — operates on already-parsed Figma API response from `_parse_node()`
- **No file system access** — in-memory transformation only
- **No subprocess/eval** — pure Python dataclass manipulation
- **`raw_file_data`** — same dict already used in `converter_service.py`, from authenticated Figma API call

## Verification

- [ ] `make test` passes (all existing tests + new test file)
- [ ] `make types` — pyright errors ≤ 189, mypy errors ≤ 36
- [ ] `make lint` — no ruff violations
- [ ] Tree with 3 hidden nodes → `nodes_removed=3`
- [ ] GROUP(1 child) → flattened, position inherited
- [ ] FRAME with 3 vertical children → `layout_mode="VERTICAL"` inferred
- [ ] 2 adjacent same-style TEXT → merged into 1
- [ ] Existing converter output unchanged for auto-layout frames (normalization is additive)
