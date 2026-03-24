"""Tests for assembler typography/spacing replacement steps (Phase 31.6)."""

from __future__ import annotations

from app.ai.agents.scaffolder.assembler import TemplateAssembler
from app.ai.agents.schemas.build_plan import (
    DesignTokens,
    EmailBuildPlan,
    TemplateSelection,
)
from app.ai.templates.models import (
    DefaultTokens,
    GoldenTemplate,
    TemplateMetadata,
)


def _make_template(html: str, default_tokens: DefaultTokens) -> GoldenTemplate:
    return GoldenTemplate(
        metadata=TemplateMetadata(
            name="test",
            display_name="Test",
            layout_type="newsletter",
            column_count=1,
            has_hero_image=False,
            has_navigation=False,
            has_social_links=False,
            sections=("hero",),
            ideal_for=("test",),
            description="Test template",
        ),
        html=html,
        slots=(),
        default_tokens=default_tokens,
    )


def _make_plan(tokens: DesignTokens) -> EmailBuildPlan:
    return EmailBuildPlan(
        template=TemplateSelection(template_name="test", reasoning="test"),
        slot_fills=(),
        design_tokens=tokens,
    )


class TestFontSizeReplacement:
    def test_heading_size_replaced(self) -> None:
        """font-size: 32px -> 28px when design tokens specify heading=28px."""
        html = '<h1 style="font-size: 32px;">Hello</h1>'
        defaults = DefaultTokens(font_sizes={"heading": "32px"})
        tokens = DesignTokens(font_sizes={"heading": "28px"})
        template = _make_template(html, defaults)

        assembler = TemplateAssembler()
        result = assembler._apply_font_size_replacement(html, template.default_tokens, tokens)  # type: ignore[arg-type]
        assert "font-size: 28px" in result
        assert "32px" not in result

    def test_skipped_when_empty(self) -> None:
        """No replacement when font_sizes empty."""
        html = '<h1 style="font-size: 32px;">Hello</h1>'
        defaults = DefaultTokens()
        tokens = DesignTokens()
        assembler = TemplateAssembler()
        result = assembler._apply_font_size_replacement(html, defaults, tokens)
        assert result == html


class TestLineHeightReplacement:
    def test_line_height_replaced(self) -> None:
        html = '<p style="line-height: 26px;">Text</p>'
        defaults = DefaultTokens(line_heights={"body": "26px"})
        tokens = DesignTokens(line_heights={"body": "24px"})
        assembler = TemplateAssembler()
        result = assembler._apply_line_height_replacement(html, defaults, tokens)
        assert "line-height: 24px" in result


class TestSpacingReplacement:
    def test_padding_replaced(self) -> None:
        html = '<td style="padding-top: 32px;">Content</td>'
        defaults = DefaultTokens(spacing={"section": "32px"})
        tokens = DesignTokens(spacing={"section": "24px"})
        assembler = TemplateAssembler()
        result = assembler._apply_spacing_replacement(html, defaults, tokens)
        assert "padding-top: 24px" in result
        assert "32px" not in result


class TestFontWeightReplacement:
    def test_weight_replaced(self) -> None:
        html = '<h1 style="font-weight: 700;">Bold</h1>'
        defaults = DefaultTokens(font_weights={"heading": "700"})
        tokens = DesignTokens(font_weights={"heading": "600"})
        assembler = TemplateAssembler()
        result = assembler._apply_font_weight_replacement(html, defaults, tokens)
        assert "font-weight: 600" in result
        assert "700" not in result


class TestResponsiveReplacement:
    def test_media_block_updated(self) -> None:
        html = """<style>@media (max-width: 600px) { .heading { font-size: 24px; } }</style>"""
        defaults = DefaultTokens(responsive={"mobile_heading_size": "24px"})
        tokens = DesignTokens(responsive={"mobile_heading_size": "20px"})
        assembler = TemplateAssembler()
        result = assembler._apply_responsive_replacement(html, defaults, tokens)
        assert "font-size: 20px" in result

    def test_skipped_when_no_responsive(self) -> None:
        html = "<style>.foo { color: red; }</style>"
        defaults = DefaultTokens()
        tokens = DesignTokens()
        assembler = TemplateAssembler()
        result = assembler._apply_responsive_replacement(html, defaults, tokens)
        assert result == html


class TestGuardClauses:
    def test_all_steps_skipped_when_no_defaults(self) -> None:
        """All replacement steps are no-ops when DefaultTokens fields are empty."""
        html = '<h1 style="font-size:32px;line-height:40px;font-weight:700;">Hi</h1>'
        defaults = DefaultTokens()
        tokens = DesignTokens()
        assembler = TemplateAssembler()

        assert assembler._apply_font_size_replacement(html, defaults, tokens) == html
        assert assembler._apply_line_height_replacement(html, defaults, tokens) == html
        assert assembler._apply_spacing_replacement(html, defaults, tokens) == html
        assert assembler._apply_font_weight_replacement(html, defaults, tokens) == html
        assert assembler._apply_responsive_replacement(html, defaults, tokens) == html


class TestCSSValueValidation:
    def test_malicious_font_size_rejected(self) -> None:
        """Malformed CSS value is rejected, not injected."""
        html = '<h1 style="font-size: 32px;">Hello</h1>'
        defaults = DefaultTokens(font_sizes={"heading": "32px"})
        tokens = DesignTokens(font_sizes={"heading": "12px; color: red; font-size"})
        assembler = TemplateAssembler()
        result = assembler._apply_font_size_replacement(html, defaults, tokens)
        assert result == html  # no replacement occurred

    def test_malicious_font_weight_rejected(self) -> None:
        html = '<h1 style="font-weight: 700;">Bold</h1>'
        defaults = DefaultTokens(font_weights={"heading": "700"})
        tokens = DesignTokens(font_weights={"heading": "700; display: none"})
        assembler = TemplateAssembler()
        result = assembler._apply_font_weight_replacement(html, defaults, tokens)
        assert result == html

    def test_malicious_spacing_rejected(self) -> None:
        html = '<td style="padding-top: 32px;">X</td>'
        defaults = DefaultTokens(spacing={"section": "32px"})
        tokens = DesignTokens(spacing={"section": "0; display:none"})
        assembler = TemplateAssembler()
        result = assembler._apply_spacing_replacement(html, defaults, tokens)
        assert result == html
