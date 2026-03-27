"""Tests for AI content detector — semantic content role detection."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.protocols import CompletionResponse
from app.design_sync.ai_content_detector import (
    _detect_heuristic,
    clear_cache,
    detect_content_roles,
)
from app.design_sync.figma.layout_analyzer import (
    ButtonElement,
    EmailSection,
    EmailSectionType,
    ImagePlaceholder,
    TextBlock,
)


def _section(
    *,
    section_type: EmailSectionType = EmailSectionType.CONTENT,
    node_id: str = "n1",
    texts: list[TextBlock] | None = None,
    images: list[ImagePlaceholder] | None = None,
    buttons: list[ButtonElement] | None = None,
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id=node_id,
        node_name="Section",
        texts=texts or [],
        images=images or [],
        buttons=buttons or [],
    )


def _text(content: str, font_size: float = 14) -> TextBlock:
    return TextBlock(node_id="t1", content=content, font_size=font_size)


def _image(width: float = 200, height: float = 100) -> ImagePlaceholder:
    return ImagePlaceholder(node_id="img1", node_name="image", width=width, height=height)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_cache()


# ── Heuristic Detection Tests ──


class TestHeuristicUnsubscribe:
    def test_unsubscribe_detected(self) -> None:
        s = _section(texts=[_text("Click here to unsubscribe from emails")])
        roles = _detect_heuristic(s, 3, 5)
        assert "unsubscribe_link" in roles

    def test_case_insensitive(self) -> None:
        s = _section(texts=[_text("UNSUBSCRIBE from this list")])
        roles = _detect_heuristic(s, 3, 5)
        assert "unsubscribe_link" in roles


class TestHeuristicCopyright:
    def test_copyright_symbol(self) -> None:
        s = _section(texts=[_text("\u00a9 2026 Acme Corp")])
        roles = _detect_heuristic(s, 4, 5)
        assert "legal_text" in roles

    def test_copyright_word(self) -> None:
        s = _section(texts=[_text("Copyright 2026 Example Inc")])
        roles = _detect_heuristic(s, 4, 5)
        assert "legal_text" in roles

    def test_all_rights_reserved(self) -> None:
        s = _section(texts=[_text("All rights reserved.")])
        roles = _detect_heuristic(s, 4, 5)
        assert "legal_text" in roles


class TestHeuristicSocial:
    def test_facebook_url(self) -> None:
        s = _section(texts=[_text("Follow us: facebook.com/acme")])
        roles = _detect_heuristic(s, 3, 5)
        assert "social_links" in roles

    def test_instagram_url(self) -> None:
        s = _section(texts=[_text("instagram.com/brand")])
        roles = _detect_heuristic(s, 3, 5)
        assert "social_links" in roles


class TestHeuristicViewBrowser:
    def test_view_in_browser(self) -> None:
        s = _section(texts=[_text("View in browser")])
        roles = _detect_heuristic(s, 0, 5)
        assert "view_in_browser" in roles

    def test_view_online(self) -> None:
        s = _section(texts=[_text("View online")])
        roles = _detect_heuristic(s, 0, 5)
        assert "view_in_browser" in roles


class TestHeuristicAddress:
    def test_street_address(self) -> None:
        s = _section(texts=[_text("123 Main St, New York, NY 10001")])
        roles = _detect_heuristic(s, 4, 5)
        assert "address" in roles

    def test_avenue(self) -> None:
        s = _section(texts=[_text("456 Park Avenue, Suite 100")])
        roles = _detect_heuristic(s, 4, 5)
        assert "address" in roles


class TestHeuristicLogo:
    def test_first_section_small_image(self) -> None:
        s = _section(
            images=[_image(width=150, height=50)],
        )
        roles = _detect_heuristic(s, 0, 5)
        assert "logo" in roles

    def test_not_logo_if_image_too_tall(self) -> None:
        s = _section(
            images=[_image(width=600, height=300)],
        )
        roles = _detect_heuristic(s, 0, 5)
        assert "logo" not in roles

    def test_not_logo_if_not_first_section(self) -> None:
        s = _section(
            images=[_image(width=150, height=50)],
        )
        roles = _detect_heuristic(s, 2, 5)
        assert "logo" not in roles


class TestHeuristicNavigation:
    def test_many_short_texts(self) -> None:
        texts = [_text(f"Link {i}") for i in range(5)]
        s = _section(texts=texts)
        roles = _detect_heuristic(s, 1, 5)
        assert "navigation" in roles

    def test_not_nav_with_long_texts(self) -> None:
        texts = [
            _text("This is a long paragraph about our products and services") for _ in range(5)
        ]
        s = _section(texts=texts)
        roles = _detect_heuristic(s, 1, 5)
        assert "navigation" not in roles


class TestHeuristicPreheader:
    def test_first_section_short_text_small_font(self) -> None:
        s = _section(texts=[_text("View this email in your browser", font_size=10)])
        roles = _detect_heuristic(s, 0, 5)
        assert "preheader" in roles

    def test_not_preheader_if_large_font(self) -> None:
        s = _section(texts=[_text("Welcome!", font_size=24)])
        roles = _detect_heuristic(s, 0, 5)
        assert "preheader" not in roles


class TestMultipleRoles:
    def test_copyright_and_unsubscribe(self) -> None:
        s = _section(texts=[_text("\u00a9 2026 Acme Corp | Unsubscribe")])
        roles = _detect_heuristic(s, 4, 5)
        assert "legal_text" in roles
        assert "unsubscribe_link" in roles

    def test_empty_section_no_roles(self) -> None:
        s = _section()
        roles = _detect_heuristic(s, 2, 5)
        assert roles == []


# ── Full Pipeline Tests ──


class TestDetectContentRoles:
    @pytest.mark.asyncio
    async def test_heuristic_only_no_llm(self) -> None:
        """Sections with heuristic matches should not trigger LLM."""
        sections = [
            _section(
                node_id="s1",
                texts=[_text("\u00a9 2026 Acme")],
                section_type=EmailSectionType.FOOTER,
            ),
        ]

        annotations = await detect_content_roles(sections)

        assert len(annotations) == 1
        assert "legal_text" in annotations[0].roles
        assert annotations[0].source == "heuristic"

    @pytest.mark.asyncio
    async def test_no_llm_for_non_unknown_sections(self) -> None:
        """Non-UNKNOWN sections without heuristic matches → no LLM call."""
        sections = [
            _section(
                node_id="s1",
                texts=[_text("Regular content paragraph")],
                section_type=EmailSectionType.CONTENT,
            ),
        ]

        # No mocking needed — LLM should never be called
        annotations = await detect_content_roles(sections)

        assert len(annotations) == 1
        assert annotations[0].roles == ()
        assert annotations[0].source == "heuristic"

    @pytest.mark.asyncio
    async def test_llm_fallback_for_unknown_section(self) -> None:
        """UNKNOWN sections with no heuristic match → LLM called."""
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content='{"roles": ["legal_text", "address"]}',
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        sections = [
            _section(
                node_id="s1",
                texts=[_text("Some ambiguous text")],
                section_type=EmailSectionType.UNKNOWN,
            ),
        ]

        with (
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            annotations = await detect_content_roles(sections)

        assert len(annotations) == 1
        assert "legal_text" in annotations[0].roles
        assert "address" in annotations[0].roles
        assert annotations[0].source == "llm"

    @pytest.mark.asyncio
    async def test_llm_error_graceful_fallback(self) -> None:
        """LLM error → empty roles, no crash."""
        provider = AsyncMock()
        provider.complete.side_effect = RuntimeError("API down")

        sections = [
            _section(
                node_id="s1",
                texts=[_text("Some text")],
                section_type=EmailSectionType.UNKNOWN,
            ),
        ]

        with (
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            annotations = await detect_content_roles(sections)

        assert len(annotations) == 1
        assert annotations[0].roles == ()

    @pytest.mark.asyncio
    async def test_invalid_roles_filtered(self) -> None:
        """LLM returning invalid role names → filtered out."""
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content='{"roles": ["legal_text", "banana", "hero_section"]}',
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        sections = [
            _section(
                node_id="s1",
                texts=[_text("Some text")],
                section_type=EmailSectionType.UNKNOWN,
            ),
        ]

        with (
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            annotations = await detect_content_roles(sections)

        assert annotations[0].roles == ("legal_text",)

    @pytest.mark.asyncio
    async def test_cache_hit(self) -> None:
        """Same content → cached result, no LLM."""
        sections = [
            _section(
                node_id="s1",
                texts=[_text("\u00a9 2026 Acme")],
                section_type=EmailSectionType.FOOTER,
            ),
        ]

        # First call
        ann1 = await detect_content_roles(sections)
        # Second call — should use cache
        ann2 = await detect_content_roles(sections)

        assert ann1[0].roles == ann2[0].roles
