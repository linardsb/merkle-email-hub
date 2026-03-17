"""Voice brief input pipeline service."""

from __future__ import annotations

import base64
import math
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.voice.brief_extractor import VoiceBriefExtractor
from app.ai.voice.exceptions import AudioValidationError, VoiceDisabledError
from app.ai.voice.schemas import (
    EmailBrief,
    Transcript,
    VoiceBriefRequest,
    VoiceRunRequest,
    VoiceTranscribeRequest,
)
from app.ai.voice.transcriber import get_transcriber
from app.auth.models import User
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Supported MIME types
_SUPPORTED_TYPES = frozenset(
    {
        "audio/wav",
        "audio/mp3",
        "audio/webm",
        "audio/ogg",
        "audio/mpeg",
    }
)


class VoiceBriefService:
    """Orchestrates voice brief pipeline: validate → transcribe → extract → run."""

    def __init__(self) -> None:
        self._extractor = VoiceBriefExtractor()

    def _ensure_enabled(self) -> None:
        """Raise if voice input is disabled."""
        settings = get_settings()
        if not settings.voice.enabled:
            raise VoiceDisabledError("Voice input is not enabled. Set VOICE__ENABLED=true.")

    def _decode_and_validate(self, audio_data: str, media_type: str) -> bytes:
        """Decode base64 audio and validate size/format."""
        settings = get_settings()

        if media_type not in _SUPPORTED_TYPES:
            raise AudioValidationError(
                f"Unsupported audio format: {media_type}. "
                f"Supported: {', '.join(sorted(_SUPPORTED_TYPES))}"
            )

        # Pre-check base64 size before decoding to prevent memory abuse
        max_bytes = settings.voice.max_file_size_mb * 1024 * 1024
        max_b64_len = math.ceil(max_bytes * 4 / 3) + 4  # base64 expands ~33%
        if len(audio_data) > max_b64_len:
            raise AudioValidationError(
                f"Audio file too large (max {settings.voice.max_file_size_mb}MB)"
            )

        try:
            audio_bytes = base64.b64decode(audio_data)
        except Exception as exc:
            raise AudioValidationError(f"Invalid base64 audio data: {exc}") from exc

        if len(audio_bytes) > max_bytes:
            raise AudioValidationError(
                f"Audio file too large: {len(audio_bytes) / 1024 / 1024:.1f}MB "
                f"(max {settings.voice.max_file_size_mb}MB)"
            )

        if len(audio_bytes) < 100:
            raise AudioValidationError("Audio file too small — likely empty or corrupt")

        return audio_bytes

    def _validate_duration(self, transcript: Transcript) -> None:
        """Validate transcript duration against configured maximum."""
        settings = get_settings()
        if transcript.duration_seconds > settings.voice.max_duration_s:
            raise AudioValidationError(
                f"Audio duration {transcript.duration_seconds:.0f}s exceeds "
                f"maximum {settings.voice.max_duration_s}s"
            )

    async def transcribe(self, request: VoiceTranscribeRequest) -> Transcript:
        """Transcribe audio to text."""
        self._ensure_enabled()
        audio_bytes = self._decode_and_validate(request.audio_data, request.media_type)

        transcriber = get_transcriber()
        transcript = await transcriber.transcribe(
            audio_bytes, request.media_type, language=request.language
        )
        self._validate_duration(transcript)
        return transcript

    async def extract_brief(
        self, request: VoiceBriefRequest
    ) -> tuple[Transcript, EmailBrief, float]:
        """Transcribe audio and extract structured brief."""
        self._ensure_enabled()
        audio_bytes = self._decode_and_validate(request.audio_data, request.media_type)

        transcriber = get_transcriber()
        transcript = await transcriber.transcribe(
            audio_bytes, request.media_type, language=request.language
        )
        self._validate_duration(transcript)

        brief, confidence = await self._extractor.extract(transcript)
        return transcript, brief, confidence

    async def run_pipeline(
        self,
        request: VoiceRunRequest,
        user: User,
        db: AsyncSession,
    ) -> tuple[Transcript, EmailBrief, float, Any]:
        """Full pipeline: transcribe → extract → blueprint run.

        Returns (transcript, brief, confidence, blueprint_run_response).
        """
        self._ensure_enabled()
        audio_bytes = self._decode_and_validate(request.audio_data, request.media_type)

        transcriber = get_transcriber()
        transcript = await transcriber.transcribe(
            audio_bytes, request.media_type, language=request.language
        )
        self._validate_duration(transcript)

        # Verify project access if project_id specified
        if request.project_id:
            from app.projects.service import ProjectService

            project_service = ProjectService(db)
            await project_service.verify_project_access(request.project_id, user)

        brief, confidence = await self._extractor.extract(transcript)

        # Build brief text for blueprint
        brief_text = self._format_brief_for_blueprint(brief)

        # Trigger blueprint run
        from app.ai.blueprints.schemas import BlueprintRunRequest
        from app.ai.blueprints.service import get_blueprint_service

        blueprint_service = get_blueprint_service()
        run_request = BlueprintRunRequest(
            blueprint_name=request.blueprint_name,
            brief=brief_text,
            options={"project_id": request.project_id} if request.project_id else {},
            persona_ids=request.persona_ids,
            template_id=request.template_id,
        )

        run_response = await blueprint_service.run(run_request, user_id=user.id, db=db)
        return transcript, brief, confidence, run_response

    @staticmethod
    def _format_brief_for_blueprint(brief: EmailBrief) -> str:
        """Convert structured EmailBrief to natural-language brief text."""
        parts: list[str] = []

        parts.append(f"Email campaign: {brief.topic}")

        if brief.audience:
            parts.append(f"Target audience: {brief.audience}")

        parts.append(f"Tone: {brief.tone}")

        if brief.sections:
            parts.append("\nRequested sections:")
            for i, section in enumerate(brief.sections, 1):
                line = f"{i}. {section.type}: {section.description}"
                if section.content_hints:
                    line += f" (hints: {', '.join(section.content_hints)})"
                parts.append(line)

        if brief.cta_text:
            parts.append(f"\nCall to action: {brief.cta_text}")

        if brief.constraints:
            parts.append(f"\nConstraints: {'; '.join(brief.constraints)}")

        # Append raw transcript for context
        if brief.raw_transcript and not brief.sections:
            parts.append(f"\nOriginal voice brief transcript:\n{brief.raw_transcript}")

        return "\n".join(parts)


# ── Singleton ──

_service: VoiceBriefService | None = None


def get_voice_service() -> VoiceBriefService:
    """Get or create VoiceBriefService singleton."""
    global _service
    if _service is None:
        _service = VoiceBriefService()
    return _service
