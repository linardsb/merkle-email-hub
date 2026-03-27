"""Figma node tree normalizer — pre-processing pass before layout analysis.

Transforms applied in order:
1. Remove invisible nodes (visible=False or opacity=0.0)
2. Flatten redundant GROUP wrappers (single-child, no meaningful props)
3. Resolve INSTANCE nodes to FRAME type
4. Infer auto-layout from child positioning
5. Merge contiguous TEXT nodes with identical styling
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.core.logging import get_logger
from app.design_sync.protocol import DesignFileStructure, DesignNode, DesignNodeType

logger = get_logger(__name__)

_POS_TOLERANCE = 5.0  # px tolerance for position alignment checks
_MEANINGFUL_GROUP_PROPS = frozenset({"fill_color", "layout_mode"})


@dataclass(frozen=True)
class NormalizationStats:
    """Counters for each normalization transform."""

    nodes_removed: int = 0
    groups_flattened: int = 0
    instances_resolved: int = 0
    layouts_inferred: int = 0
    texts_merged: int = 0


class _NormCtx:
    """Mutable counters accumulated across recursive tree walks."""

    __slots__ = (
        "groups_flattened",
        "instances_resolved",
        "layouts_inferred",
        "nodes_removed",
        "texts_merged",
    )

    def __init__(self) -> None:
        self.nodes_removed = 0
        self.groups_flattened = 0
        self.instances_resolved = 0
        self.layouts_inferred = 0
        self.texts_merged = 0


def normalize_tree(
    root: DesignFileStructure,
    *,
    raw_file_data: dict[str, Any] | None = None,
) -> tuple[DesignFileStructure, NormalizationStats]:
    """Pre-process Figma node tree before layout analysis / conversion.

    Returns the normalized structure and statistics about what changed.
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


def _normalize_page(
    page: DesignNode,
    ctx: _NormCtx,
    raw_file_data: dict[str, Any] | None,
) -> DesignNode:
    """Apply all transforms to a single page node."""
    page = _remove_invisible(page, ctx)
    page = _flatten_groups(page, ctx)
    if raw_file_data:
        page = _resolve_instances(page, ctx)
    page = _infer_auto_layout(page, ctx)
    page = _merge_contiguous_text(page, ctx)
    return page


# ---------------------------------------------------------------------------
# Transform 1 — Remove invisible nodes
# ---------------------------------------------------------------------------


def _remove_invisible(node: DesignNode, ctx: _NormCtx) -> DesignNode:
    """Drop children where visible=False or opacity<=0.0. Depth-first, leaf-up."""
    new_children: list[DesignNode] = []
    changed = False
    for child in node.children:
        if not child.visible or child.opacity <= 0.0:
            ctx.nodes_removed += 1
            changed = True
            continue
        recursed = _remove_invisible(child, ctx)
        if recursed is not child:
            changed = True
        new_children.append(recursed)
    if changed:
        return replace(node, children=new_children)
    return node


# ---------------------------------------------------------------------------
# Transform 2 — Flatten redundant groups
# ---------------------------------------------------------------------------


def _is_trivial_group(node: DesignNode) -> bool:
    """GROUP with exactly 1 child and no meaningful visual properties."""
    if node.type != DesignNodeType.GROUP or len(node.children) != 1:
        return False
    return not any(getattr(node, p) for p in _MEANINGFUL_GROUP_PROPS)


def _flatten_groups(node: DesignNode, ctx: _NormCtx) -> DesignNode:
    """Replace trivial GROUP wrappers with their single child."""
    new_children: list[DesignNode] = []
    for child in node.children:
        child = _flatten_groups(child, ctx)
        if _is_trivial_group(child):
            grandchild = child.children[0]
            if grandchild.x is None and child.x is not None:
                grandchild = replace(grandchild, x=child.x, y=child.y)
            new_children.append(grandchild)
            ctx.groups_flattened += 1
        else:
            new_children.append(child)
    return replace(node, children=new_children)


# ---------------------------------------------------------------------------
# Transform 3 — Resolve component instances
# ---------------------------------------------------------------------------


def _resolve_instances(
    node: DesignNode,
    ctx: _NormCtx,
) -> DesignNode:
    """Convert INSTANCE nodes to FRAME type for downstream processing.

    Full override resolution (merging component properties) is deferred to a
    future phase — this pass only reclassifies INSTANCE → FRAME so downstream
    code treats them as regular containers.
    """
    new_children = [_resolve_instances(c, ctx) for c in node.children]
    node = replace(node, children=new_children)
    if node.type != DesignNodeType.INSTANCE:
        return node
    ctx.instances_resolved += 1
    return replace(node, type=DesignNodeType.FRAME)


# ---------------------------------------------------------------------------
# Transform 4 — Infer auto-layout from positioning
# ---------------------------------------------------------------------------


def _infer_auto_layout(node: DesignNode, ctx: _NormCtx) -> DesignNode:
    """For FRAME nodes without layout_mode, infer direction from child positions."""
    new_children = [_infer_auto_layout(c, ctx) for c in node.children]
    node = replace(node, children=new_children)

    if node.type != DesignNodeType.FRAME or node.layout_mode:
        return node
    if len(node.children) < 2:
        return node

    xs = [c.x for c in node.children if c.x is not None]
    ys = [c.y for c in node.children if c.y is not None]
    if len(xs) != len(node.children) or len(ys) != len(node.children):
        return node

    x_spread = max(xs) - min(xs)
    y_spread = max(ys) - min(ys)

    if x_spread <= _POS_TOLERANCE and y_spread > _POS_TOLERANCE:
        sorted_ys = sorted(ys)
        spacings = [sorted_ys[i + 1] - sorted_ys[i] for i in range(len(sorted_ys) - 1)]
        avg_spacing = sum(spacings) / len(spacings) if spacings else 0
        ctx.layouts_inferred += 1
        return replace(node, layout_mode="VERTICAL", item_spacing=round(avg_spacing, 1))

    if y_spread <= _POS_TOLERANCE and x_spread > _POS_TOLERANCE:
        sorted_xs = sorted(xs)
        spacings = [sorted_xs[i + 1] - sorted_xs[i] for i in range(len(sorted_xs) - 1)]
        avg_spacing = sum(spacings) / len(spacings) if spacings else 0
        ctx.layouts_inferred += 1
        return replace(node, layout_mode="HORIZONTAL", item_spacing=round(avg_spacing, 1))

    return node


# ---------------------------------------------------------------------------
# Transform 5 — Merge contiguous text nodes
# ---------------------------------------------------------------------------


def _text_style_key(
    n: DesignNode,
) -> tuple[str | None, float | None, int | None, str | None]:
    """Key for grouping TEXT nodes with identical styling."""
    return (n.font_family, n.font_size, n.font_weight, n.text_color)


def _merge_contiguous_text(node: DesignNode, ctx: _NormCtx) -> DesignNode:
    """Merge adjacent TEXT children that share identical styling."""
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

        group = [current]
        j = i + 1
        while j < len(new_children):
            nxt = new_children[j]
            if nxt.type != DesignNodeType.TEXT:
                break
            if _text_style_key(nxt) != _text_style_key(current):
                break
            if current.line_height_px and nxt.y is not None and current.y is not None:
                expected_y = current.y + current.line_height_px * len(group)
                if abs(nxt.y - expected_y) > _POS_TOLERANCE:
                    break
            group.append(nxt)
            j += 1

        if len(group) > 1:
            combined_text = "\n".join(g.text_content for g in group if g.text_content)
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
