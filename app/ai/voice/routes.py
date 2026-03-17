"""Voice brief input pipeline routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.voice.schemas import (
    EmailBrief,
    EmailBriefResponse,
    Transcript,
    TranscriptResponse,
    VoiceBriefRequest,
    VoiceBriefResponse,
    VoiceRunRequest,
    VoiceTranscribeRequest,
)
from app.ai.voice.service import VoiceBriefService, get_voice_service
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limit import limiter

logger = get_logger(__name__)

settings = get_settings()

router = APIRouter(prefix="/v1/ai/voice", tags=["voice"])


def _transcript_to_response(transcript: Transcript) -> TranscriptResponse:
    """Convert internal Transcript to API response."""
    return TranscriptResponse(
        text=transcript.text,
        language=transcript.language,
        duration_seconds=transcript.duration_seconds,
        segments=[{"start": s.start, "end": s.end, "text": s.text} for s in transcript.segments],
    )


def _brief_to_response(brief: EmailBrief) -> EmailBriefResponse:
    """Convert internal EmailBrief to API response."""
    return EmailBriefResponse(
        topic=brief.topic,
        sections=[
            {
                "type": s.type,
                "description": s.description,
                "content_hints": s.content_hints,
            }
            for s in brief.sections
        ],
        tone=brief.tone,
        cta_text=brief.cta_text,
        audience=brief.audience,
        constraints=brief.constraints,
    )


@router.post("/transcribe", response_model=TranscriptResponse)
@limiter.limit(settings.voice.rate_limit_transcribe)
async def transcribe_audio(
    request: Request,
    body: VoiceTranscribeRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
    service: VoiceBriefService = Depends(get_voice_service),  # noqa: B008
) -> TranscriptResponse:
    """Transcribe audio to text. Returns transcript only."""
    _ = request
    transcript = await service.transcribe(body)
    return _transcript_to_response(transcript)


@router.post("/brief", response_model=VoiceBriefResponse)
@limiter.limit(settings.voice.rate_limit_brief)
async def extract_voice_brief(
    request: Request,
    body: VoiceBriefRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
    service: VoiceBriefService = Depends(get_voice_service),  # noqa: B008
) -> VoiceBriefResponse:
    """Transcribe audio and extract structured email brief."""
    _ = request
    transcript, brief, confidence = await service.extract_brief(body)
    return VoiceBriefResponse(
        transcript=_transcript_to_response(transcript),
        brief=_brief_to_response(brief),
        confidence=confidence,
    )


@router.post("/run")
@limiter.limit(settings.voice.rate_limit_run)
async def run_voice_pipeline(
    request: Request,
    body: VoiceRunRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
    service: VoiceBriefService = Depends(get_voice_service),  # noqa: B008
) -> dict[str, object]:
    """Full pipeline: transcribe → extract brief → execute blueprint run."""
    _ = request
    transcript, brief, confidence, run_response = await service.run_pipeline(
        body, user=current_user, db=db
    )
    return {
        "transcript": _transcript_to_response(transcript).model_dump(),
        "brief": _brief_to_response(brief).model_dump(),
        "confidence": confidence,
        "run": run_response.model_dump() if hasattr(run_response, "model_dump") else run_response,
    }
