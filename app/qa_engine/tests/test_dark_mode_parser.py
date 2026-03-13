# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
"""Unit tests for the dark mode parser module."""

from app.qa_engine.dark_mode_parser import (
    _contrast_ratio,
    _hex_to_luminance,
    _parse_css_color,
    validate_dark_mode,
)

# ── Color helpers ──


class TestParseCssColor:
    def test_hex_3_digit(self):
        assert _parse_css_color("#fff") == "#ffffff"

    def test_hex_6_digit(self):
        assert _parse_css_color("#1a1a1a") == "#1a1a1a"

    def test_hex_4_digit_alpha(self):
        assert _parse_css_color("#fffa") == "#ffffff"

    def test_hex_8_digit_alpha(self):
        assert _parse_css_color("#1a1a1aff") == "#1a1a1a"

    def test_named_white(self):
        assert _parse_css_color("white") == "#ffffff"

    def test_named_black(self):
        assert _parse_css_color("black") == "#000000"

    def test_rgb(self):
        assert _parse_css_color("rgb(255, 0, 128)") == "#ff0080"

    def test_unknown_returns_none(self):
        assert _parse_css_color("currentColor") is None

    def test_empty_returns_none(self):
        assert _parse_css_color("") is None

    def test_case_insensitive(self):
        assert _parse_css_color("WHITE") == "#ffffff"
        assert _parse_css_color("#FFF") == "#ffffff"


class TestLuminance:
    def test_white(self):
        assert abs(_hex_to_luminance("#ffffff") - 1.0) < 0.01

    def test_black(self):
        assert abs(_hex_to_luminance("#000000") - 0.0) < 0.01

    def test_mid_gray(self):
        lum = _hex_to_luminance("#808080")
        assert 0.2 < lum < 0.3


class TestContrastRatio:
    def test_white_on_black(self):
        ratio = _contrast_ratio(1.0, 0.0)
        assert abs(ratio - 21.0) < 0.1

    def test_same_color(self):
        ratio = _contrast_ratio(0.5, 0.5)
        assert abs(ratio - 1.0) < 0.01


# ── Meta tag parsing ──


