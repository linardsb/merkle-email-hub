# pyright: reportPrivateUsage=false
"""Tests for spacing application and layout rendering (Phase 33.11 — Step 5)."""

from __future__ import annotations

from app.design_sync.converter import convert_spacing, node_to_email_html
from app.design_sync.protocol import DesignNode, DesignNodeType, ExtractedSpacing


class TestConvertSpacing:
    """Tests for convert_spacing() named scale mapping."""

    def test_standard_scale_values(self) -> None:
        """Values matching 4/8/16/24/32 scale → semantic names."""
        spacing = [
            ExtractedSpacing(name="s1", value=8),
            ExtractedSpacing(name="s2", value=16),
            ExtractedSpacing(name="s3", value=24),
            ExtractedSpacing(name="s4", value=32),
        ]
        result = convert_spacing(spacing)
        assert result["xs"] == 8
        assert result["md"] == 16
        assert result["lg"] == 24
        assert result["xl"] == 32

    def test_non_standard_keeps_original_name(self) -> None:
        """Non-standard value → normalized original name."""
        spacing = [ExtractedSpacing(name="spacing-custom", value=10)]
        result = convert_spacing(spacing)
        assert "custom" in result
        assert result["custom"] == 10

    def test_empty_spacing(self) -> None:
        """No spacing → empty dict."""
        assert convert_spacing([]) == {}

    def test_duplicate_scale_first_wins(self) -> None:
        """Two values mapping to same scale name → first wins."""
        spacing = [
            ExtractedSpacing(name="a", value=16),
            ExtractedSpacing(name="b", value=16),
        ]
        result = convert_spacing(spacing)
        assert result["md"] == 16
        assert len([v for v in result.values() if v == 16]) == 1


class TestVerticalSpacerRows:
    """Tests for vertical auto-layout spacer <tr> rows."""

    def test_vertical_layout_spacer_rows(self) -> None:
        """Vertical auto-layout with itemSpacing → spacer <tr> between children."""
        parent = DesignNode(
            id="frame1",
            name="Stack",
            type=DesignNodeType.FRAME,
            width=600,
            height=400,
            layout_mode="VERTICAL",
            item_spacing=12,
            children=[
                DesignNode(id="c1", name="Row 1", type=DesignNodeType.FRAME, width=600, height=100),
                DesignNode(id="c2", name="Row 2", type=DesignNodeType.FRAME, width=600, height=100),
            ],
        )
        html = node_to_email_html(parent)
        assert "height:12px" in html
        assert "font-size:1px" in html
        assert "line-height:1px" in html
        assert "mso-line-height-rule:exactly" in html

    def test_no_spacer_before_first_row(self) -> None:
        """No spacer before the first child row."""
        parent = DesignNode(
            id="frame1",
            name="Stack",
            type=DesignNodeType.FRAME,
            width=600,
            height=200,
            layout_mode="VERTICAL",
            item_spacing=20,
            children=[
                DesignNode(id="c1", name="Row 1", type=DesignNodeType.FRAME, width=600, height=100),
            ],
        )
        html = node_to_email_html(parent)
        # Single child → no spacer at all
        assert "height:20px" not in html


class TestHorizontalPadding:
    """Tests for horizontal auto-layout gap via padding-left."""

    def test_horizontal_gap_padding_left(self) -> None:
        """Horizontal auto-layout with gap → padding-left on cells 2+."""
        parent = DesignNode(
            id="frame1",
            name="Row",
            type=DesignNodeType.FRAME,
            width=600,
            height=100,
            layout_mode="HORIZONTAL",
            item_spacing=8,
            children=[
                DesignNode(
                    id="c1", name="Col 1", type=DesignNodeType.FRAME, width=200, height=100, y=0
                ),
                DesignNode(
                    id="c2", name="Col 2", type=DesignNodeType.FRAME, width=200, height=100, y=0
                ),
            ],
        )
        html = node_to_email_html(parent)
        # Multi-column row triggers _render_multi_column_row with MSO ghost table
        # The gap is rendered via MSO spacer <td>
        assert "<!--[if mso]>" in html


class TestNodePadding:
    """Tests for node padding on <td> wrapper."""

    def test_node_padding_applied(self) -> None:
        """Node with padding → padding CSS on inner <td>."""
        parent = DesignNode(
            id="frame1",
            name="Padded",
            type=DesignNodeType.FRAME,
            width=600,
            height=400,
            padding_top=24,
            padding_right=16,
            padding_bottom=24,
            padding_left=16,
            children=[
                DesignNode(
                    id="c1", name="Content", type=DesignNodeType.FRAME, width=568, height=352
                ),
            ],
        )
        html = node_to_email_html(parent)
        assert "padding:24px 16px 24px 16px" in html

    def test_no_padding_no_attribute(self) -> None:
        """Node without padding → no padding CSS."""
        parent = DesignNode(
            id="frame1",
            name="NoPad",
            type=DesignNodeType.FRAME,
            width=600,
            height=400,
            children=[
                DesignNode(
                    id="c1", name="Content", type=DesignNodeType.FRAME, width=600, height=400
                ),
            ],
        )
        html = node_to_email_html(parent)
        assert "padding:" not in html
