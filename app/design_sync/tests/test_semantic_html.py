# pyright: reportPrivateUsage=false
"""Tests for semantic HTML generation: headings, paragraphs, buttons (Phase 33.11 — Step 7)."""

from __future__ import annotations

from app.design_sync.converter import (
    _determine_heading_level,
    node_to_email_html,
)
from app.design_sync.figma.layout_analyzer import TextBlock
from app.design_sync.protocol import DesignNode, DesignNodeType


class TestHeadingDetection:
    """Tests for _determine_heading_level() font size ratio detection."""

    def test_h1_from_32px(self) -> None:
        """32px / 16px = 2.0 → h1."""
        assert _determine_heading_level(32.0, 16.0) == 1

    def test_h2_from_24px(self) -> None:
        """24px / 16px = 1.5 → h2."""
        assert _determine_heading_level(24.0, 16.0) == 2

    def test_h3_from_20px(self) -> None:
        """20px / 16px = 1.25 → h3."""
        assert _determine_heading_level(20.0, 16.0) == 3

    def test_body_from_16px(self) -> None:
        """16px / 16px = 1.0 → None (body text)."""
        assert _determine_heading_level(16.0, 16.0) is None

    def test_zero_body_returns_none(self) -> None:
        """body_font_size=0 → None (guard)."""
        assert _determine_heading_level(32.0, 0.0) is None

    def test_exact_boundary_h1(self) -> None:
        """Exactly 2.0 ratio → h1 (inclusive)."""
        assert _determine_heading_level(32.0, 16.0) == 1

    def test_just_below_h2(self) -> None:
        """Ratio 1.49 → h3 (below 1.5 threshold)."""
        assert _determine_heading_level(23.84, 16.0) == 3


class TestTextRendering:
    """Tests for text node → semantic HTML rendering."""

    def test_heading_renders_in_td(self) -> None:
        """TEXT node 32px with is_heading → text directly in <td> (no h1 wrapper)."""
        node = DesignNode(
            id="txt1",
            name="Title",
            type=DesignNodeType.TEXT,
            text_content="Welcome",
            font_size=32.0,
        )
        text_meta = {"txt1": TextBlock(node_id="txt1", content="Welcome", is_heading=True)}
        result = node_to_email_html(node, text_meta=text_meta, body_font_size=16.0)
        assert "<h1" not in result
        assert "<td" in result
        assert "Welcome" in result
        assert "mso-line-height-rule:exactly" in result

    def test_body_renders_in_td(self) -> None:
        """TEXT node 16px (body) → text directly in <td> with padding."""
        node = DesignNode(
            id="txt2",
            name="Body",
            type=DesignNodeType.TEXT,
            text_content="Hello world",
        )
        result = node_to_email_html(node, body_font_size=16.0)
        assert "<p" not in result
        assert "<td" in result
        assert "padding:0 0 10px 0" in result
        assert "mso-line-height-rule:exactly" in result

    def test_multiline_text_multiple_td_rows(self) -> None:
        """TEXT with \\n → multiple <td> elements joined by </tr><tr>."""
        node = DesignNode(
            id="txt3",
            name="Multi",
            type=DesignNodeType.TEXT,
            text_content="Line one\nLine two\nLine three",
        )
        result = node_to_email_html(node)
        assert "<p" not in result
        assert result.count("<td") >= 3
        assert "</tr><tr>" in result

    def test_inline_styles_present(self) -> None:
        """Semantic elements have font-family in inline styles."""
        node = DesignNode(
            id="txt1",
            name="Title",
            type=DesignNodeType.TEXT,
            text_content="Hello",
        )
        result = node_to_email_html(node)
        assert "font-family:" in result

    def test_empty_text_renders_empty_escaped(self) -> None:
        """Empty text content → renders with empty string."""
        node = DesignNode(
            id="txt1",
            name="Empty",
            type=DesignNodeType.TEXT,
            text_content="",
        )
        result = node_to_email_html(node)
        assert "<td" in result

    def test_html_characters_escaped(self) -> None:
        """HTML special characters in text → escaped."""
        node = DesignNode(
            id="txt1",
            name="Special",
            type=DesignNodeType.TEXT,
            text_content="<script>alert('xss')</script>",
        )
        result = node_to_email_html(node)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestButtonRendering:
    """Tests for button rendering with VML fallback."""

    def test_button_has_vml_roundrect(self) -> None:
        """Button component → <a> + <v:roundrect> VML fallback."""
        node = DesignNode(
            id="btn1",
            name="CTA",
            type=DesignNodeType.COMPONENT,
            width=200,
            height=48,
            fill_color="#0066cc",
            children=[
                DesignNode(
                    id="btn1_text",
                    name="Label",
                    type=DesignNodeType.TEXT,
                    text_content="Shop Now",
                    text_color="#ffffff",
                    font_size=16.0,
                    y=0,
                ),
            ],
        )
        result = node_to_email_html(node, button_ids={"btn1"})
        assert '<a href="#"' in result
        assert "v:roundrect" in result
        assert "Shop Now" in result
        assert "#0066cc" in result.lower() or "0066cc" in result.lower()

    def test_button_min_height_44(self) -> None:
        """Button with small height → enforced to 44px minimum."""
        node = DesignNode(
            id="btn1",
            name="Tiny",
            type=DesignNodeType.COMPONENT,
            width=200,
            height=30,
            children=[
                DesignNode(id="t", name="T", type=DesignNodeType.TEXT, text_content="Click", y=0),
            ],
        )
        result = node_to_email_html(node, button_ids={"btn1"})
        assert "height:44px" in result

    def test_button_no_text_children_empty(self) -> None:
        """Button with no text children → empty string."""
        node = DesignNode(
            id="btn1",
            name="Empty",
            type=DesignNodeType.COMPONENT,
            width=200,
            height=48,
            children=[],
        )
        result = node_to_email_html(node, button_ids={"btn1"})
        assert result == ""
