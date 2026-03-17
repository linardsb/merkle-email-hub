"""Tests for YjsSyncHandler."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pycrdt
import pytest

from app.streaming.crdt.document_store import YjsDocumentStore
from app.streaming.crdt.sync_handler import (
    MessageType,
    SyncMessageType,
    YjsSyncHandler,
)

ROOM = "project:1:template:10"


@pytest.fixture
def store() -> YjsDocumentStore:
    return YjsDocumentStore(compaction_threshold=100)


@pytest.fixture
def handler(store: YjsDocumentStore) -> YjsSyncHandler:
    return YjsSyncHandler(store)


def _make_sync_step1(state_vector: bytes = b"") -> bytes:
    """Build a SyncStep1 message."""
    return bytes([MessageType.SYNC, SyncMessageType.STEP1]) + state_vector


def _make_sync_update(update: bytes) -> bytes:
    """Build a sync Update message."""
    return bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update


def _create_update(text: str = "hello") -> bytes:
    """Create a valid Yjs update."""
    doc: pycrdt.Doc[Any] = pycrdt.Doc()
    t = doc.get("content", type=pycrdt.Text)
    t += text
    return doc.get_update()


@pytest.mark.anyio
async def test_step1_returns_step2(handler: YjsSyncHandler, store: YjsDocumentStore) -> None:
    """SyncStep1 returns SyncStep2 response with document state."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    await handler.init_room(db, ROOM)

    msg = _make_sync_step1()
    replies, broadcasts = await handler.handle_sync_message(db, ROOM, "user1", msg)

    assert len(replies) == 2  # SyncStep2 + our SyncStep1
    assert replies[0][0] == MessageType.SYNC
    assert replies[0][1] == SyncMessageType.STEP2
    assert broadcasts == []


@pytest.mark.anyio
async def test_update_persists_and_broadcasts(
    handler: YjsSyncHandler, store: YjsDocumentStore
) -> None:
    """Incoming update is persisted and broadcast to peers."""
    db = AsyncMock()
    result_new = MagicMock()
    result_new.scalar_one_or_none.return_value = None

    row = MagicMock()
    row.room_id = ROOM
    row.state = b""
    row.pending_updates = b""
    row.pending_update_count = 0
    row.last_compacted_at = datetime.now(UTC)
    row.document_size_bytes = 0
    result_existing = MagicMock()
    result_existing.scalar_one.return_value = row

    db.execute.side_effect = [result_new, result_existing]

    await handler.init_room(db, ROOM)

    update = _create_update()
    msg = _make_sync_update(update)
    replies, broadcasts = await handler.handle_sync_message(db, ROOM, "user1", msg)

    assert replies == []
    assert len(broadcasts) == 1
    assert broadcasts[0][0] == MessageType.SYNC
    assert broadcasts[0][1] == SyncMessageType.UPDATE


@pytest.mark.anyio
async def test_empty_message_ignored(handler: YjsSyncHandler) -> None:
    """Messages shorter than 2 bytes are ignored."""
    db = AsyncMock()
    replies, broadcasts = await handler.handle_sync_message(db, ROOM, "user1", b"")
    assert replies == []
    assert broadcasts == []


@pytest.mark.anyio
async def test_non_sync_message_passthrough(handler: YjsSyncHandler) -> None:
    """Non-sync messages (awareness) pass through as broadcasts."""
    db = AsyncMock()
    msg = bytes([MessageType.AWARENESS, 0]) + b"awareness_data"
    replies, broadcasts = await handler.handle_sync_message(db, ROOM, "user1", msg)
    assert replies == []
    assert len(broadcasts) == 1


@pytest.mark.anyio
async def test_cleanup_room(handler: YjsSyncHandler, store: YjsDocumentStore) -> None:
    """Cleanup evicts doc from store."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock

    await handler.init_room(db, ROOM)
    assert ROOM in store._docs

    handler.cleanup_room(ROOM)
    assert ROOM not in store._docs
