"""Unit tests for RedisPubSubBridge."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest

from app.streaming.websocket.manager import CollabConnectionManager
from app.streaming.websocket.redis_bridge import RedisPubSubBridge


@pytest.fixture
def manager() -> CollabConnectionManager:
    return CollabConnectionManager()


@pytest.fixture
def bridge(manager: CollabConnectionManager) -> RedisPubSubBridge:
    return RedisPubSubBridge(manager)


ROOM = "project:1:template:10"


@pytest.mark.anyio
@patch("app.streaming.websocket.redis_bridge.get_redis", new_callable=AsyncMock)
@patch(
    "app.streaming.websocket.redis_bridge.redis_available",
    new_callable=AsyncMock,
    return_value=True,
)
async def test_publish_sends_to_redis(
    mock_available: AsyncMock, mock_get_redis: AsyncMock, bridge: RedisPubSubBridge
) -> None:
    mock_redis = AsyncMock()
    mock_get_redis.return_value = mock_redis

    await bridge.publish(ROOM, b"\x01\x02\x03", sender_user_id=42)

    mock_redis.publish.assert_called_once()
    call_args = mock_redis.publish.call_args
    assert call_args[0][0] == f"ws:collab:room:{ROOM}"
    envelope = json.loads(call_args[0][1])
    assert envelope["sender_user_id"] == 42
    assert envelope["data_hex"] == "010203"


@pytest.mark.anyio
@patch(
    "app.streaming.websocket.redis_bridge.redis_available",
    new_callable=AsyncMock,
    return_value=False,
)
async def test_publish_fallback_no_redis(
    mock_available: AsyncMock, bridge: RedisPubSubBridge
) -> None:
    # Should not raise when Redis unavailable
    await bridge.publish(ROOM, b"\x01", sender_user_id=1)


@pytest.mark.anyio
@patch("app.streaming.websocket.redis_bridge.get_redis", new_callable=AsyncMock)
@patch(
    "app.streaming.websocket.redis_bridge.redis_available",
    new_callable=AsyncMock,
    return_value=True,
)
async def test_publish_json(
    mock_available: AsyncMock, mock_get_redis: AsyncMock, bridge: RedisPubSubBridge
) -> None:
    mock_redis = AsyncMock()
    mock_get_redis.return_value = mock_redis

    data: dict[str, object] = {"type": "awareness", "user_id": 5}
    await bridge.publish_json(ROOM, data, sender_user_id=5)

    mock_redis.publish.assert_called_once()
    call_args = mock_redis.publish.call_args
    envelope = json.loads(call_args[0][1])
    assert envelope["sender_user_id"] == 5
    assert envelope["json_data"] == data


@pytest.mark.anyio
@patch(
    "app.streaming.websocket.redis_bridge.redis_available",
    new_callable=AsyncMock,
    return_value=True,
)
@patch("app.streaming.websocket.redis_bridge.get_redis", new_callable=AsyncMock)
async def test_start_stop_lifecycle(
    mock_get_redis: AsyncMock, mock_available: AsyncMock, bridge: RedisPubSubBridge
) -> None:
    # Mock the subscribe loop to exit cleanly
    mock_redis = AsyncMock()
    mock_get_redis.return_value = mock_redis
    mock_pubsub = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub

    async def _empty_aiter() -> AsyncIterator[dict[str, object]]:
        return
        yield  # makes it an async generator

    mock_pubsub.listen.return_value = _empty_aiter()

    await bridge.start()
    assert bridge._task is not None
    assert bridge._running is True

    await bridge.stop()
    assert bridge._task is None
    assert bridge._running is False
