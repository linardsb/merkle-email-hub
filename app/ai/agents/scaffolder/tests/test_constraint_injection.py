"""Tests for design system constraint injection in the scaffolder pipeline."""

from __future__ import annotations

from typing import Any

from app.ai.agents.scaffolder.assembler import TemplateAssembler
from app.ai.agents.schemas.build_plan import DesignTokens
from app.ai.templates.models import DefaultTokens
from app.projects.design_system import (
    BrandPalette,
    DesignSystem,
    FooterConfig,
    LogoConfig,
    Typography,
    resolve_color_map,
    resolve_font_map,
    resolve_font_size_map,
    resolve_spacing_map,
)


def _make_design_system(**overrides: Any) -> DesignSystem:
    """Build a DesignSystem with sensible defaults, overridable."""
    defaults: dict[str, Any] = {
        "palette": BrandPalette(
            primary="#ff0000",
            secondary="#00ff00",
            accent="#0000ff",
            background="#ffffff",
            text="#111111",
        ),
    }
    defaults.update(overrides)
    return DesignSystem(**defaults)


class TestResolveColorMap:
    def test_from_palette_only(self) -> None:
        ds = _make_design_system()
        color_map = resolve_color_map(ds)
        assert color_map["primary"] == "#ff0000"
        assert color_map["secondary"] == "#00ff00"
        assert color_map["accent"] == "#0000ff"
        assert color_map["background"] == "#ffffff"
        assert color_map["text"] == "#111111"

    def test_with_overrides(self) -> None:
        ds = _make_design_system(colors={"primary": "#aaaaaa", "cta": "#bbbbbb"})
        color_map = resolve_color_map(ds)
        assert color_map["primary"] == "#aaaaaa"
        assert color_map["cta"] == "#bbbbbb"

    def test_with_extra_roles(self) -> None:
        ds = _make_design_system(
            colors={"body": "#333333", "muted": "#999999", "surface": "#f5f5f5"}
        )
        color_map = resolve_color_map(ds)
        assert color_map["body"] == "#333333"
        assert color_map["muted"] == "#999999"
        assert color_map["surface"] == "#f5f5f5"
        assert color_map["primary"] == "#ff0000"

    def test_auto_aliases(self) -> None:
        ds = _make_design_system()
        color_map = resolve_color_map(ds)
        assert color_map["cta"] == "#ff0000"
        assert color_map["heading"] == "#111111"
        # link comes from BrandPalette default, not auto-derived from primary
        assert "link" in color_map


class TestResolveMaps:
    def test_font_map(self) -> None:
        ds = _make_design_system(
            typography=Typography(heading_font="Georgia, serif", body_font="Arial, sans-serif"),
        )
        font_map = resolve_font_map(ds)
        assert font_map["heading"] == "Georgia, serif"
        assert font_map["body"] == "Arial, sans-serif"

    def test_font_map_with_overrides(self) -> None:
        ds = _make_design_system(fonts={"heading": "Impact, sans-serif"})
        font_map = resolve_font_map(ds)
        assert font_map["heading"] == "Impact, sans-serif"

    def test_font_size_map(self) -> None:
        ds = _make_design_system()
        size_map = resolve_font_size_map(ds)
        assert size_map["base"] == "16px"

    def test_spacing_map(self) -> None:
        ds = _make_design_system(button_border_radius="8px")
        spacing_map = resolve_spacing_map(ds)
        assert spacing_map["border_radius"] == "8px"


class TestDesignPassFromSystem:
    def test_zero_llm_calls(self) -> None:
        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        ds = _make_design_system()
        tokens = ScaffolderPipeline._design_pass_from_system(ds)
        assert tokens.source == "design_system"
        assert len(tokens.colors) > 0
        assert tokens.colors["primary"] == "#ff0000"

    def test_all_roles_locked(self) -> None:
        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        ds = _make_design_system()
        tokens = ScaffolderPipeline._design_pass_from_system(ds)
        assert len(tokens.locked_roles) == len(tokens.colors)
        for role in tokens.colors:
            assert role in tokens.locked_roles


