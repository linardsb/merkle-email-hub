"""WebSocket connection manager for real-time data streaming.

Tracks active WebSocket connections with per-client subscription filters
and handles fan-out broadcasting of data updates to matching clients.
"""

from dataclasses import dataclass, field

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.core.logging import get_logger
from app.streaming.schemas import WsDataUpdate

logger = get_logger(__name__)


@dataclass
class _ClientSubscription:
    """Internal tracking of a WebSocket client and its filters.

    Attributes:
        websocket: The active WebSocket connection.
        filters: Key-value subscription filters. A None value means "all"
            for that filter dimension. An empty dict means no filters (receive everything).
    """

    websocket: WebSocket
    filters: dict[str, str | None] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]


class ConnectionManager:
    """Manages WebSocket connections and broadcasts data updates.

    Each connection has optional key-value filters. Broadcast checks
    filters before sending to each client. Filter matching logic:

    - If client has no filter for a given key, the client receives all values.
    - If client has a filter value for a key, only items matching that value are sent.

    Thread-safe via asyncio single event loop (no locks needed).

    Args:
        max_connections: Hard cap on concurrent WebSocket connections.
        max_per_user: Max concurrent connections per authenticated user.
    """

    def __init__(self, max_connections: int, max_per_user: int = 5) -> None:
        self._max_connections = max_connections
        self._max_per_user = max_per_user
        self._clients: dict[int, _ClientSubscription] = {}
        self._user_connections: dict[str, set[int]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        filters: dict[str, str | None] | None = None,
        user_id: str | None = None,
    ) -> bool:
        """Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to register.
            filters: Optional initial subscription filters.
            user_id: Authenticated user ID for per-user limit enforcement.

        Returns:
            True if the connection was registered, False if a limit was reached.
        """
        if len(self._clients) >= self._max_connections:
            logger.warning(
                "streaming.ws.connection_limit_reached",
                max_connections=self._max_connections,
                active_count=len(self._clients),
            )
            return False

        if user_id is not None:
            user_conns = self._user_connections.get(user_id, set())
            if len(user_conns) >= self._max_per_user:
                logger.warning(
                    "streaming.ws.per_user_limit_reached",
                    user_id=user_id,
                    max_per_user=self._max_per_user,
                    active_count=len(user_conns),
                )
                return False

        ws_id = id(websocket)
        self._clients[ws_id] = _ClientSubscription(
            websocket=websocket,
            filters=filters or {},
        )
        if user_id is not None:
            self._user_connections.setdefault(user_id, set()).add(ws_id)
        return True

    def disconnect(self, websocket: WebSocket, user_id: str | None = None) -> None:
        """Remove a WebSocket connection from tracking."""
        ws_id = id(websocket)
        if ws_id in self._clients:
            del self._clients[ws_id]
        if user_id is not None and user_id in self._user_connections:
            self._user_connections[user_id].discard(ws_id)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]

    def update_filters(
        self,
        websocket: WebSocket,
        filters: dict[str, str | None],
    ) -> None:
        """Update subscription filters for an existing connection.

        Args:
            websocket: The WebSocket connection to update.
            filters: New filters to apply. A None value for any key means "all".
        """
        ws_id = id(websocket)
        if ws_id in self._clients:
            self._clients[ws_id].filters = filters

    async def broadcast(
        self,
        topic: str,
        items: list[dict[str, object]],
        timestamp: str,
        attributes: dict[str, str] | None = None,
    ) -> None:
        """Send data update to all matching clients.

        Match logic for each client:
        - For each filter key the client has set (with a non-None value),
          the broadcast ``attributes`` dict must contain a matching value.
        - If attributes is None, only clients with no active filters receive the message.
        - Items are sent as-is (no per-item filtering).

        Args:
            topic: The data topic/channel name.
            items: List of data item dicts to broadcast.
            timestamp: ISO 8601 timestamp for the update.
            attributes: Key-value attributes of this broadcast batch used for
                filter matching (e.g., {"feed_id": "riga", "route_id": "22"}).
        """
        if not items:
            return

        attrs = attributes or {}
        disconnected: list[int] = []

        for ws_id, sub in self._clients.items():
            # Check if this client's filters match the broadcast attributes
            if not self._filters_match(sub.filters, attrs):
                continue

            update = WsDataUpdate(
                topic=topic,
                count=len(items),
                items=items,
                timestamp=timestamp,
            )

            try:
                await sub.websocket.send_json(update.model_dump())
            except WebSocketDisconnect:
                disconnected.append(ws_id)
                logger.info(
                    "streaming.ws.broadcast_client_disconnected",
                    ws_id=ws_id,
                )
            except Exception as e:
                disconnected.append(ws_id)
                logger.warning(
                    "streaming.ws.broadcast_client_error",
                    ws_id=ws_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Clean up disconnected clients
        for ws_id in disconnected:
            if ws_id in self._clients:
                del self._clients[ws_id]
            self._cleanup_user_tracking(ws_id)

        if self._clients:
            logger.debug(
                "streaming.ws.broadcast_completed",
                topic=topic,
                client_count=len(self._clients),
                item_count=len(items),
            )

    def _cleanup_user_tracking(self, ws_id: int) -> None:
        """Remove a ws_id from user connection tracking after broadcast disconnect."""
        for uid, conns in list(self._user_connections.items()):
            conns.discard(ws_id)
            if not conns:
                del self._user_connections[uid]

    @staticmethod
    def _filters_match(
        client_filters: dict[str, str | None],
        broadcast_attrs: dict[str, str],
    ) -> bool:
        """Check if a client's filters match a broadcast's attributes.

        A client matches if for every filter key with a non-None value,
        the broadcast attributes contain the same key with the same value.
        Filter keys with None values are wildcards (match anything).
        """
        for key, value in client_filters.items():
            if value is None:
                # Wildcard — matches any value for this key
                continue
            if broadcast_attrs.get(key) != value:
                return False
        return True

    @property
    def active_count(self) -> int:
        """Number of active connections."""
        return len(self._clients)
