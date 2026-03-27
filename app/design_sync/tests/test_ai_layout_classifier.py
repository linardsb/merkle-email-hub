"""Tests for AI layout classifier — LLM-based section classification fallback."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.protocols import CompletionResponse
from app.design_sync.ai_layout_classifier import (
    _build_prompt,
    _parse_classification,
    classify_sections_batch,
    clear_cache,
    section_cache_key,
)
from app.design_sync.converter_service import enhance_layout_with_ai
from app.design_sync.figma.layout_analyzer import (
    DesignLayoutDescription,
    EmailSection,
    EmailSectionType,
    TextBlock,
)


def _section(
    name: str = "Frame 1",
    *,
    section_type: EmailSectionType = EmailSectionType.UNKNOWN,
    node_id: str = "n1",
    width: float = 600,
    height: float = 200,
) -> EmailSection:
    return EmailSection(
        section_type=section_type,
        node_id=node_id,
        node_name=name,
        width=width,
        height=height,
    )


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_cache()


class TestSectionCacheKey:
    def test_deterministic(self) -> None:
        s = _section()
        assert section_cache_key(s) == section_cache_key(s)

    def test_different_for_different_sections(self) -> None:
        s1 = _section("Frame 1", node_id="n1")
        s2 = _section("Frame 2", node_id="n2")
        assert section_cache_key(s1) != section_cache_key(s2)

    def test_includes_dimensions(self) -> None:
        s1 = _section(width=600, height=200)
        s2 = _section(width=600, height=400)
        assert section_cache_key(s1) != section_cache_key(s2)


class TestParseClassification:
    def test_valid_json(self) -> None:
        raw = '{"section_type": "hero", "column_layout": "single", "confidence": 0.9, "reasoning": "Large image"}'
        result = _parse_classification(raw)
        assert result is not None
        assert result.section_type == "hero"
        assert result.column_layout == "single"
        assert result.confidence == 0.9
        assert result.reasoning == "Large image"

    def test_invalid_json_returns_none(self) -> None:
        assert _parse_classification("not json") is None

    def test_invalid_section_type_defaults_to_unknown(self) -> None:
        raw = '{"section_type": "banana", "column_layout": "single", "confidence": 0.8, "reasoning": "test"}'
        result = _parse_classification(raw)
        assert result is not None
        assert result.section_type == "unknown"
        assert result.confidence == 0.0  # Reset when type is invalid

    def test_invalid_column_layout_defaults_to_single(self) -> None:
        raw = '{"section_type": "hero", "column_layout": "quad", "confidence": 0.8, "reasoning": "test"}'
        result = _parse_classification(raw)
        assert result is not None
        assert result.column_layout == "single"

    def test_confidence_clamped(self) -> None:
        raw = '{"section_type": "hero", "column_layout": "single", "confidence": 5.0, "reasoning": "test"}'
        result = _parse_classification(raw)
        assert result is not None
        assert result.confidence == 1.0

    def test_reasoning_truncated(self) -> None:
        raw = (
            '{"section_type": "hero", "column_layout": "single", "confidence": 0.8, "reasoning": "'
            + "x" * 300
            + '"}'
        )
        result = _parse_classification(raw)
        assert result is not None
        assert len(result.reasoning) <= 200


class TestBuildPrompt:
    def test_contains_section_info(self) -> None:
        s = _section("Frame 1", width=600, height=300)
        prompt = _build_prompt(s, ["header", "unknown", "footer"], 1, 3)
        assert "Frame 1" in prompt
        assert "600" in prompt
        assert "300" in prompt

    def test_contains_sibling_context(self) -> None:
        s = _section()
        prompt = _build_prompt(s, ["header", "unknown", "footer"], 1, 3)
        assert "header" in prompt
        assert "footer" in prompt

    def test_first_section_no_previous(self) -> None:
        s = _section()
        prompt = _build_prompt(s, ["unknown", "footer"], 0, 2)
        assert "Previous" not in prompt
        assert "Next section: footer" in prompt


class TestClassifySectionsBatch:
    @pytest.mark.asyncio
    async def test_classify_unknown_as_hero(self) -> None:
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content='{"section_type": "hero", "column_layout": "single", "confidence": 0.9, "reasoning": "Large image at top"}',
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        s = _section("Frame 1")
        with (
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            results = await classify_sections_batch(
                [s],
                all_section_types=["header", "unknown", "footer"],
            )

        assert len(results) == 1
        assert results[0].section_type == "hero"
        assert results[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm(self) -> None:
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content='{"section_type": "footer", "column_layout": "single", "confidence": 0.8, "reasoning": "Bottom"}',
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        s = _section("Frame 5")
        with (
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            # First call
            await classify_sections_batch([s], all_section_types=["unknown"])
            # Second call — should use cache
            results = await classify_sections_batch([s], all_section_types=["unknown"])

        assert len(results) == 1
        assert results[0].section_type == "footer"
        # Provider should only be called once (first call)
        assert provider.complete.call_count == 1

    @pytest.mark.asyncio
    async def test_low_confidence_returns_unknown(self) -> None:
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content='{"section_type": "hero", "column_layout": "single", "confidence": 0.2, "reasoning": "Unsure"}',
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        s = _section("Frame 1")
        with (
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            results = await classify_sections_batch([s], all_section_types=["unknown"])

        assert results[0].section_type == "unknown"
        assert results[0].confidence == 0.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_unknown(self) -> None:
        provider = AsyncMock()
        provider.complete.side_effect = RuntimeError("API down")

        s = _section("Frame 1")
        with (
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            results = await classify_sections_batch([s], all_section_types=["unknown"])

        assert len(results) == 1
        assert results[0].section_type == "unknown"
        assert results[0].confidence == 0.0

    @pytest.mark.asyncio
    async def test_batch_multiple_unknowns(self) -> None:
        call_count = 0

        async def mock_complete(*_args: object, **_kwargs: object) -> CompletionResponse:
            nonlocal call_count
            call_count += 1
            types = ["hero", "content", "footer"]
            idx = min(call_count - 1, len(types) - 1)
            return CompletionResponse(
                content=f'{{"section_type": "{types[idx]}", "column_layout": "single", "confidence": 0.8, "reasoning": "test"}}',
                model="test",
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

        provider = AsyncMock()
        provider.complete.side_effect = mock_complete

        sections = [
            _section("Frame A", node_id="a"),
            _section("Frame B", node_id="b"),
            _section("Frame C", node_id="c"),
        ]

        with (
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            results = await classify_sections_batch(
                sections,
                all_section_types=["unknown", "unknown", "unknown"],
            )

        assert len(results) == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_invalid_json_returns_unknown(self) -> None:
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content="I can't classify this section.",
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        s = _section("Frame 1")
        with (
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            results = await classify_sections_batch([s], all_section_types=["unknown"])

        assert results[0].section_type == "unknown"


# ── enhance_layout_with_ai integration tests ──


class TestEnhanceLayoutWithAi:
    @pytest.fixture(autouse=True)
    def _clear(self) -> None:
        from app.design_sync.ai_content_detector import clear_cache as clear_role_cache

        clear_cache()
        clear_role_cache()

    @pytest.mark.asyncio
    async def test_disabled_flag_returns_layout_unchanged(self) -> None:
        layout = DesignLayoutDescription(
            file_name="test.fig",
            sections=[_section("Frame 1")],
        )

        with patch("app.design_sync.converter_service.get_settings") as mock_settings:
            mock_settings.return_value.design_sync.ai_layout_enabled = False
            result = await enhance_layout_with_ai(layout)

        assert result is layout  # Same object, not modified

    @pytest.mark.asyncio
    async def test_empty_sections_returns_layout(self) -> None:
        layout = DesignLayoutDescription(file_name="test.fig", sections=[])

        with patch("app.design_sync.converter_service.get_settings") as mock_settings:
            mock_settings.return_value.design_sync.ai_layout_enabled = True
            result = await enhance_layout_with_ai(layout)

        assert result is layout

    @pytest.mark.asyncio
    async def test_unknown_sections_get_classified(self) -> None:
        """UNKNOWN sections are reclassified by AI; non-UNKNOWN stay unchanged."""
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content='{"section_type": "hero", "column_layout": "single", "confidence": 0.9, "reasoning": "Large image"}',
            model="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        layout = DesignLayoutDescription(
            file_name="test.fig",
            sections=[
                EmailSection(
                    section_type=EmailSectionType.HEADER,
                    node_id="h1",
                    node_name="Header",
                ),
                EmailSection(
                    section_type=EmailSectionType.UNKNOWN,
                    node_id="u1",
                    node_name="Frame 1",
                    width=600,
                    height=400,
                ),
                EmailSection(
                    section_type=EmailSectionType.FOOTER,
                    node_id="f1",
                    node_name="Footer",
                ),
            ],
        )

        with (
            patch("app.design_sync.converter_service.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="haiku"),
        ):
            mock_settings.return_value.design_sync.ai_layout_enabled = True
            mock_reg.return_value.get_llm.return_value = provider
            result = await enhance_layout_with_ai(layout)

        assert len(result.sections) == 3
        assert result.sections[0].section_type == EmailSectionType.HEADER
        assert result.sections[1].section_type == EmailSectionType.HERO
        assert result.sections[1].classification_confidence == 0.9
        assert result.sections[2].section_type == EmailSectionType.FOOTER

    @pytest.mark.asyncio
    async def test_content_roles_merged(self) -> None:
        """Sections with detectable content get content_roles populated."""
        layout = DesignLayoutDescription(
            file_name="test.fig",
            sections=[
                EmailSection(
                    section_type=EmailSectionType.FOOTER,
                    node_id="f1",
                    node_name="Footer",
                    texts=[
                        TextBlock(node_id="t1", content="\u00a9 2026 Acme | Unsubscribe"),
                    ],
                ),
            ],
        )

        with patch("app.design_sync.converter_service.get_settings") as mock_settings:
            mock_settings.return_value.design_sync.ai_layout_enabled = True
            result = await enhance_layout_with_ai(layout)

        assert len(result.sections) == 1
        roles = result.sections[0].content_roles
        assert "legal_text" in roles
        assert "unsubscribe_link" in roles
