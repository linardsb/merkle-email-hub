"""Deterministic CRDT convergence tests.

Validates that concurrent edits on independent pycrdt documents
converge to identical state after bidirectional sync.
"""

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

from .conftest import apply_delete, apply_insert, get_text, sync_docs

ROOM = "project:1:template:99"


# ---------------------------------------------------------------------------
# Two-client convergence
# ---------------------------------------------------------------------------


@pytest.mark.collab
class TestTwoClientConvergence:
    """Two clients editing the same document must converge."""

    def test_concurrent_inserts_at_same_position(
        self, doc_pair: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]
    ) -> None:
        doc1, doc2 = doc_pair
        apply_insert(doc1, 0, "hello")
        apply_insert(doc2, 0, "world")
        sync_docs(doc1, doc2)

        assert get_text(doc1) == get_text(doc2)
        assert "hello" in get_text(doc1)
        assert "world" in get_text(doc1)

    def test_concurrent_inserts_at_different_positions(
        self, doc_pair: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]
    ) -> None:
        doc1, doc2 = doc_pair
        # Seed both with shared base text
        t1 = doc1.get("content", type=pycrdt.Text)
        t1 += "abcdef"
        sync_docs(doc1, doc2)

        # Concurrent edits at different positions
        apply_insert(doc1, 0, "X")
        apply_insert(doc2, 6, "Y")
        sync_docs(doc1, doc2)

        result = get_text(doc1)
        assert get_text(doc1) == get_text(doc2)
        assert "X" in result
        assert "Y" in result

    def test_concurrent_insert_and_delete(
        self, doc_pair: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]
    ) -> None:
        doc1, doc2 = doc_pair
        # Shared base
        t1 = doc1.get("content", type=pycrdt.Text)
        t1 += "abcdef"
        sync_docs(doc1, doc2)

        # Client 1 inserts, client 2 deletes
        apply_insert(doc1, 3, "XYZ")
        apply_delete(doc2, 0, 2)
        sync_docs(doc1, doc2)

        result = get_text(doc1)
        assert get_text(doc1) == get_text(doc2)
        # Insert should survive despite concurrent delete at different position
        assert "XYZ" in result

    def test_sequential_edits_different_order(
        self, doc_pair: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]
    ) -> None:
        """Apply same edits in different order — still converge."""
        doc1, doc2 = doc_pair
        # Doc1 applies A then B
        apply_insert(doc1, 0, "A")
        apply_insert(doc1, 1, "B")
        # Doc2 applies B then A
        apply_insert(doc2, 0, "B")
        apply_insert(doc2, 0, "A")
        sync_docs(doc1, doc2)

        assert get_text(doc1) == get_text(doc2)

    def test_empty_documents_converge(
        self, doc_pair: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]
    ) -> None:
        doc1, doc2 = doc_pair
        sync_docs(doc1, doc2)
        assert get_text(doc1) == get_text(doc2)
        assert get_text(doc1) == ""


# ---------------------------------------------------------------------------
# Three-client convergence
# ---------------------------------------------------------------------------


@pytest.mark.collab
class TestThreeClientConvergence:
    """Three concurrent editors must all converge."""

    def test_three_clients_converge(
        self,
        doc_trio: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any], pycrdt.Doc[Any]],
    ) -> None:
        d1, d2, d3 = doc_trio
        apply_insert(d1, 0, "aaa")
        apply_insert(d2, 0, "bbb")
        apply_insert(d3, 0, "ccc")
        sync_docs(d1, d2, d3)

        texts = [get_text(d) for d in (d1, d2, d3)]
        assert texts[0] == texts[1] == texts[2]
        for word in ("aaa", "bbb", "ccc"):
            assert word in texts[0]

    def test_three_clients_mixed_ops(
        self,
        doc_trio: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any], pycrdt.Doc[Any]],
    ) -> None:
        d1, d2, d3 = doc_trio
        # Shared base
        t1 = d1.get("content", type=pycrdt.Text)
        t1 += "hello world"
        sync_docs(d1, d2, d3)

        # Concurrent: insert, delete, insert
        apply_insert(d1, 5, "!!!")
        apply_delete(d2, 0, 5)
        apply_insert(d3, 11, " end")
        sync_docs(d1, d2, d3)

        texts = [get_text(d) for d in (d1, d2, d3)]
        assert texts[0] == texts[1] == texts[2]


