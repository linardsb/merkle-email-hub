"""Tests for Phase 33.4 — spacing token pipeline & auto-layout table mapping."""

from __future__ import annotations

from app.design_sync.converter import (
    convert_spacing,
    node_to_email_html,
)
from app.design_sync.protocol import (
    DesignNode,
    DesignNodeType,
    ExtractedSpacing,
)


class TestConvertSpacing:
    """Tests for convert_spacing() scale mapping."""

    def test_standard_scale_values(self) -> None:
        tokens = [
            ExtractedSpacing(name="spacing-8", value=8),
            ExtractedSpacing(name="spacing-16", value=16),
            ExtractedSpacing(name="spacing-32", value=32),
        ]
        result = convert_spacing(tokens)
        assert result == {"xs": 8, "md": 16, "xl": 32}

    def test_non_standard_keeps_original_name(self) -> None:
        tokens = [ExtractedSpacing(name="spacing-10", value=10)]
        result = convert_spacing(tokens)
        assert result == {"10": 10}

    def test_empty_input(self) -> None:
        assert convert_spacing([]) == {}

    def test_no_duplicate_overwrite(self) -> None:
        tokens = [
            ExtractedSpacing(name="xs", value=8),
            ExtractedSpacing(name="spacing-8", value=8),
        ]
        result = convert_spacing(tokens)
        # First one wins for "xs" key
        assert result["xs"] == 8


class TestPaddingOnTd:
    """Verify padding is applied to <td>, not <table>."""

    def test_node_padding_on_td(self) -> None:
        """Padding from DesignNode → style on wrapping <td>, not <table>."""
        node = DesignNode(
            id="frame1",
            name="Section",
            type=DesignNodeType.FRAME,
            padding_top=24,
            padding_left=16,
            padding_right=16,
            padding_bottom=0,
            children=[
                DesignNode(id="txt1", name="Hello", type=DesignNodeType.TEXT, text_content="Hello"),
            ],
        )
        html = node_to_email_html(node)
        # Padding must be on <td>, NOT on <table>
        assert "padding:24px 16px 0px 16px" in html
        # The <table> tag should NOT have padding
        table_start = html[: html.index(">") + 1]
        assert "padding:" not in table_start

    def test_no_padding_no_wrapper(self) -> None:
        """Frame with no padding → no padding on the outer <table> tag."""
        node = DesignNode(
            id="frame2",
            name="Section",
            type=DesignNodeType.FRAME,
            children=[
                DesignNode(id="txt1", name="Hi", type=DesignNodeType.TEXT, text_content="Hi"),
            ],
        )
        html = node_to_email_html(node)
        # The <table> tag itself should not carry padding; child <td> elements
        # may still add default text spacing (padding:0 0 10px 0).
        table_start = html[: html.index(">") + 1]
        assert "padding:" not in table_start


class TestVerticalAutoLayout:
    """Vertical layout → stacked rows with spacer <tr> between them."""

    def test_vertical_spacer_rows(self) -> None:
        children = [
            DesignNode(id=f"child{i}", name=f"C{i}", type=DesignNodeType.FRAME) for i in range(3)
        ]
        node = DesignNode(
            id="vbox",
            name="VStack",
            type=DesignNodeType.FRAME,
            layout_mode="VERTICAL",
            item_spacing=12,
            children=children,
        )
        html = node_to_email_html(node)
        # Each child should be in its own <tr>
        assert html.count("<tr>") >= 3
        # Spacer rows between children (2 spacers for 3 children)
        assert html.count("mso-line-height-rule:exactly") == 2
        assert "height:12px" in html
        assert "font-size:1px" in html
        assert "line-height:1px" in html

    def test_vertical_no_spacing(self) -> None:
        children = [
            DesignNode(id=f"child{i}", name=f"C{i}", type=DesignNodeType.FRAME) for i in range(2)
        ]
        node = DesignNode(
            id="vbox",
            name="VStack",
            type=DesignNodeType.FRAME,
            layout_mode="VERTICAL",
            children=children,
        )
        html = node_to_email_html(node)
        # No spacers
        assert "mso-line-height-rule" not in html


class TestHorizontalAutoLayout:
    """Horizontal layout → single <tr>, gap as padding-left."""

    def test_horizontal_gap_on_cells(self) -> None:
        children = [
            DesignNode(id=f"col{i}", name=f"Col{i}", type=DesignNodeType.FRAME) for i in range(3)
        ]
        node = DesignNode(
            id="hbox",
            name="HStack",
            type=DesignNodeType.FRAME,
            layout_mode="HORIZONTAL",
            item_spacing=8,
            children=children,
        )
        html = node_to_email_html(node)
        # Multi-column: gap rendered as MSO spacer <td width="8">
        assert html.count('width="8"') == 2

    def test_horizontal_first_cell_no_padding(self) -> None:
        children = [
            DesignNode(id=f"col{i}", name=f"Col{i}", type=DesignNodeType.FRAME) for i in range(2)
        ]
        node = DesignNode(
            id="hbox",
            name="HStack",
            type=DesignNodeType.FRAME,
            layout_mode="HORIZONTAL",
            item_spacing=16,
            children=children,
        )
        html = node_to_email_html(node)
        # Multi-column: only 1 MSO spacer between 2 columns
        assert html.count('width="16"') == 1


class TestFallbackGrouping:
    """No layout_mode → y-position grouping (existing behavior)."""

    def test_no_layout_mode_uses_y_grouping(self) -> None:
        children = [
            DesignNode(id="a", name="A", type=DesignNodeType.FRAME, x=0, y=0, width=100, height=50),
            DesignNode(
                id="b", name="B", type=DesignNodeType.FRAME, x=120, y=0, width=100, height=50
            ),
            DesignNode(
                id="c", name="C", type=DesignNodeType.FRAME, x=0, y=80, width=200, height=50
            ),
        ]
        node = DesignNode(
            id="container",
            name="Container",
            type=DesignNodeType.FRAME,
            children=children,
            width=300,
        )
        html = node_to_email_html(node)
        # A and B are on the same y → same <tr>
        # C is on a different y → separate <tr>
        # Should have 2 content <tr> rows
        assert html.count("<tr>") >= 2


class TestSpacingInDesignContext:
    """Spacing tokens appear in the design context for the Scaffolder."""

    def test_spacing_included(self) -> None:
        from unittest.mock import MagicMock

        from app.design_sync.import_service import DesignImportService
        from app.design_sync.schemas import (
            DesignSpacingResponse,
            DesignTokensResponse,
            LayoutAnalysisResponse,
        )

        svc = DesignImportService.__new__(DesignImportService)
        tokens = MagicMock(spec=DesignTokensResponse)
        tokens.colors = []
        tokens.typography = []
        tokens.spacing = [
            DesignSpacingResponse(name="sm", value=8),
            DesignSpacingResponse(name="md", value=16),
        ]
        tokens.dark_colors = []
        tokens.gradients = []
        tokens.warnings = None
        layout = MagicMock(spec=LayoutAnalysisResponse)
        layout.sections = []
        layout.file_name = "test.fig"

        ctx = svc._build_design_context(layout, None, tokens, MagicMock())
        # convert_spacing() maps 8→"xs", 16→"md"
        spacing = ctx["design_tokens"]["spacing"]  # type: ignore[index]
        assert spacing == {"xs": 8, "md": 16}
