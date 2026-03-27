"""Voice brief input pipeline schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

# ── Dataclasses (internal, frozen) ──


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """Timestamped transcript segment for UI playback sync."""

    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class Transcript:
    """Result of audio transcription."""

    text: str
    language: str
    duration_seconds: float
    segments: list[TranscriptSegment] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SectionBrief:
    """Extracted section from voice brief."""

    type: str  # hero, content_block, cta, footer, etc.
    description: str
    content_hints: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EmailBrief:
    """Structured email brief extracted from transcript."""

    topic: str
    sections: list[SectionBrief]
    tone: str
    cta_text: str | None = None
    audience: str | None = None
    constraints: list[str] = field(default_factory=list)
    raw_transcript: str = ""


# ── Pydantic models (API boundary) ──

ALLOWED_AUDIO_FORMATS = Literal["audio/wav", "audio/mp3", "audio/webm", "audio/ogg", "audio/mpeg"]


class VoiceTranscribeRequest(BaseModel):
    """Request to transcribe audio."""

    audio_data: str = Field(description="Base64-encoded audio file", min_length=1)
    media_type: ALLOWED_AUDIO_FORMATS = Field(description="Audio MIME type")
    language: str | None = Field(default=None, description="BCP-47 language hint (e.g. 'en')")


class TranscriptResponse(BaseModel):
    """Transcription result."""

    text: str
    language: str
    duration_seconds: float
    segments: list[dict[str, float | str]] = Field(default_factory=list)


class VoiceBriefRequest(BaseModel):
    """Request to transcribe audio and extract structured brief."""

    audio_data: str = Field(description="Base64-encoded audio file", min_length=1)
    media_type: ALLOWED_AUDIO_FORMATS = Field(description="Audio MIME type")
    language: str | None = Field(default=None, description="BCP-47 language hint")


class EmailBriefResponse(BaseModel):
    """Extracted email brief."""

    topic: str
    sections: list[dict[str, object]]
    tone: str
    cta_text: str | None = None
    audience: str | None = None
    constraints: list[str] = Field(default_factory=list)


class VoiceBriefResponse(BaseModel):
    """Transcription + extracted brief."""

    transcript: TranscriptResponse
    brief: EmailBriefResponse
    confidence: float


class VoiceRunRequest(BaseModel):
    """Request to transcribe audio, extract brief, and trigger blueprint run."""

    audio_data: str = Field(description="Base64-encoded audio file", min_length=1)
    media_type: ALLOWED_AUDIO_FORMATS = Field(description="Audio MIME type")
    language: str | None = Field(default=None, description="BCP-47 language hint")
    blueprint_name: str = Field(default="campaign", description="Blueprint to execute")
    project_id: int | None = Field(default=None, description="Project for design system context")
    persona_ids: list[int] = Field(default_factory=list, description="Target audience personas")
    template_id: int | None = Field(default=None, description="Existing template to version")
