"""Unit tests for briefs routes (mock service)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth.models import User
from app.briefs.routes import get_service, router
from app.briefs.schemas import (
    BriefDetailResponse,
    ConnectionResponse,
    ImportResponse,
)


@pytest.fixture
def mock_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_user() -> User:
    user = MagicMock(spec=User)
    user.id = 1
    user.role = "developer"
    user.is_active = True
    return user


@pytest.fixture
def client(mock_service: AsyncMock, mock_user: User) -> Generator[TestClient]:
    from fastapi import FastAPI
    from slowapi import _rate_limit_exceeded_handler  # pyright: ignore[reportMissingTypeStubs]
    from slowapi.errors import RateLimitExceeded  # pyright: ignore[reportMissingTypeStubs]

    from app.auth.dependencies import get_current_user
    from app.core.rate_limit import limiter

    app = FastAPI()
    app.state.limiter = limiter
    limiter.enabled = False
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.include_router(router)
    app.dependency_overrides[get_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_user

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()
    limiter.enabled = True


class TestListConnections:
    def test_returns_connections(self, client: TestClient, mock_service: AsyncMock) -> None:
        mock_service.list_connections = AsyncMock(return_value=[])
        resp = client.get("/api/v1/briefs/connections")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateConnection:
    def test_creates_connection(self, client: TestClient, mock_service: AsyncMock) -> None:
        conn_resp = MagicMock(spec=ConnectionResponse)
        conn_resp.model_dump.return_value = {
            "id": 1,
            "name": "Test",
            "platform": "jira",
            "project_url": "https://test.atlassian.net",
            "external_project_id": "TEST",
            "credential_last4": "abcd",
            "status": "connected",
            "error_message": None,
            "last_synced_at": None,
            "project_id": None,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        mock_service.create_connection = AsyncMock(return_value=conn_resp)

        resp = client.post(
            "/api/v1/briefs/connections",
            json={
                "name": "Test",
                "platform": "jira",
                "project_url": "https://test.atlassian.net/jira/software/projects/TEST",
                "credentials": {"email": "test@test.com", "api_token": "token"},
            },
        )
        assert resp.status_code == 200
        mock_service.create_connection.assert_awaited_once()


class TestDeleteConnection:
    def test_deletes_connection(
        self, client: TestClient, mock_service: AsyncMock, mock_user: User
    ) -> None:
        # Override to admin role for delete
        mock_user.role = "admin"
        mock_service.delete_connection = AsyncMock(return_value=True)

        resp = client.post(
            "/api/v1/briefs/connections/delete",
            json={"id": 1},
        )
        assert resp.status_code == 200
        assert resp.json() == {"success": True}


class TestSyncConnection:
    def test_syncs_connection(self, client: TestClient, mock_service: AsyncMock) -> None:
        conn_resp = MagicMock(spec=ConnectionResponse)
        conn_resp.model_dump.return_value = {
            "id": 1,
            "name": "Test",
            "platform": "jira",
            "project_url": "https://test.atlassian.net",
            "external_project_id": "TEST",
            "credential_last4": "abcd",
            "status": "connected",
            "error_message": None,
            "last_synced_at": "2026-01-01T00:00:00",
            "project_id": None,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        mock_service.sync_connection = AsyncMock(return_value=conn_resp)

        resp = client.post(
            "/api/v1/briefs/connections/sync",
            json={"id": 1},
        )
        assert resp.status_code == 200


class TestListItems:
    def test_list_all_items(self, client: TestClient, mock_service: AsyncMock) -> None:
        mock_service.list_items = AsyncMock(return_value=[])
        resp = client.get("/api/v1/briefs/items")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_items_with_filters(self, client: TestClient, mock_service: AsyncMock) -> None:
        mock_service.list_items = AsyncMock(return_value=[])
        resp = client.get("/api/v1/briefs/items?platform=jira&status=open&search=campaign")
        assert resp.status_code == 200


class TestListItemsForConnection:
    def test_returns_items(self, client: TestClient, mock_service: AsyncMock) -> None:
        mock_service.list_items_for_connection = AsyncMock(return_value=[])
        resp = client.get("/api/v1/briefs/connections/1/items")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetItemDetail:
    def test_returns_detail(self, client: TestClient, mock_service: AsyncMock) -> None:
        detail = MagicMock(spec=BriefDetailResponse)
        detail.model_dump.return_value = {
            "id": 1,
            "connection_id": 1,
            "external_id": "TEST-1",
            "title": "Task 1",
            "description": "Description",
            "status": "open",
            "priority": "high",
            "assignees": ["Alice"],
            "labels": ["email"],
            "due_date": None,
            "thumbnail_url": None,
            "resources": [],
            "attachments": [],
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        mock_service.get_item_detail = AsyncMock(return_value=detail)

        resp = client.get("/api/v1/briefs/items/1")
        assert resp.status_code == 200


class TestImportItems:
    def test_imports_items(self, client: TestClient, mock_service: AsyncMock) -> None:
        mock_service.import_items = AsyncMock(return_value=ImportResponse(project_id=42))
        resp = client.post(
            "/api/v1/briefs/import",
            json={"brief_item_ids": [1, 2], "project_name": "Summer Campaign"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"project_id": 42}
