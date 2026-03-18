"""Tests for YjsDocumentStore."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pycrdt
import pytest

from app.streaming.crdt.document_store import YjsDocumentStore


def _make_update() -> bytes:
    """Create a valid Yjs update by modifying a doc."""
    doc: pycrdt.Doc[Any] = pycrdt.Doc()
    text = doc.get("content", type=pycrdt.Text)
    text += "hello"
    return doc.get_update()


def _make_db_row(room_id: str = "project:1:template:1") -> MagicMock:
    row = MagicMock()
    row.room_id = room_id
    row.state = b""
    row.pending_updates = b""
    row.pending_update_count = 0
    row.last_compacted_at = datetime.now(UTC)
    row.document_size_bytes = 0
    return row


@pytest.fixture
def store() -> YjsDocumentStore:
    return YjsDocumentStore(
        compaction_threshold=3,
        compaction_interval_s=300,
        max_document_size_mb=1,
    )


ROOM = "project:1:template:10"


@pytest.mark.anyio
async def test_get_or_create_new_doc(store: YjsDocumentStore) -> None:
    """New room creates empty doc and DB record."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    doc = await store.get_or_create(db, ROOM)

    assert isinstance(doc, pycrdt.Doc)
    db.add.assert_called_once()
    db.flush.assert_awaited_once()


@pytest.mark.anyio
async def test_get_or_create_cached(store: YjsDocumentStore) -> None:
    """Second call returns cached doc without DB query."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    doc1 = await store.get_or_create(db, ROOM)
    doc2 = await store.get_or_create(db, ROOM)

    assert doc1 is doc2
    # Only one DB call (first time)
    assert db.execute.await_count == 1


@pytest.mark.anyio
async def test_apply_update(store: YjsDocumentStore) -> None:
    """Update is applied to doc and persisted."""
    db = AsyncMock()
    row = _make_db_row(ROOM)

    # First call: get_or_create
    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    # Second call: apply_update select
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row

    db.execute.side_effect = [result_new, result_existing]

    await store.get_or_create(db, ROOM)

    update = _make_update()
    applied = await store.apply_update(db, ROOM, update)

    assert applied is True
    assert row.pending_update_count == 1


@pytest.mark.anyio
async def test_compaction_triggers(store: YjsDocumentStore) -> None:
    """Compaction triggers when threshold is reached."""
    db = AsyncMock()
    row = _make_db_row(ROOM)
    row.pending_update_count = 2  # threshold is 3, so next update triggers

    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row

    db.execute.side_effect = [result_new, result_existing]

    await store.get_or_create(db, ROOM)

    update = _make_update()
    await store.apply_update(db, ROOM, update)

    # After compaction: pending is cleared, state is set
    assert row.pending_update_count == 0
    assert row.pending_updates == b""
    assert len(row.state) > 0


@pytest.mark.anyio
async def test_size_limit_rejected(store: YjsDocumentStore) -> None:
    """Updates exceeding size limit are rejected."""
    store._max_size_bytes = 10  # Very small limit

    db = AsyncMock()
    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    db.execute.return_value = result_new

    await store.get_or_create(db, ROOM)

    # This update will exceed the 10-byte limit
    big_update = _make_update()
    applied = await store.apply_update(db, ROOM, big_update)
    assert applied is False


@pytest.mark.anyio
async def test_evict(store: YjsDocumentStore) -> None:
    """Evicting removes doc from cache."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    await store.get_or_create(db, ROOM)
    assert ROOM in store._docs

    store.evict(ROOM)
    assert ROOM not in store._docs


@pytest.mark.anyio
async def test_get_full_state(store: YjsDocumentStore) -> None:
    """Full state returns valid Yjs update."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    await store.get_or_create(db, ROOM)

    state = await store.get_full_state(ROOM)
    assert isinstance(state, bytes)


# --- Phase 24.8 new tests ---


@pytest.mark.anyio
async def test_concurrent_updates_both_preserved(store: YjsDocumentStore) -> None:
    """Two sequential updates are both reflected in final state."""
    db = AsyncMock()
    # get_or_create: no existing row
    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    # apply_update calls
    row = _make_db_row(ROOM)
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row

    db.execute.side_effect = [result_new, result_existing, result_existing]

    await store.get_or_create(db, ROOM)

    update1 = _make_update()
    update2 = _make_update()

    result1 = await store.apply_update(db, ROOM, update1)
    result2 = await store.apply_update(db, ROOM, update2)

    assert result1 is True
    assert result2 is True
    assert row.pending_update_count == 2


@pytest.mark.anyio
async def test_compaction_by_time_threshold() -> None:
    """Compaction triggers when time interval exceeded."""
    store = YjsDocumentStore(
        compaction_threshold=1000,  # High count threshold
        compaction_interval_s=0,  # Zero seconds = always compact by time
    )
    db = AsyncMock()
    row = _make_db_row(ROOM)
    row.last_compacted_at = datetime(2020, 1, 1, tzinfo=UTC)  # Long ago
    row.pending_update_count = 0

    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row

    db.execute.side_effect = [result_new, result_existing]

    await store.get_or_create(db, ROOM)

    update = _make_update()
    await store.apply_update(db, ROOM, update)

    # Should have compacted due to time threshold
    assert row.pending_update_count == 0
    assert row.pending_updates == b""


@pytest.mark.anyio
async def test_corrupted_state_creates_fresh_doc() -> None:
    """Corrupted state in DB results in fresh empty document."""
    store = YjsDocumentStore()
    db = AsyncMock()
    row = _make_db_row(ROOM)
    row.state = b"\xff\xff\xff\xff"  # Invalid Yjs state
    row.pending_updates = b""

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row
    db.execute.return_value = result_mock

    doc = await store.get_or_create(db, ROOM)
    assert doc is not None
    assert isinstance(doc, pycrdt.Doc)


@pytest.mark.anyio
async def test_get_state_vector_unloaded_room() -> None:
    """get_state_vector returns empty bytes for unloaded room."""
    store = YjsDocumentStore()
    sv = await store.get_state_vector("nonexistent")
    assert sv == b""


@pytest.mark.anyio
async def test_get_update_for_peer_empty_sv(store: YjsDocumentStore) -> None:
    """Empty state vector returns full document state (new client)."""
    db = AsyncMock()
    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None
    row = _make_db_row(ROOM)
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row

    db.execute.side_effect = [result_new, result_existing]

    await store.get_or_create(db, ROOM)
    update = _make_update()
    await store.apply_update(db, ROOM, update)

    full_state = await store.get_update_for_peer(ROOM, b"")
    assert len(full_state) > 0
