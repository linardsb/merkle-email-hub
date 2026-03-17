"""Unit tests for CollabConnectionManager."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.streaming.websocket.manager import CollabConnectionManager


def _make_user(user_id: int = 1, name: str = "Alice", role: str = "admin") -> Any:
    """Create a minimal User-like object for testing."""
    return SimpleNamespace(id=user_id, name=name, role=role, email=f"user{user_id}@test.com")


def _make_ws() -> AsyncMock:
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.send_bytes = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def manager() -> CollabConnectionManager:
    return CollabConnectionManager(max_per_room=3, max_rooms_per_user=2)


ROOM = "project:1:template:10"


@pytest.mark.anyio
async def test_connect_and_disconnect(manager: CollabConnectionManager) -> None:
    ws = _make_ws()
    user = _make_user()

    info = await manager.connect(ws, ROOM, user, can_edit=True)
    assert info is not None
    assert info.user_id == 1
    assert info.display_name == "Alice"
    assert manager.get_peers(ROOM) == [info]

    left = await manager.disconnect(ws, ROOM)
    assert left is not None
    assert left.user_id == 1
    assert manager.get_peers(ROOM) == []


@pytest.mark.anyio
async def test_room_capacity_limit(manager: CollabConnectionManager) -> None:
    # Fill room to max (3)
    for i in range(3):
        ws = _make_ws()
        user = _make_user(user_id=i + 1, name=f"User{i}")
        info = await manager.connect(ws, ROOM, user, can_edit=True)
        assert info is not None

    # 4th should fail
    ws = _make_ws()
    user = _make_user(user_id=99, name="Overflow")
    info = await manager.connect(ws, ROOM, user, can_edit=True)
    assert info is None


@pytest.mark.anyio
async def test_user_room_limit(manager: CollabConnectionManager) -> None:
    user = _make_user()

    # Join 2 rooms (max)
    for i in range(2):
        ws = _make_ws()
        info = await manager.connect(ws, f"project:1:template:{i}", user, can_edit=True)
        assert info is not None

    # 3rd room should fail
    ws = _make_ws()
    info = await manager.connect(ws, "project:1:template:99", user, can_edit=True)
    assert info is None


@pytest.mark.anyio
async def test_broadcast_bytes_excludes_sender(manager: CollabConnectionManager) -> None:
    ws_a = _make_ws()
    ws_b = _make_ws()
    ws_c = _make_ws()

    await manager.connect(ws_a, ROOM, _make_user(1, "A"), can_edit=True)
    await manager.connect(ws_b, ROOM, _make_user(2, "B"), can_edit=True)
    await manager.connect(ws_c, ROOM, _make_user(3, "C"), can_edit=True)

    await manager.broadcast_bytes(ROOM, b"\x01\x02", exclude=ws_a)

    ws_a.send_bytes.assert_not_called()
    ws_b.send_bytes.assert_called_once_with(b"\x01\x02")
    ws_c.send_bytes.assert_called_once_with(b"\x01\x02")


@pytest.mark.anyio
async def test_broadcast_json_excludes_sender(manager: CollabConnectionManager) -> None:
    ws_a = _make_ws()
    ws_b = _make_ws()

    await manager.connect(ws_a, ROOM, _make_user(1, "A"), can_edit=True)
    await manager.connect(ws_b, ROOM, _make_user(2, "B"), can_edit=True)

    payload: dict[str, object] = {"type": "awareness", "user_id": 1}
    await manager.broadcast_json(ROOM, payload, exclude=ws_a)

    ws_a.send_json.assert_not_called()
    ws_b.send_json.assert_called_once_with(payload)


@pytest.mark.anyio
async def test_send_to_user(manager: CollabConnectionManager) -> None:
    ws_a = _make_ws()
    ws_b = _make_ws()

    await manager.connect(ws_a, ROOM, _make_user(1, "A"), can_edit=True)
    await manager.connect(ws_b, ROOM, _make_user(2, "B"), can_edit=True)

    result = await manager.send_to_user(ROOM, 2, b"\xff")
    assert result is True
    ws_b.send_bytes.assert_called_once_with(b"\xff")
    ws_a.send_bytes.assert_not_called()

    # Non-existent user
    result = await manager.send_to_user(ROOM, 999, b"\xff")
    assert result is False


@pytest.mark.anyio
async def test_disconnect_cleans_up_empty_room(manager: CollabConnectionManager) -> None:
    ws = _make_ws()
    await manager.connect(ws, ROOM, _make_user(), can_edit=True)
    assert manager.active_rooms == 1

    await manager.disconnect(ws, ROOM)
    assert manager.active_rooms == 0


@pytest.mark.anyio
async def test_get_peers_returns_all(manager: CollabConnectionManager) -> None:
    ws_a = _make_ws()
    ws_b = _make_ws()

    await manager.connect(ws_a, ROOM, _make_user(1, "A"), can_edit=True)
    await manager.connect(ws_b, ROOM, _make_user(2, "B"), can_edit=True)

    peers = manager.get_peers(ROOM)
    assert len(peers) == 2
    user_ids = {p.user_id for p in peers}
    assert user_ids == {1, 2}


@pytest.mark.anyio
async def test_color_assignment(manager: CollabConnectionManager) -> None:
    colors: set[str] = set()
    for i in range(3):
        ws = _make_ws()
        info = await manager.connect(ws, ROOM, _make_user(i + 1, f"U{i}"), can_edit=True)
        assert info is not None
        colors.add(info.color)

    # All 3 peers should get distinct colors
    assert len(colors) == 3
