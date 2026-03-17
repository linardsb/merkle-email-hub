"""Collaboration WebSocket message schemas.

Binary messages (Yjs updates) are handled as raw bytes — these schemas
are for JSON control/awareness messages only.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class CollabMessageType(StrEnum):
    """Types of JSON control messages in the collab protocol."""

    AWARENESS = "awareness"
    PRESENCE_JOIN = "presence_join"
    PRESENCE_LEAVE = "presence_leave"
    PRESENCE_SYNC = "presence_sync"
    ERROR = "error"
    ACK = "ack"


class ConnectionInfo(BaseModel):
    """Metadata about a single WebSocket connection."""

    user_id: int
    room_id: str
    display_name: str
    role: str  # "admin", "developer", "viewer"
    color: str = ""


class AwarenessUpdate(BaseModel):
    """Client awareness state (cursor, selection, scroll position)."""

    type: str = Field(default="awareness", frozen=True)
    user_id: int
    cursor_line: int | None = None
    cursor_column: int | None = None
    selection_start: dict[str, int] | None = None
    selection_end: dict[str, int] | None = None
    scroll_top: int | None = None


class PresenceEvent(BaseModel):
    """Presence join/leave/sync event."""

    type: str  # presence_join, presence_leave, presence_sync
    users: list[ConnectionInfo]


class CollabError(BaseModel):
    """Error message sent to client."""

    type: str = Field(default="error", frozen=True)
    code: str
    message: str


class CollabAck(BaseModel):
    """Acknowledgement sent after successful connection."""

    type: str = Field(default="ack", frozen=True)
    action: str  # "connected"
    room_id: str
    user: ConnectionInfo
    peers: list[ConnectionInfo]
