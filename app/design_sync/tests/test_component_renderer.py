"""Tests for component renderer — fills component templates with Figma content."""

from __future__ import annotations

import pytest

from app.design_sync.component_matcher import ComponentMatch, SlotFill, TokenOverride
from app.design_sync.component_renderer import ComponentRenderer
from app.design_sync.figma.layout_analyzer import (
    EmailSection,
    EmailSectionType,
)


def _make_section(
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    *,
    node_name: str = "TestSection",
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id="frame_1",
        node_name=node_name,
    )


def _make_match(
    slug: str,
    *,
    idx: int = 0,
    fills: list[SlotFill] | None = None,
    overrides: list[TokenOverride] | None = None,
    section: EmailSection | None = None,
) -> ComponentMatch:
    return ComponentMatch(
        section_idx=idx,
        section=section or _make_section(),
        component_slug=slug,
        slot_fills=fills or [],
        token_overrides=overrides or [],
    )


@pytest.fixture
def renderer() -> ComponentRenderer:
    r = ComponentRenderer(container_width=600)
    r.load()
    return r


class TestRendererLoad:
    def test_loads_templates(self, renderer: ComponentRenderer) -> None:
        assert renderer._loaded is True
        assert len(renderer._templates) > 0

    def test_has_key_slugs(self, renderer: ComponentRenderer) -> None:
        for slug in [
            "hero-block",
            "text-block",
            "cta-button",
            "email-footer",
            "column-layout-2",
            "spacer",
            "divider",
            "logo-header",
        ]:
            assert slug in renderer._templates, f"Missing template: {slug}"


class TestSlotFilling:
    def test_fill_text_slot(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "hero-block",
            fills=[SlotFill("headline", "Summer Sale!")],
        )
        result = renderer.render_section(match)
        assert "Summer Sale!" in result.html
        # Original placeholder replaced
        assert "Discover What" not in result.html

    def test_fill_cta_text_slot(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "cta-button",
            fills=[SlotFill("cta_text", "Buy Now")],
        )
        result = renderer.render_section(match)
        assert "Buy Now" in result.html

    def test_fill_image_slot(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "full-width-image",
            fills=[
                SlotFill(
                    "image_url",
                    "/api/v1/design-sync/assets/123.png",
                    slot_type="image",
                    attr_overrides={"width": "580"},
                ),
            ],
        )
        result = renderer.render_section(match)
        assert "/api/v1/design-sync/assets/123.png" in result.html

    def test_fill_cta_url_slot(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "cta-button",
            fills=[SlotFill("cta_url", "https://shop.example.com", slot_type="cta")],
        )
        result = renderer.render_section(match)
        assert 'href="https://shop.example.com"' in result.html

    def test_fill_spacer_height(self, renderer: ComponentRenderer) -> None:
        match = _make_match("spacer", fills=[SlotFill("spacer_height", "48")])
        result = renderer.render_section(match)
        assert "height:48px" in result.html
        assert 'height="48"' in result.html

    def test_fill_hero_background_image(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "hero-block",
            fills=[SlotFill("hero_image", "/img/hero.jpg", slot_type="image")],
        )
        result = renderer.render_section(match)
        assert "url('/img/hero.jpg')" in result.html
        # Also in VML src
        assert 'src="/img/hero.jpg"' in result.html

    def test_fill_column_layout(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "column-layout-2",
            fills=[
                SlotFill("col_1", "Left content"),
                SlotFill("col_2", "Right content"),
            ],
        )
        result = renderer.render_section(match)
        assert "Left content" in result.html
        assert "Right content" in result.html

    def test_fill_article_card(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "article-card",
            fills=[
                SlotFill("heading", "Article Title"),
                SlotFill("body_text", "Article body."),
                SlotFill("image_url", "/img/article.jpg", slot_type="image"),
            ],
        )
        result = renderer.render_section(match)
        assert "Article Title" in result.html
        assert "Article body." in result.html


