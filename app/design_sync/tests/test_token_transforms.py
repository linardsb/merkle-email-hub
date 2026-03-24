"""Tests for email-safe token validation and transformation."""

from app.design_sync.protocol import (
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)
from app.design_sync.token_transforms import (
    CSS_NAMED_COLORS,
    validate_and_transform,
)


class TestColorValidation:
    def test_valid_hex_passes_unchanged(self) -> None:
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="Primary", hex="#538FE4", opacity=1.0)]
        )
        result, warnings = validate_and_transform(tokens)
        assert result.colors[0].hex == "#538FE4"
        assert not any(w.field == "colors[Primary].hex" and w.level == "error" for w in warnings)

    def test_3digit_hex_expanded(self) -> None:
        tokens = ExtractedTokens(colors=[ExtractedColor(name="Red", hex="#F00", opacity=1.0)])
        result, warnings = validate_and_transform(tokens)
        assert result.colors[0].hex == "#FF0000"
        assert any(w.fixed_value == "#FF0000" for w in warnings)

    def test_named_color_converted(self) -> None:
        tokens = ExtractedTokens(colors=[ExtractedColor(name="Brand", hex="red", opacity=1.0)])
        result, _ = validate_and_transform(tokens)
        assert result.colors[0].hex == "#FF0000"

    def test_rgba_converted_to_hex(self) -> None:
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="Semi", hex="rgba(0, 0, 255, 0.5)", opacity=1.0)]
        )
        result, warnings = validate_and_transform(tokens)
        assert result.colors[0].hex == "#0000FF"
        assert any(w.level == "warning" for w in warnings)

    def test_hsl_converted_to_hex(self) -> None:
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="Blue", hex="hsl(240, 100%, 50%)", opacity=1.0)]
        )
        result, _ = validate_and_transform(tokens)
        assert result.colors[0].hex == "#0000FF"

    def test_opacity_clamped(self) -> None:
        tokens = ExtractedTokens(colors=[ExtractedColor(name="Over", hex="#000000", opacity=1.5)])
        result, warnings = validate_and_transform(tokens)
        assert result.colors[0].opacity == 1.0
        assert any("clamped" in w.message.lower() for w in warnings)

    def test_transparent_color_warns(self) -> None:
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="Ghost", hex="#FFFFFF", opacity=0.001)]
        )
        _, warnings = validate_and_transform(tokens)
        assert any("transparent" in w.message.lower() for w in warnings)

    def test_unparseable_hex_errors(self) -> None:
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="Bad", hex="not-a-color", opacity=1.0)]
        )
        result, warnings = validate_and_transform(tokens)
        assert any(w.level == "error" for w in warnings)
        assert result.colors[0].hex == "not-a-color"  # kept unchanged

    def test_lowercase_hex_uppercased(self) -> None:
        tokens = ExtractedTokens(colors=[ExtractedColor(name="Low", hex="#abcdef", opacity=1.0)])
        result, _ = validate_and_transform(tokens)
        assert result.colors[0].hex == "#ABCDEF"

    def test_negative_opacity_clamped_to_zero(self) -> None:
        tokens = ExtractedTokens(colors=[ExtractedColor(name="Neg", hex="#000000", opacity=-0.5)])
        result, warnings = validate_and_transform(tokens)
        assert result.colors[0].opacity == 0.0
        assert any("clamped" in w.message.lower() for w in warnings)


class TestTypographyValidation:
    def test_empty_family_defaults_to_arial(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(name="Body", family="", weight="400", size=16, line_height=24)
            ]
        )
        result, warnings = validate_and_transform(tokens)
        assert result.typography[0].family == "Arial"
        assert any("empty" in w.message.lower() for w in warnings)

    def test_negative_size_errors(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="Tiny", family="Inter", weight="400", size=-5, line_height=24
                )
            ]
        )
        _, warnings = validate_and_transform(tokens)
        assert any(w.level == "error" for w in warnings)

    def test_invalid_weight_mapped(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="H1", family="Inter", weight="450", size=32, line_height=40
                )
            ]
        )
        result, _ = validate_and_transform(tokens)
        assert result.typography[0].weight == "400"

    def test_unitless_line_height_converted(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="Body", family="Inter", weight="400", size=16, line_height=1.5
                )
            ]
        )
        result, warnings = validate_and_transform(tokens)
        assert result.typography[0].line_height == 24.0  # 16 * 1.5
        assert any(
            "unitless" in w.message.lower() or "ratio" in w.message.lower() for w in warnings
        )

    def test_valid_typography_unchanged(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="H1", family="Inter", weight="700", size=32, line_height=40
                )
            ]
        )
        result, _ = validate_and_transform(tokens)
        assert result.typography[0].family == "Inter"
        assert result.typography[0].weight == "700"

    def test_bold_keyword_normalized(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="H1", family="Inter", weight="bold", size=32, line_height=40
                )
            ]
        )
        result, _ = validate_and_transform(tokens)
        assert result.typography[0].weight == "700"

    def test_normal_keyword_normalized(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="Body", family="Inter", weight="normal", size=16, line_height=24
                )
            ]
        )
        result, _ = validate_and_transform(tokens)
        assert result.typography[0].weight == "400"

    def test_non_numeric_weight_defaults(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="Body", family="Inter", weight="medium", size=16, line_height=24
                )
            ]
        )
        result, warnings = validate_and_transform(tokens)
        assert result.typography[0].weight == "400"
        assert any("defaulting to 400" in w.message.lower() for w in warnings)

    def test_negative_line_height_defaults(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="Body", family="Inter", weight="400", size=16, line_height=-5
                )
            ]
        )
        result, _ = validate_and_transform(tokens)
        assert result.typography[0].line_height == 24.0  # 16 * 1.5 default


