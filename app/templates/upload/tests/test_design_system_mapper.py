# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false
"""Tests for DesignSystemMapper (Phase 31.2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.ai.templates.models import DefaultTokens
from app.templates.upload.design_system_mapper import DesignSystemMapper


def _make_design_system(
    heading_font: str = "Montserrat, sans-serif",
    body_font: str = "Arial, sans-serif",
    base_size: str = "16px",
) -> MagicMock:
    """Create a mock DesignSystem."""
    ds = MagicMock()
    ds.typography.heading_font = heading_font
    ds.typography.body_font = body_font
    ds.typography.base_size = base_size
    ds.fonts = {}
    ds.font_sizes = {"heading": "28px", "body": "16px"}
    ds.spacing = {"section": "20px"}
    ds.colors = {}
    ds.button_border_radius = "4px"
    # BrandPalette fields for resolve_color_map
    ds.palette.primary = "#0066cc"
    ds.palette.secondary = "#333333"
    ds.palette.accent = "#ff6600"
    ds.palette.background = "#ffffff"
    ds.palette.text = "#333333"
    ds.palette.link = "#0066cc"
    return ds


class TestMapTokensNoDesignSystem:
    def test_returns_tokens_unchanged(self) -> None:
        tokens = DefaultTokens(
            colors={"primary": "#ff0000"},
            fonts={"heading": "Inter, sans-serif"},
            font_sizes={"heading": "32px"},
            spacing={"section": "24px"},
        )
        mapper = DesignSystemMapper(None)
        result = mapper.map_tokens(tokens)
        assert result.fonts == tokens.fonts
        assert result.font_sizes == tokens.font_sizes

    def test_empty_diff(self) -> None:
        tokens = DefaultTokens(fonts={"heading": "Inter, sans-serif"})
        mapper = DesignSystemMapper(None)
        diff = mapper.generate_diff(tokens, mapper.map_tokens(tokens))
        assert diff == []


class TestMapTokensWithDesignSystem:
    def test_font_mapping_will_replace(self) -> None:
        """Extracted Inter + DS Montserrat → diff shows will_replace."""
        ds = _make_design_system(heading_font="Montserrat, sans-serif")
        tokens = DefaultTokens(fonts={"heading": "Inter, sans-serif"})
        mapper = DesignSystemMapper(ds)
        diff = mapper.generate_diff(tokens, mapper.map_tokens(tokens))
        font_diffs = [d for d in diff if d.property == "font-family"]
        assert len(font_diffs) == 1
        assert font_diffs[0].action == "will_replace"
        assert font_diffs[0].imported_value == "Inter, sans-serif"
        assert font_diffs[0].design_system_value == "Montserrat, sans-serif"

    def test_compatible_values(self) -> None:
        """Extracted matches DS → compatible action."""
        ds = _make_design_system(heading_font="Inter, sans-serif")
        tokens = DefaultTokens(fonts={"heading": "Inter, sans-serif"})
        mapper = DesignSystemMapper(ds)
        diff = mapper.generate_diff(tokens, mapper.map_tokens(tokens))
        font_diffs = [d for d in diff if d.property == "font-family"]
        assert len(font_diffs) == 1
        assert font_diffs[0].action == "compatible"

    def test_size_nearest_match(self) -> None:
        """Extracted 32px + DS heading=28px → nearest match with will_replace."""
        ds = _make_design_system()
        tokens = DefaultTokens(font_sizes={"heading": "32px"})
        mapper = DesignSystemMapper(ds)
        diff = mapper.generate_diff(tokens, mapper.map_tokens(tokens))
        size_diffs = [d for d in diff if d.property == "font-size"]
        assert len(size_diffs) == 1
        assert size_diffs[0].action == "will_replace"
        assert size_diffs[0].design_system_value == "28px"

    def test_no_override_when_ds_lacks_role(self) -> None:
        """No DS value for a role → no_override."""
        ds = _make_design_system()
        tokens = DefaultTokens(fonts={"custom_role": "Georgia, serif"})
        mapper = DesignSystemMapper(ds)
        diff = mapper.generate_diff(tokens, mapper.map_tokens(tokens))
        font_diffs = [d for d in diff if d.role == "custom_role"]
        assert len(font_diffs) == 1
        assert font_diffs[0].action == "no_override"


class TestNewFieldMapping:
    def test_font_weights_passed_through(self) -> None:
        """font_weights preserved through map_tokens."""
        tokens = DefaultTokens(font_weights={"heading": "700", "body": "400"})
        mapper = DesignSystemMapper(None)
        result = mapper.map_tokens(tokens)
        assert result.font_weights == {"heading": "700", "body": "400"}

    def test_line_heights_passed_through(self) -> None:
        tokens = DefaultTokens(line_heights={"heading": "40px"})
        mapper = DesignSystemMapper(None)
        result = mapper.map_tokens(tokens)
        assert result.line_heights == {"heading": "40px"}

    def test_responsive_passed_through(self) -> None:
        tokens = DefaultTokens(
            responsive={"mobile_heading_size": "24px"},
            responsive_breakpoints=("600px",),
        )
        mapper = DesignSystemMapper(None)
        result = mapper.map_tokens(tokens)
        assert result.responsive == {"mobile_heading_size": "24px"}
        assert result.responsive_breakpoints == ("600px",)

    def test_diff_includes_new_fields(self) -> None:
        """generate_diff includes font-weight and line-height rows."""
        ds = _make_design_system()
        tokens = DefaultTokens(
            font_weights={"heading": "700"},
            line_heights={"body": "26px"},
            letter_spacings={"heading": "0.5px"},
        )
        mapper = DesignSystemMapper(ds)
        diff = mapper.generate_diff(tokens, mapper.map_tokens(tokens))
        properties = {d.property for d in diff}
        assert "font-weight" in properties
        assert "line-height" in properties
        assert "letter-spacing" in properties
