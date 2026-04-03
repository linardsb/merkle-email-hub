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
