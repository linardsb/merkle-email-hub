"""Voice brief extractor tests — LLM call mocking, JSON parsing, confidence handling."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.protocols import CompletionResponse
from app.ai.voice.brief_extractor import VoiceBriefExtractor
from app.ai.voice.exceptions import BriefExtractionError
from app.ai.voice.schemas import Transcript, TranscriptSegment

# ── Fixtures ──


def _make_transcript(text: str = "Create an email about our summer sale") -> Transcript:
    return Transcript(
        text=text,
        language="en",
        duration_seconds=8.0,
        segments=[TranscriptSegment(start=0.0, end=8.0, text=text)],
    )


def _make_llm_json(
    *,
    confidence: float = 0.92,
    topic: str = "Summer Sale",
    sections: list[dict[str, object]] | None = None,
) -> str:
    data = {
        "topic": topic,
        "sections": sections
        or [
            {"type": "hero", "description": "Hero banner", "content_hints": ["summer imagery"]},
            {"type": "cta", "description": "Shop now button", "content_hints": ["discount code"]},
        ],
        "tone": "energetic",
        "cta_text": "Shop Now",
        "audience": "existing customers",
        "constraints": ["mobile-first"],
        "confidence": confidence,
    }
    return json.dumps(data)


def _make_completion(content: str) -> CompletionResponse:
    return CompletionResponse(
        content=content,
        model="test-model",
        usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
    )


def _mock_provider(content: str) -> AsyncMock:
    provider = AsyncMock()
    provider.complete = AsyncMock(return_value=_make_completion(content))
    return provider


def _patch_extractor_deps(provider: AsyncMock) -> tuple[MagicMock, ...]:
    """Return context managers for patching extractor dependencies."""
    return ()


# ── Tests ──


class TestBriefExtraction:
    """Test VoiceBriefExtractor.extract()."""

    @pytest.mark.anyio
    async def test_extract_high_confidence_returns_full_brief(self) -> None:
        """High confidence returns fully populated EmailBrief."""
        provider = _mock_provider(_make_llm_json(confidence=0.92))

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o"),
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x),
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            brief, confidence = await extractor.extract(_make_transcript())
            assert confidence == pytest.approx(0.92)  # pyright: ignore[reportUnknownMemberType]
            assert brief.topic == "Summer Sale"
            assert len(brief.sections) == 2
            assert brief.sections[0].type == "hero"
            assert brief.tone == "energetic"
            assert brief.cta_text == "Shop Now"

    @pytest.mark.anyio
    async def test_extract_low_confidence_returns_raw_transcript_only(self) -> None:
        """Low confidence returns minimal brief with raw transcript."""
        provider = _mock_provider(_make_llm_json(confidence=0.3))

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o"),
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x),
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            brief, confidence = await extractor.extract(_make_transcript())
            assert confidence == pytest.approx(0.3)  # pyright: ignore[reportUnknownMemberType]
            assert brief.sections == []
            assert brief.raw_transcript != ""

    @pytest.mark.anyio
    async def test_extract_strips_markdown_fences(self) -> None:
        """LLM response wrapped in markdown code fences is parsed correctly."""
        fenced = f"```json\n{_make_llm_json()}\n```"
        provider = _mock_provider(fenced)

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o"),
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x),
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            brief, confidence = await extractor.extract(_make_transcript())
            assert brief.topic == "Summer Sale"
            assert confidence == pytest.approx(0.92)  # pyright: ignore[reportUnknownMemberType]

    @pytest.mark.anyio
    async def test_extract_invalid_json_raises_extraction_error(self) -> None:
        """Non-JSON LLM response raises BriefExtractionError."""
        provider = _mock_provider("This is not JSON at all")

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o"),
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x),
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            with pytest.raises(BriefExtractionError, match="parse"):
                await extractor.extract(_make_transcript())

    @pytest.mark.anyio
    async def test_extract_missing_confidence_defaults_to_half(self) -> None:
        """JSON without confidence field coerces to 0.5."""
        data = json.dumps({"topic": "Test", "sections": [], "tone": "casual"})
        provider = _mock_provider(data)

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o"),
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x),
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            brief, confidence = await extractor.extract(_make_transcript())
            assert confidence == pytest.approx(0.5)  # pyright: ignore[reportUnknownMemberType]
            # 0.5 < 0.7 threshold → should return minimal brief
            assert brief.sections == []

    @pytest.mark.anyio
    async def test_extract_sanitizes_transcript_text(self) -> None:
        """sanitize_prompt is called on transcript text."""
        provider = _mock_provider(_make_llm_json())

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o"),
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x) as mock_sanitize,
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            await extractor.extract(_make_transcript("test text"))
            mock_sanitize.assert_called_once_with("test text")

    @pytest.mark.anyio
    async def test_extract_llm_failure_raises_extraction_error(self) -> None:
        """Provider.complete raising exception wraps in BriefExtractionError."""
        provider = AsyncMock()
        provider.complete = AsyncMock(side_effect=RuntimeError("LLM down"))

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o"),
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x),
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            with pytest.raises(BriefExtractionError, match="LLM call failed"):
                await extractor.extract(_make_transcript())

    @pytest.mark.anyio
    async def test_extract_non_string_response_raises(self) -> None:
        """LLM returning non-string content raises BriefExtractionError."""
        response = CompletionResponse(
            content=42,  # type: ignore[arg-type]
            model="test",
            usage=None,
        )
        provider = AsyncMock()
        provider.complete = AsyncMock(return_value=response)

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o"),
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x),
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            with pytest.raises(BriefExtractionError, match="non-text"):
                await extractor.extract(_make_transcript())

    @pytest.mark.anyio
    async def test_extract_section_types_mapped(self) -> None:
        """All 8 section types are correctly mapped to SectionBrief objects."""
        sections: list[dict[str, object]] = [
            {"type": t, "description": f"{t} section", "content_hints": []}
            for t in [
                "hero",
                "content_block",
                "cta",
                "product_card",
                "countdown",
                "footer",
                "testimonial",
                "social",
            ]
        ]
        provider = _mock_provider(_make_llm_json(sections=sections))

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o"),
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x),
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            brief, _ = await extractor.extract(_make_transcript())
            assert len(brief.sections) == 8
            types = [s.type for s in brief.sections]
            assert "hero" in types
            assert "footer" in types
            assert "social" in types

    @pytest.mark.anyio
    async def test_extract_uses_configured_model(self) -> None:
        """resolve_model is called when no extraction_model configured."""
        provider = _mock_provider(_make_llm_json())

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.ai.registry.get_registry") as mock_reg,
            patch("app.ai.routing.resolve_model", return_value="gpt-4o-mini") as mock_resolve,
            patch("app.ai.sanitize.sanitize_prompt", side_effect=lambda x: x),
        ):
            mock_settings.return_value.ai.provider = "openai"
            mock_settings.return_value.voice.extraction_model = ""
            mock_settings.return_value.voice.confidence_threshold = 0.7
            mock_reg.return_value.get_llm.return_value = provider

            extractor = VoiceBriefExtractor()
            await extractor.extract(_make_transcript())
            mock_resolve.assert_called_once_with("standard")
