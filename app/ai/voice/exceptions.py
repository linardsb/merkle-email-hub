"""Voice pipeline exceptions."""

from app.ai.exceptions import AIError


class VoiceError(AIError):
    """Base exception for voice pipeline errors."""


class VoiceDisabledError(VoiceError):
    """Voice input feature is disabled (501)."""


class AudioValidationError(VoiceError):
    """Invalid audio file (format, duration, size) (422)."""


class TranscriptionError(VoiceError):
    """Transcription failed (502)."""


class BriefExtractionError(VoiceError):
    """Brief extraction from transcript failed (502)."""
