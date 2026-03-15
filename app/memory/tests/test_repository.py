"""Unit tests for MemoryRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.memory.models import MemoryEntry
from app.memory.repository import MemoryRepository


def make_entry(
    id: int = 1,
    agent_type: str = "scaffolder",
    memory_type: str = "procedural",
    content: str = "test memory",
    project_id: int | None = 1,
) -> MemoryEntry:
    """Create a MemoryEntry for testing."""
    entry = MemoryEntry(
        agent_type=agent_type,
        memory_type=memory_type,
        content=content,
        project_id=project_id,
    )
    entry.id = id
    return entry


@pytest.fixture
def db() -> AsyncMock:
    """Mock async database session."""
    mock = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture
def repo(db: AsyncMock) -> MemoryRepository:
    """Create repository with mock db."""
    return MemoryRepository(db)


@pytest.mark.asyncio
async def test_create_memory_entry(repo: MemoryRepository, db: AsyncMock) -> None:
    """Create inserts and returns entry."""
    entry = make_entry()
    db.refresh = AsyncMock()
    result = await repo.create(entry)
    db.add.assert_called_once_with(entry)
    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once_with(entry)
    assert result is entry


@pytest.mark.asyncio
async def test_get_by_id_found(repo: MemoryRepository, db: AsyncMock) -> None:
    """Get by ID returns entry when found."""
    entry = make_entry()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = entry
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_by_id(1)
    assert result is entry


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo: MemoryRepository, db: AsyncMock) -> None:
    """Get by ID returns None when not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_by_id(999)
    assert result is None


@pytest.mark.asyncio
async def test_count_by_project(repo: MemoryRepository, db: AsyncMock) -> None:
    """Count returns scalar result."""
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.count_by_project(1)
    assert result == 42


@pytest.mark.asyncio
async def test_delete_existing(repo: MemoryRepository, db: AsyncMock) -> None:
    """Delete returns True for existing entry."""
    entry = make_entry()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = entry
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.delete(1)
    assert result is True
    db.delete.assert_awaited_once_with(entry)
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_delete_nonexistent(repo: MemoryRepository, db: AsyncMock) -> None:
    """Delete returns False for missing entry."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.delete(999)
    assert result is False
    db.delete.assert_not_awaited()
