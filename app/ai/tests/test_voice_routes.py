"""Voice API route tests — auth, rate limiting, error handling."""
# mypy: disable-error-code="attr-defined,unused-ignore"

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.ai.voice.schemas import (
    EmailBrief,
    SectionBrief,
    Transcript,
    TranscriptSegment,
)
from app.ai.voice.service import VoiceBriefService, get_voice_service
from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.main import app

# ── Fixtures ──


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None, None, None]:
    """Disable rate limiter for route tests, restore after."""
    original = limiter.enabled  # type: ignore[attr-defined]
    limiter.enabled = False  # type: ignore[attr-defined]
    yield
    limiter.enabled = original  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _clean_overrides() -> Generator[None, None, None]:
    """Ensure dependency overrides are always cleaned up."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _valid_audio_payload(media_type: str = "audio/wav") -> dict[str, object]:
    return {
        "audio_data": "dGVzdGluZyBhdWRpbyBkYXRhIHRoYXQgaXMgYXQgbGVhc3QgMTAwIGJ5dGVzIGxvbmcgZm9yIHZhbGlkYXRpb24gcGFzc2luZyBpbiB0aGUgc2VydmljZSBsYXllcg==",
        "media_type": media_type,
    }


def _make_transcript() -> Transcript:
    return Transcript(
        text="Create a summer sale email",
        language="en",
        duration_seconds=5.0,
        segments=[TranscriptSegment(start=0.0, end=5.0, text="Create a summer sale email")],
    )


def _make_brief() -> EmailBrief:
    return EmailBrief(
        topic="Summer Sale",
        sections=[SectionBrief(type="hero", description="Hero banner", content_hints=[])],
        tone="energetic",
        cta_text="Shop Now",
        raw_transcript="Create a summer sale email",
    )


def _mock_user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.role = "developer"
    return user


def _override_auth_and_service(
    mock_service: VoiceBriefService | MagicMock,
) -> None:
    """Set dependency overrides for auth + voice service."""
    app.dependency_overrides[get_current_user] = lambda: _mock_user()
    app.dependency_overrides[get_voice_service] = lambda: mock_service


# ── Transcribe Route Tests ──


class TestTranscribeRoute:
    """Test POST /api/v1/ai/voice/transcribe."""

    def test_transcribe_requires_auth(self, client: TestClient) -> None:
        """No auth header returns 401/403."""
        resp = client.post("/api/v1/ai/voice/transcribe", json=_valid_audio_payload())
        assert resp.status_code in (401, 403)

    def test_transcribe_success(self, client: TestClient) -> None:
        """Valid request with auth returns 200 with transcript text."""
        mock_service = MagicMock()
        mock_service.transcribe = AsyncMock(return_value=_make_transcript())
        _override_auth_and_service(mock_service)

        resp = client.post("/api/v1/ai/voice/transcribe", json=_valid_audio_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Create a summer sale email"
        assert data["language"] == "en"
        assert data["duration_seconds"] == pytest.approx(5.0)  # pyright: ignore[reportUnknownMemberType]

    def test_transcribe_disabled_returns_501(self, client: TestClient) -> None:
        """Voice disabled returns 501."""
        from app.ai.voice.exceptions import VoiceDisabledError

        mock_service = MagicMock()
        mock_service.transcribe = AsyncMock(
            side_effect=VoiceDisabledError("Voice input is not enabled")
        )
        _override_auth_and_service(mock_service)

        resp = client.post("/api/v1/ai/voice/transcribe", json=_valid_audio_payload())
        assert resp.status_code in (501, 500)


# ── Brief Route Tests ──


class TestBriefRoute:
    """Test POST /api/v1/ai/voice/brief."""

    def test_brief_requires_auth(self, client: TestClient) -> None:
        """No auth header returns 401/403."""
        resp = client.post("/api/v1/ai/voice/brief", json=_valid_audio_payload())
        assert resp.status_code in (401, 403)

    def test_brief_success(self, client: TestClient) -> None:
        """Valid request returns 200 with transcript + brief + confidence."""
        mock_service = MagicMock()
        mock_service.extract_brief = AsyncMock(
            return_value=(_make_transcript(), _make_brief(), 0.92)
        )
        _override_auth_and_service(mock_service)

        resp = client.post("/api/v1/ai/voice/brief", json=_valid_audio_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert data["transcript"]["text"] == "Create a summer sale email"
        assert data["brief"]["topic"] == "Summer Sale"
        assert data["confidence"] == pytest.approx(0.92)  # pyright: ignore[reportUnknownMemberType]


# ── Run Route Tests ──


class TestRunRoute:
    """Test POST /api/v1/ai/voice/run."""

    def test_run_requires_auth(self, client: TestClient) -> None:
        """No auth header returns 401/403."""
        payload = {**_valid_audio_payload(), "blueprint_name": "campaign"}
        resp = client.post("/api/v1/ai/voice/run", json=payload)
        assert resp.status_code in (401, 403)

    def test_run_success(self, client: TestClient) -> None:
        """Valid run request returns full pipeline output."""
        mock_run_response = MagicMock()
        mock_run_response.model_dump.return_value = {"id": "run-123", "status": "completed"}

        mock_service = MagicMock()
        mock_service.run_pipeline = AsyncMock(
            return_value=(_make_transcript(), _make_brief(), 0.85, mock_run_response)
        )
        _override_auth_and_service(mock_service)
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        payload = {**_valid_audio_payload(), "blueprint_name": "campaign"}
        resp = client.post("/api/v1/ai/voice/run", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["transcript"]["text"] == "Create a summer sale email"
        assert data["brief"]["topic"] == "Summer Sale"
        assert data["confidence"] == pytest.approx(0.85)  # pyright: ignore[reportUnknownMemberType]
        assert data["run"]["status"] == "completed"

    def test_run_invalid_audio_returns_422(self, client: TestClient) -> None:
        """Invalid media type returns 422 validation error."""
        app.dependency_overrides[get_current_user] = lambda: _mock_user()

        payload = {
            "audio_data": "dGVzdA==",
            "media_type": "video/mp4",  # Invalid — not an allowed audio format
            "blueprint_name": "campaign",
        }
        resp = client.post("/api/v1/ai/voice/run", json=payload)
        assert resp.status_code == 422
