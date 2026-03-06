"""Unit tests for MemoryService."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.memory.exceptions import MemoryLimitExceededError, MemoryNotFoundError
from app.memory.models import MemoryEntry
from app.memory.schemas import MemoryCreate, MemoryPromote
from app.memory.service import MemoryService


def make_entry(
    id: int = 1,
    agent_type: str = "scaffolder",
    memory_type: str = "procedural",
    content: str = "test memory",
    source: str = "agent",
) -> MemoryEntry:
    """Create a MemoryEntry for testing."""
    entry = MemoryEntry(
        agent_type=agent_type,
        memory_type=memory_type,
        content=content,
        source=source,
        source_agent=agent_type,
        project_id=1,
    )
    entry.id = id
    return entry


@pytest.fixture
def db() -> AsyncMock:
    """Mock async database session."""
    mock = AsyncMock()
    mock.commit = AsyncMock()
    return mock


@pytest.fixture
def embedding() -> AsyncMock:
    """Mock embedding provider."""
    mock = AsyncMock()
    mock.embed = AsyncMock(return_value=[[0.1] * 1024])
    mock.dimension = 1024
    return mock


@pytest.fixture
def service(db: AsyncMock, embedding: AsyncMock) -> MemoryService:
    """Create service with mocked dependencies."""
    return MemoryService(db, embedding)


@pytest.mark.asyncio
async def test_store_generates_embedding(
    service: MemoryService, embedding: AsyncMock, db: AsyncMock
) -> None:
    """Store calls embedding.embed and persists entry."""
    data = MemoryCreate(
        agent_type="scaffolder",
        memory_type="procedural",
        content="Samsung Mail needs inline styles",
        project_id=1,
    )

    # Mock repo methods
    with (
        patch.object(service.repo, "count_by_project", return_value=0),
        patch.object(service.repo, "create", side_effect=lambda e: _set_id(e, 1)),
    ):
        result = await service.store(data)

    embedding.embed.assert_awaited_once_with(["Samsung Mail needs inline styles"])
    assert result.agent_type == "scaffolder"
    assert result.memory_type == "procedural"
    assert result.embedding is not None
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_store_enforces_limit(service: MemoryService) -> None:
    """Store raises when project limit exceeded."""
    data = MemoryCreate(
        agent_type="scaffolder",
        memory_type="procedural",
        content="test",
        project_id=1,
    )

    with patch.object(service.repo, "count_by_project", return_value=5000):
        with pytest.raises(MemoryLimitExceededError):
            await service.store(data)


@pytest.mark.asyncio
async def test_recall_returns_results(service: MemoryService, embedding: AsyncMock) -> None:
    """Recall calls similarity search and returns results."""
    entry = make_entry()
    expected = [(entry, 0.95)]

    with patch.object(service.repo, "similarity_search", return_value=expected):
        results = await service.recall("dark mode fix", project_id=1)

    embedding.embed.assert_awaited_once_with(["dark mode fix"])
    assert len(results) == 1
    assert results[0][0].id == 1
    assert results[0][1] == 0.95


@pytest.mark.asyncio
async def test_promote_from_dcg(service: MemoryService, db: AsyncMock) -> None:
    """Promote creates entry with dcg source and prefixed content."""
    data = MemoryPromote(
        key="project.deletion_pattern",
        value="uses soft deletes via SoftDeleteMixin",
        project_id=1,
    )

    with (
        patch.object(service.repo, "count_by_project", return_value=0),
        patch.object(service.repo, "create", side_effect=lambda e: _set_id(e, 1)),
    ):
        result = await service.promote_from_dcg(data)

    assert result.source == "dcg"
    assert "[dcg:project.deletion_pattern]" in result.content
    assert result.memory_type == "procedural"
    # Two commits: one from store, one from promote_from_dcg
    assert db.commit.await_count >= 2


@pytest.mark.asyncio
async def test_get_by_id_raises_not_found(service: MemoryService) -> None:
    """Get raises MemoryNotFoundError when missing."""
    with patch.object(service.repo, "get_by_id", return_value=None):
        with pytest.raises(MemoryNotFoundError):
            await service.get_by_id(999)


@pytest.mark.asyncio
async def test_delete_raises_not_found(service: MemoryService, db: AsyncMock) -> None:
    """Delete raises MemoryNotFoundError when missing."""
    with patch.object(service.repo, "delete", return_value=False):
        with pytest.raises(MemoryNotFoundError):
            await service.delete(999)


def _set_id(entry: Any, id: int) -> Any:
    """Helper to set ID on entry (simulates DB insert)."""
    entry.id = id
    return entry
