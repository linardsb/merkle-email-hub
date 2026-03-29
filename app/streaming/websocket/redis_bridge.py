# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Redis pub/sub bridge for multi-instance WebSocket collaboration."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.core.redis import get_redis, redis_available

if TYPE_CHECKING:
    from app.streaming.websocket.manager import CollabConnectionManager

logger = get_logger(__name__)

_CHANNEL_PREFIX = "ws:collab:room:"
_MAX_BACKOFF = 30.0


class RedisPubSubBridge:
    """Bridges collaboration WebSocket messages across app instances via Redis pub/sub.

    Publishing: when a local peer sends a message, publish to Redis so other instances relay it.
    Subscribing: listen to Redis channels and deliver to local peers via CollabConnectionManager.
    """

    def __init__(self, manager: CollabConnectionManager) -> None:
        self._manager = manager
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def publish(self, room_id: str, data: bytes, sender_user_id: int) -> None:
        """Publish a binary message to a room channel on Redis."""
        if not await redis_available():
            return
        try:
            redis = await get_redis()
            channel = f"{_CHANNEL_PREFIX}{room_id}"
            envelope = json.dumps(
                {
                    "sender_user_id": sender_user_id,
                    "data_hex": data.hex(),
                }
            )
            await redis.publish(channel, envelope)
        except Exception as e:
            logger.warning(
                "collab.redis.publish_failed",
                room_id=room_id,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def publish_json(
        self, room_id: str, data: dict[str, object], sender_user_id: int
    ) -> None:
        """Publish a JSON awareness/presence message to a room channel on Redis."""
        if not await redis_available():
            return
        try:
            redis = await get_redis()
            channel = f"{_CHANNEL_PREFIX}{room_id}"
            envelope = json.dumps(
                {
                    "sender_user_id": sender_user_id,
                    "json_data": data,
                }
            )
            await redis.publish(channel, envelope)
        except Exception as e:
            logger.warning(
                "collab.redis.publish_json_failed",
                room_id=room_id,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def start(self) -> None:
        """Start the Redis subscriber loop."""
        if not await redis_available():
            logger.warning("collab.redis.bridge_disabled", detail="Redis unavailable")
            return
        self._running = True
        self._task = asyncio.create_task(self._subscribe_loop())
        logger.info("collab.redis.bridge_started")

    async def stop(self) -> None:
        """Stop the Redis subscriber loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("collab.redis.bridge_stopped")

    async def _subscribe_loop(self) -> None:
        """Subscribe to all collab room channels and relay messages to local peers."""
        backoff = 1.0
        pattern = f"{_CHANNEL_PREFIX}*"

        while self._running:
            pubsub = None
            try:
                redis = await get_redis()
                pubsub = redis.pubsub()
                await pubsub.psubscribe(pattern)
                logger.info("collab.redis.subscribed", pattern=pattern)
                backoff = 1.0

                async for message in pubsub.listen():
                    if not self._running:
                        break
                    if message["type"] != "pmessage":
                        continue

                    channel: str = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode()

                    room_id = channel.removeprefix(_CHANNEL_PREFIX)

                    try:
                        envelope = json.loads(message["data"])
                        sender_user_id = envelope["sender_user_id"]

                        if "data_hex" in envelope:
                            data = bytes.fromhex(envelope["data_hex"])
                            await self._relay_bytes(room_id, data, sender_user_id)
                        elif "json_data" in envelope:
                            await self._relay_json(room_id, envelope["json_data"], sender_user_id)

                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(
                            "collab.redis.message_parse_failed",
                            error=str(e),
                            channel=channel,
                        )

            except asyncio.CancelledError:
                if pubsub is not None:
                    try:
                        await pubsub.punsubscribe(pattern)
                        await pubsub.aclose()  # type: ignore[no-untyped-call]
                    except Exception:
                        logger.debug("collab.redis.cleanup_error_on_cancel")
                return
            except Exception as e:
                logger.warning(
                    "collab.redis.subscriber_reconnecting",
                    error=str(e),
                    backoff_seconds=backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)

    async def _relay_bytes(self, room_id: str, data: bytes, sender_user_id: int) -> None:
        """Relay binary message to local peers, skipping the sender."""
        room = self._manager._rooms.get(room_id)
        if not room:
            return
        for peer in room.values():
            if peer.info.user_id == sender_user_id:
                continue
            try:
                await peer.websocket.send_bytes(data)
            except Exception:
                logger.debug("collab.redis.relay_bytes_peer_error", user_id=peer.info.user_id)

    async def _relay_json(self, room_id: str, data: dict[str, object], sender_user_id: int) -> None:
        """Relay JSON message to local peers, skipping the sender."""
        room = self._manager._rooms.get(room_id)
        if not room:
            return
        for peer in room.values():
            if peer.info.user_id == sender_user_id:
                continue
            try:
                await peer.websocket.send_json(data)
            except Exception:
                logger.debug("collab.redis.relay_json_peer_error", user_id=peer.info.user_id)
