"""Tests for the Figma node tree normalizer."""

from __future__ import annotations

from typing import Any

from app.design_sync.figma.tree_normalizer import normalize_tree
from app.design_sync.protocol import DesignFileStructure, DesignNode, DesignNodeType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node(
    name: str,
    *,
    type_: DesignNodeType = DesignNodeType.FRAME,
    children: list[DesignNode] | None = None,
    **kw: Any,
) -> DesignNode:
    return DesignNode(id=name, name=name, type=type_, children=children or [], **kw)


def _text(name: str, content: str, **kw: Any) -> DesignNode:
    return DesignNode(id=name, name=name, type=DesignNodeType.TEXT, text_content=content, **kw)


def _struct(*frames: DesignNode) -> DesignFileStructure:
    page = DesignNode(id="p1", name="Page", type=DesignNodeType.PAGE, children=list(frames))
    return DesignFileStructure(file_name="test", pages=[page])


# ---------------------------------------------------------------------------
# Transform 1 — Remove invisible nodes
# ---------------------------------------------------------------------------


class TestRemoveInvisible:
    def test_drops_hidden_node(self) -> None:
        structure = _struct(
            _node("visible_frame", children=[_text("t1", "Hello")]),
            _node("hidden_frame", visible=False, children=[_text("t2", "Gone")]),
        )
        result, stats = normalize_tree(structure)
        page = result.pages[0]
        assert len(page.children) == 1
        assert page.children[0].name == "visible_frame"
        assert stats.nodes_removed == 1

    def test_drops_zero_opacity_node(self) -> None:
        structure = _struct(
            _node(
                "frame",
                children=[
                    _text("visible_text", "Keep me"),
                    _text("invisible_text", "Drop me", opacity=0.0),
                ],
            ),
        )
        result, stats = normalize_tree(structure)
        frame = result.pages[0].children[0]
        assert len(frame.children) == 1
        assert frame.children[0].name == "visible_text"
        assert stats.nodes_removed == 1

    def test_drops_deep_hidden_grandchild(self) -> None:
        """Hidden grandchild removed even when direct child is visible."""
        structure = _struct(
            _node(
                "outer",
                children=[
                    _text("keep", "Visible"),
                    _node("inner", children=[_text("gone", "Hidden", visible=False)]),
                ],
            ),
        )
        result, stats = normalize_tree(structure)
        outer = result.pages[0].children[0]
        inner = outer.children[1]
        assert len(inner.children) == 0
        assert stats.nodes_removed == 1

    def test_preserves_visible_nodes(self) -> None:
        structure = _struct(
            _node("f1", children=[_text("t1", "Hello")]),
            _node("f2", children=[_text("t2", "World")]),
        )
        result, stats = normalize_tree(structure)
        assert len(result.pages[0].children) == 2
        assert stats.nodes_removed == 0


# ---------------------------------------------------------------------------
# Transform 2 — Flatten redundant groups
# ---------------------------------------------------------------------------


class TestFlattenGroups:
    def test_flatten_trivial_group(self) -> None:
        inner = _node("inner_frame", children=[_text("t1", "Content")])
        group = _node("wrapper", type_=DesignNodeType.GROUP, children=[inner])
        structure = _struct(group)
        result, stats = normalize_tree(structure)
        page = result.pages[0]
        assert len(page.children) == 1
        assert page.children[0].name == "inner_frame"
        assert page.children[0].type == DesignNodeType.FRAME
        assert stats.groups_flattened == 1

    def test_inherits_position(self) -> None:
        inner = _node("inner", x=None, y=None)
        group = _node("wrapper", type_=DesignNodeType.GROUP, children=[inner], x=100.0, y=200.0)
        structure = _struct(group)
        result, _ = normalize_tree(structure)
        promoted = result.pages[0].children[0]
        assert promoted.x == 100.0
        assert promoted.y == 200.0

    def test_keep_group_with_fill(self) -> None:
        inner = _node("inner")
        group = _node(
            "styled_group",
            type_=DesignNodeType.GROUP,
            children=[inner],
            fill_color="#FF0000",
        )
        structure = _struct(group)
        result, stats = normalize_tree(structure)
        assert result.pages[0].children[0].type == DesignNodeType.GROUP
        assert stats.groups_flattened == 0

    def test_keep_group_with_multiple_children(self) -> None:
        group = _node(
            "multi_group",
            type_=DesignNodeType.GROUP,
            children=[_node("a"), _node("b")],
        )
        structure = _struct(group)
        result, stats = normalize_tree(structure)
        assert result.pages[0].children[0].type == DesignNodeType.GROUP
        assert len(result.pages[0].children[0].children) == 2
        assert stats.groups_flattened == 0