# ---------------------------------------------------------------------------
# Offline reconnection
# ---------------------------------------------------------------------------


@pytest.mark.collab
class TestOfflineReconnection:
    """Clients editing offline converge when they reconnect."""

    def test_offline_edits_merge_on_reconnect(
        self, doc_pair: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]
    ) -> None:
        doc1, doc2 = doc_pair
        # Initial shared state
        t1 = doc1.get("content", type=pycrdt.Text)
        t1 += "base"
        sync_docs(doc1, doc2)

        # Client 1 goes offline, both edit independently
        apply_insert(doc1, 4, " offline1")
        apply_insert(doc2, 4, " offline2")
        # "Reconnect" — sync
        sync_docs(doc1, doc2)

        result = get_text(doc1)
        assert get_text(doc1) == get_text(doc2)
        assert "offline1" in result
        assert "offline2" in result

    def test_long_offline_divergence(
        self, doc_pair: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]
    ) -> None:
        doc1, doc2 = doc_pair
        # Many offline edits on each side
        for i in range(20):
            apply_insert(doc1, i * 2, f"a{i}")
        for i in range(20):
            apply_insert(doc2, i * 2, f"b{i}")
        sync_docs(doc1, doc2)

        result = get_text(doc1)
        assert get_text(doc1) == get_text(doc2)
        # All inserts from both sides present
        assert "a0" in result
        assert "a19" in result
        assert "b0" in result
        assert "b19" in result

    def test_offline_delete_vs_online_insert(
        self, doc_pair: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]
    ) -> None:
        doc1, doc2 = doc_pair
        t1 = doc1.get("content", type=pycrdt.Text)
        t1 += "abcdefgh"
        sync_docs(doc1, doc2)

        # Client 1 deletes middle, client 2 inserts at start
        apply_delete(doc1, 2, 4)  # remove "cdef"
        apply_insert(doc2, 0, "ZZ")
        sync_docs(doc1, doc2)

        result = get_text(doc1)
        assert get_text(doc1) == get_text(doc2)
        assert "ZZ" in result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.collab
class TestEdgeCases:
    """Edge cases: idempotency, empty updates, large docs."""

    def test_duplicate_update_idempotent(self) -> None:
        doc1: pycrdt.Doc[Any] = pycrdt.Doc()
        doc2: pycrdt.Doc[Any] = pycrdt.Doc()
        t1 = doc1.get("content", type=pycrdt.Text)
        t1 += "hello"

        update = doc1.get_update()
        doc2.apply_update(update)
        doc2.apply_update(update)  # duplicate — should be safe

        assert get_text(doc2) == "hello"

    def test_empty_update_no_op(self) -> None:
        doc1: pycrdt.Doc[Any] = pycrdt.Doc()
        doc2: pycrdt.Doc[Any] = pycrdt.Doc()
        t1 = doc1.get("content", type=pycrdt.Text)
        t1 += "keep"

        # Sync then send an "empty" delta (no new ops)
        sync_docs(doc1, doc2)
        sv = doc2.get_state()
        empty_delta = doc1.get_update(sv)
        doc2.apply_update(empty_delta)

        assert get_text(doc2) == "keep"

    def test_large_document_convergence(
        self, doc_pair: tuple[pycrdt.Doc[Any], pycrdt.Doc[Any]]
    ) -> None:
        doc1, doc2 = doc_pair
        # Build a 1000-char document
        t1 = doc1.get("content", type=pycrdt.Text)
        t1 += "x" * 1000
        sync_docs(doc1, doc2)

        # Concurrent edits on large doc
        apply_insert(doc1, 500, "MIDDLE")
        apply_insert(doc2, 0, "START")
        apply_insert(doc2, 1000, "END")
        sync_docs(doc1, doc2)

        result = get_text(doc1)
        assert get_text(doc1) == get_text(doc2)
        assert "MIDDLE" in result
        assert result.startswith("START")


# ---------------------------------------------------------------------------
# Sync handler convergence (integration with YjsSyncHandler)
# ---------------------------------------------------------------------------


