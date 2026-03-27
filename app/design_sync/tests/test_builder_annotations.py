"""Tests for Phase 33.9 — builder annotations (data-section-id, data-slot-name, data-component-name)."""

from __future__ import annotations

from app.design_sync.converter import _next_slot_name, node_to_email_html
from app.design_sync.converter_service import DesignConverterService
from app.design_sync.figma.layout_analyzer import TextBlock
from app.design_sync.protocol import (
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    ExtractedTokens,
)


class TestNextSlotName:
    """Tests for _next_slot_name() dedup helper."""

    def test_first_call_returns_bare_name(self) -> None:
        counter: dict[str, int] = {}
        assert _next_slot_name(counter, "heading") == "heading"

    def test_second_call_returns_suffixed(self) -> None:
        counter: dict[str, int] = {}
        _next_slot_name(counter, "heading")
        assert _next_slot_name(counter, "heading") == "heading_2"

    def test_third_call_increments(self) -> None:
        counter: dict[str, int] = {}
        _next_slot_name(counter, "body")
        _next_slot_name(counter, "body")
        assert _next_slot_name(counter, "body") == "body_3"

    def test_different_types_independent(self) -> None:
        counter: dict[str, int] = {}
        assert _next_slot_name(counter, "heading") == "heading"
        assert _next_slot_name(counter, "body") == "body"
        assert _next_slot_name(counter, "heading") == "heading_2"


class TestTextAnnotations:
    """Tests for data-slot-name on text elements."""

    def test_heading_gets_slot_name(self) -> None:
        node = DesignNode(
            id="txt1",
            name="Title",
            type=DesignNodeType.TEXT,
            text_content="Welcome",
            font_size=32.0,
        )
        counter: dict[str, int] = {}
        text_meta = {"txt1": TextBlock(node_id="txt1", content="Welcome", is_heading=True)}
        result = node_to_email_html(
            node,
            slot_counter=counter,
            text_meta=text_meta,
            body_font_size=16.0,
        )
        assert 'data-slot-name="heading"' in result
        assert "<h1" in result

    def test_body_text_gets_slot_name(self) -> None:
        node = DesignNode(
            id="txt2",
            name="Body",
            type=DesignNodeType.TEXT,
            text_content="Hello world",
        )
        counter: dict[str, int] = {}
        result = node_to_email_html(node, slot_counter=counter)
        assert 'data-slot-name="body"' in result
        assert "<p" in result

    def test_multiline_text_sequential_slots(self) -> None:
        node = DesignNode(
            id="txt3",
            name="Multi",
            type=DesignNodeType.TEXT,
            text_content="Line one\nLine two\nLine three",
        )
        counter: dict[str, int] = {}
        result = node_to_email_html(node, slot_counter=counter)
        assert 'data-slot-name="body"' in result
        assert 'data-slot-name="body_2"' in result
        assert 'data-slot-name="body_3"' in result


class TestImageAnnotations:
    """Tests for data-slot-name on image elements."""

    def test_image_gets_slot_name(self) -> None:
        node = DesignNode(
            id="img1",
            name="Hero Image",
            type=DesignNodeType.IMAGE,
            width=600,
            height=400,
        )
        counter: dict[str, int] = {}
        result = node_to_email_html(node, slot_counter=counter)
        assert 'data-slot-name="image"' in result
        assert 'data-node-id="img1"' in result


