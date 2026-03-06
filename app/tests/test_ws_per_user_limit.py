"""Tests for per-user WebSocket connection limits."""

from unittest.mock import MagicMock

import pytest

from app.streaming.manager import ConnectionManager


def _make_ws() -> MagicMock:
    """Create a mock WebSocket with a unique id."""
    return MagicMock()


@pytest.mark.asyncio
async def test_allows_connections_within_per_user_limit() -> None:
    manager = ConnectionManager(max_connections=100, max_per_user=3)
    for _ in range(3):
        ws = _make_ws()
        assert await manager.connect(ws, user_id="user1") is True
    assert manager.active_count == 3


@pytest.mark.asyncio
async def test_blocks_user_over_per_user_limit() -> None:
    manager = ConnectionManager(max_connections=100, max_per_user=2)
    ws1 = _make_ws()
    ws2 = _make_ws()
    ws3 = _make_ws()

    assert await manager.connect(ws1, user_id="user1") is True
    assert await manager.connect(ws2, user_id="user1") is True
    # Third connection for same user should be rejected
    assert await manager.connect(ws3, user_id="user1") is False
    assert manager.active_count == 2


@pytest.mark.asyncio
async def test_other_user_not_affected() -> None:
    manager = ConnectionManager(max_connections=100, max_per_user=1)
    ws1 = _make_ws()
    ws2 = _make_ws()
    ws3 = _make_ws()

    assert await manager.connect(ws1, user_id="user1") is True
    # user1 at limit
    assert await manager.connect(ws2, user_id="user1") is False
    # user2 can still connect
    assert await manager.connect(ws3, user_id="user2") is True
    assert manager.active_count == 2


@pytest.mark.asyncio
async def test_disconnect_frees_slot() -> None:
    manager = ConnectionManager(max_connections=100, max_per_user=1)
    ws1 = _make_ws()
    ws2 = _make_ws()

    assert await manager.connect(ws1, user_id="user1") is True
    assert await manager.connect(ws2, user_id="user1") is False

    # Disconnect frees the slot
    manager.disconnect(ws1, user_id="user1")
    assert await manager.connect(ws2, user_id="user1") is True


@pytest.mark.asyncio
async def test_global_limit_still_enforced() -> None:
    manager = ConnectionManager(max_connections=3, max_per_user=5)

    for i in range(3):
        ws = _make_ws()
        assert await manager.connect(ws, user_id=f"user{i}") is True

    # Global limit reached even though per-user has room
    ws_extra = _make_ws()
    assert await manager.connect(ws_extra, user_id="user_new") is False
    assert manager.active_count == 3


@pytest.mark.asyncio
async def test_connect_without_user_id() -> None:
    """Connections without user_id bypass per-user tracking."""
    manager = ConnectionManager(max_connections=100, max_per_user=1)
    ws1 = _make_ws()
    ws2 = _make_ws()

    # Both should succeed since no user_id means no per-user tracking
    assert await manager.connect(ws1) is True
    assert await manager.connect(ws2) is True
    assert manager.active_count == 2


@pytest.mark.asyncio
async def test_cleanup_user_tracking() -> None:
    """_cleanup_user_tracking removes ws_id from all user sets."""
    manager = ConnectionManager(max_connections=100, max_per_user=5)
    ws1 = _make_ws()

    await manager.connect(ws1, user_id="user1")
    ws_id = id(ws1)

    assert "user1" in manager._user_connections
    assert ws_id in manager._user_connections["user1"]

    manager._cleanup_user_tracking(ws_id)
    # user1 entry should be removed since it's now empty
    assert "user1" not in manager._user_connections
