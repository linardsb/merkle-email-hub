"""Tests for ontology REST endpoints."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.knowledge.ontology.sync.schemas import SyncReport, SyncStatus
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
def _auth_admin() -> Generator[None]:
    """Override auth to return an admin user."""
    user = _make_user("admin")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _auth_viewer() -> Generator[None]:
    """Override auth to return a viewer user."""
    user = _make_user("viewer")
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


@pytest.fixture
def admin_client(_auth_admin: None) -> Generator[TestClient]:
    """Admin-authenticated test client."""
    limiter.enabled = False
    with TestClient(app) as c:
        yield c
    limiter.enabled = True


@pytest.fixture
def viewer_client(_auth_viewer: None) -> Generator[TestClient]:
    """Viewer-authenticated test client."""
    limiter.enabled = False
    with TestClient(app) as c:
        yield c
    limiter.enabled = True


class TestListEmailClientsEndpoint:
    """Test GET /api/v1/ontology/clients."""

    def test_unauthenticated_returns_401(self, client: TestClient) -> None:
        """No auth token → 401."""
        resp = client.get("/api/v1/ontology/clients")
        assert resp.status_code in (401, 403)

    def test_returns_client_list(self, authenticated_client: TestClient) -> None:
        """Authenticated request returns all ontology clients."""
        resp = authenticated_client.get("/api/v1/ontology/clients")
        assert resp.status_code == 200
        data: list[dict[str, object]] = resp.json()
        assert isinstance(data, list)
        assert len(data) == 25  # 25 clients in ontology

    def test_response_shape(self, authenticated_client: TestClient) -> None:
        """Each client has required fields with correct types."""
        resp = authenticated_client.get("/api/v1/ontology/clients")
        data: list[dict[str, object]] = resp.json()
        first = data[0]
        assert isinstance(first["id"], str)
        assert isinstance(first["name"], str)
        assert isinstance(first["family"], str)
        assert isinstance(first["platform"], str)
        assert isinstance(first["engine"], str)
        assert isinstance(first["market_share"], float)

    def test_known_client_present(self, authenticated_client: TestClient) -> None:
        """Spot-check: gmail_web is in the list."""
        resp = authenticated_client.get("/api/v1/ontology/clients")
        ids = [c["id"] for c in resp.json()]
        assert "gmail_web" in ids


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


class TestSyncTrigger:
    """Tests for POST /api/v1/ontology/sync."""

    def test_requires_auth(self, client: TestClient) -> None:
        """No auth token → 401."""
        resp = client.post("/api/v1/ontology/sync")
        assert resp.status_code in (401, 403)

    def test_requires_admin_role(self, viewer_client: TestClient) -> None:
        """Viewer role → 403."""
        resp = viewer_client.post("/api/v1/ontology/sync")
        assert resp.status_code == 403

    def test_developer_cannot_trigger(self, authenticated_client: TestClient) -> None:
        """Developer role → 403."""
        resp = authenticated_client.post("/api/v1/ontology/sync")
        assert resp.status_code == 403

    def test_dry_run_returns_report(self, admin_client: TestClient) -> None:
        """Admin with dry_run=true gets a report."""
        with patch("app.knowledge.ontology.routes.get_settings") as mock_settings:
            mock_settings.return_value.ontology_sync.enabled = True
            with patch(
                "app.knowledge.ontology.sync.service.CanIEmailSyncService.sync"
            ) as mock_sync:
                mock_sync.return_value = SyncReport(
                    new_properties=3, dry_run=True, commit_sha="abc123"
                )
                resp = admin_client.post("/api/v1/ontology/sync?dry_run=true")

        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        assert data["new_properties"] == 3
        assert data["commit_sha"] == "abc123"

    def test_disabled_returns_403(self, admin_client: TestClient) -> None:
        """Sync disabled → 403."""
        with patch("app.knowledge.ontology.routes.get_settings") as mock_settings:
            mock_settings.return_value.ontology_sync.enabled = False
            resp = admin_client.post("/api/v1/ontology/sync")

        assert resp.status_code == 403


class TestSyncStatus:
    """Tests for GET /api/v1/ontology/sync-status."""

    def test_requires_auth(self, client: TestClient) -> None:
        """No auth token → 401."""
        resp = client.get("/api/v1/ontology/sync-status")
        assert resp.status_code in (401, 403)

    def test_returns_status(self, authenticated_client: TestClient) -> None:
        """Authenticated developer gets sync status."""
        with patch(
            "app.knowledge.ontology.sync.service.CanIEmailSyncService.get_status"
        ) as mock_status:
            mock_status.return_value = SyncStatus(
                last_sync_at="2024-01-01T00:00:00+00:00",
                last_commit_sha="abc123",
                features_synced=100,
                error_count=0,
                last_report=None,
            )
            resp = authenticated_client.get("/api/v1/ontology/sync-status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["features_synced"] == 100
        assert data["last_commit_sha"] == "abc123"

    def test_viewer_can_read_status(self, viewer_client: TestClient) -> None:
        """Viewer role can read sync status (read-only endpoint)."""
        with patch(
            "app.knowledge.ontology.sync.service.CanIEmailSyncService.get_status"
        ) as mock_status:
            mock_status.return_value = SyncStatus()
            resp = viewer_client.get("/api/v1/ontology/sync-status")

        assert resp.status_code == 200
