# pyright: reportUnknownMemberType=false
"""Repository for memory entry database operations."""

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scoped_db import scoped_access
from app.memory.models import MemoryEntry


class MemoryRepository:
    """Database operations for agent memory entries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entry: MemoryEntry) -> MemoryEntry:
        """Insert a new memory entry."""
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def get_by_id(self, memory_id: int) -> MemoryEntry | None:
        """Get a memory entry by ID, scoped to caller's accessible projects.

        Globals (`project_id IS NULL`) are visible to every authenticated
        caller; system-context callers see everything (admin sentinel).
        """
        access = scoped_access(self.db)
        query = select(MemoryEntry).where(MemoryEntry.id == memory_id)
        if access.project_ids is not None:
            query = query.where(
                or_(
                    MemoryEntry.project_id.in_(access.project_ids),
                    MemoryEntry.project_id.is_(None),
                )
            )
        result = await self.db.execute(query)
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
        access = scoped_access(self.db)
        distance = MemoryEntry.embedding.cosine_distance(embedding)
        weighted_score = (1 - distance) * MemoryEntry.decay_weight

        query = select(MemoryEntry, weighted_score.label("score")).where(
            MemoryEntry.embedding.is_not(None)
        )

        if access.project_ids is not None:
            # Caller can only ever see memories tied to their projects + globals.
            query = query.where(
                or_(
                    MemoryEntry.project_id.in_(access.project_ids),
                    MemoryEntry.project_id.is_(None),
                )
            )
        if project_id is not None:
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
        """Count memories for a project (None counts all)."""
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
        stmt = text("""
            UPDATE memory_entries
            SET decay_weight = POWER(
                2.0,
                -EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 / :half_life
            )
            WHERE is_evergreen = false
              AND ABS(
                  decay_weight - POWER(
                      2.0,
                      -EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 / :half_life
                  )
              ) > 0.01
        """)
        result = await self.db.execute(stmt, {"half_life": half_life_days})
        return int(getattr(result, "rowcount", 0))

    async def apply_phase_aware_decay(
        self,
        *,
        active_half_life: int,
        maintenance_half_life: int,
        archived_half_life: int,
        default_half_life: int,
    ) -> int:
        """Apply temporal decay with per-project-phase half-lives.

        Memories without a project_id use default_half_life.
        """
        # Project-scoped memories: join projects table for phase
        project_stmt = text("""
            UPDATE memory_entries me
            SET decay_weight = POWER(
                2.0,
                -EXTRACT(EPOCH FROM (NOW() - me.created_at)) / 86400.0 / (
                    CASE
                        WHEN p.phase = 'maintenance' THEN :maintenance_hl
                        WHEN p.phase = 'archived' THEN :archived_hl
                        WHEN p.phase = 'active' THEN :active_hl
                        ELSE :default_hl
                    END
                )
            )
            FROM projects p
            WHERE me.project_id = p.id
              AND me.is_evergreen = false
              AND ABS(
                  me.decay_weight - POWER(
                      2.0,
                      -EXTRACT(EPOCH FROM (NOW() - me.created_at)) / 86400.0 / (
                          CASE
                              WHEN p.phase = 'maintenance' THEN :maintenance_hl
                              WHEN p.phase = 'archived' THEN :archived_hl
                              WHEN p.phase = 'active' THEN :active_hl
                              ELSE :default_hl
                          END
                      )
                  )
              ) > 0.01
        """)
        project_result = await self.db.execute(
            project_stmt,
            {
                "active_hl": active_half_life,
                "maintenance_hl": maintenance_half_life,
                "archived_hl": archived_half_life,
                "default_hl": default_half_life,
            },
        )
        project_count = int(getattr(project_result, "rowcount", 0))

        # Global memories (no project) use default half-life
        global_stmt = text("""
            UPDATE memory_entries
            SET decay_weight = POWER(
                2.0,
                -EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 / :half_life
            )
            WHERE is_evergreen = false
              AND project_id IS NULL
              AND ABS(
                  decay_weight - POWER(
                      2.0,
                      -EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 / :half_life
                  )
              ) > 0.01
        """)
        global_result = await self.db.execute(global_stmt, {"half_life": default_half_life})
        global_count = int(getattr(global_result, "rowcount", 0))

        return project_count + global_count

    async def get_non_evergreen_with_embeddings(
        self,
        limit: int = 200,
    ) -> list[MemoryEntry]:
        """Get non-evergreen memories that have embeddings, newest first."""
        query = (
            select(MemoryEntry)
            .where(
                MemoryEntry.is_evergreen == False,  # noqa: E712
                MemoryEntry.embedding.is_not(None),
                MemoryEntry.decay_weight > 0.1,  # Skip nearly-dead memories
            )
            .order_by(MemoryEntry.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

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
        entries = list(result.scalars().all())
        for entry in entries:
            await self.db.delete(entry)
        await self.db.flush()
        return len(entries)
