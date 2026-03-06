"""Route tests for agent memory API."""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.main import app
from app.memory.exceptions import MemoryNotFoundError
from app.memory.models import MemoryEntry
from app.memory.service import MemoryService


def _make_user(role: str = "developer") -> User:
    """Create a mock user."""
    user = User(email="test@example.com", hashed_password="x", role=role)
    user.id = 1
    return user


def _make_entry(
    id: int = 1,
    agent_type: str = "scaffolder",
    memory_type: str = "procedural",
    content: str = "test memory",
) -> MemoryEntry:
    """Create a MemoryEntry for testing."""
    now = datetime.now(UTC)
    entry = MemoryEntry(
        agent_type=agent_type,
        memory_type=memory_type,
        content=content,
        source="agent",
        source_agent=agent_type,
        project_id=1,
        decay_weight=1.0,
        is_evergreen=False,
    )
    entry.id = id
    entry.created_at = now
    entry.updated_at = now
    return entry


@pytest.fixture
def _auth_developer() -> Generator[None]:
    """Override auth to return a developer user."""
    user = _make_user("developer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _auth_viewer() -> Generator[None]:
    """Override auth to return a viewer user (should be rejected by role check)."""
    user = _make_user("viewer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.usefixtures("_auth_developer")
def test_store_memory_201(client: TestClient) -> None:
    """POST /memory returns 201 with stored entry."""
    entry = _make_entry()

    with patch.object(MemoryService, "store", new_callable=AsyncMock, return_value=entry):
        resp = client.post(
            "/memory/",
            json={
                "agent_type": "scaffolder",
                "memory_type": "procedural",
                "content": "Samsung Mail needs inline styles",
                "project_id": 1,
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["agent_type"] == "scaffolder"
    assert body["id"] == 1


@pytest.mark.usefixtures("_auth_developer")
def test_search_memories_200(client: TestClient) -> None:
    """POST /memory/search returns list of results."""
    entry = _make_entry()

    with patch.object(
        MemoryService,
        "recall",
        new_callable=AsyncMock,
        return_value=[(entry, 0.95)],
    ):
        resp = client.post(
            "/memory/search",
            json={"query": "dark mode fix", "project_id": 1},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == 1


@pytest.mark.usefixtures("_auth_developer")
def test_get_memory_200(client: TestClient) -> None:
    """GET /memory/{id} returns entry."""
    entry = _make_entry()

    with patch.object(MemoryService, "get_by_id", new_callable=AsyncMock, return_value=entry):
        resp = client.get("/memory/1")

    assert resp.status_code == 200
    assert resp.json()["id"] == 1


@pytest.mark.usefixtures("_auth_developer")
def test_delete_memory_204(client: TestClient) -> None:
    """DELETE /memory/{id} returns 204."""
    with patch.object(MemoryService, "delete", new_callable=AsyncMock, return_value=None):
        resp = client.delete("/memory/1")

    assert resp.status_code == 204


@pytest.mark.usefixtures("_auth_developer")
def test_promote_dcg_note_201(client: TestClient) -> None:
    """POST /memory/promote returns 201."""
    entry = _make_entry(content="[dcg:project.deletion_pattern] uses soft deletes")
    entry.source = "dcg"

    with patch.object(
        MemoryService, "promote_from_dcg", new_callable=AsyncMock, return_value=entry
    ):
        resp = client.post(
            "/memory/promote",
            json={
                "key": "project.deletion_pattern",
                "value": "uses soft deletes via SoftDeleteMixin",
                "project_id": 1,
            },
        )

    assert resp.status_code == 201
    assert resp.json()["source"] == "dcg"


@pytest.mark.usefixtures("_auth_viewer")
def test_viewer_role_forbidden(client: TestClient) -> None:
    """Viewer role gets 403 on memory endpoints."""
    resp = client.post(
        "/memory/",
        json={
            "agent_type": "scaffolder",
            "memory_type": "procedural",
            "content": "test",
            "project_id": 1,
        },
    )
    assert resp.status_code == 403


@pytest.mark.usefixtures("_auth_developer")
def test_get_memory_404(client: TestClient) -> None:
    """GET /memory/{id} returns 404 when not found."""
    with patch.object(
        MemoryService,
        "get_by_id",
        new_callable=AsyncMock,
        side_effect=MemoryNotFoundError(999),
    ):
        resp = client.get("/memory/999")

    assert resp.status_code == 404
