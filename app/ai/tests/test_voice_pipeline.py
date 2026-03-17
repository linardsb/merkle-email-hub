"""Tests for voice brief input pipeline."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.voice.exceptions import (
    AudioValidationError,
    VoiceDisabledError,
)
from app.ai.voice.schemas import (
    EmailBrief,
    SectionBrief,
    Transcript,
    TranscriptSegment,
    VoiceTranscribeRequest,
)
from app.ai.voice.service import VoiceBriefService

# ── Fixtures ──


def _make_audio_b64(size: int = 1000) -> str:
    """Create fake base64 audio data."""
    return base64.b64encode(b"\x00" * size).decode()


def _make_transcript(text: str = "We need a Black Friday email") -> Transcript:
    return Transcript(
        text=text,
        language="en",
        duration_seconds=30.0,
        segments=[TranscriptSegment(start=0.0, end=30.0, text=text)],
    )


def _make_brief() -> EmailBrief:
    return EmailBrief(
        topic="Black Friday Sale",
        sections=[
            SectionBrief(
                type="hero", description="Hero banner with sale headline", content_hints=["50% off"]
            ),
            SectionBrief(type="product_card", description="Three product cards", content_hints=[]),
            SectionBrief(type="cta", description="Shop now button", content_hints=[]),
        ],
        tone="urgent",
        cta_text="Shop Now",
        audience="existing customers",
        constraints=["must include countdown timer"],
        raw_transcript="We need a Black Friday email",
    )


# ── VoiceBriefService tests ──


class TestVoiceBriefServiceValidation:
    """Test audio validation logic."""

    def setup_method(self) -> None:
        self.service = VoiceBriefService()

    @patch("app.ai.voice.service.get_settings")
    def test_disabled_raises(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.voice.enabled = False
        with pytest.raises(VoiceDisabledError, match="not enabled"):
            self.service._ensure_enabled()

    @patch("app.ai.voice.service.get_settings")
    def test_unsupported_format_raises(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.voice.enabled = True
        mock_settings.return_value.voice.max_file_size_mb = 25
        with pytest.raises(AudioValidationError, match="Unsupported"):
            self.service._decode_and_validate(_make_audio_b64(), "audio/flac")

    @patch("app.ai.voice.service.get_settings")
    def test_invalid_base64_raises(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.voice.enabled = True
        mock_settings.return_value.voice.max_file_size_mb = 25
        with pytest.raises(AudioValidationError, match="Invalid base64"):
            self.service._decode_and_validate("not-base64!!!", "audio/wav")

    @patch("app.ai.voice.service.get_settings")
    def test_too_large_raises(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.voice.enabled = True
        mock_settings.return_value.voice.max_file_size_mb = 1  # 1MB
        big_audio = base64.b64encode(b"\x00" * (2 * 1024 * 1024)).decode()
        with pytest.raises(AudioValidationError, match="too large"):
            self.service._decode_and_validate(big_audio, "audio/wav")

    @patch("app.ai.voice.service.get_settings")
    def test_too_small_raises(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.voice.enabled = True
        mock_settings.return_value.voice.max_file_size_mb = 25
        tiny = base64.b64encode(b"\x00" * 10).decode()
        with pytest.raises(AudioValidationError, match="too small"):
            self.service._decode_and_validate(tiny, "audio/wav")

    @patch("app.ai.voice.service.get_settings")
    def test_valid_audio_decoded(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.voice.enabled = True
        mock_settings.return_value.voice.max_file_size_mb = 25
        result = self.service._decode_and_validate(_make_audio_b64(500), "audio/wav")
        assert len(result) == 500


class TestVoiceBriefServiceTranscribe:
    """Test transcription pipeline."""

    def setup_method(self) -> None:
        self.service = VoiceBriefService()

    @pytest.mark.anyio
    @patch("app.ai.voice.service.get_settings")
    @patch("app.ai.voice.service.get_transcriber")
    async def test_transcribe_success(
        self, mock_get_transcriber: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value.voice.enabled = True
        mock_settings.return_value.voice.max_file_size_mb = 25
        mock_settings.return_value.voice.max_duration_s = 300

        mock_transcriber = AsyncMock()
        mock_transcriber.transcribe.return_value = _make_transcript()
        mock_get_transcriber.return_value = mock_transcriber

        request = VoiceTranscribeRequest(
            audio_data=_make_audio_b64(),
            media_type="audio/wav",
        )
        result = await self.service.transcribe(request)
        assert result.text == "We need a Black Friday email"
        assert result.language == "en"

    @pytest.mark.anyio
    @patch("app.ai.voice.service.get_settings")
    @patch("app.ai.voice.service.get_transcriber")
    async def test_transcribe_duration_exceeded(
        self, mock_get_transcriber: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value.voice.enabled = True
        mock_settings.return_value.voice.max_file_size_mb = 25
        mock_settings.return_value.voice.max_duration_s = 10  # 10s max

        long_transcript = Transcript(text="long", language="en", duration_seconds=60.0, segments=[])
        mock_transcriber = AsyncMock()
        mock_transcriber.transcribe.return_value = long_transcript
        mock_get_transcriber.return_value = mock_transcriber

        request = VoiceTranscribeRequest(
            audio_data=_make_audio_b64(),
            media_type="audio/wav",
        )
        with pytest.raises(AudioValidationError, match="exceeds"):
            await self.service.transcribe(request)


class TestBriefFormatting:
    """Test brief-to-blueprint text formatting."""

    def test_format_with_sections(self) -> None:
        brief = _make_brief()
        text = VoiceBriefService._format_brief_for_blueprint(brief)
        assert "Black Friday Sale" in text
        assert "hero:" in text
        assert "Shop Now" in text
        assert "existing customers" in text
        assert "countdown timer" in text

    def test_format_raw_transcript_fallback(self) -> None:
        brief = EmailBrief(
            topic="Voice brief",
            sections=[],
            tone="professional",
            raw_transcript="just some raw text here",
        )
        text = VoiceBriefService._format_brief_for_blueprint(brief)
        assert "just some raw text here" in text
