"""Tests for Penpot-to-email converter."""

from __future__ import annotations

from app.design_sync.penpot.converter import (
    _group_into_rows,
    convert_colors_to_palette,
    convert_typography,
    node_to_email_html,
)
from app.design_sync.protocol import (
    DesignNode,
    DesignNodeType,
    ExtractedColor,
    ExtractedTypography,
)


class TestConvertColors:
    def test_name_based_mapping(self) -> None:
        colors = [
            ExtractedColor(name="Primary Blue", hex="#0066cc"),
            ExtractedColor(name="Background", hex="#f5f5f5"),
            ExtractedColor(name="Text Color", hex="#333333"),
        ]
        palette = convert_colors_to_palette(colors)
        assert palette.primary == "#0066cc"
        assert palette.background == "#f5f5f5"
        assert palette.text == "#333333"

    def test_fallback_positional(self) -> None:
        colors = [
            ExtractedColor(name="Blue", hex="#0000ff"),
            ExtractedColor(name="Red", hex="#ff0000"),
            ExtractedColor(name="Green", hex="#00ff00"),
        ]
        palette = convert_colors_to_palette(colors)
        assert palette.primary == "#0000ff"
        assert palette.secondary == "#ff0000"
        assert palette.accent == "#00ff00"

    def test_empty_colors(self) -> None:
        palette = convert_colors_to_palette([])
        assert palette.primary == "#333333"


class TestConvertTypography:
    def test_heading_and_body(self) -> None:
        styles = [
            ExtractedTypography(
                name="Heading 1", family="Inter", weight="700", size=32.0, line_height=1.2
            ),
            ExtractedTypography(
                name="Body Text",
                family="Roboto",
                weight="400",
                size=16.0,
                line_height=1.5,
            ),
        ]
        typo = convert_typography(styles)
        assert "Inter" in typo.heading_font
        assert "Roboto" in typo.body_font
        assert typo.base_size == "16px"

    def test_empty(self) -> None:
        typo = convert_typography([])
        assert typo.heading_font == "Arial, Helvetica, sans-serif"


class TestNodeToEmailHtml:
    def test_text_node(self) -> None:
        node = DesignNode(id="1", name="Title", type=DesignNodeType.TEXT, text_content="Hello")
        html = node_to_email_html(node)
        assert "<td" in html
        assert "Hello" in html

    def test_image_node(self) -> None:
        node = DesignNode(id="2", name="Hero", type=DesignNodeType.IMAGE, width=600, height=300)
        html = node_to_email_html(node)
        assert "<img" in html
        assert 'width="600"' in html

    def test_frame_with_children(self) -> None:
        node = DesignNode(
            id="3",
            name="Section",
            type=DesignNodeType.FRAME,
            width=600,
            children=[
                DesignNode(
                    id="4",
                    name="Text",
                    type=DesignNodeType.TEXT,
                    text_content="Hi",
                    y=0,
                ),
                DesignNode(
                    id="5",
                    name="Img",
                    type=DesignNodeType.IMAGE,
                    width=200,
                    height=100,
                    y=50,
                ),
            ],
        )
        html = node_to_email_html(node)
        assert "<table" in html
        assert "<tr>" in html


class TestGroupIntoRows:
    def test_single_row(self) -> None:
        nodes = [
            DesignNode(id="1", name="A", type=DesignNodeType.TEXT, x=0, y=0),
            DesignNode(id="2", name="B", type=DesignNodeType.TEXT, x=200, y=5),
        ]
        rows = _group_into_rows(nodes)
        assert len(rows) == 1
        assert len(rows[0]) == 2

    def test_two_rows(self) -> None:
        nodes = [
            DesignNode(id="1", name="A", type=DesignNodeType.TEXT, x=0, y=0),
            DesignNode(id="2", name="B", type=DesignNodeType.TEXT, x=0, y=100),
        ]
        rows = _group_into_rows(nodes)
        assert len(rows) == 2
