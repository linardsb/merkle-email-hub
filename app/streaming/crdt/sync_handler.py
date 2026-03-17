"""Server-side Yjs sync protocol handler.

Implements the y-protocols/sync protocol:
- SyncStep1: client sends state vector -> server responds with missing updates
- SyncStep2: client sends its updates -> server applies them
- Update: ongoing edits -> apply + broadcast
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.streaming.crdt.document_store import YjsDocumentStore

logger = get_logger(__name__)


class MessageType(IntEnum):
    """Yjs sync protocol message types (first byte)."""

    SYNC = 0
    AWARENESS = 1


class SyncMessageType(IntEnum):
    """Yjs sync sub-message types (second byte for SYNC messages)."""

    STEP1 = 0  # Client sends state vector
    STEP2 = 1  # Response with missing updates / client sends its updates
    UPDATE = 2  # Incremental update


class YjsSyncHandler:
    """Handles the Yjs sync protocol server-side.

    Processes incoming binary WebSocket messages and returns
    response messages to send back to the client and/or broadcast.
    """

    def __init__(self, store: YjsDocumentStore) -> None:
        self._store = store

    async def handle_sync_message(
        self,
        db: AsyncSession,
        room_id: str,
        client_id: str,
        message: bytes,
    ) -> tuple[list[bytes], list[bytes]]:
        """Process a binary sync message.

        Returns:
            (replies, broadcasts) -- replies go to sender only,
            broadcasts go to all other peers in the room.
        """
        if len(message) < 2:
            return [], []

        msg_type = message[0]
        if msg_type != MessageType.SYNC:
            # Non-sync message (awareness etc.) -- pass through
            return [], [message]

        sync_type = message[1]
        payload = message[2:]

        if sync_type == SyncMessageType.STEP1:
            return await self._handle_step1(room_id, payload)
        elif sync_type == SyncMessageType.STEP2:
            return await self._handle_step2(db, room_id, client_id, payload)
        elif sync_type == SyncMessageType.UPDATE:
            return await self._handle_update(db, room_id, client_id, payload)
        else:
            logger.warning("crdt.sync.unknown_type", sync_type=sync_type, room_id=room_id)
            return [], []

    async def _handle_step1(
        self,
        room_id: str,
        state_vector: bytes,
    ) -> tuple[list[bytes], list[bytes]]:
        """Client sends state vector -> respond with missing updates."""
        update = await self._store.get_update_for_peer(room_id, state_vector)

        # Build SyncStep2 response: [SYNC, STEP2, ...update]
        reply = bytes([MessageType.SYNC, SyncMessageType.STEP2]) + update

        # Also send our state vector so client can send us what we're missing
        sv = await self._store.get_state_vector(room_id)
        sv_msg = bytes([MessageType.SYNC, SyncMessageType.STEP1]) + sv

        return [reply, sv_msg], []

    async def _handle_step2(
        self,
        db: AsyncSession,
        room_id: str,
        client_id: str,
        update: bytes,
    ) -> tuple[list[bytes], list[bytes]]:
        """Client sends its updates (response to our SyncStep1)."""
        if not update:
            return [], []

        applied = await self._store.apply_update(db, room_id, update)
        if not applied:
            logger.warning("crdt.sync.step2_rejected", room_id=room_id, client_id=client_id)
            return [], []

        # Broadcast the update to other peers
        broadcast = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update
        return [], [broadcast]

    async def _handle_update(
        self,
        db: AsyncSession,
        room_id: str,
        client_id: str,
        update: bytes,
    ) -> tuple[list[bytes], list[bytes]]:
        """Ongoing incremental update from a client."""
        if not update:
            return [], []

        applied = await self._store.apply_update(db, room_id, update)
        if not applied:
            logger.warning("crdt.sync.update_rejected", room_id=room_id, client_id=client_id)
            return [], []

        # Broadcast the update to other peers
        broadcast = bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + update
        return [], [broadcast]

    async def init_room(self, db: AsyncSession, room_id: str) -> None:
        """Ensure a room's document is loaded into memory."""
        await self._store.get_or_create(db, room_id)

    def cleanup_room(self, room_id: str) -> None:
        """Evict room document from memory when room empties."""
        self._store.evict(room_id)
