"""Room-based WebSocket connection manager for real-time collaboration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from starlette.websockets import WebSocket

from app.core.logging import get_logger
from app.streaming.websocket.schemas import ConnectionInfo

if TYPE_CHECKING:
    from app.auth.models import User

logger = get_logger(__name__)

# 12 distinct cursor colors for peer differentiation
_CURSOR_COLORS = [
    "#E06C75",
    "#61AFEF",
    "#98C379",
    "#E5C07B",
    "#C678DD",
    "#56B6C2",
    "#BE5046",
    "#D19A66",
    "#7EC8E3",
    "#F4A261",
    "#A78BFA",
    "#34D399",
]


@dataclass
class Peer:
    """A single peer in a collaboration room."""

    websocket: WebSocket
    info: ConnectionInfo
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))


class CollabConnectionManager:
    """Room-based WebSocket connection manager for real-time collaboration.

    Each room tracks its own set of peers. Broadcast sends to all peers
    in a room except the sender. Supports both binary (Yjs CRDT) and
    JSON (awareness/presence) messages.
    """

    def __init__(
        self,
        max_per_room: int = 20,
        max_rooms_per_user: int = 10,
    ) -> None:
        self._max_per_room = max_per_room
        self._max_rooms_per_user = max_rooms_per_user
        # room_id -> {ws_id -> Peer}
        self._rooms: dict[str, dict[int, Peer]] = {}
        # user_id -> set of room_ids they're in
        self._user_rooms: dict[int, set[str]] = {}
        self._color_index: int = 0

    def _next_color(self) -> str:
        color = _CURSOR_COLORS[self._color_index % len(_CURSOR_COLORS)]
        self._color_index += 1
        return color

    async def connect(
        self,
        websocket: WebSocket,
        room_id: str,
        user: User,
        can_edit: bool,
    ) -> ConnectionInfo | None:
        """Add a peer to a room. Returns ConnectionInfo on success, None if limit reached."""
        user_id = user.id
        room = self._rooms.get(room_id, {})

        # Check room capacity
        if len(room) >= self._max_per_room:
            logger.warning(
                "collab.ws.room_full",
                room_id=room_id,
                max_per_room=self._max_per_room,
            )
            return None

        # Check per-user room limit
        user_rooms = self._user_rooms.get(user_id, set())
        if room_id not in user_rooms and len(user_rooms) >= self._max_rooms_per_user:
            logger.warning(
                "collab.ws.user_room_limit",
                user_id=user_id,
                max_rooms=self._max_rooms_per_user,
            )
            return None

        info = ConnectionInfo(
            user_id=user_id,
            room_id=room_id,
            display_name=user.name,
            role="viewer" if not can_edit else user.role,
            color=self._next_color(),
        )
        peer = Peer(websocket=websocket, info=info)
        ws_id = id(websocket)

        if room_id not in self._rooms:
            self._rooms[room_id] = {}
        self._rooms[room_id][ws_id] = peer
        self._user_rooms.setdefault(user_id, set()).add(room_id)

        logger.info(
            "collab.ws.peer_joined",
            user_id=user_id,
            room_id=room_id,
            room_size=len(self._rooms[room_id]),
        )
        return info

    async def disconnect(self, websocket: WebSocket, room_id: str) -> ConnectionInfo | None:
        """Remove a peer from a room. Returns the peer's info or None."""
        ws_id = id(websocket)
        room = self._rooms.get(room_id)
        if room is None or ws_id not in room:
            return None

        peer = room.pop(ws_id)
        user_id = peer.info.user_id

        # Clean up empty room
        if not room:
            del self._rooms[room_id]

        # Clean up user room tracking
        if user_id in self._user_rooms:
            self._user_rooms[user_id].discard(room_id)
            if not self._user_rooms[user_id]:
                del self._user_rooms[user_id]

        logger.info(
            "collab.ws.peer_left",
            user_id=user_id,
            room_id=room_id,
            room_size=len(self._rooms.get(room_id, {})),
        )
        return peer.info

    def get_peers(self, room_id: str) -> list[ConnectionInfo]:
        """Get info for all peers in a room."""
        room = self._rooms.get(room_id, {})
        return [p.info for p in room.values()]

    async def broadcast_bytes(
        self,
        room_id: str,
        data: bytes,
        exclude: WebSocket | None = None,
    ) -> None:
        """Send binary data (Yjs update) to all peers in a room except sender."""
        room = self._rooms.get(room_id)
        if not room:
            return

        exclude_id = id(exclude) if exclude else None
        disconnected: list[int] = []

        for ws_id, peer in room.items():
            if ws_id == exclude_id:
                continue
            try:
                await peer.websocket.send_bytes(data)
                peer.last_activity = datetime.now(UTC)
            except Exception:
                disconnected.append(ws_id)

        self._cleanup_disconnected(room_id, disconnected)

    async def broadcast_json(
        self,
        room_id: str,
        data: dict[str, object],
        exclude: WebSocket | None = None,
    ) -> None:
        """Send JSON data (awareness/presence) to all peers in a room except sender."""
        room = self._rooms.get(room_id)
        if not room:
            return

        exclude_id = id(exclude) if exclude else None
        disconnected: list[int] = []

        for ws_id, peer in room.items():
            if ws_id == exclude_id:
                continue
            try:
                await peer.websocket.send_json(data)
                peer.last_activity = datetime.now(UTC)
            except Exception:
                disconnected.append(ws_id)

        self._cleanup_disconnected(room_id, disconnected)

    async def send_to_user(
        self,
        room_id: str,
        user_id: int,
        data: bytes | dict[str, object],
    ) -> bool:
        """Send a message to a specific user in a room. Returns True if sent."""
        room = self._rooms.get(room_id)
        if not room:
            return False

        for peer in room.values():
            if peer.info.user_id == user_id:
                try:
                    if isinstance(data, bytes):
                        await peer.websocket.send_bytes(data)
                    else:
                        await peer.websocket.send_json(data)
                    return True
                except Exception:
                    return False
        return False

    def _cleanup_disconnected(self, room_id: str, ws_ids: list[int]) -> None:
        """Remove disconnected peers from room tracking."""
        room = self._rooms.get(room_id)
        if not room:
            return
        for ws_id in ws_ids:
            peer = room.pop(ws_id, None)
            if peer:
                uid = peer.info.user_id
                if uid in self._user_rooms:
                    self._user_rooms[uid].discard(room_id)
                    if not self._user_rooms[uid]:
                        del self._user_rooms[uid]
        if not room:
            del self._rooms[room_id]

    @property
    def active_rooms(self) -> int:
        """Number of active rooms."""
        return len(self._rooms)

    @property
    def total_connections(self) -> int:
        """Total peer connections across all rooms."""
        return sum(len(r) for r in self._rooms.values())
