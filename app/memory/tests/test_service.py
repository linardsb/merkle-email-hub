"""Unit tests for MemoryService."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.core.scoped_db import TenantAccess
from app.memory.exceptions import MemoryLimitExceededError, MemoryNotFoundError
from app.memory.models import MemoryEntry
from app.memory.schemas import CompactionStats, MemoryCreate, MemoryPromote
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
    """Mock async database session.

    `info` carries the system `TenantAccess` so service calls to
    `scoped_access(self.db)` see admin-equivalent (no filter).
    """
    mock = AsyncMock()
    mock.commit = AsyncMock()
    mock.info = {"tenant_access": TenantAccess(project_ids=None, org_ids=None, role="system")}
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


# --- Phase-aware decay tests ---


def test_get_decay_rate_active() -> None:
    """Active phase returns 60 days half-life."""
    assert MemoryService.get_decay_rate("active") == 60


def test_get_decay_rate_maintenance() -> None:
    """Maintenance phase returns 14 days half-life."""
    assert MemoryService.get_decay_rate("maintenance") == 14


def test_get_decay_rate_archived() -> None:
    """Archived phase returns 3 days half-life."""
    assert MemoryService.get_decay_rate("archived") == 3


def test_get_decay_rate_unknown_phase() -> None:
    """Unknown phase returns default (30) half-life."""
    assert MemoryService.get_decay_rate("unknown") == 30


@pytest.mark.asyncio
async def test_run_compaction_calls_phase_aware_decay(
    service: MemoryService, db: AsyncMock
) -> None:
    """Compaction uses phase-aware decay with correct config values."""
    with (
        patch.object(
            service.repo, "apply_phase_aware_decay", new_callable=AsyncMock, return_value=5
        ) as mock_decay,
        patch.object(service.repo, "count_by_project", return_value=100),
        patch.object(service.repo, "get_non_evergreen_with_embeddings", return_value=[]),
    ):
        stats = await service.run_compaction()

    mock_decay.assert_awaited_once_with(
        active_half_life=60,
        maintenance_half_life=14,
        archived_half_life=3,
        default_half_life=30,
    )
    assert stats.remaining_count == 100
    assert isinstance(stats, CompactionStats)


@pytest.mark.asyncio
async def test_intent_merging_equivalent_memories(service: MemoryService, db: AsyncMock) -> None:
    """Two memories judged equivalent are merged (older deleted)."""
    older = make_entry(id=1, content="Use inline styles for Samsung Mail")
    older.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    older.is_evergreen = False
    older.embedding = [0.1] * 1024

    newer = make_entry(id=2, content="Samsung Mail requires inline CSS")
    newer.created_at = datetime(2026, 3, 1, tzinfo=UTC)
    newer.is_evergreen = False
    newer.embedding = [0.1] * 1024

    mock_delete = AsyncMock(return_value=True)
    with (
        patch.object(
            service.repo, "apply_phase_aware_decay", new_callable=AsyncMock, return_value=0
        ),
        patch.object(
            service.repo, "get_non_evergreen_with_embeddings", return_value=[newer, older]
        ),
        patch.object(service.repo, "find_similar_for_compaction", return_value=[older]),
        patch.object(service.repo, "delete", mock_delete),
        patch.object(service.repo, "count_by_project", return_value=99),
        patch(
            "app.memory.compaction.judge_functional_equivalence",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_judge,
    ):
        stats = await service.run_compaction()

    mock_judge.assert_awaited_once()
    mock_delete.assert_awaited_once_with(older.id)
    assert stats.intent_merged_count == 1


@pytest.mark.asyncio
async def test_intent_merging_different_memories(service: MemoryService, db: AsyncMock) -> None:
    """Two memories judged different are NOT merged."""
    entry_a = make_entry(id=1, content="Use inline styles")
    entry_a.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    entry_a.is_evergreen = False
    entry_a.embedding = [0.1] * 1024

    entry_b = make_entry(id=2, content="Dark mode needs prefers-color-scheme")
    entry_b.created_at = datetime(2026, 3, 1, tzinfo=UTC)
    entry_b.is_evergreen = False
    entry_b.embedding = [0.1] * 1024

    mock_delete = AsyncMock(return_value=True)
    with (
        patch.object(
            service.repo, "apply_phase_aware_decay", new_callable=AsyncMock, return_value=0
        ),
        patch.object(
            service.repo, "get_non_evergreen_with_embeddings", return_value=[entry_b, entry_a]
        ),
        patch.object(service.repo, "find_similar_for_compaction", return_value=[entry_a]),
        patch.object(service.repo, "delete", mock_delete),
        patch.object(service.repo, "count_by_project", return_value=100),
        patch(
            "app.memory.compaction.judge_functional_equivalence",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        stats = await service.run_compaction()

    mock_delete.assert_not_awaited()
    assert stats.intent_merged_count == 0


@pytest.mark.asyncio
async def test_intent_judge_failure_safe() -> None:
    """LLM judge failure returns False (no merge on uncertainty)."""
    from app.memory.compaction import judge_functional_equivalence

    # The function catches all exceptions including ImportError.
    # In test env, app.ai.providers may not be importable — this exercises
    # the failure-safe path directly.
    result = await judge_functional_equivalence("memory A", "memory B")
    assert result is False


def test_compaction_stats_includes_intent_merged() -> None:
    """CompactionStats has intent_merged_count field with default 0."""
    stats = CompactionStats(merged_count=0, remaining_count=50, duration_ms=100)
    assert stats.intent_merged_count == 0

    stats_with = CompactionStats(
        merged_count=0, intent_merged_count=3, remaining_count=47, duration_ms=150
    )
    assert stats_with.intent_merged_count == 3
