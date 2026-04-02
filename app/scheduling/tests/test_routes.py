"""Tests for scheduling API routes."""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.exceptions import setup_exception_handlers
from app.core.rate_limit import limiter
from app.scheduling.registry import scheduled_job
from app.scheduling.routes import router as scheduling_router


def _make_admin() -> User:
    return User(
        id=1,
        email="admin@test.com",
        hashed_password="x",
        role="admin",
        is_active=True,
    )


def _make_job_hash(
    name: str = "test_job",
    cron: str = "0 * * * *",
    enabled: bool = True,
) -> dict[bytes, bytes]:
    return {
        b"name": name.encode(),
        b"cron_expr": cron.encode(),
        b"callable_name": name.encode(),
        b"enabled": b"1" if enabled else b"0",
        b"last_run": b"",
        b"last_status": b"",
        b"run_count": b"0",
    }


@pytest.fixture()
def test_app() -> Generator[FastAPI]:
    """Create a minimal FastAPI app with the scheduling router mounted."""
    _app = FastAPI()
    _app.state.limiter = limiter
    setup_exception_handlers(_app)
    _app.include_router(scheduling_router)
    _app.dependency_overrides[get_current_user] = _make_admin
    limiter.enabled = False
    yield _app
    _app.dependency_overrides.clear()
    limiter.enabled = True


@pytest.fixture()
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)


class TestListJobs:
    def test_list_jobs(self, client: TestClient) -> None:
        """GET /jobs returns registered jobs."""
        mock_redis = AsyncMock()

        async def _scan_iter(match: str = "*") -> AsyncGenerator[bytes]:
            yield b"scheduling:jobs:my_job"

        mock_redis.scan_iter = _scan_iter
        mock_redis.hgetall = AsyncMock(return_value=_make_job_hash("my_job"))

        with patch("app.scheduling.service.get_redis", return_value=mock_redis):
            resp = client.get("/api/v1/scheduling/jobs")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "my_job"
        assert data[0]["cron_expr"] == "0 * * * *"


class TestTriggerJob:
    def test_trigger_job(self, client: TestClient) -> None:
        """POST /jobs/{name}/trigger executes the job."""
        executed = False

        @scheduled_job(cron="0 * * * *")
        async def trigger_me() -> None:
            nonlocal executed
            executed = True

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)
        mock_redis.hset = AsyncMock()
        mock_redis.hincrby = AsyncMock()
        mock_redis.lpush = AsyncMock()
        mock_redis.ltrim = AsyncMock()

        with patch("app.scheduling.service.get_redis", return_value=mock_redis):
            resp = client.post("/api/v1/scheduling/jobs/trigger_me/trigger")

        assert resp.status_code == 200
        data = resp.json()
        assert data["job_name"] == "trigger_me"
        assert data["status"] == "success"
        assert executed is True


class TestUpdateJob:
    def test_update_job_disable(self, client: TestClient) -> None:
        """PATCH /jobs/{name} with enabled=false persists."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value=_make_job_hash("my_job"))
        mock_redis.hset = AsyncMock()

        with patch("app.scheduling.service.get_redis", return_value=mock_redis):
            resp = client.patch(
                "/api/v1/scheduling/jobs/my_job",
                json={"enabled": False},
            )

        assert resp.status_code == 200
        # Verify hset was called with enabled=0
        hset_calls = mock_redis.hset.call_args_list
        disable_call = next(
            (c for c in hset_calls if c.kwargs.get("mapping", {}).get("enabled") == "0"),
            None,
        )
        assert disable_call is not None

    def test_update_invalid_cron(self, client: TestClient) -> None:
        """PATCH with invalid cron returns 422."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value=_make_job_hash("my_job"))

        with patch("app.scheduling.service.get_redis", return_value=mock_redis):
            resp = client.patch(
                "/api/v1/scheduling/jobs/my_job",
                json={"cron_expr": "not-valid"},
            )

        assert resp.status_code == 422
