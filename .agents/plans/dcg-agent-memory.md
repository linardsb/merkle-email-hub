# Plan: Hub Agent Memory System (PRD 4.9.3–4.9.6 + 4.9.7 DCG Bridge)

## Context

The PRD defines a full Smart Agent Memory System at `app/memory/` (Sections 4.9.3-4.9.6). Currently **none of it exists** — `app/memory/` is empty. The frontend conversation history tab (4.9.1) is done but has no backend persistence. The existing `app/knowledge/` module provides pgvector + embedding infrastructure that we reuse.

Task 7.5 in TODO.md references the DCG lightweight memory layer (4.9.7), which is a **complement** — dcg notes that exceed confidence/frequency thresholds get promoted to this Hub memory system. This plan builds the Hub side.

**What exists that we build on:**
- `app/knowledge/embedding.py` — `EmbeddingProvider` Protocol + OpenAI/Jina/Local implementations
- `app/knowledge/models.py` — pgvector `Vector(1024)` column pattern, `DocumentChunk` with embeddings
- `app/core/poller.py` — `DataPoller` base class for background tasks (leader election, Redis)
- `app/core/database.py` — async SQLAlchemy, `Base`, `get_db()`, `get_db_context()`
- `app/shared/models.py` — `TimestampMixin`, `SoftDeleteMixin`, `utcnow()`
- `app/shared/schemas.py` — `PaginatedResponse[T]`, `PaginationParams`

**PRD acceptance criteria (summary):**
- Agents store memories after significant interactions (procedural, episodic, semantic)
- Memories are embedded in pgvector and retrieved via similarity search
- Memory retrieval injected into agent context before each response
- Cross-agent: Dark Mode Agent stores fix → Scaffolder retrieves it next session
- Temporal decay: recent memories rank higher, stale ones down-ranked
- Background compaction merges redundant memories
- DCG bridge: promote high-frequency dcg notes into Hub memory

## Files to Create

### New VSA Module: `app/memory/`
- `app/memory/__init__.py`
- `app/memory/models.py` — `MemoryEntry` SQLAlchemy model (pgvector)
- `app/memory/schemas.py` — Pydantic request/response schemas
- `app/memory/repository.py` — DB operations (CRUD, similarity search, decay query)
- `app/memory/service.py` — Business logic (store, recall, compact, promote from dcg)
- `app/memory/exceptions.py` — `MemoryError` hierarchy
- `app/memory/routes.py` — REST endpoints under `/api/v1/memory`
- `app/memory/compaction.py` — Background compaction poller (extends `DataPoller`)

### Modified Files
- `app/main.py` — Register memory router
- `app/core/config.py` — Add `MemoryConfig` settings group
- `alembic/versions/xxx_add_memory_entries.py` — Migration for `memory_entries` table

### Test Files
- `app/memory/tests/__init__.py`
- `app/memory/tests/test_repository.py`
- `app/memory/tests/test_service.py`
- `app/memory/tests/test_routes.py`

## Implementation Steps

### Step 1: Add `MemoryConfig` to `app/core/config.py`

Add after `BlueprintConfig` class (~line 114):

```python
class MemoryConfig(BaseModel):
    """Agent memory system settings."""

    enabled: bool = True
    embedding_dimension: int = 1024
    default_decay_half_life_days: int = 30  # episodic memories
    compaction_interval_hours: int = 24
    compaction_similarity_threshold: float = 0.92  # merge above this cosine sim
    max_memories_per_project: int = 5000
    context_injection_limit: int = 10  # max memories injected per agent call
    dcg_promotion_min_frequency: int = 3  # promote dcg note after N occurrences
```

Add to `Settings` class:

```python
memory: MemoryConfig = MemoryConfig()
```

### Step 2: Create `app/memory/models.py`

PRD 4.9.3 specifies the schema:
`id | agent_type | memory_type | content | embedding(1024) | project_id | metadata(jsonb) | decay_weight | created_at`

```python
"""SQLAlchemy models for agent memory entries."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class MemoryEntry(Base, TimestampMixin):
    """Persistent agent memory with vector embedding for similarity search.

    Memory types:
    - procedural: learned patterns (e.g., "Samsung Mail needs inline styles for dark mode")
    - episodic: session logs (e.g., "fixed VML background in Outlook 2016 build")
    - semantic: durable facts (e.g., "Gmail clips emails over 102KB")
    """

    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # procedural | episodic | semantic
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1024))
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    metadata_json: Mapped[str | None] = mapped_column(JSONB, nullable=True)
    decay_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="agent"
    )  # agent | dcg | compaction
    source_agent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_evergreen: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index("ix_memory_project_agent", "project_id", "agent_type"),
        Index("ix_memory_type_decay", "memory_type", "decay_weight"),
    )
```

