"""Root pytest configuration and shared fixtures.

Provides fixtures available to ALL test modules across the application.
Feature-specific fixtures should remain in their respective tests/ directories.
"""

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import clear_user_cache
from app.core.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def _clear_auth_cache() -> Generator[None, None, None]:
    """Clear the auth user TTL cache between tests to prevent cross-test pollution."""
    clear_user_cache()
    yield
    clear_user_cache()


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
