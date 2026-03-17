"""Yjs document persistence with inline compaction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pycrdt
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.streaming.crdt.models import CollaborativeDocument

logger = get_logger(__name__)


class YjsDocumentStore:
    """Manages Yjs document persistence in PostgreSQL.

    Documents are stored as a compacted state + pending incremental updates.
    Compaction merges pending updates into the state when thresholds are reached.
    """

    def __init__(
        self,
        compaction_threshold: int = 100,
        compaction_interval_s: int = 300,
        max_document_size_mb: int = 5,
    ) -> None:
        self._compaction_threshold = compaction_threshold
        self._compaction_interval_s = compaction_interval_s
        self._max_size_bytes = max_document_size_mb * 1024 * 1024
        # In-memory doc cache: room_id -> pycrdt.Doc[Any]
        self._docs: dict[str, pycrdt.Doc[Any]] = {}

    async def get_or_create(self, db: AsyncSession, room_id: str) -> pycrdt.Doc[Any]:
        """Load or create a Yjs document for a room.

        Returns a pycrdt.Doc[Any] with the full state applied.
        The doc is cached in memory for the lifetime of this store instance.
        """
        if room_id in self._docs:
            return self._docs[room_id]

        result = await db.execute(
            sa.select(CollaborativeDocument).where(CollaborativeDocument.room_id == room_id)
        )
        row = result.scalar_one_or_none()

        doc: pycrdt.Doc[Any] = pycrdt.Doc()
        if row is not None:
            try:
                # Apply compacted state
                if row.state:
                    doc.apply_update(row.state)
                # Apply pending updates
                if row.pending_updates:
                    doc.apply_update(row.pending_updates)
            except Exception:
                logger.warning("crdt.doc.corrupted_state", room_id=room_id)
                doc = pycrdt.Doc()  # Start fresh on corrupted state
        else:
            # Create new document record
            new_doc = CollaborativeDocument(room_id=room_id)
            db.add(new_doc)
            await db.flush()

        self._docs[room_id] = doc
        logger.info("crdt.doc.loaded", room_id=room_id, from_db=row is not None)
        return doc

    async def apply_update(
        self,
        db: AsyncSession,
        room_id: str,
        update: bytes,
    ) -> bool:
        """Apply a Yjs update to the document and persist it.

        Returns True if applied, False if rejected (size limit).
        Triggers inline compaction when thresholds are reached.
        """
        doc = self._docs.get(room_id)
        if doc is None:
            doc = await self.get_or_create(db, room_id)

        # Size guard
        current_state = doc.get_update()
        current_size = len(current_state)
        if current_size + len(update) > self._max_size_bytes:
            logger.warning(
                "crdt.doc.size_limit",
                room_id=room_id,
                current_bytes=current_size,
                update_bytes=len(update),
                max_bytes=self._max_size_bytes,
            )
            return False

        # Apply to in-memory doc
        try:
            doc.apply_update(update)
        except Exception:
            logger.warning("crdt.doc.invalid_update", room_id=room_id, update_bytes=len(update))
            return False

        # Persist: append to pending_updates and increment counter
        result = await db.execute(
            sa.select(CollaborativeDocument).where(CollaborativeDocument.room_id == room_id)
        )
        row = result.scalar_one()

        # Concatenate the new update to pending (simple append; both are valid Yjs updates)
        row.pending_updates = row.pending_updates + update if row.pending_updates else update
        row.pending_update_count += 1
        row.document_size_bytes = len(doc.get_update())  # post-apply state

        # Check compaction thresholds
        needs_compaction = (
            row.pending_update_count >= self._compaction_threshold
            or (datetime.now(UTC) - row.last_compacted_at).total_seconds()
            >= self._compaction_interval_s
        )

        if needs_compaction:
            await self._compact(row, doc)

        await db.flush()
        return True

    async def get_state_vector(self, room_id: str) -> bytes:
        """Get the state vector for sync protocol Step 1."""
        doc = self._docs.get(room_id)
        if doc is None:
            return b""
        return doc.get_state()

    async def get_update_for_peer(self, room_id: str, state_vector: bytes) -> bytes:
        """Compute the update a peer needs based on their state vector (sync Step 2)."""
        doc = self._docs.get(room_id)
        if doc is None:
            return b""
        if not state_vector:
            # Empty state vector means client has nothing — send full state
            return doc.get_update()
        return doc.get_update(state_vector)

    async def get_full_state(self, room_id: str) -> bytes:
        """Get full document state as a single Yjs update (for new connections)."""
        doc = self._docs.get(room_id)
        if doc is None:
            return b""
        return doc.get_update()

    def evict(self, room_id: str) -> None:
        """Remove a document from the in-memory cache (when room empties)."""
        self._docs.pop(room_id, None)
        logger.info("crdt.doc.evicted", room_id=room_id)

    async def _compact(
        self,
        row: CollaborativeDocument,
        doc: pycrdt.Doc[Any],
    ) -> None:
        """Merge pending updates into compacted state."""
        row.state = doc.get_update()
        row.pending_updates = b""
        row.pending_update_count = 0
        row.last_compacted_at = datetime.now(UTC)
        logger.info(
            "crdt.doc.compacted",
            room_id=row.room_id,
            state_bytes=len(row.state),
        )
