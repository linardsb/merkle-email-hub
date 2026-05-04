"""WebSocket endpoint for real-time collaboration."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from fastapi import APIRouter, Query
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.logging import get_logger
from app.streaming.websocket.auth import authenticate_websocket, verify_room_access
from app.streaming.websocket.schemas import (
    CollabAck,
    CollabError,
    PresenceEvent,
)

if TYPE_CHECKING:
    from app.streaming.crdt.sync_handler import YjsSyncHandler
    from app.streaming.websocket.manager import CollabConnectionManager
    from app.streaming.websocket.redis_bridge import RedisPubSubBridge

logger = get_logger(__name__)

collab_router = APIRouter()

# Module-level singletons (set in lifespan)
_collab_manager: CollabConnectionManager | None = None
_redis_bridge: RedisPubSubBridge | None = None


def set_collab_manager(manager: CollabConnectionManager) -> None:
    """Set the global CollabConnectionManager instance."""
    global _collab_manager
    _collab_manager = manager


def get_collab_manager() -> CollabConnectionManager:
    """Get the global CollabConnectionManager instance."""
    if _collab_manager is None:
        msg = "CollabConnectionManager not initialized"
        raise RuntimeError(msg)
    return _collab_manager


def set_redis_bridge(bridge: RedisPubSubBridge) -> None:
    """Set the global RedisPubSubBridge instance."""
    global _redis_bridge
    _redis_bridge = bridge


def get_redis_bridge() -> RedisPubSubBridge | None:
    """Get the global RedisPubSubBridge instance."""
    return _redis_bridge


_sync_handler: YjsSyncHandler | None = None


def set_sync_handler(handler: YjsSyncHandler) -> None:
    """Set the global YjsSyncHandler instance."""
    global _sync_handler
    _sync_handler = handler


def get_sync_handler() -> YjsSyncHandler | None:
    """Get the global YjsSyncHandler instance."""
    return _sync_handler


def close_collab_manager() -> None:
    """Clear global collab singletons."""
    global _collab_manager, _redis_bridge, _sync_handler
    _collab_manager = None
    _redis_bridge = None
    _sync_handler = None


async def _send_heartbeats(websocket: WebSocket, interval: int) -> None:
    """Send periodic ping messages to keep the connection alive."""
    try:
        while True:
            await asyncio.sleep(interval)
            await websocket.send_json({"type": "ping"})
    except Exception:
        logger.debug("collab.ws.heartbeat_stopped")


@collab_router.websocket("/ws/collab/{room_id}")
async def ws_collab(
    websocket: WebSocket,
    room_id: str,
    token: str | None = Query(None),
) -> None:
    """WebSocket endpoint for real-time collaboration.

    Protocol:
    - Binary messages: Yjs CRDT document updates (relayed to all peers)
    - JSON messages: awareness updates (cursors, selections, presence)
    - Server sends: ping (heartbeat), presence events, ack, errors

    Authentication: JWT token via ?token= query parameter.
    Room ID format: project:{project_id}:template:{template_id}
    """
    settings = get_settings()

    if not settings.collab_ws.enabled:
        await websocket.close(code=1013, reason="Collaboration disabled")
        return

    manager = get_collab_manager()

    # --- Authentication ---
    auth_result = await authenticate_websocket(token)
    if auth_result is None:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user = auth_result.user
    can_edit = auth_result.can_edit

    # --- Room access (BOLA) ---
    if not await verify_room_access(user, room_id):
        await websocket.close(code=4003, reason="Access denied")
        return

    # --- Accept & join room ---
    await websocket.accept()

    peer_info = await manager.connect(websocket, room_id, user, can_edit)
    if peer_info is None:
        error = CollabError(code="room_full", message="Room connection limit reached")
        await websocket.send_json(error.model_dump())
        await websocket.close(code=1013, reason="Room full")
        return

    # Send connection ack with peer list
    peers = manager.get_peers(room_id)
    ack = CollabAck(
        action="connected",
        room_id=room_id,
        user=peer_info,
        peers=[p for p in peers if p.user_id != user.id],
    )
    await websocket.send_json(ack.model_dump())

    # Notify existing peers of new join
    join_event = PresenceEvent(type="presence_join", users=[peer_info])
    await manager.broadcast_json(room_id, join_event.model_dump(), exclude=websocket)

    # Publish join to Redis for cross-instance awareness
    bridge = get_redis_bridge()
    if bridge:
        await bridge.publish_json(room_id, join_event.model_dump(), user.id)

    # Initialize CRDT document for this room (Phase 24.2)
    sync = get_sync_handler()
    if sync is not None and settings.collab_ws.crdt_enabled:
        from app.core.scoped_db import get_scoped_db_context

        async with get_scoped_db_context(user) as db:
            await sync.init_room(db, room_id)
            await db.commit()

    # Start heartbeat
    heartbeat_task = asyncio.create_task(
        _send_heartbeats(websocket, settings.collab_ws.heartbeat_interval_seconds)
    )

    # --- Message loop ---
    max_msg_bytes = settings.collab_ws.max_message_bytes
    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"] is not None:
                # Binary: Yjs CRDT update
                data: bytes = message["bytes"]

                # Size guard
                if len(data) > max_msg_bytes:
                    err = CollabError(
                        code="message_too_large", message="Message exceeds size limit"
                    )
                    await websocket.send_json(err.model_dump())
                    continue

                # Viewers cannot send document updates
                if not can_edit:
                    # Viewers can receive sync but not send updates
                    sync = get_sync_handler()
                    if (
                        sync is not None
                        and settings.collab_ws.crdt_enabled
                        and len(data) >= 2
                        and data[0] == 0
                        and data[1] == 0
                    ):
                        from app.core.scoped_db import get_scoped_db_context

                        async with get_scoped_db_context(user) as db:
                            replies, _ = await sync.handle_sync_message(
                                db,
                                room_id,
                                str(user.id),
                                data,
                            )
                            # Don't commit -- viewer sync is read-only
                        for reply in replies:
                            await websocket.send_bytes(reply)
                        continue
                    err = CollabError(code="read_only", message="Viewer role cannot edit")
                    await websocket.send_json(err.model_dump())
                    continue

                # CRDT sync protocol (Phase 24.2)
                sync = get_sync_handler()
                if sync is not None and settings.collab_ws.crdt_enabled:
                    from app.core.scoped_db import get_scoped_db_context

                    try:
                        async with get_scoped_db_context(user) as db:
                            replies, broadcasts = await sync.handle_sync_message(
                                db,
                                room_id,
                                str(user.id),
                                data,
                            )
                            await db.commit()

                        # Send replies to this client only
                        for reply in replies:
                            await websocket.send_bytes(reply)

                        # Broadcast to local peers
                        for bcast in broadcasts:
                            await manager.broadcast_bytes(room_id, bcast, exclude=websocket)
                            if bridge:
                                await bridge.publish(room_id, bcast, user.id)
                    except Exception as exc:
                        logger.warning(
                            "crdt.sync.handler_error",
                            room_id=room_id,
                            error=str(exc),
                            error_type=type(exc).__name__,
                        )
                else:
                    # Passthrough mode (no CRDT -- raw relay as in 24.1)
                    await manager.broadcast_bytes(room_id, data, exclude=websocket)
                    if bridge:
                        await bridge.publish(room_id, data, user.id)

            elif message.get("text"):
                # JSON: awareness/presence updates
                raw = message["text"]
                if len(raw) > max_msg_bytes:
                    continue

                try:
                    data_json = json.loads(raw)
                except json.JSONDecodeError:
                    err = CollabError(code="parse_error", message="Invalid JSON")
                    await websocket.send_json(err.model_dump())
                    continue

                msg_type = data_json.get("type")

                if msg_type == "awareness":
                    # Relay cursor/selection state
                    data_json["user_id"] = user.id  # Enforce server-side user_id
                    await manager.broadcast_json(room_id, data_json, exclude=websocket)
                    if bridge:
                        await bridge.publish_json(room_id, data_json, user.id)

                elif msg_type == "pong":
                    pass  # Heartbeat response

                else:
                    err = CollabError(
                        code="unknown_type",
                        message=f"Unknown message type: {str(msg_type)[:50]}",
                    )
                    await websocket.send_json(err.model_dump())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(
            "collab.ws.unexpected_error",
            user_id=user.id,
            room_id=room_id,
            error=str(e),
            error_type=type(e).__name__,
        )
    finally:
        heartbeat_task.cancel()
        left_info = await manager.disconnect(websocket, room_id)

        # Evict CRDT doc from memory when room empties (Phase 24.2)
        if not manager.get_peers(room_id):
            sync = get_sync_handler()
            if sync is not None:
                sync.cleanup_room(room_id)

        # Notify peers of departure
        if left_info:
            leave_event = PresenceEvent(type="presence_leave", users=[left_info])
            await manager.broadcast_json(room_id, leave_event.model_dump())
            if bridge:
                await bridge.publish_json(room_id, leave_event.model_dump(), user.id)

        logger.info(
            "collab.ws.disconnected",
            user_id=user.id,
            room_id=room_id,
            active_rooms=manager.active_rooms,
            total_connections=manager.total_connections,
        )
