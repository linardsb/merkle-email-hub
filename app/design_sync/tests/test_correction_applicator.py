"""Tests for deterministic correction applicator (Phase 47.3)."""

from __future__ import annotations

from typing import Any

from app.design_sync.correction_applicator import apply_corrections
from app.design_sync.visual_verify import SectionCorrection

_HTML = (
    "<html><body>"
    "<!-- section:hero_1 -->"
    '<table><tr><td style="color:#333; padding:16px;">'
    '<h1 style="font-size:28px;">Shop Now</h1>'
    "</td></tr></table>"
    "<!-- section:footer_2 -->"
    '<table><tr><td style="background-color:#fff;">'
    '<img src="logo.png" width="600" height="100">'
    "</td></tr></table>"
    "</body></html>"
)


def _make_correction(**overrides: Any) -> SectionCorrection:
    defaults: dict[str, Any] = {
        "node_id": "hero_1",
        "section_idx": 0,
        "correction_type": "color",
        "css_selector": "td",
        "css_property": "color",
        "current_value": "#333",
        "correct_value": "#2D2D2D",
        "confidence": 0.9,
        "reasoning": "test",
    }
    defaults.update(overrides)
    return SectionCorrection(**defaults)


class TestStyleCorrections:
    def test_color_correction(self) -> None:
        corr = _make_correction()
        result = apply_corrections(_HTML, [corr])

        assert len(result.applied) == 1
        assert len(result.skipped) == 0
        assert "color: #2D2D2D" in result.html
        assert "color:#333" not in result.html

    def test_background_color_correction(self) -> None:
        corr = _make_correction(
            node_id="footer_2",
            css_property="background-color",
            current_value="#fff",
            correct_value="#F5F5F5",
        )
        result = apply_corrections(_HTML, [corr])

        assert len(result.applied) == 1
        assert "#F5F5F5" in result.html

    def test_font_size_correction(self) -> None:
        corr = _make_correction(
            correction_type="font",
            css_selector="h1",
            css_property="font-size",
            current_value="28px",
            correct_value="32px",
        )
        result = apply_corrections(_HTML, [corr])

        assert len(result.applied) == 1
        assert "32px" in result.html

    def test_padding_correction(self) -> None:
        corr = _make_correction(
            correction_type="spacing",
            css_property="padding",
            current_value="16px",
            correct_value="24px",
        )
        result = apply_corrections(_HTML, [corr])

        assert len(result.applied) == 1
        assert "24px" in result.html


class TestImageCorrection:
    def test_image_dimension_correction(self) -> None:
        corr = _make_correction(
            node_id="footer_2",
            correction_type="image",
            css_selector="img",
            css_property="width",
            current_value="600",
            correct_value="580",
        )
        result = apply_corrections(_HTML, [corr])

        assert len(result.applied) == 1
        assert 'width="580"' in result.html


class TestContentCorrection:
    def test_content_correction(self) -> None:
        corr = _make_correction(
            correction_type="content",
            css_selector="h1",
            css_property="text",
            current_value="Shop Now",
            correct_value="Buy Now",
        )
        result = apply_corrections(_HTML, [corr])

        assert len(result.applied) == 1
        assert "Buy Now" in result.html
        assert "Shop Now" not in result.html


class TestSectionIsolation:
    def test_section_isolation(self) -> None:
        """Correction targets hero section; footer section stays unchanged."""
        corr = _make_correction()
        result = apply_corrections(_HTML, [corr])

        # Footer section should retain original background-color
        assert "background-color:#fff" in result.html or "background-color: #fff" in result.html


class TestOrdering:
    def test_multiple_corrections_ordered(self) -> None:
        """Two corrections applied in sequence, both visible in output."""
        corr1 = _make_correction()  # color:#333 -> #2D2D2D
        corr2 = _make_correction(
            correction_type="spacing",
            css_property="padding",
            current_value="16px",
            correct_value="24px",
        )
        result = apply_corrections(_HTML, [corr1, corr2])

        assert len(result.applied) == 2
        assert "#2D2D2D" in result.html
        assert "24px" in result.html


class TestSkipping:
    def test_low_confidence_skipped(self) -> None:
        corr = _make_correction(confidence=0.3)
        result = apply_corrections(_HTML, [corr], confidence_threshold=0.5)

        assert len(result.applied) == 0
        assert len(result.skipped) == 1
        # Original value unchanged
        assert "color:#333" in result.html or "color: #333" in result.html

    def test_missing_section_skipped(self) -> None:
        corr = _make_correction(node_id="nonexistent_99")
        result = apply_corrections(_HTML, [corr])

        assert len(result.applied) == 0
        assert len(result.skipped) == 1


# ---------------------------------------------------------------------------
# New test classes (47.9)
# ---------------------------------------------------------------------------

_HTML_MULTI = (
    "<html><body>"
    "<!-- section:hero_1 -->"
    '<table><tr><td style="color:#333; padding:16px;"><h1>Title</h1></td></tr></table>'
    "<!-- section:content_2 -->"
    '<table><tr><td style="background-color:#fff; font-size:14px;"><p>Body</p></td></tr></table>'
    "<!-- section:footer_3 -->"
    '<table><tr><td style="color:#666;"><a href="#">Unsubscribe</a></td></tr></table>'
    "</body></html>"
)


