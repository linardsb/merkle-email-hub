"""Tests for W3C Design Tokens v1.0 parser."""

from __future__ import annotations

import pytest

from app.design_sync.exceptions import W3cTokenParseError
from app.design_sync.w3c_tokens import W3cParseResult, parse_w3c_tokens


class TestParseW3cColors:
    """Color token parsing."""

    def test_hex_color(self) -> None:
        result = parse_w3c_tokens({"primary": {"$type": "color", "$value": "#ff0000"}})
        assert len(result.tokens.colors) == 1
        assert result.tokens.colors[0].name == "primary"
        assert result.tokens.colors[0].hex == "#FF0000"

    def test_short_hex_expanded(self) -> None:
        result = parse_w3c_tokens({"accent": {"$type": "color", "$value": "#f00"}})
        assert result.tokens.colors[0].hex == "#FF0000"

    def test_hex8_with_alpha(self) -> None:
        result = parse_w3c_tokens({"overlay": {"$type": "color", "$value": "#FF000080"}})
        color = result.tokens.colors[0]
        assert color.hex == "#FF0000"
        assert 0.49 < color.opacity < 0.51  # 128/255 ≈ 0.502

    def test_rgba_color(self) -> None:
        result = parse_w3c_tokens({"bg": {"$type": "color", "$value": "rgba(255, 128, 0, 0.5)"}})
        color = result.tokens.colors[0]
        assert color.hex == "#FF8000"
        assert color.opacity == 0.5

    def test_rgb_no_alpha(self) -> None:
        result = parse_w3c_tokens({"text": {"$type": "color", "$value": "rgb(0, 128, 255)"}})
        assert result.tokens.colors[0].opacity == 1.0

    def test_multiple_colors(self) -> None:
        result = parse_w3c_tokens(
            {
                "color": {
                    "$type": "color",
                    "primary": {"$value": "#ff0000"},
                    "secondary": {"$value": "#00ff00"},
                    "tertiary": {"$value": "#0000ff"},
                    "neutral": {"$value": "#888888"},
                    "accent": {"$value": "#ff8800"},
                }
            }
        )
        assert len(result.tokens.colors) == 5


class TestParseW3cTypography:
    """Font token parsing."""

    def test_font_family_group(self) -> None:
        result = parse_w3c_tokens(
            {
                "heading": {
                    "family": {"$type": "fontFamily", "$value": "Inter, sans-serif"},
                    "weight": {"$type": "fontWeight", "$value": 700},
                    "size": {"$type": "fontSize", "$value": "24px"},
                }
            }
        )
        assert len(result.tokens.typography) == 1
        typo = result.tokens.typography[0]
        assert typo.family == "Inter, sans-serif"
        assert typo.weight == "700"
        assert typo.size == 24.0

    def test_font_defaults(self) -> None:
        """Font group with only family should still produce typography."""
        result = parse_w3c_tokens(
            {
                "body": {
                    "family": {"$type": "fontFamily", "$value": "Arial"},
                }
            }
        )
        assert len(result.tokens.typography) == 1
        typo = result.tokens.typography[0]
        assert typo.weight == "400"
        assert typo.size == 16.0

    def test_font_rem_size(self) -> None:
        result = parse_w3c_tokens(
            {
                "title": {
                    "family": {"$type": "fontFamily", "$value": "Georgia"},
                    "size": {"$type": "fontSize", "$value": "2rem"},
                }
            }
        )
        assert result.tokens.typography[0].size == 32.0


class TestParseW3cSpacing:
    """Dimension/spacing token parsing."""

    def test_px_dimension(self) -> None:
        result = parse_w3c_tokens({"sm": {"$type": "dimension", "$value": "8px"}})
        assert len(result.tokens.spacing) == 1
        assert result.tokens.spacing[0].value == 8.0

    def test_rem_dimension(self) -> None:
        result = parse_w3c_tokens({"md": {"$type": "dimension", "$value": "1rem"}})
        assert result.tokens.spacing[0].value == 16.0

    def test_numeric_dimension(self) -> None:
        result = parse_w3c_tokens({"gap": {"$type": "dimension", "$value": 12}})
        assert result.tokens.spacing[0].value == 12.0


class TestParseW3cGradients:
    """Gradient token parsing."""

    def test_linear_gradient(self) -> None:
        result = parse_w3c_tokens(
            {
                "hero_bg": {
                    "$type": "gradient",
                    "$value": {
                        "type": "linear",
                        "angle": 90,
                        "stops": [
                            {"color": "#ff0000", "position": 0.0},
                            {"color": "#0000ff", "position": 1.0},
                        ],
                    },
                }
            }
        )
        assert len(result.tokens.gradients) == 1
        grad = result.tokens.gradients[0]
        assert grad.type == "linear"
        assert grad.angle == 90.0
        assert len(grad.stops) == 2


