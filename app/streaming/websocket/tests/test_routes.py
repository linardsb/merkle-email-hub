"""Integration-style tests for WebSocket collaboration endpoint."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.streaming.websocket.auth import AuthResult
from app.streaming.websocket.manager import CollabConnectionManager
from app.streaming.websocket.routes import (
    close_collab_manager,
    set_collab_manager,
    set_redis_bridge,
)


def _make_user(user_id: int = 1, role: str = "admin") -> Any:
    return SimpleNamespace(id=user_id, name="Test", role=role, email="test@test.com")


ROOM = "project:1:template:10"


@pytest.fixture
def _collab_setup():
    """Set up and tear down collab manager for each test."""
    mgr = CollabConnectionManager(max_per_room=3, max_rooms_per_user=10)
    set_collab_manager(mgr)
    set_redis_bridge(None)  # type: ignore[arg-type]
    yield mgr
    close_collab_manager()


@pytest.fixture
def client(_collab_setup: CollabConnectionManager) -> TestClient:
    from app.main import app

    return TestClient(app)


@patch("app.streaming.websocket.routes.get_settings")
def test_connect_disabled(mock_settings: AsyncMock, client: TestClient) -> None:
    settings = mock_settings.return_value
    settings.collab_ws.enabled = False

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/collab/{ROOM}"):
            pass


@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_connect_no_token(
    mock_settings: AsyncMock, mock_auth: AsyncMock, client: TestClient
) -> None:
    settings = mock_settings.return_value
    settings.collab_ws.enabled = True
    mock_auth.return_value = None

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/collab/{ROOM}"):
            pass


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_connect_no_project_access(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    settings = mock_settings.return_value
    settings.collab_ws.enabled = True
    mock_auth.return_value = AuthResult(user=_make_user(), can_edit=True)
    mock_access.return_value = False

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/collab/{ROOM}"):
            pass


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_connect_success_receives_ack(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    settings = mock_settings.return_value
    settings.collab_ws.enabled = True
    settings.collab_ws.heartbeat_interval_seconds = 300  # Long interval to avoid during test
    settings.collab_ws.max_message_bytes = 1_048_576
    mock_auth.return_value = AuthResult(user=_make_user(), can_edit=True)
    mock_access.return_value = True

    with client.websocket_connect(f"/ws/collab/{ROOM}") as ws:
        data = ws.receive_json()
        assert data["type"] == "ack"
        assert data["action"] == "connected"
        assert data["room_id"] == ROOM
        assert data["user"]["user_id"] == 1


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_viewer_cannot_send_binary(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    settings = mock_settings.return_value
    settings.collab_ws.enabled = True
    settings.collab_ws.heartbeat_interval_seconds = 300
    settings.collab_ws.max_message_bytes = 1_048_576
    mock_auth.return_value = AuthResult(user=_make_user(role="viewer"), can_edit=False)
    mock_access.return_value = True

    with client.websocket_connect(f"/ws/collab/{ROOM}") as ws:
        # Receive ack
        ws.receive_json()

        # Send binary as viewer
        ws.send_bytes(b"\x01\x02")
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "read_only"


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_awareness_relay(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    settings = mock_settings.return_value
    settings.collab_ws.enabled = True
    settings.collab_ws.heartbeat_interval_seconds = 300
    settings.collab_ws.max_message_bytes = 1_048_576
    mock_auth.return_value = AuthResult(user=_make_user(), can_edit=True)
    mock_access.return_value = True

    with client.websocket_connect(f"/ws/collab/{ROOM}") as ws:
        ws.receive_json()  # ack

        # Send awareness — should get no error
        ws.send_text(json.dumps({"type": "awareness", "cursor_line": 5}))
        # No direct echo back to sender, but connection should stay alive


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_message_size_limit(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    settings = mock_settings.return_value
    settings.collab_ws.enabled = True
    settings.collab_ws.heartbeat_interval_seconds = 300
    settings.collab_ws.max_message_bytes = 100  # Very small limit for test
    mock_auth.return_value = AuthResult(user=_make_user(), can_edit=True)
    mock_access.return_value = True

    with client.websocket_connect(f"/ws/collab/{ROOM}") as ws:
        ws.receive_json()  # ack

        # Send oversized binary
        ws.send_bytes(b"\x00" * 200)
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "message_too_large"


# --- Phase 24.8 new tests ---


def _setup_mocks(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    role: str = "admin",
) -> None:
    """Common mock setup for route tests."""
    settings = mock_settings.return_value
    settings.collab_ws.enabled = True
    settings.collab_ws.heartbeat_interval_seconds = 300
    settings.collab_ws.max_message_bytes = 1_048_576
    settings.collab_ws.crdt_enabled = False
    can_edit = role != "viewer"
    mock_auth.return_value = AuthResult(user=_make_user(role=role), can_edit=can_edit)
    mock_access.return_value = True


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_viewer_receives_ack_with_viewer_role(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    """Viewer receives ack with viewer role."""
    _setup_mocks(mock_settings, mock_auth, mock_access, role="viewer")
    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ack = ws.receive_json()
        assert ack["type"] == "ack"
        assert ack["user"]["role"] == "viewer"


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_unknown_json_type_returns_error(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    """Unknown JSON message type triggers error response."""
    _setup_mocks(mock_settings, mock_auth, mock_access)
    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ws.receive_json()  # ack
        ws.send_json({"type": "unknown_type"})
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert resp["code"] == "unknown_type"


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_expired_token_rejected(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    """Auth failure (e.g. expired JWT) rejects connection."""
    settings = mock_settings.return_value
    settings.collab_ws.enabled = True
    mock_auth.return_value = None  # Auth fails

    with pytest.raises((WebSocketDisconnect, Exception)):
        with client.websocket_connect(f"/ws/collab/{ROOM}?token=expired") as ws:
            ws.receive_json()


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_awareness_message_relayed(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    """Awareness messages are accepted and relayed (no error returned)."""
    _setup_mocks(mock_settings, mock_auth, mock_access)
    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ws.receive_json()  # ack
        ws.send_json(
            {
                "type": "awareness",
                "cursor_line": 10,
                "cursor_column": 5,
            }
        )
        # No error returned — alone in room so no relay target, but connection stays alive


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_invalid_json_returns_parse_error(
    mock_settings: AsyncMock,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
) -> None:
    """Invalid JSON text returns parse_error."""
    _setup_mocks(mock_settings, mock_auth, mock_access)
    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ws.receive_json()  # ack
        ws.send_text("not valid json{{{")
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert resp["code"] == "parse_error"
