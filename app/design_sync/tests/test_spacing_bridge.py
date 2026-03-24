"""Tests for spacing bridge (Phase 31.6)."""

from __future__ import annotations

from app.design_sync.figma.layout_analyzer import (
    DesignLayoutDescription,
    EmailSection,
    EmailSectionType,
    TextBlock,
)
from app.design_sync.spacing_bridge import figma_spacing_to_tokens, figma_typography_to_tokens


def _make_layout(sections: list[EmailSection]) -> DesignLayoutDescription:
    return DesignLayoutDescription(
        file_name="Test",
        sections=sections,
    )


class TestFigmaSpacingToTokens:
    def test_uniform_padding(self) -> None:
        """All sections have same padding -> single section_padding value."""
        sections = [
            EmailSection(
                section_type=EmailSectionType.HEADER,
                node_id="s1",
                node_name="Header",
                padding_top=32.0,
                padding_right=32.0,
                padding_bottom=32.0,
                padding_left=32.0,
            ),
            EmailSection(
                section_type=EmailSectionType.CONTENT,
                node_id="s2",
                node_name="Content",
                padding_top=32.0,
                padding_right=32.0,
                padding_bottom=32.0,
                padding_left=32.0,
            ),
        ]
        result = figma_spacing_to_tokens(_make_layout(sections))
        assert result["section_padding"] == "32px"

    def test_element_gap_extracted(self) -> None:
        """Sections with item_spacing -> element_gap token."""
        sections = [
            EmailSection(
                section_type=EmailSectionType.CONTENT,
                node_id="s1",
                node_name="Content",
                item_spacing=16.0,
            ),
        ]
        result = figma_spacing_to_tokens(_make_layout(sections))
        assert result["element_gap"] == "16px"

    def test_no_spacing_data(self) -> None:
        """Sections without spacing -> empty dict."""
        sections = [
            EmailSection(
                section_type=EmailSectionType.CONTENT,
                node_id="s1",
                node_name="Content",
            ),
        ]
        result = figma_spacing_to_tokens(_make_layout(sections))
        assert result == {}


class TestFigmaTypographyToTokens:
    def test_heading_body_sizes(self) -> None:
        """TextBlocks with heading/body -> correct font_sizes."""
        sections = [
            EmailSection(
                section_type=EmailSectionType.HERO,
                node_id="s1",
                node_name="Hero",
                texts=[
                    TextBlock(
                        node_id="t1",
                        content="Headline",
                        font_size=32.0,
                        is_heading=True,
                        font_family="Inter",
                        font_weight=700,
                        line_height=40.0,
                    ),
                    TextBlock(
                        node_id="t2",
                        content="Body text",
                        font_size=16.0,
                        is_heading=False,
                        font_family="Arial",
                        font_weight=400,
                        line_height=24.0,
                    ),
                ],
            )
        ]
        result = figma_typography_to_tokens(_make_layout(sections))
        assert result.font_sizes["heading"] == "32px"
        assert result.font_sizes["body"] == "16px"
        assert result.fonts["heading"] == "Inter"
        assert result.fonts["body"] == "Arial"
        assert result.font_weights["heading"] == "700"
        assert result.font_weights["body"] == "400"
        assert result.line_heights["heading"] == "40px"
        assert result.line_heights["body"] == "24px"

    def test_empty_layout(self) -> None:
        """No text blocks -> empty dicts."""
        result = figma_typography_to_tokens(_make_layout([]))
        assert result.font_sizes == {}
        assert result.fonts == {}
        assert result.font_weights == {}
        assert result.line_heights == {}
