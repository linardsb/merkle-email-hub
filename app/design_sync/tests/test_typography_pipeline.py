# pyright: reportPrivateUsage=false
"""Tests for typography pipeline: font stacks, convert_typography, weight mapping (Phase 33.11 — Step 4, 38.8)."""

from __future__ import annotations

from app.design_sync.converter import _font_stack, convert_typography, node_to_email_html
from app.design_sync.protocol import DesignNode, DesignNodeType, ExtractedTypography
from app.design_sync.render_context import RenderContext


class TestFontStack:
    """Tests for _font_stack() email-safe font fallback chains."""

    def test_inter_font_stack(self) -> None:
        """Inter → YAML-mapped fallback chain."""
        result = _font_stack("Inter")
        assert result == "Inter, Arial, Helvetica, sans-serif"

    def test_playfair_font_stack(self) -> None:
        """Playfair Display → serif chain from YAML."""
        result = _font_stack("Playfair Display")
        assert "Georgia" in result
        assert "Times New Roman" in result
        assert "serif" in result
        assert result.startswith("Playfair Display")

    def test_unknown_font_default(self) -> None:
        """Unknown font → default sans-serif chain."""
        result = _font_stack("Unknown Custom Font")
        assert result == "Unknown Custom Font, Arial, Helvetica, sans-serif"

    def test_montserrat_font_stack(self) -> None:
        """Montserrat → Verdana chain from YAML."""
        result = _font_stack("Montserrat")
        assert "Verdana" in result
        assert "sans-serif" in result

    def test_already_has_comma_passthrough(self) -> None:
        """Font string with commas → returned as-is."""
        assert _font_stack("Inter, Arial") == "Inter, Arial"

    def test_generic_keyword(self) -> None:
        """Generic CSS keyword → returned as-is."""
        assert _font_stack("sans-serif") == "sans-serif"
        assert _font_stack("serif") == "serif"

    def test_case_insensitive_lookup(self) -> None:
        """Font lookup is case-insensitive."""
        result = _font_stack("inter")
        assert "Arial" in result
        assert result.startswith("inter")


class TestConvertTypography:
    """Tests for convert_typography() mapping extracted styles to Typography model."""

    def test_single_style(self) -> None:
        """Single typography style → used as both heading and body."""
        styles = [
            ExtractedTypography(
                name="Body", family="Inter", weight="400", size=16.0, line_height=24.0
            ),
        ]
        typo = convert_typography(styles)
        assert "Inter" in typo.heading_font
        assert "Inter" in typo.body_font
        assert typo.base_size == "16px"

    def test_heading_body_separation(self) -> None:
        """Largest size → heading, smallest → body."""
        styles = [
            ExtractedTypography(
                name="H1", family="Inter", weight="700", size=32.0, line_height=40.0
            ),
            ExtractedTypography(
                name="Body", family="Inter", weight="400", size=16.0, line_height=24.0
            ),
        ]
        typo = convert_typography(styles)
        assert typo.base_size == "16px"
        assert typo.heading_line_height == "40px"
        assert typo.body_line_height == "24px"

    def test_line_height_rounding(self) -> None:
        """Fractional line height → rounded to nearest int px."""
        styles = [
            ExtractedTypography(
                name="H1", family="Inter", weight="700", size=24.0, line_height=28.8
            ),
        ]
        typo = convert_typography(styles)
        assert typo.heading_line_height == "29px"

    def test_letter_spacing_preserved(self) -> None:
        """Letter spacing from Figma → preserved in Typography model."""
        styles = [
            ExtractedTypography(
                name="H1",
                family="Inter",
                weight="700",
                size=32.0,
                line_height=40.0,
                letter_spacing=-0.5,
            ),
        ]
        typo = convert_typography(styles)
        assert typo.heading_letter_spacing == "-0.5px"

    def test_zero_letter_spacing_omitted(self) -> None:
        """Zero letter spacing → None (omitted)."""
        styles = [
            ExtractedTypography(
                name="H1",
                family="Inter",
                weight="700",
                size=32.0,
                line_height=40.0,
                letter_spacing=0.0,
            ),
        ]
        typo = convert_typography(styles)
        assert typo.heading_letter_spacing is None

    def test_text_transform_preserved(self) -> None:
        """Text transform from Figma → preserved in Typography model."""
        styles = [
            ExtractedTypography(
                name="Heading",
                family="Inter",
                weight="700",
                size=32.0,
                line_height=40.0,
                text_transform="uppercase",
            ),
        ]
        typo = convert_typography(styles)
        assert typo.heading_text_transform == "uppercase"

    def test_empty_styles_returns_defaults(self) -> None:
        """Empty styles list → default Typography."""
        typo = convert_typography([])
        assert typo.heading_font is not None  # has defaults

    def test_name_matching_heading_keyword(self) -> None:
        """Style named 'Heading' selected over larger unnamed style."""
        styles = [
            ExtractedTypography(
                name="Extra Large", family="Inter", weight="700", size=64.0, line_height=72.0
            ),
            ExtractedTypography(
                name="Heading", family="Inter", weight="600", size=32.0, line_height=40.0
            ),
            ExtractedTypography(
                name="Body", family="Inter", weight="400", size=16.0, line_height=24.0
            ),
        ]
        typo = convert_typography(styles)
        # "Heading" keyword takes priority over largest font size
        assert typo.heading_line_height == "40px"


class TestFontPreservation:
    """38.8: Font family from Figma preserved through converter pipeline."""

    def test_helvetica_font_stack(self) -> None:
        """Helvetica → includes Helvetica in stack with proper fallbacks."""
        result = _font_stack("Helvetica")
        assert "Helvetica" in result
        assert "sans-serif" in result

    def test_font_family_preserved_through_converter(self) -> None:
        """DesignNode with font_family → font-family in output HTML."""
        node = DesignNode(
            id="t1",
            name="Heading",
            type=DesignNodeType.TEXT,
            text_content="Hello World",
            font_family="Helvetica",
            font_size=24.0,
        )
        html = node_to_email_html(node, RenderContext.from_legacy_kwargs(body_font_size=16.0))
        assert "Helvetica" in html
        assert "font-family:" in html