class TestAliasResolution:
    """Alias / reference resolution."""

    def test_simple_alias(self) -> None:
        result = parse_w3c_tokens(
            {
                "color": {
                    "$type": "color",
                    "primary": {"$value": "#ff0000"},
                    "accent": {"$value": "{color.primary}"},
                }
            }
        )
        assert len(result.tokens.colors) == 2
        assert result.tokens.colors[1].hex == "#FF0000"

    def test_nested_alias(self) -> None:
        result = parse_w3c_tokens(
            {
                "color": {
                    "$type": "color",
                    "base": {"$value": "#00ff00"},
                    "mid": {"$value": "{color.base}"},
                    "top": {"$value": "{color.mid}"},
                }
            }
        )
        assert len(result.tokens.colors) == 3
        assert result.tokens.colors[2].hex == "#00FF00"

    def test_circular_alias_warning(self) -> None:
        result = parse_w3c_tokens(
            {
                "color": {
                    "$type": "color",
                    "a": {"$value": "{color.b}"},
                    "b": {"$value": "{color.a}"},
                }
            }
        )
        assert len(result.tokens.colors) == 0
        assert any("Circular alias" in w.message for w in result.warnings)

    def test_missing_alias_target(self) -> None:
        result = parse_w3c_tokens({"x": {"$type": "color", "$value": "{nonexistent.path}"}})
        assert len(result.tokens.colors) == 0
        assert any("not found" in w.message for w in result.warnings)


class TestTypeInheritance:
    """$type inherited from parent groups."""

    def test_inherited_type(self) -> None:
        result = parse_w3c_tokens(
            {
                "spacing": {
                    "$type": "dimension",
                    "sm": {"$value": "4px"},
                    "md": {"$value": "8px"},
                    "lg": {"$value": "16px"},
                }
            }
        )
        assert len(result.tokens.spacing) == 3


class TestDarkMode:
    """$extensions.mode.dark parsing."""

    def test_dark_mode_colors(self) -> None:
        result = parse_w3c_tokens(
            {
                "color": {
                    "$type": "color",
                    "bg": {"$value": "#ffffff"},
                    "$extensions": {
                        "mode": {
                            "dark": {
                                "bg": {"$type": "color", "$value": "#1a1a1a"},
                            }
                        }
                    },
                }
            }
        )
        assert len(result.tokens.colors) == 1
        assert len(result.tokens.dark_colors) == 1
        assert result.tokens.dark_colors[0].hex == "#1A1A1A"


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_input(self) -> None:
        result = parse_w3c_tokens({})
        assert isinstance(result, W3cParseResult)
        assert len(result.tokens.colors) == 0
        assert len(result.tokens.typography) == 0

    def test_unknown_type_warning(self) -> None:
        with pytest.raises(W3cTokenParseError, match="Unknown \\$type"):
            parse_w3c_tokens({"x": {"$type": "invented_type", "$value": "test"}})

    def test_composite_type_skipped(self) -> None:
        result = parse_w3c_tokens(
            {
                "card": {"$type": "shadow", "$value": {"x": 0, "y": 2, "blur": 4}},
                "primary": {"$type": "color", "$value": "#ff0000"},
            }
        )
        assert len(result.tokens.colors) == 1
        assert any("shadow" in w.message and "skipped" in w.message for w in result.warnings)

    def test_ignored_types_no_warning(self) -> None:
        result = parse_w3c_tokens(
            {
                "fast": {"$type": "duration", "$value": "200ms"},
                "ease": {"$type": "cubicBezier", "$value": [0.4, 0, 0.2, 1]},
            }
        )
        assert len(result.warnings) == 0

    def test_nesting_depth_validation(self) -> None:
        """Deeply nested JSON should raise W3cTokenParseError."""
        deeply_nested: dict = {"$type": "color"}
        current = deeply_nested
        for i in range(25):
            child: dict = {"$type": "color"} if i < 24 else {"$type": "color", "$value": "#fff"}
            current[f"level{i}"] = child
            current = child

        with pytest.raises(W3cTokenParseError, match="Nesting depth"):
            parse_w3c_tokens(deeply_nested)

    def test_round_trip(self) -> None:
        """parse → export → parse should preserve token data."""
        from app.design_sync.w3c_export import export_w3c_tokens

        input_json: dict = {
            "color": {
                "$type": "color",
                "red": {"$value": "#FF0000"},
                "green": {"$value": "#00FF00"},
            },
            "spacing": {
                "$type": "dimension",
                "sm": {"$value": "8px"},
                "md": {"$value": "16px"},
            },
        }

        result1 = parse_w3c_tokens(input_json)
        exported = export_w3c_tokens(result1.tokens)
        result2 = parse_w3c_tokens(exported)

        assert len(result2.tokens.colors) == len(result1.tokens.colors)
        assert len(result2.tokens.spacing) == len(result1.tokens.spacing)

        colors1 = {c.name: c.hex for c in result1.tokens.colors}
        colors2 = {c.name: c.hex for c in result2.tokens.colors}
        assert colors1 == colors2
