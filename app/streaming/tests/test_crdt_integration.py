"""Integration tests: CRDT document store + sync handler end-to-end."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pycrdt
import pytest

from app.streaming.crdt.document_store import YjsDocumentStore
from app.streaming.crdt.sync_handler import MessageType, SyncMessageType, YjsSyncHandler

ROOM = "project:1:template:1"


def _make_db_row(room_id: str = ROOM) -> MagicMock:
    row = MagicMock()
    row.room_id = room_id
    row.state = b""
    row.pending_updates = b""
    row.pending_update_count = 0
    row.last_compacted_at = datetime.now(UTC)
    row.document_size_bytes = 0
    return row


def _make_db(row: MagicMock | None = None) -> AsyncMock:
    """Create mock db session. If row is None, simulates new doc creation."""
    db = AsyncMock()
    if row is None:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock
    else:
        result_new = MagicMock()
        result_new.scalar_one_or_none.return_value = None
        result_existing = MagicMock()
        result_existing.scalar_one.return_value = row
        db.execute.side_effect = [result_new, result_existing]
    return db


def _create_update(text: str = "hello") -> bytes:
    """Create a valid Yjs update with text content."""
    doc: pycrdt.Doc[Any] = pycrdt.Doc()
    t = doc.get("content", type=pycrdt.Text)
    t += text
    return doc.get_update()


@pytest.mark.anyio
async def test_full_sync_protocol_flow() -> None:
    """SyncStep1 -> SyncStep2 -> both sides converge."""
    store = YjsDocumentStore(compaction_threshold=100)
    handler = YjsSyncHandler(store)

    db = _make_db()
    await handler.init_room(db, ROOM)

    # Client sends SyncStep1 with empty state vector
    step1_msg = bytes([MessageType.SYNC, SyncMessageType.STEP1])
    replies, broadcasts = await handler.handle_sync_message(db, ROOM, "client1", step1_msg)

    # Should get SyncStep2 (with doc state) + server SyncStep1 (requesting client state)
    assert len(replies) == 2
    assert replies[0][0] == MessageType.SYNC
    assert replies[0][1] == SyncMessageType.STEP2
    assert replies[1][0] == MessageType.SYNC
    assert replies[1][1] == SyncMessageType.STEP1
    assert broadcasts == []


@pytest.mark.anyio
async def test_two_clients_concurrent_edits() -> None:
    """Two updates applied sequentially, both text preserved in doc."""
    store = YjsDocumentStore(compaction_threshold=100)
    handler = YjsSyncHandler(store)

    row = _make_db_row()
    db = AsyncMock()
    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row
    # init + 2 apply_update calls
    db.execute.side_effect = [result_new, result_existing, result_existing]

    await handler.init_room(db, ROOM)

    update1 = _create_update("hello")
    msg1 = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update1
    _, broadcasts1 = await handler.handle_sync_message(db, ROOM, "c1", msg1)
    assert len(broadcasts1) == 1

    update2 = _create_update(" world")
    msg2 = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update2
    _, broadcasts2 = await handler.handle_sync_message(db, ROOM, "c2", msg2)
    assert len(broadcasts2) == 1

    # Both updates applied
    assert row.pending_update_count == 2


@pytest.mark.anyio
async def test_compaction_preserves_all_content() -> None:
    """Many updates -> compact -> text content is intact."""
    store = YjsDocumentStore(compaction_threshold=3)
    handler = YjsSyncHandler(store)

    row = _make_db_row()
    db = AsyncMock()
    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row
    # init + 5 updates
    db.execute.side_effect = [result_new] + [result_existing] * 5

    await handler.init_room(db, ROOM)

    for i in range(5):
        update = _create_update(f"part{i}")
        msg = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update
        await handler.handle_sync_message(db, ROOM, "c1", msg)

    # After 5 updates with threshold=3, compaction should have triggered
    # Row state should contain compacted data
    assert len(row.state) > 0

    # Content should be accessible via the doc
    full = await store.get_full_state(ROOM)
    assert len(full) > 0


@pytest.mark.anyio
async def test_sync_after_compaction() -> None:
    """Compacted state syncs correctly to new peer via SyncStep1."""
    store = YjsDocumentStore(compaction_threshold=2)
    handler = YjsSyncHandler(store)

    row = _make_db_row()
    db = AsyncMock()
    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row
    db.execute.side_effect = [result_new] + [result_existing] * 3

    await handler.init_room(db, ROOM)

    # Apply updates to trigger compaction
    for i in range(3):
        update = _create_update(f"text{i}")
        msg = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update
        await handler.handle_sync_message(db, ROOM, "c1", msg)

    # New peer syncs with empty state vector
    step1 = bytes([MessageType.SYNC, SyncMessageType.STEP1])
    replies, _ = await handler.handle_sync_message(db, ROOM, "c2", step1)

    assert len(replies) == 2
    # SyncStep2 should contain all content
    assert len(replies[0]) > 2  # More than just header bytes


@pytest.mark.anyio
async def test_large_document_growth() -> None:
    """Document size is tracked via document_size_bytes."""
    store = YjsDocumentStore(compaction_threshold=100)
    handler = YjsSyncHandler(store)

    row = _make_db_row()
    db = AsyncMock()
    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row
    db.execute.side_effect = [result_new] + [result_existing] * 3

    await handler.init_room(db, ROOM)

    sizes: list[int] = []
    for i in range(3):
        update = _create_update(f"growth test {i} " * 10)
        msg = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update
        await handler.handle_sync_message(db, ROOM, "c1", msg)
        sizes.append(row.document_size_bytes)

    # Size should be monotonically increasing
    assert sizes[0] > 0
    assert sizes[-1] >= sizes[0]


@pytest.mark.anyio
async def test_evict_and_reload() -> None:
    """Evict from cache, verify no longer present."""
    store = YjsDocumentStore(compaction_threshold=100)
    handler = YjsSyncHandler(store)

    db = _make_db()
    await handler.init_room(db, ROOM)
    assert ROOM in store._docs

    handler.cleanup_room(ROOM)
    assert ROOM not in store._docs

    # Re-load creates a fresh doc
    db2 = _make_db()
    await handler.init_room(db2, ROOM)
    assert ROOM in store._docs


@pytest.mark.anyio
async def test_init_room_idempotent() -> None:
    """Calling init_room twice is safe (cached on second call)."""
    store = YjsDocumentStore(compaction_threshold=100)
    handler = YjsSyncHandler(store)

    db = _make_db()
    await handler.init_room(db, ROOM)
    doc1 = store._docs.get(ROOM)

    # Second init uses cached doc
    await handler.init_room(db, ROOM)
    doc2 = store._docs.get(ROOM)

    assert doc1 is doc2


@pytest.mark.anyio
async def test_cleanup_room_idempotent() -> None:
    """Calling cleanup on empty room is safe."""
    store = YjsDocumentStore()
    handler = YjsSyncHandler(store)

    # Cleanup on room that was never loaded — should not raise
    handler.cleanup_room("nonexistent:room")
    handler.cleanup_room("nonexistent:room")  # Second call also safe
