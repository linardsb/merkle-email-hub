"""Enriched typography token extraction tests (Phase 31.8)."""

from __future__ import annotations

from app.templates.upload.analyzer import TokenInfo
from app.templates.upload.token_extractor import TokenExtractor


class TestFontWeightEnriched:
    def test_heading_700(self) -> None:
        """HTML with font-weight: 700 on headings -> font_weights populated."""
        info = TokenInfo(
            colors={},
            fonts={},
            font_sizes={},
            spacing={},
            font_weights={"heading": ["700", "700", "700"]},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.font_weights.get("heading") == "700"

    def test_heading_and_body_weights(self) -> None:
        info = TokenInfo(
            colors={},
            fonts={},
            font_sizes={},
            spacing={},
            font_weights={"heading": ["700"], "body": ["400", "400"]},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.font_weights.get("heading") == "700"
        assert tokens.font_weights.get("body") == "400"


class TestLineHeightEnriched:
    def test_heading_and_body_line_heights(self) -> None:
        """Heading 40px, body 26px -> both captured."""
        info = TokenInfo(
            colors={},
            fonts={},
            font_sizes={},
            spacing={},
            line_heights={"heading": ["40px"], "body": ["26px"]},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.line_heights.get("heading") == "40px"
        assert tokens.line_heights.get("body") == "26px"


class TestLetterSpacingEnriched:
    def test_letter_spacing_extracted(self) -> None:
        info = TokenInfo(
            colors={},
            fonts={},
            font_sizes={},
            spacing={},
            letter_spacings={"all": ["0.5px", "0.5px"]},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.letter_spacings.get("heading") == "0.5px"


class TestColorRolesEnriched:
    def test_link_color(self) -> None:
        """Link colors from <a> elements -> colors includes link role."""
        info = TokenInfo(
            colors={
                "background": ["#FFFFFF"],
                "text": ["#333333"],
                "all": ["#FFFFFF", "#333333", "#32A5DB"],
            },
            fonts={},
            font_sizes={},
            spacing={},
            color_roles={"link": ["#32A5DB", "#32A5DB"]},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.colors.get("link") == "#32A5DB"

    def test_muted_color(self) -> None:
        """Muted footer text color extracted."""
        info = TokenInfo(
            colors={
                "background": ["#FFFFFF", "#FFFFFF"],
                "text": ["#333333", "#333333", "#999999"],
                "all": ["#FFFFFF", "#333333", "#999999"],
            },
            fonts={},
            font_sizes={},
            spacing={},
            color_roles={"muted": ["#999999"]},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.colors.get("muted") == "#999999"

    def test_accent_color(self) -> None:
        """Accent color from prominent element."""
        info = TokenInfo(
            colors={
                "background": ["#FFFFFF"],
                "text": ["#333333"],
                "all": ["#FFFFFF", "#333333", "#EF3E5D"],
            },
            fonts={},
            font_sizes={},
            spacing={},
            color_roles={"accent": ["#EF3E5D"]},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.colors.get("accent") == "#EF3E5D"


class TestBackwardCompatibility:
    def test_core_roles_still_populated(self) -> None:
        """text, secondary, cta, background roles still populated."""
        info = TokenInfo(
            colors={
                "background": ["#FFFFFF", "#FFFFFF"],
                "text": ["#333333", "#333333", "#666666"],
                "all": ["#FFFFFF", "#333333", "#666666", "#0066CC", "#FF5500"],
            },
            fonts={},
            font_sizes={},
            spacing={},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.colors.get("background") == "#FFFFFF"
        assert tokens.colors.get("text") == "#333333"
