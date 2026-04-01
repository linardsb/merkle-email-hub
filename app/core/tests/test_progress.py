"""Tests for unified progress tracking (42.6)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.progress import OperationStatus, ProgressTracker
from app.core.rate_limit import limiter
from app.main import app

BASE = "/api/v1/progress"


# ── Helpers ──


def _make_user(role: str = "developer") -> User:
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


# ── Fixtures ──


@pytest.fixture(autouse=True)
def _clear_tracker() -> Generator[None]:
    ProgressTracker.clear()
    yield
    ProgressTracker.clear()


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_developer() -> Generator[None]:
    app.dependency_overrides[get_current_user] = lambda: _make_user("developer")
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── ProgressTracker unit tests ──


class TestProgressTracker:
    """Unit tests for the in-memory progress tracker."""

    def test_start_creates_entry(self) -> None:
        """start() creates an entry with PENDING status and progress=0."""
        entry = ProgressTracker.start("op-1", "rendering")
        assert entry.operation_id == "op-1"
        assert entry.operation_type == "rendering"
        assert entry.status == OperationStatus.PENDING
        assert entry.progress == 0
        assert entry.message == ""
        assert entry.error is None

    def test_update_progress(self) -> None:
        """update() modifies fields and bumps updated_at."""
        entry = ProgressTracker.start("op-2", "qa_scan")
        old_updated = entry.updated_at

        updated = ProgressTracker.update(
            "op-2",
            progress=50,
            status=OperationStatus.PROCESSING,
            message="Running check 5/10",
        )
        assert updated is not None
        assert updated.progress == 50
        assert updated.status == OperationStatus.PROCESSING
        assert updated.message == "Running check 5/10"
        assert updated.updated_at >= old_updated

    def test_get_existing(self) -> None:
        """get() returns the entry for a known operation_id."""
        ProgressTracker.start("op-3", "design_sync")
        entry = ProgressTracker.get("op-3")
        assert entry is not None
        assert entry.operation_type == "design_sync"

    def test_get_nonexistent_returns_none(self) -> None:
        """get() returns None for an unknown operation_id."""
        assert ProgressTracker.get("no-such-op") is None

    def test_cleanup_removes_expired(self) -> None:
        """cleanup_completed() removes entries older than max_age."""
        entry = ProgressTracker.start("op-4", "export")
        entry.status = OperationStatus.COMPLETED
        entry.updated_at = datetime.now(UTC) - timedelta(seconds=400)

        removed = ProgressTracker.cleanup_completed(max_age_seconds=300)
        assert removed == 1
        assert ProgressTracker.get("op-4") is None

    def test_cleanup_preserves_active(self) -> None:
        """cleanup_completed() does not remove active entries."""
        entry = ProgressTracker.start("op-5", "rendering")
        entry.status = OperationStatus.PROCESSING

        removed = ProgressTracker.cleanup_completed(max_age_seconds=0)
        assert removed == 0
        assert ProgressTracker.get("op-5") is not None

    def test_get_active_filters(self) -> None:
        """get_active() returns only PENDING/PROCESSING entries."""
        ProgressTracker.start("a", "rendering")
        ProgressTracker.start("b", "qa_scan")
        ProgressTracker.update("b", status=OperationStatus.PROCESSING)
        ProgressTracker.start("c", "export")
        ProgressTracker.update("c", status=OperationStatus.COMPLETED)

        active = ProgressTracker.get_active()
        active_ids = {e.operation_id for e in active}
        assert active_ids == {"a", "b"}

    def test_concurrent_operations(self) -> None:
        """Multiple operations coexist independently."""
        ProgressTracker.start("r-1", "rendering")
        ProgressTracker.start("q-1", "qa_scan")
        ProgressTracker.update("r-1", progress=50)
        ProgressTracker.update("q-1", progress=70)

        r = ProgressTracker.get("r-1")
        q = ProgressTracker.get("q-1")
        assert r is not None and r.progress == 50
        assert q is not None and q.progress == 70

    def test_status_transitions(self) -> None:
        """Status transitions PENDING -> PROCESSING -> COMPLETED."""
        ProgressTracker.start("op-6", "blueprint")
        ProgressTracker.update("op-6", status=OperationStatus.PROCESSING)
        entry = ProgressTracker.get("op-6")
        assert entry is not None and entry.status == OperationStatus.PROCESSING

        ProgressTracker.update("op-6", status=OperationStatus.COMPLETED, progress=100)
        entry = ProgressTracker.get("op-6")
        assert entry is not None and entry.status == OperationStatus.COMPLETED
        assert entry.progress == 100

    def test_error_capture(self) -> None:
        """Failed operations store error message."""
        ProgressTracker.start("op-7", "export")
        ProgressTracker.update("op-7", status=OperationStatus.FAILED, error="Connection timeout")

        entry = ProgressTracker.get("op-7")
        assert entry is not None
        assert entry.status == OperationStatus.FAILED
        assert entry.error == "Connection timeout"


# ── Route tests ──


@pytest.mark.usefixtures("_auth_developer")
class TestProgressRoutes:
    """Route tests for /api/v1/progress endpoints."""

    def test_get_progress_200(self, client: TestClient) -> None:
        """GET /{operation_id} returns progress JSON."""
        ProgressTracker.start("route-1", "rendering")
        ProgressTracker.update(
            "route-1", status=OperationStatus.PROCESSING, progress=30, message="Rendering Gmail..."
        )

        resp = client.get(f"{BASE}/route-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["operation_id"] == "route-1"
        assert body["operation_type"] == "rendering"
        assert body["status"] == "processing"
        assert body["progress"] == 30
        assert body["message"] == "Rendering Gmail..."
        assert body["error"] is None

    def test_get_progress_404(self, client: TestClient) -> None:
        """GET /{operation_id} returns 404 for unknown operation."""
        resp = client.get(f"{BASE}/no-such-op")
        assert resp.status_code == 404

    def test_get_active_list_200(self, client: TestClient) -> None:
        """GET /active/list returns only in-flight operations."""
        ProgressTracker.start("active-1", "rendering")
        ProgressTracker.update("active-1", status=OperationStatus.PROCESSING, progress=50)
        ProgressTracker.start("done-1", "qa_scan")
        ProgressTracker.update("done-1", status=OperationStatus.COMPLETED, progress=100)

        resp = client.get(f"{BASE}/active/list")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["operation_id"] == "active-1"
