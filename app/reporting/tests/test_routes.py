"""Tests for reporting API routes — auth, rate limiting, endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import limiter
from app.main import app
from app.reporting.routes import router as reporting_router


@pytest.fixture(autouse=True)
def _disable_rate_limit() -> None:
    """Disable rate limiting for route tests."""
    limiter.enabled = False


@pytest.fixture
def client() -> Iterator[TestClient]:
    """TestClient with reporting router registered (regardless of REPORTING__ENABLED)."""
    # Temporarily add router if not already present
    existing = {cast(Any, r).path for r in app.routes if hasattr(r, "path")}
    needs_add = "/api/v1/reports/qa" not in existing
    if needs_add:
        app.include_router(reporting_router)
    yield TestClient(app)
    if needs_add:
        # Remove the routes we added (last N routes)
        app.routes[:] = [
            r
            for r in app.routes
            if not (
                hasattr(r, "path") and str(getattr(r, "path", "")).startswith("/api/v1/reports")
            )
        ]


class TestReportRoutes:
    def test_qa_report_requires_auth(self, client: TestClient) -> None:
        """POST /api/v1/reports/qa requires authentication."""
        response = client.post(
            "/api/v1/reports/qa",
            json={"qa_result_id": 1},
        )
        assert response.status_code in (401, 403)

    def test_approval_requires_auth(self, client: TestClient) -> None:
        """POST /api/v1/reports/approval requires authentication."""
        response = client.post(
            "/api/v1/reports/approval",
            json={"qa_result_id": 1},
        )
        assert response.status_code in (401, 403)

    def test_regression_requires_auth(self, client: TestClient) -> None:
        """POST /api/v1/reports/regression requires authentication."""
        response = client.post(
            "/api/v1/reports/regression",
            json={"entity_type": "component_version", "entity_id": 1},
        )
        assert response.status_code in (401, 403)

    def test_get_report_requires_auth(self, client: TestClient) -> None:
        """GET /api/v1/reports/{id} requires authentication."""
        response = client.get("/api/v1/reports/abc123")
        assert response.status_code in (401, 403)