class TestLayoutCorrections:
    def test_layout_simple_prop_applied(self) -> None:
        """Layout correction with text-align (in _LAYOUT_SIMPLE_PROPS) -> applied."""
        corr = _make_correction(
            correction_type="layout",
            css_selector="td",
            css_property="text-align",
            current_value="left",
            correct_value="center",
        )
        html = (
            "<html><body>"
            "<!-- section:hero_1 -->"
            '<table><tr><td style="text-align:left; color:#333;">Test</td></tr></table>'
            "</body></html>"
        )
        result = apply_corrections(html, [corr])
        assert len(result.applied) == 1
        assert "text-align: center" in result.html

    def test_layout_complex_skipped(self) -> None:
        """Layout correction with display (not in _LAYOUT_SIMPLE_PROPS) -> skipped."""
        corr = _make_correction(
            correction_type="layout",
            css_selector="td",
            css_property="display",
            current_value="block",
            correct_value="inline-block",
        )
        result = apply_corrections(_HTML, [corr])
        assert len(result.applied) == 0
        assert len(result.skipped) == 1


class TestCSSSanitization:
    def test_blocks_xss(self) -> None:
        """correct_value that is entirely an unsafe CSS expression -> skipped."""
        corr = _make_correction(
            correct_value="expression(",
        )
        result = apply_corrections(_HTML, [corr])
        assert len(result.applied) == 0
        assert len(result.skipped) == 1

    def test_strips_control_chars(self) -> None:
        """Control chars stripped, clean value still applied."""
        corr = _make_correction(
            correct_value="#2D\x002D2D",
        )
        result = apply_corrections(_HTML, [corr])
        assert len(result.applied) == 1
        assert "#2D2D2D" in result.html


class TestSelectorEdgeCases:
    def test_invalid_selector(self) -> None:
        """Invalid CSS selector -> skipped gracefully."""
        corr = _make_correction(css_selector=">>>invalid")
        result = apply_corrections(_HTML, [corr])
        assert len(result.applied) == 0
        assert len(result.skipped) == 1

    def test_section_prefix_match(self) -> None:
        """Marker '<!-- section:hero_1:content -->' matches node_id 'hero_1'."""
        html = (
            "<html><body>"
            "<!-- section:hero_1:content -->"
            '<table><tr><td style="color:#333;">Text</td></tr></table>'
            "</body></html>"
        )
        corr = _make_correction(node_id="hero_1")
        result = apply_corrections(html, [corr])
        assert len(result.applied) == 1
        assert "#2D2D2D" in result.html

    def test_last_section_extends_to_body(self) -> None:
        """Last section extends to </body>."""
        html = (
            "<html><body>"
            "<!-- section:hero_1 -->"
            '<table><tr><td style="color:#333;">Only section</td></tr></table>'
            "</body></html>"
        )
        corr = _make_correction(node_id="hero_1")
        result = apply_corrections(html, [corr])
        assert len(result.applied) == 1
        assert "#2D2D2D" in result.html


class TestImageCorrectionExtended:
    def test_height_correction(self) -> None:
        """Image height correction -> attribute updated."""
        corr = _make_correction(
            node_id="footer_2",
            correction_type="image",
            css_selector="img",
            css_property="height",
            current_value="100",
            correct_value="120",
        )
        result = apply_corrections(_HTML, [corr])
        assert len(result.applied) == 1
        assert 'height="120"' in result.html

    def test_non_numeric_skipped(self) -> None:
        """Image correct_value='abc' -> skipped (regex strips non-numeric -> empty)."""
        corr = _make_correction(
            node_id="footer_2",
            correction_type="image",
            css_selector="img",
            css_property="width",
            current_value="600",
            correct_value="abc",
        )
        result = apply_corrections(_HTML, [corr])
        assert len(result.applied) == 0
        assert len(result.skipped) == 1

    def test_image_style_sync(self) -> None:
        """img with inline style='width:600px' -> both attr + style updated."""
        html = (
            "<html><body>"
            "<!-- section:footer_2 -->"
            "<table><tr><td>"
            '<img src="logo.png" width="600" style="width:600px">'
            "</td></tr></table>"
            "</body></html>"
        )
        corr = _make_correction(
            node_id="footer_2",
            correction_type="image",
            css_selector="img",
            css_property="width",
            current_value="600",
            correct_value="580",
        )
        result = apply_corrections(html, [corr])
        assert len(result.applied) == 1
        assert 'width="580"' in result.html
        assert "580px" in result.html


class TestContentCorrectionExtended:
    def test_no_text_skipped(self) -> None:
        """Element has text=None and current_value set -> skipped."""
        html = (
            "<html><body>"
            "<!-- section:hero_1 -->"
            "<table><tr><td><h1><span>Inner</span></h1></td></tr></table>"
            "</body></html>"
        )
        corr = _make_correction(
            correction_type="content",
            css_selector="h1",
            css_property="text",
            current_value="Something",
            correct_value="New Text",
        )
        result = apply_corrections(html, [corr])
        assert len(result.applied) == 0
        assert len(result.skipped) == 1


class TestMultipleSections:
    def test_targets_second_section(self) -> None:
        """Two sections, correction targets second -> first unchanged."""
        corr = _make_correction(
            node_id="content_2",
            css_selector="td",
            css_property="background-color",
            current_value="#fff",
            correct_value="#F5F5F5",
        )
        result = apply_corrections(_HTML_MULTI, [corr])
        assert len(result.applied) == 1
        assert "#F5F5F5" in result.html
        # First section color unchanged
        assert "color:#333" in result.html or "color: #333" in result.html