### Step 3: Create `app/memory/schemas.py`

```python
"""Pydantic schemas for agent memory."""

from datetime import datetime

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    """Request to store a new memory entry."""

    agent_type: str = Field(..., max_length=50)
    memory_type: str = Field(..., pattern=r"^(procedural|episodic|semantic)$")
    content: str = Field(..., min_length=1, max_length=4000)
    project_id: int | None = None
    metadata: dict | None = None
    is_evergreen: bool = False


class MemoryResponse(BaseModel):
    """Memory entry response."""

    id: int
    agent_type: str
    memory_type: str
    content: str
    project_id: int | None
    metadata: dict | None
    decay_weight: float
    source: str
    is_evergreen: bool
    created_at: datetime
    updated_at: datetime
    similarity: float | None = None  # populated on search results

    model_config = {"from_attributes": True}


class MemorySearch(BaseModel):
    """Search request for memory retrieval."""

    query: str = Field(..., min_length=1, max_length=1000)
    agent_type: str | None = None
    memory_type: str | None = None
    project_id: int | None = None
    limit: int = Field(default=10, ge=1, le=50)


class MemoryPromote(BaseModel):
    """Request to promote a DCG note into Hub memory."""

    key: str = Field(..., max_length=128)
    value: str = Field(..., max_length=1024)
    agent_type: str = Field(default="dcg", max_length=50)
    project_id: int | None = None


class CompactionStats(BaseModel):
    """Result of a compaction run."""

    merged_count: int
    remaining_count: int
    duration_ms: int
```

### Step 4: Create `app/memory/exceptions.py`

```python
"""Memory module exceptions."""

from app.core.exceptions import AppError, DomainValidationError, NotFoundError


class MemoryNotFoundError(NotFoundError):
    """Memory entry not found."""

    pass


class MemoryValidationError(DomainValidationError):
    """Memory validation failure."""

    pass


class MemoryLimitExceededError(AppError):
    """Project memory limit exceeded."""

    pass
```

### Step 5: Create `app/memory/repository.py`

```python
"""Repository for memory entry database operations."""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import MemoryEntry


class MemoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entry: MemoryEntry) -> MemoryEntry:
        """Insert a new memory entry."""
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def get_by_id(self, memory_id: int) -> MemoryEntry | None:
        """Get a memory entry by ID."""
        result = await self.db.execute(
            select(MemoryEntry).where(MemoryEntry.id == memory_id)
        )
        return result.scalar_one_or_none()

    async def similarity_search(
        self,
        embedding: list[float],
        *,
        project_id: int | None = None,
        agent_type: str | None = None,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[tuple[MemoryEntry, float]]:
        """Find similar memories using pgvector cosine distance.

        Returns (entry, similarity_score) tuples sorted by relevance.
        Decay weight is factored into ranking: score = cosine_sim * decay_weight.
        """
        # cosine distance: 1 - cosine_sim, so lower = more similar
        distance = MemoryEntry.embedding.cosine_distance(embedding)
        weighted_score = (1 - distance) * MemoryEntry.decay_weight

        query = (
            select(MemoryEntry, weighted_score.label("score"))
            .where(MemoryEntry.embedding.is_not(None))
        )

        if project_id is not None:
            # Include project-specific + global (project_id IS NULL) memories
            query = query.where(
                (MemoryEntry.project_id == project_id) | (MemoryEntry.project_id.is_(None))
            )
        if agent_type is not None:
            query = query.where(MemoryEntry.agent_type == agent_type)
        if memory_type is not None:
            query = query.where(MemoryEntry.memory_type == memory_type)

        query = query.order_by(text("score DESC")).limit(limit)
        result = await self.db.execute(query)
        return [(row[0], float(row[1])) for row in result.all()]

    async def count_by_project(self, project_id: int | None) -> int:
        """Count memories for a project."""
        query = select(func.count(MemoryEntry.id))
        if project_id is not None:
            query = query.where(MemoryEntry.project_id == project_id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def find_similar_for_compaction(
        self,
        entry: MemoryEntry,
        threshold: float,
    ) -> list[MemoryEntry]:
        """Find memories similar enough to merge with the given entry."""
        if entry.embedding is None:
            return []
        distance = MemoryEntry.embedding.cosine_distance(entry.embedding)
        query = (
            select(MemoryEntry)
            .where(
                MemoryEntry.id != entry.id,
                MemoryEntry.project_id == entry.project_id,
                MemoryEntry.memory_type == entry.memory_type,
                (1 - distance) >= threshold,
            )
            .limit(10)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def apply_decay(self, half_life_days: int) -> int:
        """Apply temporal decay to non-evergreen memories.

        Returns count of updated entries.
        """
        # decay_weight = 2^(-age_days / half_life_days)
        # Only update entries where current weight differs significantly
        stmt = text("""
            UPDATE memory_entries
            SET decay_weight = POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 / :half_life)
            WHERE is_evergreen = false
              AND ABS(decay_weight - POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 / :half_life)) > 0.01
        """)
        result = await self.db.execute(stmt, {"half_life": half_life_days})
        return result.rowcount  # type: ignore[return-value]

    async def delete(self, memory_id: int) -> bool:
        """Delete a memory entry. Returns True if deleted."""
        entry = await self.get_by_id(memory_id)
        if entry is None:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True

    async def bulk_delete(self, memory_ids: list[int]) -> int:
        """Delete multiple memory entries. Returns count deleted."""
        if not memory_ids:
            return 0
        query = select(MemoryEntry).where(MemoryEntry.id.in_(memory_ids))
        result = await self.db.execute(query)
        entries = result.scalars().all()
        for entry in entries:
            await self.db.delete(entry)
        await self.db.flush()
        return len(entries)
```

