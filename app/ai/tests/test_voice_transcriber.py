"""Voice transcriber unit tests (WhisperAPI + WhisperLocal)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.voice.exceptions import TranscriptionError
from app.ai.voice.schemas import Transcript
from app.ai.voice.transcriber import WhisperAPITranscriber, WhisperLocalTranscriber

# ── Helpers ──


def _make_api_transcriber(client: AsyncMock) -> WhisperAPITranscriber:
    """Create WhisperAPITranscriber bypassing __init__ (which needs openai)."""
    t = WhisperAPITranscriber.__new__(WhisperAPITranscriber)
    t._client = client
    t._model = "whisper-1"
    return t


def _make_local_transcriber() -> WhisperLocalTranscriber:
    """Create WhisperLocalTranscriber bypassing __init__ (which needs whisper package)."""
    t = WhisperLocalTranscriber.__new__(WhisperLocalTranscriber)
    t._model = MagicMock()
    return t


# ── WhisperAPITranscriber Tests ──


class TestWhisperAPITranscriber:
    """Test OpenAI Whisper API transcriber."""

    @pytest.mark.anyio
    async def test_transcribe_success(self) -> None:
        """Successful transcription returns Transcript with all fields."""
        mock_response = MagicMock()
        mock_response.text = "Hello, this is a test brief."
        mock_response.language = "en"
        mock_response.duration = 5.2
        mock_response.segments = [
            MagicMock(start=0.0, end=2.5, text="Hello, this is"),
            MagicMock(start=2.5, end=5.2, text="a test brief."),
        ]

        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        transcriber = _make_api_transcriber(mock_client)
        result = await transcriber.transcribe(b"fake-audio", "audio/wav")
        assert isinstance(result, Transcript)
        assert result.text == "Hello, this is a test brief."
        assert result.language == "en"
        assert result.duration_seconds == pytest.approx(5.2)
        assert len(result.segments) == 2

    @pytest.mark.anyio
    async def test_transcribe_extracts_segments(self) -> None:
        """Segments are extracted with correct start/end/text mapping."""
        mock_response = MagicMock()
        mock_response.text = "First. Second. Third."
        mock_response.language = "en"
        mock_response.duration = 9.0
        mock_response.segments = [
            MagicMock(start=0.0, end=3.0, text="First."),
            MagicMock(start=3.0, end=6.0, text="Second."),
            MagicMock(start=6.0, end=9.0, text="Third."),
        ]

        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        transcriber = _make_api_transcriber(mock_client)
        result = await transcriber.transcribe(b"fake-audio", "audio/wav")
        assert len(result.segments) == 3
        assert result.segments[0].start == 0.0
        assert result.segments[1].end == 6.0
        assert result.segments[2].text == "Third."

    @pytest.mark.anyio
    async def test_transcribe_passes_language_hint(self) -> None:
        """Language hint is forwarded to the API call."""
        mock_response = MagicMock()
        mock_response.text = "Bonjour"
        mock_response.language = "fr"
        mock_response.duration = 1.0
        mock_response.segments = []

        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        transcriber = _make_api_transcriber(mock_client)
        await transcriber.transcribe(b"fake-audio", "audio/wav", language="fr")
        call_kwargs = mock_client.audio.transcriptions.create.call_args
        # language is passed as a kwarg
        assert call_kwargs.kwargs.get("language") == "fr"

    @pytest.mark.anyio
    async def test_transcribe_api_error_raises_transcription_error(self) -> None:
        """API exception is wrapped in TranscriptionError."""
        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(side_effect=RuntimeError("API down"))

        transcriber = _make_api_transcriber(mock_client)
        with pytest.raises(TranscriptionError, match="Whisper API"):
            await transcriber.transcribe(b"fake-audio", "audio/wav")


# ── WhisperLocalTranscriber Tests ──


class TestWhisperLocalTranscriber:
    """Test local Whisper model transcriber."""

    @pytest.mark.anyio
    async def test_transcribe_success(self) -> None:
        """Successful local transcription returns Transcript."""
        mock_whisper_result: dict[str, object] = {
            "text": "Hello from local whisper",
            "language": "en",
            "segments": [
                {"start": 0.0, "end": 3.0, "text": "Hello from"},
                {"start": 3.0, "end": 5.0, "text": "local whisper"},
            ],
        }

        transcriber = _make_local_transcriber()

        with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_whisper_result
            result = await transcriber.transcribe(b"fake-audio", "audio/wav")
            assert isinstance(result, Transcript)
            assert result.text == "Hello from local whisper"
            assert len(result.segments) == 2

    @pytest.mark.anyio
    async def test_transcribe_writes_and_cleans_temp_file(self) -> None:
        """Transcription creates temp file and cleans it up."""
        mock_whisper_result: dict[str, object] = {
            "text": "test",
            "language": "en",
            "segments": [],
        }

        transcriber = _make_local_transcriber()

        with (
            patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_thread,
            patch("tempfile.NamedTemporaryFile") as mock_tmp,
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            mock_tmp.return_value.name = "/tmp/audio.wav"
            mock_thread.return_value = mock_whisper_result

            await transcriber.transcribe(b"fake-audio", "audio/wav")
            mock_unlink.assert_called_once_with(missing_ok=True)

    @pytest.mark.anyio
    async def test_transcribe_runs_in_thread(self) -> None:
        """CPU-bound transcription runs via anyio.to_thread.run_sync."""
        mock_whisper_result: dict[str, object] = {
            "text": "threaded",
            "language": "en",
            "segments": [],
        }

        transcriber = _make_local_transcriber()

        with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_whisper_result
            await transcriber.transcribe(b"fake-audio", "audio/wav")
            mock_thread.assert_called_once()

    @pytest.mark.anyio
    async def test_transcribe_model_error_raises_transcription_error(self) -> None:
        """Model exception is wrapped in TranscriptionError."""
        transcriber = _make_local_transcriber()

        with patch(
            "anyio.to_thread.run_sync",
            new_callable=AsyncMock,
            side_effect=RuntimeError("CUDA error"),
        ):
            with pytest.raises(TranscriptionError, match="Local Whisper"):
                await transcriber.transcribe(b"fake-audio", "audio/wav")