class TestLockedFills:
    def test_only_existing_slots(self) -> None:
        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        ds = _make_design_system(
            footer=FooterConfig(
                company_name="Acme Inc.",
                legal_text="Copyright 2026",
                address="123 Main St",
            ),
        )
        available = {"footer_company", "footer_legal"}
        locked = ScaffolderPipeline._build_locked_fills(ds, available)
        assert "footer_company" in locked
        assert "footer_legal" in locked
        assert "footer_address" not in locked

    def test_footer_all_fields(self) -> None:
        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        ds = _make_design_system(
            footer=FooterConfig(
                company_name="Acme Inc.",
                legal_text="Copyright 2026",
                address="123 Main St",
                unsubscribe_text="Opt out",
            ),
        )
        available = {"footer_company", "footer_legal", "footer_address", "footer_unsubscribe"}
        locked = ScaffolderPipeline._build_locked_fills(ds, available)
        assert locked["footer_company"].content == "Acme Inc."
        assert locked["footer_legal"].content == "Copyright 2026"
        assert locked["footer_address"].content == "123 Main St"
        assert locked["footer_unsubscribe"].content == "Opt out"

    def test_logo_url_and_alt(self) -> None:
        from app.ai.agents.scaffolder.pipeline import ScaffolderPipeline

        ds = _make_design_system(
            logo=LogoConfig(
                url="https://example.com/logo.png",
                alt_text="Acme Logo",
                width=200,
                height=50,
            ),
        )
        available = {"logo_url", "logo_alt"}
        locked = ScaffolderPipeline._build_locked_fills(ds, available)
        assert locked["logo_url"].content == "https://example.com/logo.png"
        assert locked["logo_alt"].content == "Acme Logo"


class TestPaletteReplacement:
    def test_basic(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        defaults = DefaultTokens(colors={"cta": "#e84e0f", "heading": "#1a1a1a"})
        tokens = DesignTokens(colors={"cta": "#ff0000", "heading": "#002200"})
        html = '<td style="background-color: #e84e0f;"><h1 style="color: #1a1a1a;">Hi</h1></td>'
        result = assembler._apply_palette_replacement(html, defaults, tokens)
        assert "#ff0000" in result
        assert "#002200" in result
        assert "#e84e0f" not in result
        assert "#1a1a1a" not in result

    def test_case_insensitive(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        defaults = DefaultTokens(colors={"cta": "#e84e0f"})
        tokens = DesignTokens(colors={"cta": "#ff0000"})
        html = '<td style="background-color: #E84E0F;">'
        result = assembler._apply_palette_replacement(html, defaults, tokens)
        assert "#ff0000" in result
        assert "#E84E0F" not in result

    def test_preserves_unmatched(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        defaults = DefaultTokens(colors={"cta": "#e84e0f"})
        tokens = DesignTokens(colors={"heading": "#002200"})
        html = '<td style="background-color: #e84e0f;">'
        result = assembler._apply_palette_replacement(html, defaults, tokens)
        assert "#e84e0f" in result


class TestFontReplacement:
    def test_font_stack_replaced(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        defaults = DefaultTokens(
            fonts={"body": "Arial, sans-serif"},
            font_sizes={"base": "16px"},
            spacing={"border_radius": "4px"},
        )
        tokens = DesignTokens(
            fonts={"body": "Georgia, serif"},
            font_sizes={"base": "18px"},
            spacing={"border_radius": "8px"},
        )
        html = '<p style="font-family: Arial, sans-serif; font-size: 16px; border-radius: 4px;">'
        result = assembler._apply_font_replacement(html, defaults, tokens)
        assert "Georgia, serif" in result
        assert "font-size: 18px" in result
        assert "border-radius: 8px" in result


class TestDarkModeReplacement:
    def test_dark_colors_updated(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        defaults = DefaultTokens(colors={"dark_background": "#1a1a2e", "dark_text": "#e5e5e5"})
        tokens = DesignTokens(colors={"dark_background": "#222222", "dark_text": "#cccccc"})
        html = (
            "<style>.dark-bg { background-color: #1a1a2e; } .dark-text { color: #e5e5e5; }</style>"
        )
        result = assembler._apply_dark_mode_replacement(html, defaults, tokens)
        assert "#222222" in result
        assert "#cccccc" in result
        assert "#1a1a2e" not in result


class TestLogoDimensionEnforcement:
    def test_dimensions_set(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        logo = LogoConfig(
            url="https://example.com/logo.png",
            alt_text="Logo",
            width=200,
            height=50,
        )
        html = '<img data-slot="logo_url" src="https://example.com/logo.png" width="100" height="30" />'
        result = assembler._enforce_logo_dimensions(html, logo)
        assert 'width="200"' in result
        assert 'height="50"' in result


class TestBrandColorSweep:
    def test_replaces_off_palette(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        client_colors = {"primary": "#ff0000", "bg": "#ffffff"}
        html = '<p style="color: #ff0001;">text</p>'
        result = assembler._brand_color_sweep(html, client_colors)
        assert "#ff0000" in result
        assert "#ff0001" not in result

    def test_allows_palette(self) -> None:
        assembler = TemplateAssembler.__new__(TemplateAssembler)
        client_colors = {"primary": "#ff0000"}
        html = '<p style="color: #ff0000;">text</p>'
        result = assembler._brand_color_sweep(html, client_colors)
        assert "#ff0000" in result