### Step 6: Create `app/memory/service.py`

```python
"""Business logic for agent memory operations."""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.embedding import EmbeddingProvider
from app.memory.exceptions import MemoryLimitExceededError, MemoryNotFoundError
from app.memory.models import MemoryEntry
from app.memory.repository import MemoryRepository
from app.memory.schemas import CompactionStats, MemoryCreate, MemoryPromote

logger = get_logger(__name__)
settings = get_settings()


class MemoryService:
    def __init__(
        self,
        db: AsyncSession,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.repo = MemoryRepository(db)
        self.db = db
        self.embedding = embedding_provider

    async def store(self, data: MemoryCreate) -> MemoryEntry:
        """Store a new memory entry with embedding."""
        # Check project limit
        count = await self.repo.count_by_project(data.project_id)
        if count >= settings.memory.max_memories_per_project:
            raise MemoryLimitExceededError(
                f"Project memory limit ({settings.memory.max_memories_per_project}) exceeded"
            )

        # Generate embedding
        embeddings = await self.embedding.embed([data.content])
        embedding = embeddings[0] if embeddings else None

        entry = MemoryEntry(
            agent_type=data.agent_type,
            memory_type=data.memory_type,
            content=data.content,
            embedding=embedding,
            project_id=data.project_id,
            metadata_json=data.metadata,
            is_evergreen=data.is_evergreen,
            source="agent",
            source_agent=data.agent_type,
        )

        entry = await self.repo.create(entry)
        await self.db.commit()

        logger.info(
            "memory.store_completed",
            memory_id=entry.id,
            agent_type=data.agent_type,
            memory_type=data.memory_type,
            project_id=data.project_id,
        )
        return entry

    async def recall(
        self,
        query: str,
        *,
        project_id: int | None = None,
        agent_type: str | None = None,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[tuple[MemoryEntry, float]]:
        """Recall relevant memories via similarity search."""
        embeddings = await self.embedding.embed([query])
        if not embeddings:
            return []

        results = await self.repo.similarity_search(
            embeddings[0],
            project_id=project_id,
            agent_type=agent_type,
            memory_type=memory_type,
            limit=limit,
        )

        logger.info(
            "memory.recall_completed",
            query_length=len(query),
            results_count=len(results),
            project_id=project_id,
        )
        return results

    async def promote_from_dcg(self, data: MemoryPromote) -> MemoryEntry:
        """Promote a DCG note into Hub memory (PRD 4.9.7 bridge)."""
        create_data = MemoryCreate(
            agent_type=data.agent_type,
            memory_type="procedural",
            content=f"[dcg:{data.key}] {data.value}",
            project_id=data.project_id,
            metadata={"source": "dcg", "dcg_key": data.key},
        )
        entry = await self.store(create_data)
        entry.source = "dcg"
        await self.db.commit()

        logger.info(
            "memory.dcg_promotion_completed",
            memory_id=entry.id,
            dcg_key=data.key,
        )
        return entry

    async def get_by_id(self, memory_id: int) -> MemoryEntry:
        """Get a memory entry by ID or raise."""
        entry = await self.repo.get_by_id(memory_id)
        if entry is None:
            raise MemoryNotFoundError(f"Memory entry {memory_id} not found")
        return entry

    async def delete(self, memory_id: int) -> None:
        """Delete a memory entry."""
        deleted = await self.repo.delete(memory_id)
        if not deleted:
            raise MemoryNotFoundError(f"Memory entry {memory_id} not found")
        await self.db.commit()

    async def run_compaction(self) -> CompactionStats:
        """Merge near-duplicate memories within each project.

        Finds clusters of similar memories (above threshold) and merges
        them into a single entry with combined content.
        """
        start = time.monotonic()
        threshold = settings.memory.compaction_similarity_threshold
        merged_count = 0

        # Apply decay weights first
        await self.repo.apply_decay(settings.memory.default_decay_half_life_days)

        # TODO: Implement full compaction logic:
        # 1. Query memories grouped by project_id + memory_type
        # 2. For each, find clusters above similarity threshold
        # 3. Merge cluster into single entry (newest content, max decay_weight)
        # 4. Delete merged duplicates
        # This is Phase 2 — decay application alone provides immediate value

        await self.db.commit()

        duration_ms = int((time.monotonic() - start) * 1000)
        remaining = await self.repo.count_by_project(None)

        logger.info(
            "memory.compaction_completed",
            merged_count=merged_count,
            remaining_count=remaining,
            duration_ms=duration_ms,
        )

        return CompactionStats(
            merged_count=merged_count,
            remaining_count=remaining,
            duration_ms=duration_ms,
        )
```

