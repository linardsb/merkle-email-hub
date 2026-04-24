"""Audio transcription providers."""

from __future__ import annotations

import io
from typing import Any, Protocol, cast, runtime_checkable

from app.ai.voice.exceptions import TranscriptionError
from app.ai.voice.schemas import Transcript, TranscriptSegment
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class VoiceTranscriber(Protocol):
    """Protocol for audio transcription providers."""

    async def transcribe(
        self, audio: bytes, media_type: str, *, language: str | None = None
    ) -> Transcript: ...


# ── Format mapping ──

_MIME_TO_EXT: dict[str, str] = {
    "audio/wav": "wav",
    "audio/mp3": "mp3",
    "audio/mpeg": "mp3",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
}


# ── Whisper API Transcriber ──


class WhisperAPITranscriber:
    """Transcription via OpenAI Whisper API."""

    def __init__(self) -> None:
        import openai

        settings = get_settings()
        api_key = settings.ai.api_key
        if not api_key:
            from app.ai.exceptions import AIConfigurationError

            raise AIConfigurationError("AI__API_KEY required for Whisper API transcription")

        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = settings.voice.whisper_model

    async def transcribe(
        self, audio: bytes, media_type: str, *, language: str | None = None
    ) -> Transcript:
        """Transcribe audio via OpenAI Whisper API."""
        ext = _MIME_TO_EXT.get(media_type, "wav")

        try:
            create_kwargs: dict[str, Any] = {
                "model": self._model,
                "file": (f"audio.{ext}", io.BytesIO(audio), media_type),
                "response_format": "verbose_json",
                "timestamp_granularities": ["segment"],
            }
            if language:
                create_kwargs["language"] = language
            response_raw: Any = cast(
                Any, await self._client.audio.transcriptions.create(**create_kwargs)
            )
        except TranscriptionError:
            raise
        except Exception as exc:
            logger.error("voice.transcribe.api_failed", error=str(exc))
            raise TranscriptionError(f"Whisper API transcription failed: {exc}") from exc

        response = response_raw
        segments_raw: list[Any] = response.segments or []
        segments = [
            TranscriptSegment(
                start=float(getattr(s, "start", 0.0)),
                end=float(getattr(s, "end", 0.0)),
                text=str(getattr(s, "text", "")).strip(),
            )
            for s in segments_raw
        ]

        text: str = str(response.text or "")
        lang: str = str(response.language or "en")
        duration: float = float(response.duration or 0.0)

        logger.info(
            "voice.transcribe.completed",
            provider="whisper_api",
            duration_seconds=duration,
            language=lang,
            text_length=len(text),
        )

        return Transcript(
            text=text.strip(),
            language=lang,
            duration_seconds=float(duration),
            segments=segments,
        )


# ── Whisper Local Transcriber ──


class WhisperLocalTranscriber:
    """Transcription via local openai-whisper model (requires openai-whisper package)."""

    def __init__(self) -> None:
        try:
            import whisper  # type: ignore[import-not-found]  # noqa: F401
        except ImportError as exc:
            from app.ai.exceptions import AIConfigurationError

            raise AIConfigurationError(
                "openai-whisper package required for local transcription. "
                "Install: pip install openai-whisper"
            ) from exc

        settings = get_settings()
        model_name = settings.voice.whisper_local_model
        logger.info("voice.transcribe.loading_local_model", model=model_name)
        self._model: Any = __import__("whisper").load_model(model_name)

    async def transcribe(
        self, audio: bytes, media_type: str, *, language: str | None = None
    ) -> Transcript:
        """Transcribe audio via local Whisper model."""
        import tempfile
        from pathlib import Path

        import anyio

        ext = _MIME_TO_EXT.get(media_type, "wav")

        # Whisper requires file path — write to temp file, process, delete
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(audio)
        try:
            # Run CPU-bound whisper in thread pool
            model = self._model

            def _transcribe() -> dict[str, Any]:
                import whisper  # type: ignore[import-not-found,unused-ignore]

                return whisper.transcribe(  # type: ignore[no-any-return]
                    model,
                    str(tmp_path),
                    **({"language": language} if language else {}),
                )

            result_raw = await anyio.to_thread.run_sync(_transcribe)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType,reportAttributeAccessIssue]
            result = cast(dict[str, Any], result_raw)  # type: ignore[redundant-cast]
        except TranscriptionError:
            raise
        except Exception as exc:
            logger.error("voice.transcribe.local_failed", error=str(exc))
            raise TranscriptionError(f"Local Whisper transcription failed: {exc}") from exc
        finally:
            tmp_path.unlink(missing_ok=True)

        raw_segments = cast(
            list[dict[str, Any]],
            [s for s in result.get("segments", []) if isinstance(s, dict)],
        )
        segments = [
            TranscriptSegment(
                start=float(s.get("start", 0)),
                end=float(s.get("end", 0)),
                text=str(s.get("text", "")).strip(),
            )
            for s in raw_segments
        ]

        text = str(result.get("text", ""))
        lang = str(result.get("language", "en"))

        # Estimate duration from last segment
        duration = segments[-1].end if segments else 0.0

        logger.info(
            "voice.transcribe.completed",
            provider="whisper_local",
            duration_seconds=duration,
            language=lang,
            text_length=len(text),
        )

        return Transcript(
            text=text.strip(),
            language=lang,
            duration_seconds=duration,
            segments=segments,
        )


# ── Factory ──

_transcriber: VoiceTranscriber | None = None


def get_transcriber() -> VoiceTranscriber:
    """Get configured transcriber singleton."""
    global _transcriber
    if _transcriber is None:
        settings = get_settings()
        provider = settings.voice.transcriber
        if provider == "whisper_local":
            _transcriber = WhisperLocalTranscriber()
        else:
            _transcriber = WhisperAPITranscriber()
        logger.info("voice.transcriber.initialized", provider=provider)
    return _transcriber
