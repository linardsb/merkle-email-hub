# pyright: reportUnknownMemberType=false, reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Background task that subscribes to Redis Pub/Sub and dispatches to WebSocket clients.

Subscribes to a configurable channel pattern and fans out data updates
to all connected WebSocket clients via the ConnectionManager.
"""

import asyncio
import json

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.streaming.manager import ConnectionManager

logger = get_logger(__name__)

_subscriber_task: asyncio.Task[None] | None = None

MAX_BACKOFF_SECONDS = 30


async def _subscribe_loop(
    manager: ConnectionManager,
    channel_pattern: str,
) -> None:
    """Subscribe to Redis Pub/Sub channels and dispatch updates.

    Expected message format on each channel::

        {
            "topic": "vehicles",
            "items": [...],
            "timestamp": "2025-01-01T00:00:00Z",
            "attributes": {"feed_id": "riga"}  // optional, used for filter matching
        }

    Args:
        manager: The ConnectionManager to broadcast updates through.
        channel_pattern: Redis Pub/Sub pattern to subscribe to (e.g., "stream:data:*").
    """
    backoff = 1.0

    pubsub = None
    while True:
        try:
            redis_client = await get_redis()
            pubsub = redis_client.pubsub()
            await pubsub.psubscribe(channel_pattern)
            logger.info(
                "streaming.ws.subscriber_started",
                channel_pattern=channel_pattern,
            )
            backoff = 1.0  # Reset backoff on successful connection

            async for message in pubsub.listen():
                if message["type"] != "pmessage":
                    continue

                try:
                    data = json.loads(message["data"])
                    topic: str = data["topic"]
                    items: list[dict[str, object]] = data["items"]
                    timestamp: str = data["timestamp"]
                    attributes: dict[str, str] | None = data.get("attributes")
                    await manager.broadcast(topic, items, timestamp, attributes)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(
                        "streaming.ws.subscriber_message_parse_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                    )

        except asyncio.CancelledError:
            # Graceful shutdown
            if pubsub is not None:
                try:
                    await pubsub.punsubscribe(channel_pattern)
                    await pubsub.aclose()  # type: ignore[no-untyped-call]
                except Exception:
                    logger.warning("streaming.ws.subscriber_cleanup_error", exc_info=True)
            logger.info(
                "streaming.ws.subscriber_stopped",
                channel_pattern=channel_pattern,
            )
            return

        except Exception as e:
            logger.warning(
                "streaming.ws.subscriber_reconnecting",
                error=str(e),
                error_type=type(e).__name__,
                backoff_seconds=backoff,
                channel_pattern=channel_pattern,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)


async def start_ws_subscriber(
    manager: ConnectionManager,
    channel_pattern: str = "stream:data:*",
) -> asyncio.Task[None]:
    """Create and return the subscriber background task.

    Args:
        manager: The ConnectionManager to broadcast updates through.
        channel_pattern: Redis Pub/Sub pattern to subscribe to.
            Defaults to "stream:data:*".

    Returns:
        The created asyncio Task.
    """
    global _subscriber_task  # noqa: PLW0603
    _subscriber_task = asyncio.create_task(_subscribe_loop(manager, channel_pattern))
    return _subscriber_task


async def stop_ws_subscriber() -> None:
    """Cancel the subscriber task and wait for cleanup."""
    global _subscriber_task  # noqa: PLW0603
    if _subscriber_task is not None:
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.warning("streaming.ws.subscriber_stop_error", exc_info=True)
        _subscriber_task = None
