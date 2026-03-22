"""Route tests for sandbox endpoints — auth, feature-flag, happy path."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.main import app
from app.rendering.exceptions import SandboxUnavailableError
from app.rendering.sandbox.schemas import (
    SandboxDOMDiff,
    SandboxHealthResponse,
    SandboxProfileResult,
    SandboxTestResponse,
)

BASE = "/api/v1/rendering/sandbox"

# Email-structure HTML for test payloads
_EMAIL_HTML = (
    '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
    '<tr><td style="color: #333333; font-family: Arial, sans-serif;">Hello</td></tr>'
    "</table>"
)


def _make_user(role: str = "admin") -> User:
    user = User(email="admin@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


@pytest.fixture(autouse=True)
def _disable_rate_limit() -> Generator[None, None, None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


class TestSandboxTestEndpoint:
    def test_requires_admin(self, client: TestClient) -> None:
        viewer = _make_user(role="viewer")
        app.dependency_overrides[get_current_user] = lambda: viewer
        try:
            resp = client.post(f"{BASE}/test", json={"html": _EMAIL_HTML})
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_rejects_unauthenticated(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/test", json={"html": _EMAIL_HTML})
        assert resp.status_code in (401, 403)

    @patch("app.rendering.routes.run_sandbox_test", new_callable=AsyncMock)
    def test_happy_path(self, mock_run: AsyncMock, client: TestClient) -> None:
        admin = _make_user(role="admin")
        app.dependency_overrides[get_current_user] = lambda: admin
        try:
            mock_run.return_value = SandboxTestResponse(
                message_id="<test@sandbox.local>",
                results=[
                    SandboxProfileResult(
                        profile="mailpit",
                        rendered_html=_EMAIL_HTML,
                        dom_diff=SandboxDOMDiff(),
                    )
                ],
            )
            resp = client.post(
                f"{BASE}/test",
                json={"html": _EMAIL_HTML, "profiles": ["mailpit"]},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["message_id"] == "<test@sandbox.local>"
            assert len(body["results"]) == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.rendering.routes.run_sandbox_test", new_callable=AsyncMock)
    def test_disabled_returns_503(self, mock_run: AsyncMock, client: TestClient) -> None:
        admin = _make_user(role="admin")
        app.dependency_overrides[get_current_user] = lambda: admin
        try:
            mock_run.side_effect = SandboxUnavailableError("Sandbox disabled")
            resp = client.post(f"{BASE}/test", json={"html": _EMAIL_HTML})
            assert resp.status_code == 503
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestSandboxHealthEndpoint:
    def test_requires_admin(self, client: TestClient) -> None:
        viewer = _make_user(role="viewer")
        app.dependency_overrides[get_current_user] = lambda: viewer
        try:
            resp = client.get(f"{BASE}/health")
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.rendering.routes.check_sandbox_health", new_callable=AsyncMock)
    def test_disabled_sandbox(self, mock_health: AsyncMock, client: TestClient) -> None:
        admin = _make_user(role="admin")
        app.dependency_overrides[get_current_user] = lambda: admin
        try:
            mock_health.return_value = SandboxHealthResponse(sandbox_enabled=False)
            resp = client.get(f"{BASE}/health")
            assert resp.status_code == 200
            assert resp.json()["sandbox_enabled"] is False
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    @patch("app.rendering.routes.check_sandbox_health", new_callable=AsyncMock)
    def test_healthy_sandbox(self, mock_health: AsyncMock, client: TestClient) -> None:
        admin = _make_user(role="admin")
        app.dependency_overrides[get_current_user] = lambda: admin
        try:
            mock_health.return_value = SandboxHealthResponse(
                sandbox_enabled=True,
                mailpit_reachable=True,
                roundcube_reachable=True,
                smtp_reachable=True,
            )
            resp = client.get(f"{BASE}/health")
            assert resp.status_code == 200
            body = resp.json()
            assert body["sandbox_enabled"] is True
            assert body["mailpit_reachable"] is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)
