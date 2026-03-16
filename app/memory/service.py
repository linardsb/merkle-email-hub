"""Business logic for agent memory operations."""

import time
from typing import Any

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
    """Orchestrates agent memory storage, retrieval, and maintenance."""

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
        count = await self.repo.count_by_project(data.project_id)
        if count >= settings.memory.max_memories_per_project:
            raise MemoryLimitExceededError(
                f"Project memory limit ({settings.memory.max_memories_per_project}) exceeded"
            )

        embeddings = await self.embedding.embed([data.content])
        embedding = embeddings[0] if embeddings else None

        metadata: dict[str, Any] | None = None
        if data.metadata is not None:
            metadata = dict(data.metadata)

        entry = MemoryEntry(
            agent_type=data.agent_type,
            memory_type=data.memory_type,
            content=data.content,
            embedding=embedding,
            project_id=data.project_id,
            metadata_json=metadata,
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

    @staticmethod
    def get_decay_rate(phase: str) -> int:
        """Return half-life days for a project phase."""
        s = get_settings()
        rates: dict[str, int] = {
            "active": s.memory.decay_active_days,
            "maintenance": s.memory.decay_maintenance_days,
            "archived": s.memory.decay_archived_days,
        }
        return rates.get(phase, s.memory.default_decay_half_life_days)

    async def run_compaction(self) -> CompactionStats:
        """Apply phase-aware decay and intent-aware merging."""
        start = time.monotonic()

        # Phase 1: Phase-aware decay
        await self.repo.apply_phase_aware_decay(
            active_half_life=settings.memory.decay_active_days,
            maintenance_half_life=settings.memory.decay_maintenance_days,
            archived_half_life=settings.memory.decay_archived_days,
            default_half_life=settings.memory.default_decay_half_life_days,
        )
        await self.db.commit()

        # Phase 2: Intent-aware merging
        intent_merged = await self._run_intent_merging()
        if intent_merged > 0:
            await self.db.commit()

        duration_ms = int((time.monotonic() - start) * 1000)
        remaining = await self.repo.count_by_project(None)

        logger.info(
            "memory.compaction_completed",
            merged_count=0,
            intent_merged_count=intent_merged,
            remaining_count=remaining,
            duration_ms=duration_ms,
        )

        return CompactionStats(
            merged_count=0,
            intent_merged_count=intent_merged,
            remaining_count=remaining,
            duration_ms=duration_ms,
        )

    async def _run_intent_merging(self) -> int:
        """Merge functionally equivalent memories using embedding + LLM judge.

        For each non-evergreen memory, find candidates with cosine > intent_threshold.
        Run lightweight LLM judge to confirm functional equivalence before merging.
        Keep the newer memory, delete the older one.
        """
        from app.memory.compaction import judge_functional_equivalence

        threshold = settings.memory.intent_similarity_threshold
        merged = 0
        processed_ids: set[int] = set()

        entries = await self.repo.get_non_evergreen_with_embeddings()

        for entry in entries:
            if entry.id in processed_ids:
                continue
            candidates = await self.repo.find_similar_for_compaction(entry, threshold)
            for candidate in candidates:
                if candidate.id in processed_ids:
                    continue
                is_equivalent = await judge_functional_equivalence(entry.content, candidate.content)
                if is_equivalent:
                    older = candidate if entry.created_at >= candidate.created_at else entry
                    newer = entry if older is candidate else candidate
                    await self.repo.delete(older.id)
                    processed_ids.add(older.id)
                    merged += 1
                    logger.info(
                        "memory.intent_merge_completed",
                        kept_id=newer.id,
                        deleted_id=older.id,
                    )
                    break  # Move to next entry after first merge

        return merged
