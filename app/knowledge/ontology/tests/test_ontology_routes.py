"""Tests for ontology REST endpoints."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.main import app


def _make_user(role: str = "developer") -> User:
    """Create a mock user."""
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


@pytest.fixture
def _auth_developer() -> Generator[None]:
    """Override auth to return a developer user."""
    user = _make_user("developer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient]:
    """Unauthenticated test client."""
    limiter.enabled = False
    with TestClient(app) as c:
        yield c
    limiter.enabled = True


@pytest.fixture
def authenticated_client(_auth_developer: None) -> Generator[TestClient]:
    """Authenticated test client."""
    limiter.enabled = False
    with TestClient(app) as c:
        yield c
    limiter.enabled = True


class TestCompetitiveReportEndpoint:
    """Test GET /api/v1/ontology/competitive-report."""

    def test_unauthenticated_returns_401(self, client: TestClient) -> None:
        """No auth token → 401."""
        resp = client.get("/api/v1/ontology/competitive-report")
        assert resp.status_code in (401, 403)

    def test_basic_report(self, authenticated_client: TestClient) -> None:
        """Authenticated request returns report structure."""
        resp = authenticated_client.get("/api/v1/ontology/competitive-report")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_capabilities" in data
        assert "hub_advantages" in data
        assert "gaps" in data

    def test_with_client_ids(self, authenticated_client: TestClient) -> None:
        """Query params filter by audience."""
        resp = authenticated_client.get(
            "/api/v1/ontology/competitive-report",
            params={"client_ids": ["gmail_web", "outlook_2019_win"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["audience_client_ids"] == ["gmail_web", "outlook_2019_win"]

    def test_with_competitor_filter(self, authenticated_client: TestClient) -> None:
        """competitor_id filters to single competitor."""
        resp = authenticated_client.get(
            "/api/v1/ontology/competitive-report",
            params={"competitor_id": "stripo"},
        )
        assert resp.status_code == 200

    def test_text_report(self, authenticated_client: TestClient) -> None:
        """Text report endpoint returns formatted report."""
        resp = authenticated_client.get("/api/v1/ontology/competitive-report/text")
        assert resp.status_code == 200
        assert "report" in resp.json()