### Step 7: Create `app/memory/routes.py`

```python
"""REST API routes for agent memory."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.config import get_settings
from app.core.database import get_db
from app.knowledge.embedding import get_embedding_provider
from app.memory.schemas import (
    MemoryCreate,
    MemoryPromote,
    MemoryResponse,
    MemorySearch,
)
from app.memory.service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])
settings = get_settings()


def _get_service(db: AsyncSession = Depends(get_db)) -> MemoryService:
    provider = get_embedding_provider(settings)
    return MemoryService(db, provider)


@router.post("/", response_model=MemoryResponse, status_code=201)
async def store_memory(
    data: MemoryCreate,
    current_user: User = Depends(require_role(["admin", "developer"])),
    service: MemoryService = Depends(_get_service),
) -> MemoryResponse:
    """Store a new agent memory entry."""
    entry = await service.store(data)
    return MemoryResponse.model_validate(entry)


@router.post("/search", response_model=list[MemoryResponse])
async def search_memories(
    data: MemorySearch,
    current_user: User = Depends(require_role(["admin", "developer"])),
    service: MemoryService = Depends(_get_service),
) -> list[MemoryResponse]:
    """Search memories by similarity."""
    results = await service.recall(
        data.query,
        project_id=data.project_id,
        agent_type=data.agent_type,
        memory_type=data.memory_type,
        limit=data.limit,
    )
    return [
        MemoryResponse.model_validate(entry, update={"similarity": score})
        for entry, score in results
    ]


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: int,
    current_user: User = Depends(require_role(["admin", "developer"])),
    service: MemoryService = Depends(_get_service),
) -> MemoryResponse:
    """Get a specific memory entry."""
    entry = await service.get_by_id(memory_id)
    return MemoryResponse.model_validate(entry)


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: int,
    current_user: User = Depends(require_role(["admin", "developer"])),
    service: MemoryService = Depends(_get_service),
) -> None:
    """Delete a memory entry."""
    await service.delete(memory_id)


@router.post("/promote", response_model=MemoryResponse, status_code=201)
async def promote_dcg_note(
    data: MemoryPromote,
    current_user: User = Depends(require_role(["admin", "developer"])),
    service: MemoryService = Depends(_get_service),
) -> MemoryResponse:
    """Promote a DCG note into Hub memory (4.9.7 bridge)."""
    entry = await service.promote_from_dcg(data)
    return MemoryResponse.model_validate(entry)
```

### Step 8: Create `app/memory/compaction.py`

