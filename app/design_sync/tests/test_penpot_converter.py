"""Tests for design-to-email converter."""

from __future__ import annotations

from app.design_sync.converter import (
    _group_into_rows,
    _NodeProps,
    _sanitize_css_value,
    convert_colors_to_palette,
    convert_typography,
    node_to_email_html,
    sanitize_web_tags_for_email,
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

    def test_dark_bg_dark_text_contrast_fix(self) -> None:
        """Dark background with dark text should auto-correct to white text."""
        colors = [
            ExtractedColor(name="Background", hex="#1a1a2e"),
            ExtractedColor(name="Text Color", hex="#000000"),
        ]
        palette = convert_colors_to_palette(colors)
        assert palette.background == "#1a1a2e"
        assert palette.text == "#ffffff"  # contrast-corrected

    def test_light_bg_light_text_contrast_fix(self) -> None:
        """Light background with light text should auto-correct to black text."""
        colors = [
            ExtractedColor(name="Background", hex="#f5f5f5"),
            ExtractedColor(name="Text Color", hex="#eeeeee"),
        ]
        palette = convert_colors_to_palette(colors)
        assert palette.background == "#f5f5f5"
        assert palette.text == "#000000"  # contrast-corrected

    def test_adequate_contrast_preserved(self) -> None:
        """Colors with good contrast should not be modified."""
        colors = [
            ExtractedColor(name="Background", hex="#ffffff"),
            ExtractedColor(name="Text Color", hex="#333333"),
        ]
        palette = convert_colors_to_palette(colors)
        assert palette.text == "#333333"  # unchanged


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
        result = node_to_email_html(node)
        assert "<td" in result
        assert "Hello" in result

    def test_image_node(self) -> None:
        node = DesignNode(id="2", name="Hero", type=DesignNodeType.IMAGE, width=600, height=300)
        result = node_to_email_html(node)
        assert "<img" in result
        assert 'width="600"' in result

    def test_image_node_has_node_id_and_alt(self) -> None:
        """Image tags include data-node-id for URL mapping and alt for accessibility."""
        node = DesignNode(id="1:2", name="Logo", type=DesignNodeType.IMAGE, width=200, height=50)
        result = node_to_email_html(node)
        assert 'data-node-id="1:2"' in result
        assert 'alt="Logo"' in result
        assert 'src=""' in result  # empty until _fill_image_urls post-processes

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
        result = node_to_email_html(node)
        assert "<table" in result
        assert "<tr>" in result

    def test_instance_node(self) -> None:
        """INSTANCE type renders as table (same as FRAME)."""
        node = DesignNode(
            id="10",
            name="Button Instance",
            type=DesignNodeType.INSTANCE,
            width=200,
            children=[
                DesignNode(
                    id="11", name="Label", type=DesignNodeType.TEXT, text_content="Click", y=0
                ),
            ],
        )
        result = node_to_email_html(node)
        assert "<table" in result
        assert 'width="100%"' in result
        assert "Click" in result

    def test_component_node_with_children(self) -> None:
        """COMPONENT with nested nodes renders recursively."""
        node = DesignNode(
            id="20",
            name="Card Component",
            type=DesignNodeType.COMPONENT,
            width=300,
            children=[
                DesignNode(
                    id="21", name="Title", type=DesignNodeType.TEXT, text_content="Title", y=0
                ),
                DesignNode(
                    id="22", name="Body", type=DesignNodeType.TEXT, text_content="Body text", y=30
                ),
            ],
        )
        result = node_to_email_html(node)
        assert "<table" in result
        assert "Title" in result
        assert "Body text" in result

    def test_props_map_font_override(self) -> None:
        """TEXT node with props_map uses custom font."""
        node = DesignNode(id="30", name="Custom", type=DesignNodeType.TEXT, text_content="Styled")
        props_map = {
            "30": _NodeProps(font_family="Inter", font_size=24.0, font_weight="700"),
        }
        result = node_to_email_html(node, props_map=props_map)
        assert "Inter" in result
        assert "font-size:24px" in result
        assert "font-weight:700" in result
        assert "Styled" in result

    def test_props_map_bg_color(self) -> None:
        """FRAME with props_map bg_color gets bgcolor attr."""
        node = DesignNode(
            id="40", name="Section", type=DesignNodeType.FRAME, width=600, children=[]
        )
        props_map = {"40": _NodeProps(bg_color="#f5f5f5")}
        result = node_to_email_html(node, props_map=props_map)
        assert 'bgcolor="#f5f5f5"' in result

    def test_dark_bg_text_gets_white_color(self) -> None:
        """TEXT inside a dark-background FRAME gets color:#ffffff."""
        node = DesignNode(
            id="100",
            name="Dark Section",
            type=DesignNodeType.FRAME,
            width=600,
            children=[
                DesignNode(
                    id="101", name="Body", type=DesignNodeType.TEXT, text_content="Hello", y=0
                ),
            ],
        )
        props_map = {"100": _NodeProps(bg_color="#1a1a2e")}
        result = node_to_email_html(node, props_map=props_map)
        assert "color:#ffffff" in result
        assert "Hello" in result

    def test_light_bg_text_gets_black_color(self) -> None:
        """TEXT inside a light-background FRAME gets color:#000000."""
        node = DesignNode(
            id="110",
            name="Light Section",
            type=DesignNodeType.FRAME,
            width=600,
            children=[
                DesignNode(
                    id="111", name="Body", type=DesignNodeType.TEXT, text_content="World", y=0
                ),
            ],
        )
        props_map = {"110": _NodeProps(bg_color="#ffffff")}
        result = node_to_email_html(node, props_map=props_map)
        assert "color:#000000" in result

    def test_nested_dark_bg_propagates(self) -> None:
        """Nested frames inherit parent bg for text contrast."""
        inner = DesignNode(
            id="121",
            name="Inner",
            type=DesignNodeType.GROUP,
            children=[
                DesignNode(
                    id="122", name="Copy", type=DesignNodeType.TEXT, text_content="Deep", y=0
                ),
            ],
        )
        outer = DesignNode(
            id="120",
            name="Outer",
            type=DesignNodeType.FRAME,
            width=600,
            children=[inner],
        )
        props_map = {"120": _NodeProps(bg_color="#0d1117")}
        result = node_to_email_html(outer, props_map=props_map)
        assert "color:#ffffff" in result
        assert "Deep" in result

    def test_props_map_padding(self) -> None:
        """FRAME with padding props gets padding style."""
        node = DesignNode(id="50", name="Padded", type=DesignNodeType.FRAME, width=600, children=[])
        props_map = {
            "50": _NodeProps(padding_top=20, padding_right=10, padding_bottom=20, padding_left=10),
        }
        result = node_to_email_html(node, props_map=props_map)
        assert "padding:20px 10px 20px 10px" in result

    def test_text_content_html_escaped(self) -> None:
        """Text content with HTML chars is escaped to prevent XSS."""
        node = DesignNode(
            id="60",
            name="XSS",
            type=DesignNodeType.TEXT,
            text_content='<script>alert("xss")</script>',
        )
        result = node_to_email_html(node)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestSanitizeCssValue:
    def test_clean_value_unchanged(self) -> None:
        assert _sanitize_css_value("Inter") == "Inter"
        assert _sanitize_css_value("Arial, Helvetica, sans-serif") == "Arial, Helvetica, sans-serif"

    def test_strips_semicolon(self) -> None:
        assert ";" not in _sanitize_css_value("Arial; background:url(evil)")

    def test_strips_angle_brackets(self) -> None:
        result = _sanitize_css_value("Inter; } </style><script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result
        assert "script" in result  # text preserved, tags stripped

    def test_strips_braces(self) -> None:
        assert "{" not in _sanitize_css_value("Inter { color: red }")

    def test_empty_on_all_unsafe(self) -> None:
        assert _sanitize_css_value(";<>{}") == ""

    def test_numeric_weight(self) -> None:
        assert _sanitize_css_value("700") == "700"


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

    def test_hero_image_own_row(self) -> None:
        """Wide IMAGE (>=80% parent width) gets its own row."""
        nodes = [
            DesignNode(id="1", name="Hero", type=DesignNodeType.IMAGE, x=0, y=0, width=550),
            DesignNode(id="2", name="Text", type=DesignNodeType.TEXT, x=300, y=0),
        ]
        rows = _group_into_rows(nodes, parent_width=600)
        # Hero image should be in its own row (550 >= 600*0.8=480)
        assert len(rows) == 2
        assert rows[0][0].id == "1"
        assert rows[1][0].id == "2"


class TestFillColorFromNode:
    def test_fill_color_from_node(self) -> None:
        """DesignNode with fill_color renders bgcolor attribute."""
        node = DesignNode(
            id="fc1",
            name="Dark Section",
            type=DesignNodeType.FRAME,
            width=600,
            fill_color="#1a1a2e",
            children=[],
        )
        result = node_to_email_html(node)
        assert 'bgcolor="#1a1a2e"' in result

    def test_text_color_from_node(self) -> None:
        """TEXT node with text_color uses it instead of contrast auto."""
        frame = DesignNode(
            id="tc1",
            name="Section",
            type=DesignNodeType.FRAME,
            width=600,
            fill_color="#1a1a2e",
            children=[
                DesignNode(
                    id="tc2",
                    name="Title",
                    type=DesignNodeType.TEXT,
                    text_content="Custom Color",
                    text_color="#ff6600",
                    y=0,
                ),
            ],
        )
        result = node_to_email_html(frame)
        assert "color:#ff6600;" in result
        assert "Custom Color" in result
        # Should NOT use contrast-auto white
        assert "color:#ffffff;" not in result

    def test_text_color_fallback_to_contrast(self) -> None:
        """TEXT node without text_color in dark parent still gets white."""
        frame = DesignNode(
            id="cf1",
            name="Dark",
            type=DesignNodeType.FRAME,
            width=600,
            fill_color="#0d1117",
            children=[
                DesignNode(
                    id="cf2",
                    name="Body",
                    type=DesignNodeType.TEXT,
                    text_content="Auto contrast",
                    y=0,
                ),
            ],
        )
        result = node_to_email_html(frame)
        assert "color:#ffffff;" in result

    def test_image_responsive_styles(self) -> None:
        """Image nodes include width:100%;height:auto for responsiveness."""
        node = DesignNode(id="ri1", name="Hero", type=DesignNodeType.IMAGE, width=600, height=300)
        result = node_to_email_html(node)
        assert "width:100%;height:auto;" in result

    def test_props_map_overrides_fill_color(self) -> None:
        """props_map bg_color takes precedence over node.fill_color."""
        node = DesignNode(
            id="po1",
            name="Section",
            type=DesignNodeType.FRAME,
            width=600,
            fill_color="#111111",
            children=[],
        )
        props_map = {"po1": _NodeProps(bg_color="#f5f5f5")}
        result = node_to_email_html(node, props_map=props_map)
        assert 'bgcolor="#f5f5f5"' in result
        assert 'bgcolor="#111111"' not in result


class TestFrameWidthAndFont:
    def test_frame_table_width_100_percent(self) -> None:
        """FRAME nodes produce width='100%' instead of pixel width."""
        node = DesignNode(
            id="w1",
            name="Section",
            type=DesignNodeType.FRAME,
            width=480,
            children=[],
        )
        result = node_to_email_html(node)
        assert 'width="100%"' in result
        assert 'width="480"' not in result

    def test_font_family_propagates_to_children(self) -> None:
        """Parent frame font reaches child TEXT <td> via parent_font."""
        frame = DesignNode(
            id="f1",
            name="Section",
            type=DesignNodeType.FRAME,
            width=600,
            children=[
                DesignNode(
                    id="t1", name="Body", type=DesignNodeType.TEXT, text_content="Hello", y=0
                ),
            ],
        )
        props_map = {"f1": _NodeProps(font_family="Inter")}
        result = node_to_email_html(frame, props_map=props_map)
        assert "Inter,Arial,Helvetica,sans-serif" in result

    def test_font_family_on_td_wrapper(self) -> None:
        """Non-text child <td> gets style='font-family:...' when parent has font."""
        frame = DesignNode(
            id="f2",
            name="Outer",
            type=DesignNodeType.FRAME,
            width=600,
            children=[
                DesignNode(
                    id="inner1",
                    name="Inner",
                    type=DesignNodeType.FRAME,
                    width=300,
                    children=[],
                    y=0,
                ),
            ],
        )
        props_map = {"f2": _NodeProps(font_family="Roboto")}
        result = node_to_email_html(frame, props_map=props_map)
        assert 'style="font-family:Roboto,Arial,Helvetica,sans-serif;"' in result

    def test_email_skeleton_has_width_600(self) -> None:
        """EMAIL_SKELETON formatted output contains width='600' on main table."""
        from app.design_sync.converter_service import EMAIL_SKELETON

        html = EMAIL_SKELETON.format(
            style_block="<style></style>",
            bg_color="#ffffff",
            text_color="#000000",
            body_font="Arial, Helvetica, sans-serif",
            sections="",
            container_width=600,
        )
        # The non-MSO main table should have width="600"
        assert 'width="600"' in html
        assert "max-width:600px" in html
        assert "mso-table-lspace:0pt" in html
        assert "mso-table-rspace:0pt" in html

    def test_email_skeleton_body_has_inline_font(self) -> None:
        """<body> tag includes font-family: in inline style."""
        from app.design_sync.converter_service import EMAIL_SKELETON

        html = EMAIL_SKELETON.format(
            style_block="<style></style>",
            bg_color="#ffffff",
            text_color="#000000",
            body_font="Inter, Arial, Helvetica, sans-serif",
            sections="",
            container_width=600,
        )
        assert "font-family:Inter, Arial, Helvetica, sans-serif;" in html


class TestConverterNoDivOrP:
    """Converter output uses table layout — no div/p for structure."""

    def test_skeleton_no_div_or_p(self) -> None:
        from app.design_sync.converter_service import EMAIL_SKELETON

        html = EMAIL_SKELETON.format(
            style_block="<style></style>",
            bg_color="#ffffff",
            text_color="#000000",
            body_font="Arial, Helvetica, sans-serif",
            sections="<tr><td>Content</td></tr>",
            container_width=600,
        )
        assert "<div" not in html
        assert "<p" not in html

    def test_full_conversion_uses_tables(self) -> None:
        from app.design_sync.converter_service import DesignConverterService
        from app.design_sync.protocol import DesignFileStructure, ExtractedTokens

        structure = DesignFileStructure(
            file_name="test.penpot",
            pages=[
                DesignNode(
                    id="page",
                    name="Page",
                    type=DesignNodeType.PAGE,
                    children=[
                        DesignNode(
                            id="frame1",
                            name="Hero",
                            type=DesignNodeType.FRAME,
                            width=600,
                            children=[
                                DesignNode(
                                    id="t1",
                                    name="Title",
                                    type=DesignNodeType.TEXT,
                                    text_content="Hello World",
                                    y=0,
                                ),
                                DesignNode(
                                    id="img1",
                                    name="Hero Image",
                                    type=DesignNodeType.IMAGE,
                                    width=600,
                                    height=300,
                                    y=50,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(structure, ExtractedTokens())
        assert "<table" in result.html
        # No layout divs in output
        assert "<div" not in result.html

    def test_node_to_email_html_uses_tables(self) -> None:
        node = DesignNode(
            id="f1",
            name="Section",
            type=DesignNodeType.FRAME,
            width=600,
            children=[
                DesignNode(
                    id="t1", name="Text", type=DesignNodeType.TEXT, text_content="Body", y=0
                ),
                DesignNode(
                    id="g1",
                    name="Group",
                    type=DesignNodeType.GROUP,
                    children=[
                        DesignNode(
                            id="t2",
                            name="Nested",
                            type=DesignNodeType.TEXT,
                            text_content="Nested text",
                            y=0,
                        ),
                    ],
                    y=50,
                ),
            ],
        )
        result = node_to_email_html(node)
        assert "<div" not in result
        assert "<table" in result


class TestSanitizeWebTagsForEmail:
    def test_p_inside_td_preserved_with_margin(self) -> None:
        """<p> inside <td> is preserved with margin reset for accessibility."""
        html_input = '<td><p style="color:red;">text</p></td>'
        result = sanitize_web_tags_for_email(html_input)
        assert "<p" in result
        assert "margin:0 0 10px 0" in result
        assert "color:red" in result
        assert "text" in result

    def test_p_outside_td_stripped(self) -> None:
        """<p> outside <td> is stripped to content (backward compat)."""
        html_input = "<p>standalone</p>"
        result = sanitize_web_tags_for_email(html_input)
        assert "<p" not in result
        assert "standalone" in result

    def test_multiple_p_inside_td_preserved(self) -> None:
        """Multiple <p> tags inside <td> all get margin resets."""
        html_input = "<td><p>one</p><p>two</p></td>"
        result = sanitize_web_tags_for_email(html_input)
        assert result.count("<p") == 2
        assert result.count("margin:0 0 10px 0") == 2

    def test_multiple_p_outside_td_get_br_separator(self) -> None:
        html_input = "<p>one</p><p>two</p>"
        result = sanitize_web_tags_for_email(html_input)
        assert "<p" not in result
        assert "one<br><br>two" in result

    def test_p_with_existing_margin_preserved(self) -> None:
        """<p> that already has margin is not double-set."""
        html_input = '<td><p style="margin:0;">text</p></td>'
        result = sanitize_web_tags_for_email(html_input)
        assert "<p" in result
        assert "margin:0;" in result
        assert "margin:0 0 10px 0" not in result

    def test_div_with_layout_css_converted_to_table(self) -> None:
        """<div> with layout CSS becomes table wrapper."""
        html_input = '<div style="width:300px;">content</div>'
        result = sanitize_web_tags_for_email(html_input)
        assert "<div" not in result
        assert "</div>" not in result
        assert '<table role="presentation"' in result
        assert "</td></tr></table>" in result
        assert "content" in result

    def test_div_simple_wrapper_inside_td_preserved(self) -> None:
        """<div> with text-align inside <td> is preserved (content wrapper)."""
        html_input = '<td><div style="text-align:center;">centered</div></td>'
        result = sanitize_web_tags_for_email(html_input)
        assert "<div" in result
        assert "text-align:center" in result
        assert "centered" in result

    def test_div_outside_td_no_layout_unwrapped(self) -> None:
        """<div> outside <td> with no layout CSS is unwrapped."""
        html_input = '<div role="article"><table><tr><td>content</td></tr></table></div>'
        result = sanitize_web_tags_for_email(html_input)
        assert "<div" not in result
        assert "</div>" not in result
        assert "<table>" in result
        assert "content" in result

    def test_nested_divs_outside_td_stripped(self) -> None:
        html_input = "<div><div><table><tr><td>deep</td></tr></table></div></div>"
        result = sanitize_web_tags_for_email(html_input)
        assert "<div" not in result
        assert "</div>" not in result
        assert "<table>" in result

    def test_mso_comment_preserved(self) -> None:
        html_input = (
            "before<!--[if mso]><div><table><tr><td>mso</td></tr></table></div><![endif]-->after"
        )
        result = sanitize_web_tags_for_email(html_input)
        assert "<!--[if mso]>" in result
        assert "<div>" in result  # inside MSO block, untouched
        assert "<![endif]-->" in result
        assert "before" in result
        assert "after" in result

    def test_div_with_display_flex_converted(self) -> None:
        """div with display:flex is layout — converted to table."""
        html_input = '<div style="display:flex;">items</div>'
        result = sanitize_web_tags_for_email(html_input)
        assert "<div" not in result
        assert '<table role="presentation"' in result
        assert "items" in result

    def test_div_with_max_width_converted(self) -> None:
        """div with max-width is layout — converted to table."""
        html_input = '<div style="max-width:600px;">wrapper</div>'
        result = sanitize_web_tags_for_email(html_input)
        assert "<div" not in result
        assert '<table role="presentation"' in result

    def test_llm_output_p_preserved_div_classified(self) -> None:
        """LLM output inside table: <p> preserved, simple <div> preserved."""
        llm_output = (
            '<table><tr><td><div style="text-align:center;"><p>Intro</p>'
            "<p>Details</p></div></td></tr></table>"
        )
        result = sanitize_web_tags_for_email(llm_output)
        # <p> inside <td> → preserved
        assert "<p" in result
        assert "Intro" in result
        assert "Details" in result
        # Simple <div> inside <td> → preserved
        assert "text-align:center" in result
        assert "<table>" in result

    def test_p_between_nested_tables_inside_outer_td(self) -> None:
        """<p> between nested tables but still inside outer <td> is preserved."""
        html_input = "<td><table><tr><td>inner</td></tr></table><p>between</p></td>"
        result = sanitize_web_tags_for_email(html_input)
        assert "<p" in result
        assert "margin:0 0 10px 0" in result
        assert "between" in result

    def test_div_between_nested_tables_inside_outer_td(self) -> None:
        """Simple <div> between nested tables but inside outer <td> is preserved."""
        html_input = (
            "<td><table><tr><td>inner</td></tr></table>"
            '<div style="text-align:center;">wrap</div></td>'
        )
        result = sanitize_web_tags_for_email(html_input)
        assert "<div" in result
        assert "text-align:center" in result
        assert "wrap" in result


class TestEmailSkeletonMetaTags:
    def test_format_detection_meta(self) -> None:
        from app.design_sync.converter_service import EMAIL_SKELETON

        html = EMAIL_SKELETON.format(
            style_block="<style></style>",
            bg_color="#ffffff",
            text_color="#000000",
            body_font="Arial, Helvetica, sans-serif",
            sections="",
            container_width=600,
        )
        assert '<meta name="format-detection"' in html
        assert '<meta name="x-apple-disable-message-reformatting">' in html

    def test_mso_reset_in_style_block(self) -> None:
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
                            children=[],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(structure, ExtractedTokens())
        assert "border-collapse: collapse" in result.html
        assert "mso-table-lspace: 0pt" in result.html
        assert "-ms-interpolation-mode: bicubic" in result.html


class TestInlineMSOStyles:
    def test_table_has_mso_resets(self) -> None:
        """Every <table> in converter output has MSO reset inline styles."""
        node = DesignNode(
            id="1",
            name="Section",
            type=DesignNodeType.FRAME,
            width=600,
            children=[],
        )
        result = node_to_email_html(node)
        assert "border-collapse:collapse" in result
        assert "mso-table-lspace:0pt" in result
        assert "mso-table-rspace:0pt" in result

    def test_image_has_mso_resets(self) -> None:
        """<img> tags include MSO-safe inline styles."""
        node = DesignNode(id="2", name="Photo", type=DesignNodeType.IMAGE, width=600, height=300)
        result = node_to_email_html(node)
        assert "-ms-interpolation-mode:bicubic" in result
        assert "outline:none" in result
        assert "text-decoration:none" in result


class TestNestingDepthGuard:
    def test_depth_exceeding_6_flattens(self) -> None:
        """Deeply nested frames are flattened beyond depth 6."""
        # Build 8-level deep nesting
        deepest = DesignNode(
            id="t-deep",
            name="deep-text",
            type=DesignNodeType.TEXT,
            text_content="deep",
            y=0,
        )
        current = deepest
        for i in range(8):
            current = DesignNode(
                id=f"f{i}",
                name=f"Frame-{i}",
                type=DesignNodeType.FRAME,
                width=600,
                children=[current],
            )
        result = node_to_email_html(current)
        # Should still contain the text
        assert "deep" in result
        # Count <table> tags — should be capped (not 8 nested tables)
        table_count = result.count("<table")
        assert table_count <= 7  # depth 0-6 = 7 tables max


class TestLayoutAnalyzerIntegration:
    def test_convert_populates_layout(self) -> None:
        """convert() returns ConversionResult with layout data."""
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
                            name="Header",
                            type=DesignNodeType.FRAME,
                            x=0,
                            y=0,
                            width=600,
                            height=80,
                            children=[],
                        ),
                        DesignNode(
                            id="f2",
                            name="Content",
                            type=DesignNodeType.FRAME,
                            x=0,
                            y=100,
                            width=600,
                            height=200,
                            children=[
                                DesignNode(
                                    id="t1",
                                    name="Body",
                                    type=DesignNodeType.TEXT,
                                    text_content="Hello",
                                    y=0,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(structure, ExtractedTokens())
        assert result.layout is not None
        assert len(result.layout.sections) == 2
        assert result.sections_count == 2

    def test_container_width_from_layout(self) -> None:
        """Container width derived from layout.overall_width."""
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
                            x=0,
                            y=0,
                            width=700,
                            height=200,
                            children=[],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(structure, ExtractedTokens())
        assert 'width="700"' in result.html
        assert "max-width:700px" in result.html

    def test_container_width_clamped(self) -> None:
        """Container width > 800 is clamped to 800."""
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
                            x=0,
                            y=0,
                            width=1200,
                            height=200,
                            children=[],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(structure, ExtractedTokens())
        assert 'width="800"' in result.html
        assert "max-width:800px" in result.html


class TestBuildPropsMapFromNodes:
    def test_extracts_all_fields(self) -> None:
        """_build_props_map_from_nodes extracts full DesignNode properties."""
        from app.design_sync.converter_service import DesignConverterService

        frames = [
            DesignNode(
                id="f1",
                name="Section",
                type=DesignNodeType.FRAME,
                width=600,
                padding_top=24.0,
                padding_right=16.0,
                padding_bottom=24.0,
                padding_left=16.0,
                layout_mode="HORIZONTAL",
                children=[
                    DesignNode(
                        id="t1",
                        name="Text",
                        type=DesignNodeType.TEXT,
                        font_family="Inter",
                        font_size=18.0,
                        font_weight=700,
                        line_height_px=24.0,
                        letter_spacing_px=0.5,
                        text_content="Hello",
                    ),
                ],
            ),
        ]
        svc = DesignConverterService()
        props = svc._build_props_map_from_nodes(frames)

        assert "f1" in props
        assert props["f1"].padding_top == 24.0
        assert props["f1"].padding_right == 16.0
        assert props["f1"].layout_direction == "row"

        assert "t1" in props
        assert props["t1"].font_family == "Inter"
        assert props["t1"].font_size == 18.0
        assert props["t1"].font_weight == "700"
        assert props["t1"].line_height_px == 24.0
        assert props["t1"].letter_spacing_px == 0.5

    def test_vertical_layout_direction(self) -> None:
        from app.design_sync.converter_service import DesignConverterService

        frames = [
            DesignNode(
                id="f1",
                name="Stack",
                type=DesignNodeType.FRAME,
                width=600,
                layout_mode="VERTICAL",
            ),
        ]
        svc = DesignConverterService()
        props = svc._build_props_map_from_nodes(frames)
        assert props["f1"].layout_direction == "column"


class TestInterSectionSpacer:
    def test_spacer_row_when_spacing_after(self) -> None:
        """Sections with spacing_after > 0 produce spacer <tr> rows."""
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
                            name="Header",
                            type=DesignNodeType.FRAME,
                            x=0,
                            y=0,
                            width=600,
                            height=80,
                            children=[],
                        ),
                        DesignNode(
                            id="f2",
                            name="Content",
                            type=DesignNodeType.FRAME,
                            x=0,
                            y=120,  # 40px gap from header bottom (80)
                            width=600,
                            height=200,
                            children=[],
                        ),
                    ],
                ),
            ],
        )
        result = DesignConverterService().convert(structure, ExtractedTokens())
        assert "mso-line-height-rule:exactly" in result.html
        assert 'aria-hidden="true"' in result.html
