"""Voice pipeline exceptions."""

from app.ai.exceptions import AIError


class VoiceError(AIError):
    """Base exception for voice pipeline errors."""

    pass


class VoiceDisabledError(VoiceError):
    """Voice input feature is disabled (501)."""

    pass


class AudioValidationError(VoiceError):
    """Invalid audio file (format, duration, size) (422)."""

    pass


class TranscriptionError(VoiceError):
    """Transcription failed (502)."""

    pass


class BriefExtractionError(VoiceError):
    """Brief extraction from transcript failed (502)."""

    pass
