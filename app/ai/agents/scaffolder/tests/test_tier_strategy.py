"""Tests for 24B.3 — Progressive Enhancement Assembly."""

from __future__ import annotations

from typing import Literal

from app.ai.agents.scaffolder.assembler import TemplateAssembler
from app.ai.agents.schemas.build_plan import (
    DesignTokens,
    EmailBuildPlan,
    SlotFill,
    TemplateSelection,
)


def _make_plan(tier_strategy: Literal["universal", "progressive"] = "universal") -> EmailBuildPlan:
    """Create a minimal EmailBuildPlan for testing."""
    return EmailBuildPlan(
        template=TemplateSelection(
            template_name="test_template",
            reasoning="test",
        ),
        slot_fills=(SlotFill(slot_id="body", content="Hello"),),
        design_tokens=DesignTokens(),
        tier_strategy=tier_strategy,
    )


class TestUniversalPassthrough:
    """Universal strategy should not change HTML."""

    def test_no_change(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        html = '<table><tr data-section="hero"><td style="padding: 20px;">Hello</td></tr></table>'
        plan = _make_plan("universal")
        result = assembler._apply_tier_strategy(html, plan)
        assert result == html


class TestProgressiveWrapping:
    """Progressive strategy wraps flexbox in MSO conditionals."""

    def test_wraps_flexbox_in_mso(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        html = '<div data-section="hero" style="display: flex;">Content</div>'
        plan = _make_plan("progressive")
        result = assembler._apply_tier_strategy(html, plan)
        assert "<!--[if !mso]><!-->" in result
        assert "<!--[if mso]>" in result
        assert "display: block" in result

    def test_wraps_grid_in_mso(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        html = '<div data-section="grid" style="display: grid; gap: 10px;">Content</div>'
        plan = _make_plan("progressive")
        result = assembler._apply_tier_strategy(html, plan)
        assert "<!--[if !mso]><!-->" in result


class TestWordFallback:
    """Word engine fallback generation."""

    def test_strips_border_radius(self) -> None:
        html = '<td style="border-radius: 8px; padding: 10px;">Hello</td>'
        result = TemplateAssembler._generate_word_fallback(html)
        assert "border-radius" not in result
        assert "padding" in result

    def test_replaces_flex_with_block(self) -> None:
        html = '<div style="display: flex;">Content</div>'
        result = TemplateAssembler._generate_word_fallback(html)
        assert "display: block" in result
        assert "display: flex" not in result


class TestMSOConditionalWrapping:
    """MSO conditional comment wrapping."""

    def test_wraps_correctly(self) -> None:
        enhanced = '<div style="display: flex;">Modern</div>'
        fallback = '<div style="display: block;">Fallback</div>'
        result = TemplateAssembler._wrap_mso_conditional(enhanced, fallback)
        assert "<!--[if !mso]><!-->" in result
        assert "<!--<![endif]-->" in result
        assert "<!--[if mso]>" in result
        assert "<![endif]-->" in result
        assert "Modern" in result
        assert "Fallback" in result


class TestTableOnlyStaysUniversal:
    """Table-only template should stay universal."""

    def test_no_modern_css_stays_universal(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        html = '<table><tr data-section="body"><td style="padding: 20px; color: #333;">Hello</td></tr></table>'
        plan = _make_plan("progressive")
        result = assembler._apply_tier_strategy(html, plan)
        # No modern CSS detected, so no MSO wrapping even with progressive strategy
        assert "<!--[if !mso]><!-->" not in result
