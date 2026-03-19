# pyright: reportUnknownMemberType=false
"""Route tests for Tolgee TMS endpoints."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.connectors.tolgee.routes import router
from app.core.database import get_db
from app.core.rate_limit import limiter


def _make_user(role: str = "developer") -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.email = "dev@test.com"
    user.role = role
    return user


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.include_router(router)
    return test_app


@pytest.fixture(autouse=True)
def _setup(app: FastAPI) -> Generator[None]:
    limiter.enabled = False
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestTolgeeRoutes:
    """Tests for Tolgee API endpoints."""

    def test_create_connection_201(self, client: TestClient) -> None:
        """POST /connect returns 201 with connection response."""
        from app.connectors.tolgee.schemas import TolgeeConnectionResponse

        mock_response = TolgeeConnectionResponse(
            id=1,
            name="Test",
            status="connected",
            credentials_hint="****test",
            tolgee_project_id=42,
            project_id=1,
            created_at=datetime.now(UTC),
        )

        with patch("app.connectors.tolgee.routes.TolgeeService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.create_connection.return_value = mock_response
            mock_svc_cls.return_value = mock_svc

            response = client.post(
                "/api/v1/connectors/tolgee/connect",
                json={
                    "name": "Test",
                    "project_id": 1,
                    "tolgee_project_id": 42,
                    "pat": "tgpat_test",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test"
        assert data["status"] == "connected"

    def test_sync_keys_200(self, client: TestClient) -> None:
        """POST /sync-keys returns 200 with sync result."""
        from app.connectors.tolgee.schemas import PushResult, TranslationSyncResponse

        mock_response = TranslationSyncResponse(
            keys_extracted=15,
            push_result=PushResult(created=10, updated=5),
            template_id=5,
        )

        with patch("app.connectors.tolgee.routes.TolgeeService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.sync_keys.return_value = mock_response
            mock_svc_cls.return_value = mock_svc

            response = client.post(
                "/api/v1/connectors/tolgee/sync-keys",
                json={"connection_id": 1, "template_id": 5},
            )

        assert response.status_code == 200
        assert response.json()["keys_extracted"] == 15

    def test_get_languages_200(self, app: FastAPI, client: TestClient) -> None:
        """GET /connections/{id}/languages returns language list."""
        from app.connectors.tolgee.schemas import TolgeeLanguage

        # This endpoint requires "viewer" role
        app.dependency_overrides[get_current_user] = lambda: _make_user("viewer")

        mock_languages = [
            TolgeeLanguage(id=1, tag="en", name="English", base=True),
            TolgeeLanguage(id=2, tag="de", name="German"),
        ]

        with patch("app.connectors.tolgee.routes.TolgeeService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_languages.return_value = mock_languages
            mock_svc_cls.return_value = mock_svc

            response = client.get("/api/v1/connectors/tolgee/connections/1/languages")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["tag"] == "en"
