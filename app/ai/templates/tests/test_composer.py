"""Tests for TemplateComposer — section-based template composition."""

import pytest

from app.ai.templates.composer import (
    CompositionError,
    TemplateComposer,
    _extract_slots_from_html,
    _infer_slot_type,
)


@pytest.fixture
def composer() -> TemplateComposer:
    c = TemplateComposer()
    c.load()
    return c


class TestTemplateComposer:
    def test_loads_sections(self, composer: TemplateComposer) -> None:
        sections = composer.available_sections()
        assert len(sections) >= 10
        assert "hero_image" in sections
        assert "cta_button" in sections
        assert "footer_standard" in sections

    def test_compose_basic(self, composer: TemplateComposer) -> None:
        """Compose a simple hero + content + CTA + footer layout."""
        template = composer.compose(["hero_image", "content_1col", "cta_button", "footer_standard"])
        assert template.metadata.name == "__compose__"
        assert "<!DOCTYPE html>" in template.html
        assert "data-slot=" in template.html
        assert len(template.slots) > 0

    def test_compose_preserves_mso(self, composer: TemplateComposer) -> None:
        """Composed templates must have MSO conditionals from skeleton."""
        template = composer.compose(["hero_image", "footer_minimal"])
        assert "<!--[if mso]>" in template.html
        assert "<![endif]-->" in template.html

    def test_compose_unknown_section_raises(self, composer: TemplateComposer) -> None:
        with pytest.raises(CompositionError, match="Unknown section"):
            composer.compose(["hero_image", "nonexistent_block"])

    def test_compose_empty_raises(self, composer: TemplateComposer) -> None:
        with pytest.raises(CompositionError, match="empty"):
            composer.compose([])

    def test_compose_dark_mode_css(self, composer: TemplateComposer) -> None:
        """Sections with dark-bg/dark-text classes get dark mode CSS."""
        template = composer.compose(["hero_image", "content_1col", "footer_standard"])
        assert "prefers-color-scheme: dark" in template.html

    def test_compose_multi_column(self, composer: TemplateComposer) -> None:
        """2-col section should result in column_count=2 metadata."""
        template = composer.compose(["hero_text", "content_2col", "footer_minimal"])
        assert template.metadata.column_count == 2

    def test_compose_slot_ids_unique(self, composer: TemplateComposer) -> None:
        """All slot IDs in composed template should be unique."""
        template = composer.compose(["hero_image", "content_1col", "cta_button", "footer_standard"])
        slot_ids = [s.slot_id for s in template.slots]
        assert len(slot_ids) == len(set(slot_ids)), f"Duplicate slots: {slot_ids}"

    def test_get_section(self, composer: TemplateComposer) -> None:
        block = composer.get_section("hero_image")
        assert block is not None
        assert block.block_id == "hero_image"
        assert len(block.html) > 50

    def test_get_section_nonexistent(self, composer: TemplateComposer) -> None:
        assert composer.get_section("nonexistent") is None

    def test_compose_metadata_has_hero(self, composer: TemplateComposer) -> None:
        template = composer.compose(["hero_image", "footer_minimal"])
        assert template.metadata.has_hero_image is True

    def test_compose_metadata_no_hero(self, composer: TemplateComposer) -> None:
        template = composer.compose(["content_1col", "footer_minimal"])
        assert template.metadata.has_hero_image is False

    def test_compose_has_navigation(self, composer: TemplateComposer) -> None:
        template = composer.compose(["navigation", "content_1col", "footer_minimal"])
        assert template.metadata.has_navigation is True

    def test_compose_has_social_links(self, composer: TemplateComposer) -> None:
        template = composer.compose(["content_1col", "social_links", "footer_minimal"])
        assert template.metadata.has_social_links is True

    def test_compose_all_sections(self, composer: TemplateComposer) -> None:
        """Compose with every available section — must not crash."""
        all_sections = composer.available_sections()
        template = composer.compose(all_sections)
        assert "<!DOCTYPE html>" in template.html
        assert template.metadata.name == "__compose__"

    def test_compose_accessibility_attributes(self, composer: TemplateComposer) -> None:
        """Composed templates must have accessibility attributes from skeleton."""
        template = composer.compose(["hero_image", "footer_minimal"])
        assert 'role="article"' in template.html
        assert 'aria-roledescription="email"' in template.html
        assert 'lang="en"' in template.html

    def test_compose_preheader_slot(self, composer: TemplateComposer) -> None:
        """Skeleton provides a preheader slot."""
        template = composer.compose(["hero_image", "footer_minimal"])
        assert 'data-slot="preheader"' in template.html

    def test_idempotent_load(self, composer: TemplateComposer) -> None:
        """Loading twice should not duplicate sections."""
        count_before = len(composer.available_sections())
        composer.load()
        assert len(composer.available_sections()) == count_before


class TestSlotExtraction:
    def test_extract_slots_from_html(self) -> None:
        html = '<h1 data-slot="test_headline">Hello</h1><p data-slot="test_body">Body</p>'
        slots = _extract_slots_from_html(html, "test")
        assert len(slots) == 2
        assert slots[0].slot_id == "test_headline"

    def test_infer_slot_type(self) -> None:
        assert _infer_slot_type("hero_headline") == "headline"
        assert _infer_slot_type("hero_image") == "image"
        assert _infer_slot_type("cta_url") == "cta"
        assert _infer_slot_type("body_content") == "body"
        assert _infer_slot_type("preheader") == "preheader"
        assert _infer_slot_type("footer_text") == "footer"
        assert _infer_slot_type("navigation_links") == "nav"
        assert _infer_slot_type("social_links_icons") == "social"
