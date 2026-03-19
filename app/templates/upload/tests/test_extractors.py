"""Tests for slot and token extractors (Phase 25.10)."""

from __future__ import annotations

from app.ai.templates.models import DefaultTokens
from app.templates.upload.analyzer import SectionInfo, SlotInfo, TokenInfo
from app.templates.upload.slot_extractor import SlotExtractor
from app.templates.upload.token_extractor import TokenExtractor


class TestSlotExtractor:
    def test_maps_headline_slot_type(self) -> None:
        """headline SlotInfo -> headline TemplateSlot."""
        slots = [
            SlotInfo(
                slot_id="s1",
                slot_type="headline",
                selector="h1",
                required=True,
                max_chars=100,
                content_preview="Hello",
                section_id="hero",
            )
        ]
        sections = [
            SectionInfo(
                section_id="hero", component_name="hero", element_count=5, layout_type="single"
            )
        ]
        result = SlotExtractor().extract(slots, sections)
        assert len(result) == 1
        assert result[0].slot_type == "headline"
        assert result[0].required is True

    def test_maps_body_and_image_types(self) -> None:
        """body and image slot types mapped correctly."""
        slots = [
            SlotInfo(
                slot_id="s1",
                slot_type="body",
                selector="p.body",
                required=False,
                max_chars=500,
                content_preview="Text",
                section_id="sec1",
            ),
            SlotInfo(
                slot_id="s2",
                slot_type="image",
                selector="img.hero",
                required=True,
                max_chars=None,
                content_preview="",
                section_id="sec1",
            ),
        ]
        sections = [
            SectionInfo(
                section_id="sec1", component_name="content", element_count=3, layout_type="single"
            )
        ]
        result = SlotExtractor().extract(slots, sections)
        types = {s.slot_type for s in result}
        assert "body" in types
        assert "image" in types

    def test_empty_slots_returns_empty(self) -> None:
        result = SlotExtractor().extract([], [])
        assert result == ()

    def test_placeholder_truncation(self) -> None:
        """Content preview truncated to 60 chars max."""
        long_preview = "A" * 200
        slots = [
            SlotInfo(
                slot_id="s1",
                slot_type="body",
                selector="p",
                required=False,
                max_chars=None,
                content_preview=long_preview,
                section_id="sec",
            )
        ]
        sections = [
            SectionInfo(
                section_id="sec", component_name="body", element_count=1, layout_type="single"
            )
        ]
        result = SlotExtractor().extract(slots, sections)
        assert len(result[0].placeholder) <= 60

    def test_unknown_type_falls_back_to_body(self) -> None:
        """Unknown slot type defaults to 'body'."""
        slots = [
            SlotInfo(
                slot_id="s1",
                slot_type="unknown_widget",
                selector="div",
                required=False,
                max_chars=None,
                content_preview="",
                section_id="sec",
            )
        ]
        sections = [
            SectionInfo(
                section_id="sec", component_name="main", element_count=1, layout_type="single"
            )
        ]
        result = SlotExtractor().extract(slots, sections)
        assert result[0].slot_type == "body"


class TestTokenExtractor:
    def test_color_role_assignment(self) -> None:
        """Most common bg -> background role, text -> text role."""
        info = TokenInfo(
            colors={
                "background": ["#ffffff", "#ffffff", "#f5f5f5"],
                "text": ["#333333", "#333333", "#0066cc"],
                "all": ["#ffffff", "#333333", "#0066cc"],
            },
            fonts={"heading": ["Arial"], "body": ["Georgia"]},
            font_sizes={"all": ["16px", "24px", "12px"]},
            spacing={"padding": ["20px", "20px", "10px"]},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.colors.get("background") == "#ffffff"
        assert tokens.colors.get("text") == "#333333"

    def test_empty_token_info(self) -> None:
        """Empty TokenInfo -> DefaultTokens with empty dicts."""
        info = TokenInfo(colors={}, fonts={}, font_sizes={}, spacing={})
        tokens = TokenExtractor().extract(info)
        assert isinstance(tokens, DefaultTokens)

    def test_font_size_sorting(self) -> None:
        """Largest -> heading, 2nd -> body, smallest -> small."""
        info = TokenInfo(
            colors={},
            fonts={"heading": ["Helvetica"]},
            font_sizes={"all": ["32px", "16px", "12px"]},
            spacing={},
        )
        tokens = TokenExtractor().extract(info)
        assert "heading" in tokens.font_sizes, "heading font size should be extracted"
        assert "body" in tokens.font_sizes, "body font size should be extracted"
        h = int(tokens.font_sizes["heading"].replace("px", ""))
        b = int(tokens.font_sizes["body"].replace("px", ""))
        assert h > b

    def test_spacing_extraction(self) -> None:
        """Most common padding -> section spacing."""
        info = TokenInfo(
            colors={},
            fonts={},
            font_sizes={},
            spacing={"padding": ["24px", "24px", "24px", "8px"]},
        )
        tokens = TokenExtractor().extract(info)
        assert tokens.spacing.get("section") == "24px"