```python
"""Background memory compaction and decay poller."""

from app.core.config import get_settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.core.poller import DataPoller
from app.knowledge.embedding import get_embedding_provider
from app.memory.service import MemoryService

logger = get_logger(__name__)
settings = get_settings()


class MemoryCompactionPoller(DataPoller):
    """Periodically applies decay weights and compacts redundant memories."""

    def __init__(self) -> None:
        super().__init__(
            name="memory-compaction",
            interval_seconds=settings.memory.compaction_interval_hours * 3600,
        )

    async def fetch(self) -> object:
        """Run compaction cycle."""
        async with get_db_context() as db:
            provider = get_embedding_provider(settings)
            service = MemoryService(db, provider)
            stats = await service.run_compaction()
            return stats

    async def store(self, data: object) -> None:
        """Log compaction results."""
        logger.info("memory.compaction.cycle_completed", stats=str(data))
```

### Step 9: Create `app/memory/__init__.py`

```python
"""Agent memory system — persistent, searchable, project-scoped memory for AI agents."""
```

### Step 10: Register router in `app/main.py`

Find where other routers are included (look for `app.include_router`) and add:

```python
from app.memory.routes import router as memory_router
app.include_router(memory_router, prefix="/api/v1")
```

### Step 11: Alembic migration

```bash
make db-revision m="add memory_entries table"
```

The migration should create:
- `memory_entries` table with all columns from the model
- pgvector extension (if not already enabled — check existing migrations)
- Indexes: `ix_memory_project_agent`, `ix_memory_type_decay`, plus the default PK and individual column indexes
- ivfflat or HNSW index on the embedding column for fast similarity search

### Step 12: Tests

**`app/memory/tests/test_repository.py`** (unit tests with AsyncMock db):
1. `test_create_memory_entry` — inserts and returns with ID
2. `test_get_by_id_found` — returns entry
3. `test_get_by_id_not_found` — returns None
4. `test_count_by_project` — returns correct count
5. `test_delete_existing` — returns True
6. `test_delete_nonexistent` — returns False

**`app/memory/tests/test_service.py`** (unit tests with mocked repo + embedding):
7. `test_store_generates_embedding` — calls embedding.embed, stores result
8. `test_store_enforces_limit` — raises `MemoryLimitExceededError` at max
9. `test_recall_returns_sorted_results` — similarity search with scores
10. `test_promote_from_dcg` — creates entry with source="dcg", correct content prefix
11. `test_get_by_id_raises_not_found` — raises `MemoryNotFoundError`
12. `test_delete_raises_not_found` — raises `MemoryNotFoundError`

**`app/memory/tests/test_routes.py`** (route tests with mocked service):
13. `test_store_memory_201` — POST /memory returns 201
14. `test_search_memories_200` — POST /memory/search returns list
15. `test_get_memory_200` — GET /memory/{id} returns entry
16. `test_delete_memory_204` — DELETE /memory/{id} returns 204
17. `test_promote_dcg_note_201` — POST /memory/promote returns 201
18. `test_viewer_role_forbidden` — viewer gets 403 on all endpoints

## Key Design Decisions

1. **Reuse `app/knowledge/embedding.py`** — same `EmbeddingProvider` Protocol, same dimension (1024), no duplicate embedding infrastructure
2. **Decay via SQL** — `POWER(2, -age/half_life)` computed in PostgreSQL, not Python. Single UPDATE for all entries.
3. **Cross-agent by default** — memories are tagged with `source_agent` but readable by all agents in the project. No agent isolation.
4. **DCG bridge endpoint** — `POST /memory/promote` is the entry point for task 7.5's "Bridge to Hub memory" (TODO line 705). DCG notes promoted here get embedded and become searchable.
5. **Compaction as DataPoller** — reuses existing background task infrastructure with leader election
6. **project_id nullable** — NULL = global/org-level memory (PRD 4.9.6: "Cross-project memories available at organisation level")

## Verification

- [ ] `make lint` passes
- [ ] `make types` passes
- [ ] `make test` passes (all existing + 18 new tests)
- [ ] `POST /api/v1/memory/` stores entry with embedding
- [ ] `POST /api/v1/memory/search` returns relevant results by similarity
- [ ] `POST /api/v1/memory/promote` creates entry with source="dcg"
- [ ] `DELETE /api/v1/memory/{id}` removes entry
- [ ] Alembic migration creates table with pgvector index
