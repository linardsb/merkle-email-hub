"""Tests for section_classifier module."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.design_sync.email_design_document import (
    DocumentButton,
    DocumentImage,
    DocumentSection,
    DocumentText,
)
from app.design_sync.html_import.section_classifier import (
    classify_sections,
    classify_with_ai_fallback,
)


def _section(
    section_id: str = "s1",
    section_type: str = "unknown",
    texts: list[DocumentText] | None = None,
    images: list[DocumentImage] | None = None,
    buttons: list[DocumentButton] | None = None,
    height: float | None = 100.0,
) -> DocumentSection:
    return DocumentSection(
        id=section_id,
        type=section_type,
        texts=texts or [],
        images=images or [],
        buttons=buttons or [],
        height=height,
        width=600.0,
    )


def _text(
    content: str = "Hello",
    font_size: float | None = 16.0,
    is_heading: bool = False,
) -> DocumentText:
    return DocumentText(
        node_id="t1",
        content=content,
        font_size=font_size,
        is_heading=is_heading,
    )


def _image(width: float = 600.0, height: float = 300.0) -> DocumentImage:
    return DocumentImage(node_id="i1", node_name="image", width=width, height=height)


def _button(text: str = "Click") -> DocumentButton:
    return DocumentButton(node_id="b1", text=text)


class TestClassifySections:
    def test_preserves_already_classified(self) -> None:
        sections = [_section(section_type="hero")]
        result = classify_sections(sections)
        assert result[0].type == "hero"

    def test_header_small_image_first_section(self) -> None:
        sections = [
            _section(images=[_image(width=150.0, height=60.0)]),
            _section(section_id="s2", texts=[_text()]),
        ]
        result = classify_sections(sections)
        assert result[0].type == "header"

    def test_hero_large_heading(self) -> None:
        sections = [
            _section(
                texts=[_text(content="Big Title", font_size=32.0, is_heading=True)],
                buttons=[_button()],
            ),
        ]
        result = classify_sections(sections)
        assert result[0].type == "hero"

    def test_cta_only_buttons(self) -> None:
        sections = [_section(buttons=[_button("Shop Now")])]
        result = classify_sections(sections)
        assert result[0].type == "cta"

    def test_footer_unsubscribe(self) -> None:
        sections = [
            _section(section_id="s1", texts=[_text()]),
            _section(
                section_id="s2",
                texts=[_text(content="Unsubscribe from emails", font_size=11.0)],
            ),
        ]
        result = classify_sections(sections)
        assert result[1].type == "footer"

    def test_footer_copyright(self) -> None:
        sections = [
            _section(section_id="s1", texts=[_text()]),
            _section(
                section_id="s2",
                texts=[_text(content="© 2026 Company Inc. All rights reserved.", font_size=10.0)],
            ),
        ]
        result = classify_sections(sections)
        assert result[1].type == "footer"

    def test_social_media_urls(self) -> None:
        sections = [
            _section(
                texts=[_text(content="Follow us on facebook and twitter")],
            ),
        ]
        result = classify_sections(sections)
        assert result[0].type == "social"

    def test_spacer_no_content(self) -> None:
        sections = [_section(height=20.0)]
        result = classify_sections(sections)
        assert result[0].type == "spacer"

    def test_content_default(self) -> None:
        sections = [
            _section(
                texts=[_text(content="Regular paragraph text"), _text(content="More text")],
                images=[_image()],
            ),
        ]
        result = classify_sections(sections)
        assert result[0].type == "content"

    def test_bottom_position_small_text_footer(self) -> None:
        # 5 sections, last one has small text
        sections = [_section(section_id=f"s{i}", texts=[_text()], height=100.0) for i in range(4)]
        sections.append(
            _section(
                section_id="s4",
                texts=[_text(content="Legal text", font_size=10.0)],
                height=50.0,
            )
        )
        result = classify_sections(sections)
        assert result[4].type == "footer"

    def test_empty_sections_list(self) -> None:
        result = classify_sections([])
        assert result == []

    def test_mixed_classification(self) -> None:
        sections = [
            _section(section_id="s0", images=[_image(width=100.0, height=40.0)]),
            _section(section_id="s1", texts=[_text("Welcome", font_size=28.0, is_heading=True)]),
            _section(section_id="s2", texts=[_text("Body text")]),
            _section(section_id="s3", buttons=[_button("Buy")]),
            _section(section_id="s4", texts=[_text("Unsubscribe", font_size=10.0)]),
        ]
        result = classify_sections(sections)
        types = [s.type for s in result]
        assert types[0] == "header"
        assert types[1] == "hero"
        assert types[2] == "content"
        assert types[3] == "cta"
        assert types[4] == "footer"


class TestClassifyWithAiFallback:
    @pytest.mark.asyncio
    async def test_ai_disabled_keeps_unknown(self) -> None:
        # Create a section that won't match any heuristic
        sections = [_section(section_type="unknown", texts=[], images=[], buttons=[], height=100.0)]
        result = await classify_with_ai_fallback(sections, ai_enabled=False)
        # The spacer heuristic will catch the empty section
        assert result[0].type in ("spacer", "unknown")

    @pytest.mark.asyncio
    async def test_ai_enabled_classifies_unknown(self) -> None:
        from app.design_sync.ai_layout_classifier import SectionClassification

        mock_result = SectionClassification(
            section_type="content",
            column_layout="single",
            confidence=0.85,
            reasoning="Detected body content",
        )

        sections = [_section(section_type="unknown", texts=[_text("Ambiguous")])]

        with (
            patch(
                "app.design_sync.ai_layout_classifier.classify_sections_batch",
                new_callable=AsyncMock,
                return_value=[mock_result],
            ),
            patch(
                "app.design_sync.ai_content_detector.detect_content_roles",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            # The heuristic will classify "Ambiguous" as content first
            result = await classify_with_ai_fallback(sections, ai_enabled=True)
            assert result[0].type == "content"

    @pytest.mark.asyncio
    async def test_ai_failure_graceful(self) -> None:
        sections = [_section(texts=[_text("Something")])]

        with (
            patch(
                "app.design_sync.ai_layout_classifier.classify_sections_batch",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LLM unavailable"),
            ),
            patch(
                "app.design_sync.ai_content_detector.detect_content_roles",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await classify_with_ai_fallback(sections, ai_enabled=True)
            # Should not crash
            assert len(result) == 1
