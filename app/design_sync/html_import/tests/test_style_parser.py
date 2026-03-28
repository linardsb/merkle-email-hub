"""Tests for style_parser module."""

from __future__ import annotations

from app.design_sync.html_import.style_parser import (
    extract_font_size_px,
    normalize_hex_color,
    parse_css_rules,
    parse_inline_style,
    parse_padding_shorthand,
    parse_style_blocks,
)


class TestParseInlineStyle:
    def test_basic_properties(self) -> None:
        result = parse_inline_style("color: red; font-size: 16px;")
        assert result.properties["color"] == "red"
        assert result.properties["font-size"] == "16px"

    def test_important_stripped(self) -> None:
        result = parse_inline_style("color: red !important; margin: 0")
        assert result.properties["color"] == "red"
        assert result.properties["margin"] == "0"

    def test_quoted_font_family(self) -> None:
        result = parse_inline_style("font-family: 'Helvetica Neue', Arial, sans-serif")
        assert "Helvetica" in result.properties["font-family"]

    def test_empty_string(self) -> None:
        result = parse_inline_style("")
        assert result.properties == {}

    def test_whitespace_only(self) -> None:
        result = parse_inline_style("   ")
        assert result.properties == {}

    def test_malformed_no_colon(self) -> None:
        result = parse_inline_style("broken-declaration")
        assert result.properties == {}

    def test_property_names_lowercased(self) -> None:
        result = parse_inline_style("FONT-SIZE: 14px; Color: blue")
        assert "font-size" in result.properties
        assert "color" in result.properties

    def test_shorthand_padding(self) -> None:
        result = parse_inline_style("padding: 10px 20px 30px 40px")
        assert result.properties["padding"] == "10px 20px 30px 40px"


class TestParseStyleBlocks:
    def test_extracts_single_block(self) -> None:
        html = "<html><head><style>body { color: red; }</style></head></html>"
        blocks = parse_style_blocks(html)
        assert len(blocks) == 1
        assert "color: red" in blocks[0]

    def test_extracts_multiple_blocks(self) -> None:
        html = "<style>a { color: blue; }</style><style>p { margin: 0; }</style>"
        blocks = parse_style_blocks(html)
        assert len(blocks) == 2

    def test_preserves_media_queries(self) -> None:
        html = "<style>@media (prefers-color-scheme: dark) { .bg { color: #fff; } }</style>"
        blocks = parse_style_blocks(html)
        assert "prefers-color-scheme" in blocks[0]

    def test_no_style_blocks(self) -> None:
        html = "<html><body><p>Hello</p></body></html>"
        blocks = parse_style_blocks(html)
        assert blocks == []


class TestParseCssRules:
    def test_simple_rule(self) -> None:
        rules = parse_css_rules("body { color: red; font-size: 16px; }")
        assert len(rules) == 1
        assert rules[0].selector == "body"
        assert rules[0].properties["color"] == "red"
        assert not rules[0].is_dark_mode

    def test_dark_mode_rules(self) -> None:
        css = """
        body { color: #333; }
        @media (prefers-color-scheme: dark) {
            body { color: #eee; background-color: #111; }
        }
        """
        rules = parse_css_rules(css)
        light_rules = [r for r in rules if not r.is_dark_mode]
        dark_rules = [r for r in rules if r.is_dark_mode]
        assert len(light_rules) >= 1
        assert len(dark_rules) >= 1
        assert dark_rules[0].properties.get("color") == "#eee"

    def test_empty_css(self) -> None:
        rules = parse_css_rules("")
        assert rules == []

    def test_multiple_selectors(self) -> None:
        rules = parse_css_rules("h1 { font-size: 24px; } p { margin: 0; }")
        assert len(rules) == 2


class TestExtractFontSizePx:
    def test_px(self) -> None:
        assert extract_font_size_px("16px") == 16.0

    def test_pt(self) -> None:
        result = extract_font_size_px("12pt")
        assert result is not None
        assert abs(result - 16.0) < 0.1

    def test_em(self) -> None:
        assert extract_font_size_px("1.5em") == 24.0

    def test_rem(self) -> None:
        assert extract_font_size_px("2rem") == 32.0

    def test_invalid(self) -> None:
        assert extract_font_size_px("auto") is None

    def test_empty(self) -> None:
        assert extract_font_size_px("") is None


class TestNormalizeHexColor:
    def test_hex6(self) -> None:
        assert normalize_hex_color("#FF5500") == "#ff5500"

    def test_hex3(self) -> None:
        assert normalize_hex_color("#F50") == "#ff5500"

    def test_rgb(self) -> None:
        assert normalize_hex_color("rgb(255, 85, 0)") == "#ff5500"

    def test_named_color(self) -> None:
        assert normalize_hex_color("white") == "#ffffff"
        assert normalize_hex_color("black") == "#000000"

    def test_invalid(self) -> None:
        assert normalize_hex_color("not-a-color") is None

    def test_empty(self) -> None:
        assert normalize_hex_color("") is None

    def test_rgb_clamped(self) -> None:
        assert normalize_hex_color("rgb(300, 0, 0)") == "#ff0000"


class TestParsePaddingShorthand:
    def test_four_values(self) -> None:
        result = parse_padding_shorthand("10px 20px 30px 40px")
        assert result == (10.0, 20.0, 30.0, 40.0)

    def test_two_values(self) -> None:
        result = parse_padding_shorthand("10px 20px")
        assert result == (10.0, 20.0, 10.0, 20.0)

    def test_one_value(self) -> None:
        result = parse_padding_shorthand("15px")
        assert result == (15.0, 15.0, 15.0, 15.0)

    def test_three_values(self) -> None:
        result = parse_padding_shorthand("10px 20px 30px")
        assert result == (10.0, 20.0, 30.0, 20.0)

    def test_empty(self) -> None:
        assert parse_padding_shorthand("") is None

    def test_invalid(self) -> None:
        assert parse_padding_shorthand("auto") is None