# ---------------------------------------------------------------------------
# Transform 3 — Resolve component instances
# ---------------------------------------------------------------------------


class TestResolveInstances:
    def test_instance_becomes_frame(self) -> None:
        instance = _node(
            "my_instance",
            type_=DesignNodeType.INSTANCE,
            children=[_text("t1", "Hello")],
        )
        structure = _struct(instance)
        raw = {"document": {"type": "DOCUMENT", "children": []}}
        result, stats = normalize_tree(structure, raw_file_data=raw)
        resolved = result.pages[0].children[0]
        assert resolved.type == DesignNodeType.FRAME
        assert resolved.children[0].text_content == "Hello"
        assert stats.instances_resolved == 1

    def test_instance_resolved_only_with_raw_data(self) -> None:
        """Without raw_file_data, INSTANCE stays as INSTANCE."""
        instance = _node("inst", type_=DesignNodeType.INSTANCE)
        structure = _struct(instance)
        result, stats = normalize_tree(structure)
        assert result.pages[0].children[0].type == DesignNodeType.INSTANCE
        assert stats.instances_resolved == 0

    def test_instance_resolved_with_raw_data(self) -> None:
        instance = _node("inst", type_=DesignNodeType.INSTANCE)
        structure = _struct(instance)
        raw = {"document": {"type": "DOCUMENT", "children": []}}
        result, stats = normalize_tree(structure, raw_file_data=raw)
        assert result.pages[0].children[0].type == DesignNodeType.FRAME
        assert stats.instances_resolved == 1


# ---------------------------------------------------------------------------
# Transform 4 — Infer auto-layout from positioning
# ---------------------------------------------------------------------------


class TestInferAutoLayout:
    def test_infer_vertical_layout(self) -> None:
        frame = _node(
            "container",
            children=[
                _node("child1", x=0.0, y=0.0, width=200.0, height=80.0),
                _node("child2", x=0.0, y=100.0, width=200.0, height=80.0),
                _node("child3", x=0.0, y=200.0, width=200.0, height=80.0),
            ],
        )
        structure = _struct(frame)
        result, stats = normalize_tree(structure)
        container = result.pages[0].children[0]
        assert container.layout_mode == "VERTICAL"
        assert container.item_spacing == 100.0
        assert stats.layouts_inferred == 1

    def test_infer_horizontal_layout(self) -> None:
        frame = _node(
            "row",
            children=[
                _node("col1", x=0.0, y=0.0, width=180.0, height=100.0),
                _node("col2", x=200.0, y=0.0, width=180.0, height=100.0),
                _node("col3", x=400.0, y=0.0, width=180.0, height=100.0),
            ],
        )
        structure = _struct(frame)
        result, stats = normalize_tree(structure)
        row = result.pages[0].children[0]
        assert row.layout_mode == "HORIZONTAL"
        assert row.item_spacing == 200.0
        assert stats.layouts_inferred == 1

    def test_no_infer_when_layout_exists(self) -> None:
        frame = _node(
            "has_layout",
            layout_mode="VERTICAL",
            item_spacing=16.0,
            children=[
                _node("a", x=0.0, y=0.0),
                _node("b", x=0.0, y=100.0),
            ],
        )
        structure = _struct(frame)
        result, stats = normalize_tree(structure)
        assert result.pages[0].children[0].layout_mode == "VERTICAL"
        assert result.pages[0].children[0].item_spacing == 16.0
        assert stats.layouts_inferred == 0

    def test_no_infer_ambiguous_positions(self) -> None:
        frame = _node(
            "scattered",
            children=[
                _node("a", x=0.0, y=0.0),
                _node("b", x=100.0, y=100.0),
                _node("c", x=200.0, y=50.0),
            ],
        )
        structure = _struct(frame)
        result, stats = normalize_tree(structure)
        assert result.pages[0].children[0].layout_mode is None
        assert stats.layouts_inferred == 0

    def test_no_infer_single_child(self) -> None:
        frame = _node("single", children=[_node("only", x=0.0, y=0.0)])
        structure = _struct(frame)
        result, stats = normalize_tree(structure)
        assert result.pages[0].children[0].layout_mode is None
        assert stats.layouts_inferred == 0