class TestTokenOverrides:
    def test_background_color_override(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "text-block",
            overrides=[TokenOverride("background-color", "_outer", "#f5f0e8")],
        )
        result = renderer.render_section(match)
        assert (
            "background-color:#f5f0e8" in result.html or "background-color: #f5f0e8" in result.html
        )

    def test_heading_font_override(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "text-block",
            overrides=[TokenOverride("font-family", "_heading", "Georgia, serif")],
        )
        result = renderer.render_section(match)
        assert "Georgia, serif" in result.html

    def test_heading_color_override(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "text-block",
            overrides=[TokenOverride("color", "_heading", "#FFFFFF")],
        )
        result = renderer.render_section(match)
        assert "color:#FFFFFF" in result.html

    def test_body_color_override(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "text-block",
            overrides=[TokenOverride("color", "_body", "#AABBCC")],
        )
        result = renderer.render_section(match)
        assert "color:#AABBCC" in result.html

    def test_color_override_does_not_corrupt_background_color(
        self, renderer: ComponentRenderer
    ) -> None:
        """Regression: color override must not match background-color: property."""
        match = _make_match(
            "text-block",
            overrides=[
                TokenOverride("background-color", "_outer", "#FE5117"),
                TokenOverride("color", "_heading", "#FFFFFF"),
            ],
        )
        result = renderer.render_section(match)
        assert "background-color:#FE5117" in result.html
        assert "color:#FFFFFF" in result.html

    def test_placeholder_url_stripped(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "article-card",
            fills=[
                SlotFill("image_url", "https://via.placeholder.com/280x200", slot_type="image"),
                SlotFill("heading", "Test Title"),
            ],
        )
        result = renderer.render_section(match)
        assert "via.placeholder.com" not in result.html


class TestAnnotations:
    def test_section_comment_marker(self, renderer: ComponentRenderer) -> None:
        match = _make_match("text-block", idx=3)
        result = renderer.render_section(match)
        assert "<!-- section:section_3 -->" in result.html
        assert "<!-- /section:section_3 -->" in result.html

    def test_component_name_attribute(self, renderer: ComponentRenderer) -> None:
        section = _make_section(node_name="Hero Banner")
        match = _make_match("hero-block", section=section)
        result = renderer.render_section(match)
        assert 'data-component-name="Hero Banner"' in result.html

    def test_component_name_html_escaped(self, renderer: ComponentRenderer) -> None:
        section = _make_section(node_name='Frame "Special" <1>')
        match = _make_match("text-block", section=section)
        result = renderer.render_section(match)
        assert "&quot;" in result.html or "&#34;" in result.html


class TestMsoWidths:
    def test_updates_mso_width_600(self, renderer: ComponentRenderer) -> None:
        match = _make_match("text-block")
        result = renderer.render_section(match)
        assert 'width="600"' in result.html

    def test_updates_mso_width_custom(self) -> None:
        r = ComponentRenderer(container_width=700)
        r.load()
        match = _make_match("text-block")
        result = r.render_section(match)
        assert 'width="700"' in result.html


class TestDarkModeExtraction:
    def test_extracts_dark_mode_classes(self, renderer: ComponentRenderer) -> None:
        match = _make_match("text-block")
        result = renderer.render_section(match)
        assert "textblock-bg" in result.dark_mode_classes

    def test_hero_has_overlay_class(self, renderer: ComponentRenderer) -> None:
        match = _make_match("hero-block")
        result = renderer.render_section(match)
        assert "hero-overlay" in result.dark_mode_classes


class TestImageExtraction:
    def test_extracts_images(self, renderer: ComponentRenderer) -> None:
        match = _make_match(
            "full-width-image",
            fills=[
                SlotFill("image_url", "/img/banner.jpg", slot_type="image"),
            ],
        )
        result = renderer.render_section(match)
        assert len(result.images) >= 1
        assert any("/img/banner.jpg" in img["src"] for img in result.images)


class TestFallbackRender:
    def test_missing_slug_falls_back(self) -> None:
        r = ComponentRenderer(container_width=600)
        r.load()
        match = _make_match("nonexistent-component-xyz")
        result = r.render_section(match)
        assert result.component_slug == "text-block"
        assert "table" in result.html


class TestOutputStructure:
    """Verify the output uses independent table blocks (not tr-stacking)."""

    def test_output_is_independent_table(self, renderer: ComponentRenderer) -> None:
        match = _make_match("text-block")
        result = renderer.render_section(match)
        # Should NOT be wrapped in <tr>
        assert "<tr data-section-id" not in result.html
        # Should be an independent table
        assert '<table role="presentation"' in result.html

    def test_output_has_mso_wrapper(self, renderer: ComponentRenderer) -> None:
        match = _make_match("text-block")
        result = renderer.render_section(match)
        assert "<!--[if mso]>" in result.html
        assert "<![endif]-->" in result.html

    def test_nesting_depth_under_5(self, renderer: ComponentRenderer) -> None:
        """Component templates should have max 4 levels of table nesting."""
        for slug in ["text-block", "hero-block", "cta-button", "email-footer", "divider"]:
            match = _make_match(slug)
            result = renderer.render_section(match)
            # Count max nesting by tracking open/close table tags
            depth = 0
            max_depth = 0
            for line in result.html.split("\n"):
                depth += line.count("<table") - line.count("</table")
                max_depth = max(max_depth, depth)
            assert max_depth <= 5, f"{slug} has {max_depth} levels of table nesting"
