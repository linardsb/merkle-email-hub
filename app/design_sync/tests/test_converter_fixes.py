# pyright: reportPrivateUsage=false
"""Tests for converter fixes B1-B4 (recursive converter improvements)."""

from __future__ import annotations

from app.design_sync.converter import (
    _calculate_column_widths,
    _has_visible_content,
    _is_inline_row,
    node_to_email_html,
)
from app.design_sync.protocol import DesignNode, DesignNodeType

# ---------------------------------------------------------------------------
# B3: _has_visible_content — empty subtree pruning
# ---------------------------------------------------------------------------


class TestHasVisibleContent:
    def test_text_node_is_visible(self) -> None:
        node = DesignNode(id="t1", name="T", type=DesignNodeType.TEXT, text_content="Hi")
        assert _has_visible_content(node) is True

    def test_image_node_is_visible(self) -> None:
        node = DesignNode(id="i1", name="I", type=DesignNodeType.IMAGE, width=100, height=50)
        assert _has_visible_content(node) is True

    def test_empty_frame_is_not_visible(self) -> None:
        node = DesignNode(id="f1", name="F", type=DesignNodeType.FRAME, children=[])
        assert _has_visible_content(node) is False

    def test_frame_with_no_children_attr(self) -> None:
        node = DesignNode(id="f1", name="F", type=DesignNodeType.FRAME)
        assert _has_visible_content(node) is False

    def test_nested_text_is_visible(self) -> None:
        inner = DesignNode(id="t1", name="T", type=DesignNodeType.TEXT, text_content="X")
        outer = DesignNode(id="f1", name="F", type=DesignNodeType.FRAME, children=[inner])
        assert _has_visible_content(outer) is True

    def test_deeply_nested_image_is_visible(self) -> None:
        img = DesignNode(id="i1", name="I", type=DesignNodeType.IMAGE, width=10, height=10)
        mid = DesignNode(id="f2", name="F2", type=DesignNodeType.GROUP, children=[img])
        outer = DesignNode(id="f1", name="F1", type=DesignNodeType.FRAME, children=[mid])
        assert _has_visible_content(outer) is True

    def test_nested_empty_frames_not_visible(self) -> None:
        inner = DesignNode(id="f2", name="F2", type=DesignNodeType.FRAME, children=[])
        outer = DesignNode(id="f1", name="F1", type=DesignNodeType.FRAME, children=[inner])
        assert _has_visible_content(outer) is False