# ---------------------------------------------------------------------------
# Transform 5 — Merge contiguous text nodes
# ---------------------------------------------------------------------------


class TestMergeContiguousText:
    def test_merge_same_style_text(self) -> None:
        frame = _node(
            "container",
            children=[
                _text("t1", "Line 1", font_family="Inter", font_size=16.0, font_weight=400),
                _text("t2", "Line 2", font_family="Inter", font_size=16.0, font_weight=400),
            ],
        )
        structure = _struct(frame)
        result, stats = normalize_tree(structure)
        container = result.pages[0].children[0]
        assert len(container.children) == 1
        assert container.children[0].text_content == "Line 1\nLine 2"
        assert stats.texts_merged == 1

    def test_no_merge_different_style(self) -> None:
        frame = _node(
            "container",
            children=[
                _text("t1", "Heading", font_size=32.0),
                _text("t2", "Body text", font_size=16.0),
            ],
        )
        structure = _struct(frame)
        result, stats = normalize_tree(structure)
        container = result.pages[0].children[0]
        assert len(container.children) == 2
        assert stats.texts_merged == 0

    def test_no_merge_non_adjacent(self) -> None:
        frame = _node(
            "container",
            children=[
                _text("t1", "Before", font_size=16.0),
                _node("img", type_=DesignNodeType.IMAGE, width=100.0, height=100.0),
                _text("t2", "After", font_size=16.0),
            ],
        )
        structure = _struct(frame)
        result, stats = normalize_tree(structure)
        container = result.pages[0].children[0]
        assert len(container.children) == 3
        assert stats.texts_merged == 0


# ---------------------------------------------------------------------------
# Integration / edge cases
# ---------------------------------------------------------------------------


class TestNormalizeIntegration:
    def test_full_pipeline_stats(self) -> None:
        """Structure with a mix of issues produces correct aggregate stats."""
        structure = _struct(
            _node("hidden", visible=False, children=[_text("t", "gone")]),
            _node(
                "group_wrapper",
                type_=DesignNodeType.GROUP,
                children=[_node("inner", children=[_text("t1", "kept")])],
            ),
            _node(
                "vertical_stack",
                children=[
                    _text("line1", "A", font_size=14.0, x=0.0, y=0.0),
                    _text("line2", "B", font_size=14.0, x=0.0, y=20.0),
                ],
            ),
        )
        raw = {"document": {"type": "DOCUMENT", "children": []}}
        result, stats = normalize_tree(structure, raw_file_data=raw)
        assert stats.nodes_removed == 1
        assert stats.groups_flattened == 1
        assert stats.layouts_inferred == 1  # vertical_stack inferred before text merge
        assert stats.texts_merged == 1
        assert len(result.pages[0].children) == 2

    def test_preserves_auto_layout_frames(self) -> None:
        frame = _node(
            "auto_layout",
            layout_mode="HORIZONTAL",
            item_spacing=24.0,
            padding_top=16.0,
            children=[
                _node("col1", x=0.0, y=0.0, width=280.0),
                _node("col2", x=300.0, y=0.0, width=280.0),
            ],
        )
        structure = _struct(frame)
        result, stats = normalize_tree(structure)
        out = result.pages[0].children[0]
        assert out.layout_mode == "HORIZONTAL"
        assert out.item_spacing == 24.0
        assert out.padding_top == 16.0
        assert stats.layouts_inferred == 0

    def test_empty_structure(self) -> None:
        structure = DesignFileStructure(file_name="empty", pages=[])
        result, stats = normalize_tree(structure)
        assert result.pages == []
        assert stats.nodes_removed == 0
        assert stats.groups_flattened == 0
        assert stats.instances_resolved == 0
        assert stats.layouts_inferred == 0
        assert stats.texts_merged == 0
