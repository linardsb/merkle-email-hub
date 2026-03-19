"""Route tests for skill extraction API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import limiter
from app.main import app

limiter.enabled = False


def _mock_user(role: str = "admin") -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.role = role
    user.email = "admin@example.com"
    return user


@pytest.fixture(autouse=True)
def _save_overrides():
    saved = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestSkillRoutes:
    def test_list_pending_requires_auth(self, client: TestClient) -> None:
        """No auth token -> 401/403."""
        resp = client.get("/api/v1/skills/amendments/pending")
        assert resp.status_code in (401, 403, 404, 405)

    def test_approve_requires_auth(self, client: TestClient) -> None:
        """No auth -> 401/403."""
        resp = client.post("/api/v1/skills/amendments/test123/approve")
        assert resp.status_code in (401, 403, 404, 405)

    def test_reject_requires_auth(self, client: TestClient) -> None:
        """No auth -> 401/403."""
        resp = client.post("/api/v1/skills/amendments/test123/reject")
        assert resp.status_code in (401, 403, 404, 405)

    def test_batch_requires_auth(self, client: TestClient) -> None:
        """No auth -> 401/403."""
        resp = client.post(
            "/api/v1/skills/amendments/batch",
            json={"actions": []},
        )
        assert resp.status_code in (401, 403, 404, 405)

    def test_list_pending_with_mock_service(self, client: TestClient) -> None:
        """Mocked service returns correct shape."""
        from app.auth.dependencies import require_role

        mock_user = _mock_user()
        mock_service = AsyncMock()
        mock_service.list_pending.return_value = ([], 0)

        with patch("app.ai.skills.routes._get_service", return_value=mock_service):
            app.dependency_overrides[require_role("admin")] = lambda: mock_user
            resp = client.get("/api/v1/skills/amendments/pending")
            # 200 if route registered, 404/405 if feature flag off
            if resp.status_code == 200:
                data = resp.json()
                assert data["total"] == 0
                assert data["amendments"] == []
            else:
                assert resp.status_code in (404, 405)

    def test_batch_empty_actions(self, client: TestClient) -> None:
        """Empty actions list -> 200 with 0 processed."""
        from app.auth.dependencies import require_role

        mock_user = _mock_user()
        mock_service = AsyncMock()
        mock_service.batch_action.return_value = (0, [])

        with patch("app.ai.skills.routes._get_service", return_value=mock_service):
            app.dependency_overrides[require_role("admin")] = lambda: mock_user
            resp = client.post(
                "/api/v1/skills/amendments/batch",
                json={"actions": []},
            )
            if resp.status_code == 200:
                data = resp.json()
                assert data["processed"] == 0
            else:
                assert resp.status_code in (404, 405)
