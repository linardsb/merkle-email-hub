# pyright: reportPrivateUsage=false
"""Tests for multi-column layout: width calculation, MSO ghost tables, row grouping (Phase 33.11 — Step 6)."""

from __future__ import annotations

from app.design_sync.converter import (
    _calculate_column_widths,
    _group_into_rows,
    node_to_email_html,
)
from app.design_sync.protocol import DesignNode, DesignNodeType


class TestColumnWidths:
    """Tests for _calculate_column_widths() proportional distribution."""

    def test_proportional_widths(self) -> None:
        """200px + 400px in 600px → proportional split."""
        children = [
            DesignNode(id="c1", name="A", type=DesignNodeType.FRAME, width=200, height=100),
            DesignNode(id="c2", name="B", type=DesignNodeType.FRAME, width=400, height=100),
        ]
        widths = _calculate_column_widths(children, 600)
        assert widths[0] == 200
        assert widths[1] == 400

    def test_equal_widths(self) -> None:
        """3 children with no widths → equal distribution."""
        children = [
            DesignNode(id=f"c{i}", name=f"C{i}", type=DesignNodeType.FRAME) for i in range(3)
        ]
        widths = _calculate_column_widths(children, 600)
        assert len(widths) == 3
        assert sum(widths) == 600
        # All should be approximately equal (200px each)
        for w in widths:
            assert abs(w - 200) <= 1

    def test_gap_subtracted(self) -> None:
        """Gap between columns reduces available width."""
        children = [
            DesignNode(id="c1", name="A", type=DesignNodeType.FRAME, width=200, height=100),
            DesignNode(id="c2", name="B", type=DesignNodeType.FRAME, width=200, height=100),
        ]
        widths = _calculate_column_widths(children, 600, gap=20)
        # Available = 600 - 20 = 580, proportional 50/50
        assert sum(widths) == 580

    def test_single_child(self) -> None:
        """Single child → full container width."""
        children = [
            DesignNode(id="c1", name="A", type=DesignNodeType.FRAME, width=300, height=100),
        ]
        widths = _calculate_column_widths(children, 600)
        assert widths == [600]

    def test_empty_children(self) -> None:
        """No children → empty list."""
        assert _calculate_column_widths([], 600) == []

    def test_last_column_absorbs_rounding(self) -> None:
        """3 equal in 601px → last absorbs rounding error."""
        children = [
            DesignNode(id=f"c{i}", name=f"C{i}", type=DesignNodeType.FRAME) for i in range(3)
        ]
        widths = _calculate_column_widths(children, 601)
        assert sum(widths) == 601


class TestMSOGhostTable:
    """Tests for MSO ghost table wrappers in multi-column output."""

    def test_mso_ghost_table_present(self) -> None:
        """Multi-column row emits MSO ghost table."""
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
        assert "display:inline-block" in html
        assert 'class="column"' in html

    def test_mso_spacer_td_for_gap(self) -> None:
        """Gap between columns → MSO spacer <td>."""
        parent = DesignNode(
            id="frame1",
            name="Row",
            type=DesignNodeType.FRAME,
            width=600,
            height=200,
            layout_mode="HORIZONTAL",
            item_spacing=20,
            children=[
                DesignNode(
                    id="c1", name="A", type=DesignNodeType.FRAME, width=280, height=200, y=0
                ),
                DesignNode(
                    id="c2", name="B", type=DesignNodeType.FRAME, width=280, height=200, y=0
                ),
            ],
        )
        html = node_to_email_html(parent)
        assert 'width="20"' in html  # MSO spacer td


class TestRowGrouping:
    """Tests for _group_into_rows() y-position grouping."""

    def test_vertical_stacked(self) -> None:
        """VERTICAL layout_mode → each child in own row (handled by node_to_email_html)."""
        parent = DesignNode(
            id="frame1",
            name="Stack",
            type=DesignNodeType.FRAME,
            width=600,
            height=400,
            layout_mode="VERTICAL",
            children=[
                DesignNode(id="c1", name="A", type=DesignNodeType.FRAME, width=600, height=100),
                DesignNode(id="c2", name="B", type=DesignNodeType.FRAME, width=600, height=100),
            ],
        )
        html = node_to_email_html(parent)
        # Each child gets its own <tr> (no multi-column)
        assert html.count("<tr>") >= 2

    def test_no_layout_fallback_to_y_position(self) -> None:
        """No layout_mode → _group_into_rows() by y-position."""
        nodes = [
            DesignNode(
                id="a", name="A", type=DesignNodeType.FRAME, width=200, height=100, x=0, y=0
            ),
            DesignNode(
                id="b", name="B", type=DesignNodeType.FRAME, width=200, height=100, x=200, y=0
            ),
            DesignNode(
                id="c", name="C", type=DesignNodeType.FRAME, width=600, height=100, x=0, y=150
            ),
        ]
        rows = _group_into_rows(nodes)
        assert len(rows) == 2
        assert len(rows[0]) == 2  # A and B on same row
        assert len(rows[1]) == 1  # C alone

    def test_y_none_single_row(self) -> None:
        """All y=None → single horizontal row."""
        nodes = [
            DesignNode(id="a", name="A", type=DesignNodeType.FRAME, width=200, height=100),
            DesignNode(id="b", name="B", type=DesignNodeType.FRAME, width=200, height=100),
        ]
        rows = _group_into_rows(nodes)
        assert len(rows) == 1
        assert len(rows[0]) == 2

    def test_tolerance_15px_same_row(self) -> None:
        """15px y-offset (< 20px tolerance) → same row."""
        nodes = [
            DesignNode(id="a", name="A", type=DesignNodeType.FRAME, width=200, height=100, y=0),
            DesignNode(id="b", name="B", type=DesignNodeType.FRAME, width=200, height=100, y=15),
        ]
        rows = _group_into_rows(nodes)
        assert len(rows) == 1
        assert len(rows[0]) == 2

    def test_25px_offset_different_row(self) -> None:
        """25px y-offset (> 20px tolerance) → different rows."""
        nodes = [
            DesignNode(id="a", name="A", type=DesignNodeType.FRAME, width=200, height=100, y=0),
            DesignNode(id="b", name="B", type=DesignNodeType.FRAME, width=200, height=100, y=25),
        ]
        rows = _group_into_rows(nodes)
        assert len(rows) == 2

    def test_empty_nodes(self) -> None:
        """Empty input → empty output."""
        assert _group_into_rows([]) == []
