"""Integration tests: WebSocket routes + CRDT sync handler together."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.streaming.crdt.document_store import YjsDocumentStore
from app.streaming.crdt.sync_handler import MessageType, SyncMessageType, YjsSyncHandler
from app.streaming.websocket.auth import AuthResult
from app.streaming.websocket.manager import CollabConnectionManager
from app.streaming.websocket.routes import (
    close_collab_manager,
    set_collab_manager,
    set_redis_bridge,
    set_sync_handler,
)

ROOM = "project:1:template:1"


def _make_user(user_id: int = 1, role: str = "admin") -> Any:
    return SimpleNamespace(id=user_id, name="Test", role=role, email=f"u{user_id}@test.com")


def _make_mock_db() -> AsyncMock:
    """Create a mock async DB session for CRDT operations."""
    db = AsyncMock()
    db.add = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock
    return db


@asynccontextmanager
async def _mock_session():
    """Mock async context manager for AsyncSessionLocal."""
    yield _make_mock_db()


@pytest.fixture
def _full_collab_setup():
    """Setup manager + CRDT sync handler."""
    mgr = CollabConnectionManager(max_per_room=5, max_rooms_per_user=3)
    set_collab_manager(mgr)
    set_redis_bridge(None)  # type: ignore[arg-type]

    store = YjsDocumentStore(compaction_threshold=50)
    sync = YjsSyncHandler(store)
    set_sync_handler(sync)

    yield mgr, store, sync

    close_collab_manager()
    set_sync_handler(None)  # type: ignore[arg-type]


@pytest.fixture
def client(
    _full_collab_setup: tuple[CollabConnectionManager, YjsDocumentStore, YjsSyncHandler],
) -> TestClient:
    from app.main import app

    return TestClient(app)


def _setup_mocks(
    mock_settings: Any,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    role: str = "admin",
    crdt_enabled: bool = True,
) -> None:
    """Common mock setup."""
    settings = mock_settings.return_value
    settings.collab_ws.enabled = True
    settings.collab_ws.heartbeat_interval_seconds = 300
    settings.collab_ws.max_message_bytes = 1_048_576
    settings.collab_ws.crdt_enabled = crdt_enabled
    can_edit = role != "viewer"
    mock_auth.return_value = AuthResult(user=_make_user(role=role), can_edit=can_edit)
    mock_access.return_value = True


# All CRDT-enabled tests also mock AsyncSessionLocal to avoid real DB connections
_DB_PATCH = "app.core.database.AsyncSessionLocal"


@patch(_DB_PATCH, side_effect=lambda: _mock_session())
@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_connect_with_crdt_enabled(
    mock_settings: Any,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    _mock_db: Any,
    client: TestClient,
    _full_collab_setup: tuple[CollabConnectionManager, YjsDocumentStore, YjsSyncHandler],
) -> None:
    """CRDT init happens on first connect when crdt_enabled=True."""
    _setup_mocks(mock_settings, mock_auth, mock_access, crdt_enabled=True)
    _, store, _ = _full_collab_setup

    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ack = ws.receive_json()
        assert ack["type"] == "ack"
        assert ROOM in store._docs


@patch(_DB_PATCH, side_effect=lambda: _mock_session())
@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_binary_sync_step1_response(
    mock_settings: Any,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    _mock_db: Any,
    client: TestClient,
    _full_collab_setup: tuple[CollabConnectionManager, YjsDocumentStore, YjsSyncHandler],
) -> None:
    """Client sends SyncStep1, gets SyncStep2 reply."""
    _setup_mocks(mock_settings, mock_auth, mock_access, crdt_enabled=True)

    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ws.receive_json()  # ack

        ws.send_bytes(bytes([MessageType.SYNC, SyncMessageType.STEP1]))

        reply1 = ws.receive_bytes()
        assert reply1[0] == MessageType.SYNC
        assert reply1[1] == SyncMessageType.STEP2

        reply2 = ws.receive_bytes()
        assert reply2[0] == MessageType.SYNC
        assert reply2[1] == SyncMessageType.STEP1


@patch(_DB_PATCH, side_effect=lambda: _mock_session())
@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_viewer_sync_step1_allowed(
    mock_settings: Any,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    _mock_db: Any,
    client: TestClient,
    _full_collab_setup: tuple[CollabConnectionManager, YjsDocumentStore, YjsSyncHandler],
) -> None:
    """Viewer can request state vector via SyncStep1 (read-only sync)."""
    _setup_mocks(mock_settings, mock_auth, mock_access, role="viewer", crdt_enabled=True)

    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ws.receive_json()  # ack

        ws.send_bytes(bytes([MessageType.SYNC, SyncMessageType.STEP1]))

        reply = ws.receive_bytes()
        assert reply[0] == MessageType.SYNC
        assert reply[1] == SyncMessageType.STEP2


@patch(_DB_PATCH, side_effect=lambda: _mock_session())
@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_viewer_update_rejected(
    mock_settings: Any,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    _mock_db: Any,
    client: TestClient,
    _full_collab_setup: tuple[CollabConnectionManager, YjsDocumentStore, YjsSyncHandler],
) -> None:
    """Viewer binary update (non-SyncStep1) is blocked."""
    _setup_mocks(mock_settings, mock_auth, mock_access, role="viewer", crdt_enabled=True)

    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ws.receive_json()  # ack

        ws.send_bytes(bytes([MessageType.SYNC, SyncMessageType.UPDATE]) + b"\x01\x02")
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "read_only"


@patch(_DB_PATCH, side_effect=lambda: _mock_session())
@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_room_cleanup_evicts_crdt_doc(
    mock_settings: Any,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    _mock_db: Any,
    client: TestClient,
    _full_collab_setup: tuple[CollabConnectionManager, YjsDocumentStore, YjsSyncHandler],
) -> None:
    """Last peer leaving evicts CRDT doc from memory."""
    _setup_mocks(mock_settings, mock_auth, mock_access, crdt_enabled=True)
    _, store, _ = _full_collab_setup

    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ws.receive_json()  # ack
        assert ROOM in store._docs

    # After disconnect, doc should be evicted
    assert ROOM not in store._docs


@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_passthrough_mode_without_crdt(
    mock_settings: Any,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
    _full_collab_setup: tuple[CollabConnectionManager, YjsDocumentStore, YjsSyncHandler],
) -> None:
    """Without CRDT enabled, binary messages are relayed passthrough."""
    _setup_mocks(mock_settings, mock_auth, mock_access, crdt_enabled=False)

    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ws.receive_json()  # ack
        ws.send_bytes(b"\x01\x02\x03")
        # No error returned — connection stays alive


@pytest.mark.integration
@patch("app.streaming.websocket.routes.verify_room_access", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.authenticate_websocket", new_callable=AsyncMock)
@patch("app.streaming.websocket.routes.get_settings")
def test_pong_message_accepted(
    mock_settings: Any,
    mock_auth: AsyncMock,
    mock_access: AsyncMock,
    client: TestClient,
    _full_collab_setup: tuple[CollabConnectionManager, YjsDocumentStore, YjsSyncHandler],
) -> None:
    """Pong heartbeat response is silently accepted."""
    _setup_mocks(mock_settings, mock_auth, mock_access)

    with client.websocket_connect(f"/ws/collab/{ROOM}?token=valid") as ws:
        ws.receive_json()  # ack
        ws.send_json({"type": "pong"})
        # No error or response — pong is silently accepted
