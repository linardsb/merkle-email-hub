"""Redis Pub/Sub publisher for broadcasting updates.

Provides a simple interface for publishing messages to Redis channels.
Subscribers (e.g., WebSocket manager) receive these messages and fan out
to connected clients.

Usage:
    publisher = Publisher(channel_prefix="myapp")
    await publisher.publish("orders", {"order_id": 123, "status": "shipped"})
    # Publishes to channel: myapp:orders
"""

import json
from typing import Any

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)


class Publisher:
    """Redis Pub/Sub publisher with channel prefix support."""

    def __init__(self, channel_prefix: str = "app") -> None:
        self.channel_prefix = channel_prefix

    def _channel(self, topic: str) -> str:
        """Build the full channel name."""
        return f"{self.channel_prefix}:{topic}"

    async def publish(self, topic: str, data: dict[str, Any]) -> int:
        """Publish a message to a Redis Pub/Sub channel.

        Args:
            topic: The topic/channel suffix (e.g., "updates", "notifications").
            data: The message payload (will be JSON-serialized).

        Returns:
            Number of subscribers that received the message.
        """
        channel = self._channel(topic)
        try:
            redis = await get_redis()
            message = json.dumps(data)
            count: int = await redis.publish(channel, message)  # type: ignore[misc]
            return count
        except Exception as e:
            logger.error(
                "publisher.publish_failed",
                channel=channel,
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    async def publish_batch(self, topic: str, items: list[dict[str, Any]]) -> int:
        """Publish multiple messages as a single batch payload.

        Args:
            topic: The topic/channel suffix.
            items: List of message payloads.

        Returns:
            Number of subscribers that received the batch.
        """
        if not items:
            return 0
        return await self.publish(topic, {"type": "batch", "items": items})
