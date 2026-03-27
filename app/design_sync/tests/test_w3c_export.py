"""Tests for W3C Design Tokens v1.0 exporter."""

from __future__ import annotations

from app.design_sync.protocol import (
    ExtractedColor,
    ExtractedGradient,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)
from app.design_sync.w3c_export import export_w3c_tokens


class TestExportColors:
    """Color export tests."""

    def test_opaque_color(self) -> None:
        tokens = ExtractedTokens(colors=[ExtractedColor(name="primary", hex="#FF0000")])
        result = export_w3c_tokens(tokens)
        assert result["color"]["primary"]["$value"] == "#FF0000"
        assert result["color"]["$type"] == "color"

    def test_transparent_color(self) -> None:
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="overlay", hex="#000000", opacity=0.5)]
        )
        result = export_w3c_tokens(tokens)
        value = result["color"]["overlay"]["$value"]
        assert value == "#00000080"

    def test_dark_colors_in_extensions(self) -> None:
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="bg", hex="#FFFFFF")],
            dark_colors=[ExtractedColor(name="bg", hex="#1A1A1A")],
        )
        result = export_w3c_tokens(tokens)
        dark = result["color"]["$extensions"]["mode"]["dark"]
        assert dark["bg"]["$value"] == "#1A1A1A"


class TestExportTypography:
    """Typography export tests."""

    def test_full_typography(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="heading",
                    family="Inter",
                    weight="700",
                    size=24.0,
                    line_height=32.0,
                    letter_spacing=0.5,
                )
            ]
        )
        result = export_w3c_tokens(tokens)
        heading = result["typography"]["heading"]
        assert heading["family"]["$type"] == "fontFamily"
        assert heading["family"]["$value"] == "Inter"
        assert heading["weight"]["$value"] == 700
        assert heading["size"]["$value"] == "24.0px"
        assert heading["lineHeight"]["$value"] == "32.0px"
        assert heading["letterSpacing"]["$value"] == "0.5px"

    def test_typography_no_letter_spacing(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="body", family="Arial", weight="400", size=16.0, line_height=24.0
                )
            ]
        )
        result = export_w3c_tokens(tokens)
        assert "letterSpacing" not in result["typography"]["body"]


class TestExportSpacing:
    """Spacing export tests."""

    def test_spacing_px(self) -> None:
        tokens = ExtractedTokens(
            spacing=[
                ExtractedSpacing(name="sm", value=8.0),
                ExtractedSpacing(name="md", value=16.0),
            ]
        )
        result = export_w3c_tokens(tokens)
        assert result["spacing"]["sm"]["$value"] == "8.0px"
        assert result["spacing"]["$type"] == "dimension"


class TestExportGradients:
    """Gradient export tests."""

    def test_gradient(self) -> None:
        tokens = ExtractedTokens(
            gradients=[
                ExtractedGradient(
                    name="hero",
                    type="linear",
                    angle=90.0,
                    stops=(("#FF0000", 0.0), ("#0000FF", 1.0)),
                    fallback_hex="#880088",
                )
            ]
        )
        result = export_w3c_tokens(tokens)
        grad = result["gradient"]["hero"]["$value"]
        assert grad["type"] == "linear"
        assert grad["angle"] == 90.0
        assert len(grad["stops"]) == 2


class TestExportEmpty:
    """Empty tokens handling."""

    def test_empty_tokens(self) -> None:
        result = export_w3c_tokens(ExtractedTokens())
        assert result == {}

    def test_only_colors(self) -> None:
        tokens = ExtractedTokens(colors=[ExtractedColor(name="x", hex="#AABBCC")])
        result = export_w3c_tokens(tokens)
        assert "color" in result
        assert "typography" not in result
        assert "spacing" not in result
