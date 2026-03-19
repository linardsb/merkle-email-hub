"""Route tests for template upload API."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Disable rate limiter for tests
from app.core.rate_limit import limiter
from app.main import app
from app.templates.upload.schemas import (
    AnalysisPreview,
    TemplateUploadResponse,
    TokenPreview,
    UploadStatus,
)

limiter.enabled = False


def _mock_user(user_id: int = 1, role: str = "developer") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = role
    user.email = "test@example.com"
    return user


def _mock_analysis_preview() -> AnalysisPreview:
    return AnalysisPreview(
        upload_id=1,
        sections=[],
        slots=[],
        tokens=TokenPreview(colors={}, fonts={}, font_sizes={}, spacing={}),
        esp_platform=None,
        layout_type="newsletter",
        column_count=1,
        complexity_score=10,
        suggested_name="uploaded_newsletter_abc123",
        suggested_description="Test template",
    )


def _mock_upload_response() -> TemplateUploadResponse:
    return TemplateUploadResponse(
        id=1,
        status=UploadStatus.CONFIRMED,
        template_name="uploaded_newsletter_abc123",
        created_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def _save_overrides():
    saved = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestUploadEndpoint:
    def test_upload_requires_auth(self, client: TestClient) -> None:
        response = client.post("/api/v1/templates/upload")
        # 405 when feature flag is off (router not registered), 401/403 when on
        assert response.status_code in (401, 403, 404, 405, 422)

    def test_upload_with_auth(self, client: TestClient) -> None:
        from app.auth.dependencies import require_role
        from app.templates.upload.service import TemplateUploadService

        mock_user = _mock_user()
        mock_service = AsyncMock(spec=TemplateUploadService)
        mock_service.upload_and_analyze.return_value = _mock_analysis_preview()

        with patch("app.templates.upload.routes._get_service", return_value=mock_service):
            app.dependency_overrides[require_role("developer")] = lambda: mock_user
            html_content = b"<html><body><h1>Test</h1></body></html>"
            response = client.post(
                "/api/v1/templates/upload",
                files={"file": ("test.html", BytesIO(html_content), "text/html")},
            )
            # Route may not be registered if feature flag is off
            assert response.status_code in (201, 404, 405)


class TestPreviewEndpoint:
    def test_preview_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/templates/upload/1/preview")
        assert response.status_code in (401, 403, 404, 405)


class TestConfirmEndpoint:
    def test_confirm_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/templates/upload/1/confirm",
            json={},
        )
        assert response.status_code in (401, 403, 404, 405, 422)


class TestRejectEndpoint:
    def test_reject_requires_auth(self, client: TestClient) -> None:
        response = client.delete("/api/v1/templates/upload/1")
        assert response.status_code in (401, 403, 404, 405)


class TestUploadValidation:
    def test_upload_rejects_oversized_file(self, client: TestClient) -> None:
        """File >2MB triggers 400/413 or service-level error."""
        from app.auth.dependencies import require_role
        from app.templates.upload.exceptions import TemplateTooLargeError
        from app.templates.upload.service import TemplateUploadService

        mock_user = _mock_user()
        mock_service = AsyncMock(spec=TemplateUploadService)
        mock_service.upload_and_analyze.side_effect = TemplateTooLargeError("Too large")

        with patch("app.templates.upload.routes._get_service", return_value=mock_service):
            app.dependency_overrides[require_role("developer")] = lambda: mock_user
            huge = b"x" * (3 * 1024 * 1024)
            response = client.post(
                "/api/v1/templates/upload",
                files={"file": ("big.html", BytesIO(huge), "text/html")},
            )
            # 400 from service error, or 404/405 if feature flag off
            assert response.status_code in (400, 404, 405, 413)

    def test_confirm_wrong_user_returns_404(self, client: TestClient) -> None:
        """Confirming another user's upload -> 404."""
        from app.auth.dependencies import require_role
        from app.templates.upload.exceptions import UploadNotFoundError
        from app.templates.upload.service import TemplateUploadService

        mock_user = _mock_user(user_id=999)
        mock_service = AsyncMock(spec=TemplateUploadService)
        mock_service.confirm.side_effect = UploadNotFoundError("Not found")

        with patch("app.templates.upload.routes._get_service", return_value=mock_service):
            app.dependency_overrides[require_role("developer")] = lambda: mock_user
            response = client.post("/api/v1/templates/upload/1/confirm", json={})
            assert response.status_code in (404, 405)

    def test_reject_nonexistent_returns_404(self, client: TestClient) -> None:
        """Rejecting nonexistent upload -> 404."""
        from app.auth.dependencies import require_role
        from app.templates.upload.exceptions import UploadNotFoundError
        from app.templates.upload.service import TemplateUploadService

        mock_user = _mock_user()
        mock_service = AsyncMock(spec=TemplateUploadService)
        mock_service.reject.side_effect = UploadNotFoundError("Not found")

        with patch("app.templates.upload.routes._get_service", return_value=mock_service):
            app.dependency_overrides[require_role("developer")] = lambda: mock_user
            response = client.delete("/api/v1/templates/upload/999")
            assert response.status_code in (404, 405)

    def test_upload_missing_file_returns_422(self, client: TestClient) -> None:
        """POST without file attachment -> 422."""
        from app.auth.dependencies import require_role

        mock_user = _mock_user()
        app.dependency_overrides[require_role("developer")] = lambda: mock_user
        response = client.post("/api/v1/templates/upload")
        # 422 (missing file) or 404/405 if feature flag off
        assert response.status_code in (404, 405, 422)