class TestSpacingValidation:
    def test_negative_spacing_errors(self) -> None:
        tokens = ExtractedTokens(spacing=[ExtractedSpacing(name="gap", value=-5)])
        result, warnings = validate_and_transform(tokens)
        assert any(w.level == "error" for w in warnings)
        assert result.spacing[0].value == 0  # clamped to 0

    def test_large_spacing_warns(self) -> None:
        tokens = ExtractedTokens(spacing=[ExtractedSpacing(name="huge", value=600)])
        _, warnings = validate_and_transform(tokens)
        assert any(w.level == "warning" for w in warnings)

    def test_valid_spacing_unchanged(self) -> None:
        tokens = ExtractedTokens(spacing=[ExtractedSpacing(name="md", value=16)])
        result, _ = validate_and_transform(tokens)
        assert result.spacing[0].value == 16


class TestCrossTokenValidation:
    def test_empty_tokens_warns(self) -> None:
        tokens = ExtractedTokens()
        _, warnings = validate_and_transform(tokens)
        assert any("no colors" in w.message.lower() for w in warnings)
        assert any("no typography" in w.message.lower() for w in warnings)

    def test_duplicate_colors_deduped(self) -> None:
        tokens = ExtractedTokens(
            colors=[
                ExtractedColor(name="Primary", hex="#538FE4", opacity=1.0),
                ExtractedColor(name="Primary", hex="#538FE4", opacity=1.0),
            ]
        )
        result, warnings = validate_and_transform(tokens)
        assert len(result.colors) == 1
        assert any("duplicate" in w.message.lower() for w in warnings)

    def test_duplicate_typography_deduped(self) -> None:
        tokens = ExtractedTokens(
            typography=[
                ExtractedTypography(
                    name="Body", family="Inter", weight="400", size=16, line_height=24
                ),
                ExtractedTypography(
                    name="Body", family="Inter", weight="400", size=16, line_height=24
                ),
            ]
        )
        result, _ = validate_and_transform(tokens)
        assert len(result.typography) == 1

    def test_duplicate_spacing_deduped(self) -> None:
        tokens = ExtractedTokens(
            spacing=[
                ExtractedSpacing(name="md", value=16),
                ExtractedSpacing(name="md", value=16),
            ]
        )
        result, _ = validate_and_transform(tokens)
        assert len(result.spacing) == 1


class TestNamedColorMap:
    def test_contains_standard_colors(self) -> None:
        for name in ("red", "blue", "green", "black", "white", "transparent"):
            assert name in CSS_NAMED_COLORS

    def test_all_values_are_valid_hex(self) -> None:
        import re

        hex_re = re.compile(r"^#[0-9A-F]{6}$")
        for name, hex_val in CSS_NAMED_COLORS.items():
            assert hex_re.match(hex_val), f"{name} -> {hex_val} is not valid 6-digit hex"


class TestFullPipeline:
    """Integration: real-ish token sets through the full pipeline."""

    def test_mixed_issues_all_fixed(self) -> None:
        tokens = ExtractedTokens(
            colors=[
                ExtractedColor(name="Primary", hex="#538FE4", opacity=1.0),
                ExtractedColor(name="Accent", hex="#F00", opacity=1.0),
                ExtractedColor(name="Named", hex="red", opacity=1.0),
            ],
            typography=[
                ExtractedTypography(
                    name="H1", family="Inter", weight="700", size=32, line_height=40
                ),
                ExtractedTypography(name="Body", family="", weight="400", size=16, line_height=1.5),
            ],
            spacing=[
                ExtractedSpacing(name="sm", value=8),
                ExtractedSpacing(name="md", value=16),
            ],
        )
        result, warnings = validate_and_transform(tokens)

        # Colors fixed
        assert result.colors[0].hex == "#538FE4"
        assert result.colors[1].hex == "#FF0000"  # expanded
        assert result.colors[2].hex == "#FF0000"  # named -> hex

        # Typography fixed
        assert result.typography[0].family == "Inter"
        assert result.typography[1].family == "Arial"  # empty -> default
        assert result.typography[1].line_height == 24.0  # 16 * 1.5

        # Spacing unchanged
        assert result.spacing[0].value == 8
        assert result.spacing[1].value == 16

        # Warnings emitted
        assert len(warnings) > 0

    def test_stroke_colors_validated(self) -> None:
        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="Fill", hex="#000000", opacity=1.0)],
            stroke_colors=[
                ExtractedColor(name="Border", hex="#f00", opacity=1.0),
                ExtractedColor(name="Border", hex="#f00", opacity=1.0),
            ],
        )
        result, _ = validate_and_transform(tokens)
        # Stroke colors should be expanded and deduped
        assert len(result.stroke_colors) == 1
        assert result.stroke_colors[0].hex == "#FF0000"

    def test_variables_passed_through(self) -> None:
        from app.design_sync.protocol import ExtractedVariable

        tokens = ExtractedTokens(
            colors=[ExtractedColor(name="Fill", hex="#000000", opacity=1.0)],
            variables_source=True,
            modes={"light": "default"},
            variables=[
                ExtractedVariable(
                    name="primary",
                    collection="tokens",
                    type="COLOR",
                    values_by_mode={"default": "#000000"},
                )
            ],
        )
        result, _ = validate_and_transform(tokens)
        assert result.variables_source is True
        assert result.modes == {"light": "default"}
        assert len(result.variables) == 1
        assert result.variables[0].name == "primary"