def _make_db_row(room_id: str = ROOM) -> MagicMock:
    row = MagicMock()
    row.room_id = room_id
    row.state = b""
    row.pending_updates = b""
    row.pending_update_count = 0
    row.last_compacted_at = datetime.now(UTC)
    row.document_size_bytes = 0
    return row


def _create_update(text: str = "hello") -> bytes:
    doc: pycrdt.Doc[Any] = pycrdt.Doc()
    t = doc.get("content", type=pycrdt.Text)
    t += text
    return doc.get_update()


@pytest.mark.collab
class TestSyncHandlerConvergence:
    """Convergence through the YjsSyncHandler layer."""

    @pytest.mark.anyio
    async def test_two_clients_through_sync_handler(self) -> None:
        """Two clients send updates via handler, doc contains both."""
        store = YjsDocumentStore(compaction_threshold=100)
        handler = YjsSyncHandler(store)

        row = _make_db_row()
        db = AsyncMock()
        result_new = MagicMock()
        result_new.scalar_one_or_none.return_value = None
        result_existing = MagicMock()
        result_existing.scalar_one.return_value = row
        db.execute.side_effect = [result_new] + [result_existing] * 4
        db.add = MagicMock()

        await handler.init_room(db, ROOM)

        # Client A sends update
        update_a = _create_update("alpha")
        msg_a = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update_a
        await handler.handle_sync_message(db, ROOM, "clientA", msg_a)

        # Client B sends update
        update_b = _create_update("beta")
        msg_b = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update_b
        await handler.handle_sync_message(db, ROOM, "clientB", msg_b)

        # Full state should contain both
        full_state = await store.get_full_state(ROOM)
        verify_doc: pycrdt.Doc[Any] = pycrdt.Doc()
        verify_doc.apply_update(full_state)
        content = str(verify_doc.get("content", type=pycrdt.Text))
        assert "alpha" in content
        assert "beta" in content

    @pytest.mark.anyio
    async def test_update_broadcasts_to_peers(self) -> None:
        """Updates produce broadcasts for other connected peers."""
        store = YjsDocumentStore(compaction_threshold=100)
        handler = YjsSyncHandler(store)

        row = _make_db_row()
        db = AsyncMock()
        result_new = MagicMock()
        result_new.scalar_one_or_none.return_value = None
        result_existing = MagicMock()
        result_existing.scalar_one.return_value = row
        db.execute.side_effect = [result_new] + [result_existing] * 2
        db.add = MagicMock()

        await handler.init_room(db, ROOM)

        update = _create_update("broadcast test")
        msg = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update
        _replies, broadcasts = await handler.handle_sync_message(db, ROOM, "sender", msg)

        assert len(broadcasts) >= 1
        # Broadcast contains the update data
        assert len(broadcasts[0]) > 2

    @pytest.mark.anyio
    async def test_new_peer_gets_full_state(self) -> None:
        """A new peer joining via SyncStep1 receives all prior content."""
        store = YjsDocumentStore(compaction_threshold=100)
        handler = YjsSyncHandler(store)

        row = _make_db_row()
        db = AsyncMock()
        result_new = MagicMock()
        result_new.scalar_one_or_none.return_value = None
        result_existing = MagicMock()
        result_existing.scalar_one.return_value = row
        db.execute.side_effect = [result_new] + [result_existing] * 3
        db.add = MagicMock()

        await handler.init_room(db, ROOM)

        # First client adds content
        update = _create_update("existing content")
        msg = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update
        await handler.handle_sync_message(db, ROOM, "c1", msg)

        # New peer syncs with empty state vector
        step1 = bytes([MessageType.SYNC, SyncMessageType.STEP1])
        replies, _ = await handler.handle_sync_message(db, ROOM, "c2", step1)

        # SyncStep2 reply should contain existing content
        assert len(replies) >= 1
        # Apply the SyncStep2 payload to a fresh doc and verify content
        peer_doc: pycrdt.Doc[Any] = pycrdt.Doc()
        # replies[0] is [msg_type, sync_type, ...update_bytes]
        peer_doc.apply_update(bytes(replies[0][2:]))
        peer_text = str(peer_doc.get("content", type=pycrdt.Text))
        assert "existing content" in peer_text