class TestEmptyFramePruningService:
    """B3: Empty frames are pruned at the service level (_collect_frames)."""

    def test_empty_frame_pruned_from_conversion(self) -> None:
        from app.design_sync.converter_service import DesignConverterService
        from app.design_sync.protocol import DesignFileStructure, ExtractedTokens

        structure = DesignFileStructure(
            file_name="test.fig",
            pages=[
                DesignNode(
                    id="page",
                    name="Page",
                    type=DesignNodeType.PAGE,
                    children=[
                        DesignNode(
                            id="empty",
                            name="Empty",
                            type=DesignNodeType.FRAME,
                            width=600,
                            children=[],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(
            structure, ExtractedTokens(), use_components=False
        )
        assert result.sections_count == 0
        assert "No frames found" in result.warnings

    def test_visible_frame_kept(self) -> None:
        from app.design_sync.converter_service import DesignConverterService
        from app.design_sync.protocol import DesignFileStructure, ExtractedTokens

        structure = DesignFileStructure(
            file_name="test.fig",
            pages=[
                DesignNode(
                    id="page",
                    name="Page",
                    type=DesignNodeType.PAGE,
                    children=[
                        DesignNode(
                            id="f1",
                            name="Section",
                            type=DesignNodeType.FRAME,
                            width=600,
                            children=[
                                DesignNode(
                                    id="t1",
                                    name="T",
                                    type=DesignNodeType.TEXT,
                                    text_content="Hello",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(
            structure, ExtractedTokens(), use_components=False
        )
        assert result.sections_count >= 1
        assert "Hello" in result.html


# ---------------------------------------------------------------------------
# B2: _is_inline_row — inline content heuristic
# ---------------------------------------------------------------------------


class TestIsInlineRow:
    def test_text_and_small_image(self) -> None:
        children = [
            DesignNode(id="t1", name="T", type=DesignNodeType.TEXT, text_content="Nav"),
            DesignNode(id="i1", name="Icon", type=DesignNodeType.IMAGE, width=16, height=16),
        ]
        assert _is_inline_row(children) is True

    def test_two_texts(self) -> None:
        children = [
            DesignNode(id="t1", name="A", type=DesignNodeType.TEXT, text_content="A"),
            DesignNode(id="t2", name="B", type=DesignNodeType.TEXT, text_content="B"),
        ]
        assert _is_inline_row(children) is True

    def test_large_image_not_inline(self) -> None:
        children = [
            DesignNode(id="t1", name="T", type=DesignNodeType.TEXT, text_content="Label"),
            DesignNode(id="i1", name="Big", type=DesignNodeType.IMAGE, width=200, height=100),
        ]
        assert _is_inline_row(children) is False

    def test_single_child_not_inline(self) -> None:
        children = [
            DesignNode(id="t1", name="T", type=DesignNodeType.TEXT, text_content="Solo"),
        ]
        assert _is_inline_row(children) is False

    def test_five_children_not_inline(self) -> None:
        children = [
            DesignNode(id=f"t{i}", name=f"T{i}", type=DesignNodeType.TEXT, text_content=f"T{i}")
            for i in range(5)
        ]
        assert _is_inline_row(children) is False

    def test_frames_not_inline(self) -> None:
        children = [
            DesignNode(id="f1", name="F1", type=DesignNodeType.FRAME, width=200),
            DesignNode(id="f2", name="F2", type=DesignNodeType.FRAME, width=200),
        ]
        assert _is_inline_row(children) is False

    def test_image_at_boundary_30px(self) -> None:
        children = [
            DesignNode(id="t1", name="T", type=DesignNodeType.TEXT, text_content="Nav"),
            DesignNode(id="i1", name="Icon", type=DesignNodeType.IMAGE, width=30, height=30),
        ]
        assert _is_inline_row(children) is True

    def test_image_just_over_boundary(self) -> None:
        children = [
            DesignNode(id="t1", name="T", type=DesignNodeType.TEXT, text_content="Nav"),
            DesignNode(id="i1", name="Icon", type=DesignNodeType.IMAGE, width=31, height=16),
        ]
        assert _is_inline_row(children) is False


class TestInlineRowRendering:
    """B2: Inline rows render as single <td> without ghost table overhead."""

    def test_inline_row_no_ghost_table(self) -> None:
        parent = DesignNode(
            id="nav",
            name="Nav Item",
            type=DesignNodeType.FRAME,
            width=200,
            height=30,
            layout_mode="HORIZONTAL",
            children=[
                DesignNode(
                    id="t1", name="Label", type=DesignNodeType.TEXT, text_content="Man", y=0
                ),
                DesignNode(
                    id="i1",
                    name="Arrow",
                    type=DesignNodeType.IMAGE,
                    width=16,
                    height=16,
                    y=0,
                ),
            ],
        )
        html = node_to_email_html(parent)
        # TEXT rendered as <span> with font styles (not <td><p>)
        assert "<span" in html
        assert "Man" in html
        # IMAGE rendered as inline <img> (not ghost table column)
        assert "<img" in html
        assert "Arrow" in html
        # No <p> tags — inline content uses <span> for text
        assert "<p " not in html
        # No MSO ghost table
        assert "<!--[if mso]>" not in html

    def test_inline_text_has_font_styles(self) -> None:
        parent = DesignNode(
            id="nav",
            name="Nav",
            type=DesignNodeType.FRAME,
            width=200,
            height=30,
            layout_mode="HORIZONTAL",
            children=[
                DesignNode(id="t1", name="T", type=DesignNodeType.TEXT, text_content="Click", y=0),
                DesignNode(
                    id="i1", name="Icon", type=DesignNodeType.IMAGE, width=12, height=12, y=0
                ),
            ],
        )
        html = node_to_email_html(parent)
        # Text <span> should have font-family on parent <td>
        assert "font-family:" in html
        # Structure: <td> wraps all inline children — no nested <td>
        assert html.count("<td") >= 1
        assert "<td><td" not in html.replace(" ", "").replace("\n", "")


# ---------------------------------------------------------------------------
# B4: Sparse layout detection in _calculate_column_widths
# ---------------------------------------------------------------------------


class TestSparseColumnWidths:
    def test_sparse_keeps_natural_widths(self) -> None:
        """3 x 80px buttons in 600px -> sparse (240/600=40%) -> keep natural widths."""
        children = [
            DesignNode(id=f"c{i}", name=f"C{i}", type=DesignNodeType.FRAME, width=80)
            for i in range(3)
        ]
        widths = _calculate_column_widths(children, 600)
        assert widths == [80, 80, 80]

    def test_not_sparse_redistributes(self) -> None:
        """200+400 in 600px → 100% → NOT sparse → proportional redistribution."""
        children = [
            DesignNode(id="c1", name="A", type=DesignNodeType.FRAME, width=200, height=100),
            DesignNode(id="c2", name="B", type=DesignNodeType.FRAME, width=400, height=100),
        ]
        widths = _calculate_column_widths(children, 600)
        assert widths[0] == 200
        assert widths[1] == 400

    def test_threshold_boundary_59_percent(self) -> None:
        """Total = 59% of container → sparse (< 60%)."""
        children = [
            DesignNode(id="c1", name="A", type=DesignNodeType.FRAME, width=177),
            DesignNode(id="c2", name="B", type=DesignNodeType.FRAME, width=177),
        ]
        # 354 / 600 = 59% < 60% → sparse
        widths = _calculate_column_widths(children, 600)
        assert widths == [177, 177]

    def test_threshold_boundary_61_percent(self) -> None:
        """Total = 61% of container → NOT sparse (> 60%)."""
        children = [
            DesignNode(id="c1", name="A", type=DesignNodeType.FRAME, width=183),
            DesignNode(id="c2", name="B", type=DesignNodeType.FRAME, width=183),
        ]
        # 366 / 600 = 61% > 60% → NOT sparse → proportional redistribution
        widths = _calculate_column_widths(children, 600)
        assert sum(widths) == 600

    def test_unknown_widths_not_affected(self) -> None:
        """Children with no widths → equal distribution (sparse check N/A)."""
        children = [
            DesignNode(id=f"c{i}", name=f"C{i}", type=DesignNodeType.FRAME) for i in range(3)
        ]
        widths = _calculate_column_widths(children, 600)
        assert sum(widths) == 600


# ---------------------------------------------------------------------------
# B1: Table wrapper replaces div wrapper in multi-column
# ---------------------------------------------------------------------------


class TestTableColumnWrapper:
    """B1: Multi-column uses <table class="column"> instead of <div class="column">."""

    def test_column_uses_table_not_div(self) -> None:
        parent = DesignNode(
            id="frame1",
            name="Row",
            type=DesignNodeType.FRAME,
            width=600,
            height=200,
            layout_mode="HORIZONTAL",
            children=[
                DesignNode(
                    id="c1", name="A", type=DesignNodeType.FRAME, width=300, height=200, y=0
                ),
                DesignNode(
                    id="c2", name="B", type=DesignNodeType.FRAME, width=300, height=200, y=0
                ),
            ],
        )
        html = node_to_email_html(parent)
        # B1: should use <table class="column"> not <div class="column">
        assert '<table class="column"' in html
        assert '<div class="column"' not in html

    def test_column_has_inline_block(self) -> None:
        parent = DesignNode(
            id="frame1",
            name="Row",
            type=DesignNodeType.FRAME,
            width=600,
            height=200,
            layout_mode="HORIZONTAL",
            children=[
                DesignNode(
                    id="c1", name="A", type=DesignNodeType.FRAME, width=300, height=200, y=0
                ),
                DesignNode(
                    id="c2", name="B", type=DesignNodeType.FRAME, width=300, height=200, y=0
                ),
            ],
        )
        html = node_to_email_html(parent)
        assert "display:inline-block" in html

    def test_mso_ghost_table_still_present(self) -> None:
        parent = DesignNode(
            id="frame1",
            name="Row",
            type=DesignNodeType.FRAME,
            width=600,
            height=200,
            layout_mode="HORIZONTAL",
            children=[
                DesignNode(
                    id="c1", name="A", type=DesignNodeType.FRAME, width=300, height=200, y=0
                ),
                DesignNode(
                    id="c2", name="B", type=DesignNodeType.FRAME, width=300, height=200, y=0
                ),
            ],
        )
        html = node_to_email_html(parent)
        assert "<!--[if mso]>" in html
        assert "<![endif]-->" in html

    def test_no_double_table_nesting(self) -> None:
        """B1: Single table per column (no div→table sanitizer double-wrap)."""
        parent = DesignNode(
            id="frame1",
            name="Row",
            type=DesignNodeType.FRAME,
            width=600,
            height=200,
            layout_mode="HORIZONTAL",
            children=[
                DesignNode(
                    id="c1",
                    name="A",
                    type=DesignNodeType.FRAME,
                    width=300,
                    height=200,
                    y=0,
                    children=[
                        DesignNode(
                            id="t1",
                            name="Text",
                            type=DesignNodeType.TEXT,
                            text_content="Col 1",
                        ),
                    ],
                ),
                DesignNode(
                    id="c2",
                    name="B",
                    type=DesignNodeType.FRAME,
                    width=300,
                    height=200,
                    y=0,
                    children=[
                        DesignNode(
                            id="t2",
                            name="Text",
                            type=DesignNodeType.TEXT,
                            text_content="Col 2",
                        ),
                    ],
                ),
            ],
        )
        html = node_to_email_html(parent)
        # Count tables: parent(1) + padding wrapper(1) + 2 column tables + 2 child frames = 6
        # Before B1 fix: parent(1) + padding(1) + 2 div→table + 2 inner + 2 child = 8
        table_count = html.count("<table")
        assert table_count <= 6