class TestButtonAnnotations:
    """Tests for data-slot-name on button elements."""

    def test_button_gets_slot_name(self) -> None:
        node = DesignNode(
            id="btn1",
            name="CTA Button",
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
        counter: dict[str, int] = {}
        result = node_to_email_html(node, button_ids={"btn1"}, slot_counter=counter)
        assert 'data-slot-name="cta"' in result
        assert '<a href="#"' in result


class TestSectionAnnotations:
    """Tests for data-section-id and data-component-name."""

    def test_section_wrapper_has_section_id(self) -> None:
        frame = DesignNode(
            id="frame1",
            name="Hero Section",
            type=DesignNodeType.FRAME,
            width=600,
            height=400,
            children=[
                DesignNode(
                    id="txt1", name="Title", type=DesignNodeType.TEXT, text_content="Hi", y=0
                ),
            ],
        )
        page = DesignNode(id="page1", name="Page", type=DesignNodeType.PAGE, children=[frame])
        structure = DesignFileStructure(file_name="test.fig", pages=[page])
        tokens = ExtractedTokens()
        result = DesignConverterService().convert(structure, tokens, use_components=False)
        assert 'data-section-id="section_0"' in result.html

    def test_section_root_has_component_name(self) -> None:
        frame = DesignNode(
            id="frame1",
            name="Hero Section",
            type=DesignNodeType.FRAME,
            width=600,
            height=400,
            children=[
                DesignNode(
                    id="txt1", name="Title", type=DesignNodeType.TEXT, text_content="Hi", y=0
                ),
            ],
        )
        page = DesignNode(id="page1", name="Page", type=DesignNodeType.PAGE, children=[frame])
        structure = DesignFileStructure(file_name="test.fig", pages=[page])
        tokens = ExtractedTokens()
        result = DesignConverterService().convert(structure, tokens, use_components=False)
        assert 'data-component-name="Hero Section"' in result.html

    def test_component_name_html_escaped(self) -> None:
        frame = DesignNode(
            id="frame1",
            name='Section <"Hero"> & More',
            type=DesignNodeType.FRAME,
            width=600,
            height=400,
            children=[
                DesignNode(
                    id="txt1", name="Title", type=DesignNodeType.TEXT, text_content="Hi", y=0
                ),
            ],
        )
        page = DesignNode(id="page1", name="Page", type=DesignNodeType.PAGE, children=[frame])
        structure = DesignFileStructure(file_name="test.fig", pages=[page])
        tokens = ExtractedTokens()
        result = DesignConverterService().convert(structure, tokens, use_components=False)
        assert 'data-component-name="Section &lt;&quot;Hero&quot;&gt; &amp; More"' in result.html

    def test_slot_counter_resets_per_section(self) -> None:
        frame0 = DesignNode(
            id="frame0",
            name="Section 0",
            type=DesignNodeType.FRAME,
            width=600,
            height=200,
            children=[
                DesignNode(
                    id="txt0", name="T0", type=DesignNodeType.TEXT, text_content="Hello", y=0
                ),
            ],
        )
        frame1 = DesignNode(
            id="frame1",
            name="Section 1",
            type=DesignNodeType.FRAME,
            width=600,
            height=200,
            children=[
                DesignNode(
                    id="txt1", name="T1", type=DesignNodeType.TEXT, text_content="World", y=0
                ),
            ],
        )
        page = DesignNode(
            id="page1", name="Page", type=DesignNodeType.PAGE, children=[frame0, frame1]
        )
        structure = DesignFileStructure(file_name="test.fig", pages=[page])
        tokens = ExtractedTokens()
        result = DesignConverterService().convert(structure, tokens, use_components=False)
        # Both sections should have "body" (not "body_2" in second section)
        assert 'data-section-id="section_0"' in result.html
        assert 'data-section-id="section_1"' in result.html
        # Count occurrences of data-slot-name="body" — should be 2 (one per section)
        assert result.html.count('data-slot-name="body"') == 2


class TestBackwardCompatibility:
    """Tests that no annotations are emitted when slot_counter is None."""

    def test_no_annotations_when_counter_none(self) -> None:
        node = DesignNode(
            id="txt1",
            name="Title",
            type=DesignNodeType.TEXT,
            text_content="Hello",
        )
        result = node_to_email_html(node)
        assert "data-slot-name" not in result

    def test_no_component_name_when_counter_none(self) -> None:
        node = DesignNode(
            id="frame1",
            name="Hero",
            type=DesignNodeType.FRAME,
            width=600,
            height=400,
            children=[
                DesignNode(id="txt1", name="T", type=DesignNodeType.TEXT, text_content="Hi", y=0),
            ],
        )
        result = node_to_email_html(node)
        assert "data-component-name" not in result