class TestMetaTags:
    def test_color_scheme_detected(self):
        html = (
            "<html><head>"
            "<meta name='color-scheme' content='light dark'>"
            "</head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert result.meta_tags.has_color_scheme is True
        assert result.meta_tags.content_value == "light dark"
        assert result.meta_tags.color_scheme_in_head is True

    def test_supported_color_schemes_detected(self):
        html = (
            "<html><head>"
            "<meta name='supported-color-schemes' content='light dark'>"
            "</head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert result.meta_tags.has_supported_color_schemes is True

    def test_css_color_scheme_detected(self):
        html = (
            "<html><head><style>"
            ":root { color-scheme: light dark; }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert result.meta_tags.has_css_color_scheme is True

    def test_css_color_scheme_not_confused_with_media_query(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .x { color: #fff; } }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert result.meta_tags.has_css_color_scheme is False

    def test_meta_in_body_detected(self):
        html = (
            "<html><head></head><body><meta name='color-scheme' content='light dark'></body></html>"
        )
        result = validate_dark_mode(html)
        assert result.meta_tags.has_color_scheme is True
        assert result.meta_tags.color_scheme_in_head is False

    def test_no_meta_tags(self):
        html = "<html><head></head><body>x</body></html>"
        result = validate_dark_mode(html)
        assert result.meta_tags.has_color_scheme is False
        assert result.meta_tags.has_supported_color_schemes is False
        assert result.meta_tags.has_css_color_scheme is False

    def test_empty_html(self):
        result = validate_dark_mode("")
        assert result.meta_tags.has_color_scheme is False


# ── Media query parsing ──


class TestMediaQueries:
    def test_basic_media_query(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.media_queries) == 1
        mq = result.media_queries[0]
        assert mq.has_color_props is True
        assert mq.has_important is True
        assert mq.is_empty is False

    def test_empty_media_query(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.media_queries) == 1
        assert result.media_queries[0].is_empty is True
        assert result.media_queries[0].has_color_props is False

    def test_media_query_without_important(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .x { color: #fff; background-color: #000; } }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.media_queries) == 1
        mq = result.media_queries[0]
        assert mq.has_color_props is True
        assert mq.has_important is False

    def test_media_query_non_color_only(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .x { display: block !important; } }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.media_queries) == 1
        assert result.media_queries[0].has_color_props is False

    def test_multiple_media_queries(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .a { color: #fff !important; } }"
            "@media (prefers-color-scheme: dark) { .b { background-color: #000 !important; } }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.media_queries) == 2

    def test_no_media_query(self):
        html = "<html><head><style>.x { color: red; }</style></head><body>x</body></html>"
        result = validate_dark_mode(html)
        assert len(result.media_queries) == 0

    def test_nested_selector_blocks(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .a { color: #fff !important; } .b { background-color: #1a1a1a !important; } }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.media_queries) == 1
        mq = result.media_queries[0]
        assert len(mq.declarations) >= 2
        assert mq.has_color_props is True


# ── Outlook selectors ──


class TestOutlookSelectors:
    def test_ogsc_detected(self):
        html = (
            "<html><head><style>[data-ogsc] .x { color: #fff; }</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.outlook_selectors) == 1
        assert result.outlook_selectors[0].selector_type == "ogsc"
        assert result.outlook_selectors[0].has_declarations is True

    def test_ogsb_detected(self):
        html = (
            "<html><head><style>"
            "[data-ogsb] .x { background-color: #000; }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.outlook_selectors) == 1
        assert result.outlook_selectors[0].selector_type == "ogsb"

    def test_empty_outlook_selector(self):
        html = "<html><head><style>[data-ogsc] .x { }</style></head><body>x</body></html>"
        result = validate_dark_mode(html)
        assert len(result.outlook_selectors) == 1
        assert result.outlook_selectors[0].has_declarations is False

    def test_both_selectors(self):
        html = (
            "<html><head><style>"
            "[data-ogsc] .x { color: #fff; }"
            "[data-ogsb] .x { background-color: #000; }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        types = {s.selector_type for s in result.outlook_selectors}
        assert types == {"ogsc", "ogsb"}

    def test_no_outlook_selectors(self):
        html = "<html><head><style>.x { color: red; }</style></head><body>x</body></html>"
        result = validate_dark_mode(html)
        assert len(result.outlook_selectors) == 0


# ── Color pair extraction ──


class TestColorPairs:
    def test_inline_style_matched_to_dark_mode(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .text { color: #e0e0e0 !important; } }"
            "</style></head><body>"
            '<td class="text" style="color: #333333;">Hello</td>'
            "</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.color_pairs) == 1
        pair = result.color_pairs[0]
        assert pair.selector == ".text"
        assert pair.css_property == "color"
        assert pair.light_value == "#333333"
        assert pair.dark_value == "#e0e0e0"
        assert pair.contrast_ratio > 0

    def test_high_contrast_pair(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .bg { background-color: #1a1a1a !important; } }"
            "</style></head><body>"
            '<td class="bg" style="background-color: #ffffff;">Content</td>'
            "</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.color_pairs) == 1
        # White (#fff) vs very dark (#1a1a1a) — high contrast
        assert result.color_pairs[0].contrast_ratio > 10

    def test_low_contrast_pair(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .low { color: #222222 !important; } }"
            "</style></head><body>"
            '<td class="low" style="color: #333333;">Text</td>'
            "</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.color_pairs) == 1
        # Both dark colors — very low contrast
        assert result.color_pairs[0].contrast_ratio < 2.0

    def test_no_inline_style_no_pairs(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .x { color: #fff !important; } }"
            "</style></head><body>"
            '<td class="x">No inline style</td>'
            "</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.color_pairs) == 0

    def test_no_matching_class_no_pairs(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { .darkclass { color: #fff !important; } }"
            "</style></head><body>"
            '<td class="otherclass" style="color: #000;">No match</td>'
            "</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.color_pairs) == 0

    def test_multiple_color_pairs(self):
        html = (
            "<html><head><style>"
            "@media (prefers-color-scheme: dark) { "
            ".a { color: #e0e0e0 !important; } "
            ".b { background-color: #1a1a1a !important; } "
            "}"
            "</style></head><body>"
            '<td class="a" style="color: #333;">Text</td>'
            '<td class="b" style="background-color: #fff;">Bg</td>'
            "</body></html>"
        )
        result = validate_dark_mode(html)
        assert len(result.color_pairs) == 2


# ── Image patterns ──


class TestImagePatterns:
    def test_picture_source_dark_detected(self):
        html = (
            "<html><head></head><body>"
            "<picture>"
            '<source media="(prefers-color-scheme: dark)" srcset="dark-logo.png">'
            '<img src="light-logo.png" alt="Logo">'
            "</picture>"
            "</body></html>"
        )
        result = validate_dark_mode(html)
        assert result.has_image_swap is True

    def test_dark_img_class_detected(self):
        html = "<html><head><style>.dark-img { display: none; }</style></head><body>x</body></html>"
        result = validate_dark_mode(html)
        assert result.has_image_swap is True

    def test_1x1_trick_detected(self):
        html = (
            "<html><head></head><body>"
            '<td style="background-image: url(1x1.png); background-color: #1a1a1a;">'
            "Content</td>"
            "</body></html>"
        )
        result = validate_dark_mode(html)
        assert result.has_1x1_trick is True

    def test_no_image_patterns(self):
        html = "<html><head></head><body><p>No images</p></body></html>"
        result = validate_dark_mode(html)
        assert result.has_image_swap is False
        assert result.has_1x1_trick is False


# ── Full validation ──


class TestValidateDarkMode:
    def test_comprehensive_valid_html(self):
        html = (
            '<!DOCTYPE html><html lang="en"><head>'
            '<meta name="color-scheme" content="light dark">'
            '<meta name="supported-color-schemes" content="light dark">'
            "<style>"
            ":root { color-scheme: light dark; }"
            "@media (prefers-color-scheme: dark) { .x { color: #e0e0e0 !important; } }"
            "[data-ogsc] .x { color: #e0e0e0; }"
            "[data-ogsb] .x { background-color: #1a1a1a; }"
            "</style></head><body>x</body></html>"
        )
        result = validate_dark_mode(html)
        assert result.meta_tags.has_color_scheme is True
        assert result.meta_tags.has_supported_color_schemes is True
        assert result.meta_tags.has_css_color_scheme is True
        assert len(result.media_queries) == 1
        assert len(result.outlook_selectors) == 2

    def test_empty_html_returns_empty_result(self):
        result = validate_dark_mode("")
        assert result.meta_tags.has_color_scheme is False
        assert len(result.media_queries) == 0
        assert len(result.outlook_selectors) == 0

    def test_malformed_html_returns_empty_result(self):
        # lxml is very tolerant, so this still parses; just verify no crash
        result = validate_dark_mode("<<<not html at all>>>")
        assert result is not None
