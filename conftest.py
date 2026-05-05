# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedFunction=false
"""Root pytest configuration and shared fixtures.

Provides fixtures available to ALL test modules across the application.
Feature-specific fixtures should remain in their respective tests/ directories.
"""

import os
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import clear_user_cache
from app.core.config import get_settings
from app.core.scoped_db import TenantAccess, get_scoped_db
from app.main import app

# Modules that import `scoped_access` directly. Unit tests use AsyncMock
# sessions which can't carry `session.info["tenant_access"]` naturally; the
# autouse fixture below replaces `scoped_access` with a constant that returns
# system-equivalent access (no filter), so unrelated tests don't have to
# stamp every mock. Integration tests that exercise the real scoping path go
# through `get_scoped_db` and are unaffected.
_SCOPED_ACCESS_IMPORTERS = (
    "app.approval.repository",
    "app.briefs.repository",
    "app.memory.repository",
    "app.memory.service",
    "app.projects.repository",
    "app.qa_engine.repository",
    "app.templates.repository",
)
_SYSTEM_TEST_ACCESS = TenantAccess(project_ids=None, org_ids=None, role="system")


@pytest.fixture(autouse=True)
def _bypass_scoped_access_in_unit_tests(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Patch `scoped_access` to return system access for unit tests.

    Real scoping is exercised in tests marked ``tenant_isolation`` and
    in integration tests via `get_scoped_db`. Unit tests with mocked
    `AsyncSession`s would otherwise `RuntimeError` because the mock has
    no `info` dict.
    """
    if request.node.get_closest_marker("tenant_isolation") is not None:
        yield
        return
    for module_path in _SCOPED_ACCESS_IMPORTERS:
        monkeypatch.setattr(f"{module_path}.scoped_access", lambda _session: _SYSTEM_TEST_ACCESS)
    yield


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "tenant_isolation: opt out of the autouse `scoped_access` bypass — "
        "use for tests that exercise the real scoping logic.",
    )


@pytest.fixture(autouse=True)
def _clear_auth_cache() -> Generator[None, None, None]:
    """Clear the auth user TTL cache between tests to prevent cross-test pollution."""
    clear_user_cache()
    yield
    clear_user_cache()


async def _mock_scoped_db() -> AsyncGenerator[AsyncMock, None]:
    """Override `get_scoped_db` for TestClient-based route tests.

    Real `get_scoped_db` opens `AsyncSessionLocal()` and queries `ProjectMember`,
    which fails in CI where no Postgres is reachable from the unit-test job.
    Tests that mock the service layer never touch the session anyway; tests that
    exercise the real DB path are integration-marked and use a real fixture.
    """
    session = AsyncMock()
    session.info = {"tenant_access": _SYSTEM_TEST_ACCESS}
    yield session


@pytest.fixture(autouse=True)
def _override_scoped_db(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Patch the FastAPI dependency override so route tests don't hit Postgres.

    Tests marked ``tenant_isolation`` opt out — they need the real
    ``get_scoped_db`` to exercise per-user scope resolution against a real DB.
    """
    if request.node.get_closest_marker("tenant_isolation") is not None:
        yield
        return
    app.dependency_overrides[get_scoped_db] = _mock_scoped_db
    yield
    app.dependency_overrides.pop(get_scoped_db, None)


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient for endpoint testing."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def mock_settings() -> Generator[None, None, None]:
    """Patch environment variables for unit tests.

    Sets safe test defaults so unit tests don't depend on a .env file.
    """
    get_settings.cache_clear()
    with patch.dict(
        os.environ,
        {
            "DATABASE__URL": "postgresql+asyncpg://test:test@localhost:5432/test_db",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
        },
    ):
        yield
    get_settings.cache_clear()
