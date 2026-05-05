# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Tests for Figma webhook endpoint, signature verification, and debounce logic."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.rate_limit import limiter
from app.design_sync.exceptions import WebhookSignatureError
from app.design_sync.schemas import (
    FigmaWebhookPayload,
    TokenDiffEntry,
    TokenDiffResponse,
)
from app.design_sync.services._context import DesignSyncContext
from app.design_sync.services.connection_service import ConnectionService
from app.design_sync.services.conversion_service import TokenConversionService
from app.design_sync.services.webhook_service import WebhookService, format_diff_summary
from app.design_sync.webhook import verify_signature
from app.main import app

BASE = "/api/v1/design-sync"
PASSCODE = "test-webhook-secret"


# ── Helpers ──


def _make_user(role: str = "admin") -> User:
    user = User(email="admin@test.com", hashed_password="x", role=role)
    user.id = 1
    return user


def _make_webhook_payload(
    event_type: str = "FILE_UPDATE",
    file_key: str = "abc123",
) -> bytes:
    payload = {
        "event_type": event_type,
        "file_key": file_key,
        "file_name": "Test Design",
        "timestamp": "2026-03-27T10:00:00Z",
        "team_id": "team42",
    }
    return json.dumps(payload).encode()


def _sign(payload: bytes, passcode: str = PASSCODE) -> str:
    return hmac.new(passcode.encode(), payload, hashlib.sha256).hexdigest()


def _mock_connection(
    id: int = 1,
    file_ref: str = "abc123",
    project_id: int | None = 1,
    webhook_id: str | None = None,
) -> MagicMock:
    conn = MagicMock()
    conn.id = id
    conn.file_ref = file_ref
    conn.provider = "figma"
    conn.project_id = project_id
    conn.webhook_id = webhook_id
    conn.encrypted_token = "enc_token"
    conn.token_last4 = "x7Kz"
    conn.name = "Test"
    conn.file_url = "https://figma.com/design/abc123/Test"
    conn.status = "connected"
    conn.error_message = None
    conn.last_synced_at = None
    conn.config_json = None
    conn.created_by_id = 1
    conn.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    conn.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    return conn


# ── Fixtures ──


@pytest.fixture(autouse=True)
def _disable_rate_limiter() -> Generator[None]:
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def _auth_admin() -> Generator[None]:
    user = _make_user("admin")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _auth_viewer() -> Generator[None]:
    user = _make_user("viewer")
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── Signature Verification ──


class TestVerifySignature:
    """Tests for HMAC-SHA256 signature validation."""

    def test_valid_signature(self) -> None:
        payload = b'{"event_type": "FILE_UPDATE"}'
        sig = _sign(payload)
        verify_signature(payload, sig, PASSCODE)  # Should not raise

    def test_invalid_signature(self) -> None:
        payload = b'{"event_type": "FILE_UPDATE"}'
        with pytest.raises(WebhookSignatureError, match="Invalid"):
            verify_signature(payload, "bad_signature", PASSCODE)

    def test_empty_signature(self) -> None:
        payload = b'{"event_type": "FILE_UPDATE"}'
        with pytest.raises(WebhookSignatureError, match="Missing"):
            verify_signature(payload, "", PASSCODE)

    def test_tampered_payload(self) -> None:
        payload = b'{"event_type": "FILE_UPDATE"}'
        sig = _sign(payload)
        tampered = b'{"event_type": "FILE_DELETE"}'
        with pytest.raises(WebhookSignatureError, match="Invalid"):
            verify_signature(tampered, sig, PASSCODE)


# ── Webhook Payload Schema ──


class TestFigmaWebhookPayload:
    def test_parse_file_update(self) -> None:
        raw = _make_webhook_payload()
        payload = FigmaWebhookPayload.model_validate_json(raw)
        assert payload.event_type == "FILE_UPDATE"
        assert payload.file_key == "abc123"
        assert payload.team_id == "team42"

    def test_optional_team_id(self) -> None:
        data = {"event_type": "PING", "file_key": "x", "file_name": "Y", "timestamp": "now"}
        payload = FigmaWebhookPayload.model_validate(data)
        assert payload.team_id is None


# ── Webhook Endpoint ──


class TestWebhookEndpoint:
    """Tests for POST /webhooks/figma."""

    def test_disabled_returns_status(self, client: TestClient) -> None:
        """When figma_webhook_enabled=False, returns disabled."""
        with patch("app.core.config.get_settings") as mock_settings:
            s = mock_settings.return_value
            s.design_sync.figma_webhook_enabled = False
            resp = client.post(f"{BASE}/webhooks/figma", content=b"{}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_invalid_signature_returns_401(self, client: TestClient) -> None:
        """Invalid HMAC signature returns 401."""
        payload = _make_webhook_payload()
        with patch("app.core.config.get_settings") as mock_settings:
            s = mock_settings.return_value
            s.design_sync.figma_webhook_enabled = True
            s.design_sync.figma_webhook_passcode = PASSCODE
            resp = client.post(
                f"{BASE}/webhooks/figma",
                content=payload,
                headers={"X-Figma-Signature": "wrong"},
            )
        assert resp.status_code == 401

    def test_non_file_update_ignored(self, client: TestClient) -> None:
        """Non-FILE_UPDATE events are ignored."""
        payload = _make_webhook_payload(event_type="PING")
        sig = _sign(payload)
        with patch("app.core.config.get_settings") as mock_settings:
            s = mock_settings.return_value
            s.design_sync.figma_webhook_enabled = True
            s.design_sync.figma_webhook_passcode = PASSCODE
            resp = client.post(
                f"{BASE}/webhooks/figma",
                content=payload,
                headers={"X-Figma-Signature": sig},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_unknown_file_key_ok(self, client: TestClient) -> None:
        """FILE_UPDATE for unknown file_key returns ok silently."""
        payload = _make_webhook_payload(file_key="unknown_key")
        sig = _sign(payload)

        mock_repo = AsyncMock()
        mock_repo.get_connection_by_file_ref = AsyncMock(return_value=None)

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.design_sync.routes.DesignSyncRepository", return_value=mock_repo),
        ):
            s = mock_settings.return_value
            s.design_sync.figma_webhook_enabled = True
            s.design_sync.figma_webhook_passcode = PASSCODE
            resp = client.post(
                f"{BASE}/webhooks/figma",
                content=payload,
                headers={"X-Figma-Signature": sig},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_valid_event_enqueues_sync(self, client: TestClient) -> None:
        """Valid FILE_UPDATE enqueues debounced sync."""
        payload = _make_webhook_payload()
        sig = _sign(payload)
        conn = _mock_connection()

        mock_repo = AsyncMock()
        mock_repo.get_connection_by_file_ref = AsyncMock(return_value=conn)

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.design_sync.routes.DesignSyncRepository", return_value=mock_repo),
            patch(
                "app.design_sync.webhook.enqueue_debounced_sync", new_callable=AsyncMock
            ) as mock_enqueue,
            patch("app.design_sync.webhook.debounced_sync_worker", new_callable=AsyncMock),
        ):
            s = mock_settings.return_value
            s.design_sync.figma_webhook_enabled = True
            s.design_sync.figma_webhook_passcode = PASSCODE
            resp = client.post(
                f"{BASE}/webhooks/figma",
                content=payload,
                headers={"X-Figma-Signature": sig},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_enqueue.assert_called_once_with("abc123", conn.id)


# ── Register/Unregister Webhook ──


class TestRegisterWebhook:
    """Tests for POST /connections/{id}/webhook."""

    @pytest.mark.usefixtures("_auth_admin")
    def test_register_success(self, client: TestClient) -> None:
        with patch.object(
            WebhookService,
            "register_figma_webhook",
            new_callable=AsyncMock,
            return_value="wh_123",
        ):
            resp = client.post(
                f"{BASE}/connections/1/webhook?team_id=team42",
            )
        assert resp.status_code == 201
        assert resp.json()["webhook_id"] == "wh_123"

    @pytest.mark.usefixtures("_auth_viewer")
    def test_register_viewer_forbidden(self, client: TestClient) -> None:
        resp = client.post(f"{BASE}/connections/1/webhook?team_id=team42")
        assert resp.status_code == 403


class TestUnregisterWebhook:
    """Tests for DELETE /connections/{id}/webhook."""

    @pytest.mark.usefixtures("_auth_admin")
    def test_unregister_success(self, client: TestClient) -> None:
        with patch.object(
            WebhookService,
            "unregister_figma_webhook",
            new_callable=AsyncMock,
        ):
            resp = client.delete(f"{BASE}/connections/1/webhook")
        assert resp.status_code == 204

    @pytest.mark.usefixtures("_auth_viewer")
    def test_unregister_viewer_forbidden(self, client: TestClient) -> None:
        resp = client.delete(f"{BASE}/connections/1/webhook")
        assert resp.status_code == 403


# ── Service: handle_webhook_sync ──


class TestHandleWebhookSync:
    """Tests for WebhookService.handle_webhook_sync()."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def ctx(self, mock_db: AsyncMock, mock_repo: AsyncMock) -> DesignSyncContext:
        ctx = DesignSyncContext(mock_db)
        ctx._repo_default = mock_repo
        return ctx

    @pytest.fixture
    def service(self, ctx: DesignSyncContext) -> WebhookService:
        return WebhookService(ctx)

    @pytest.mark.asyncio
    async def test_connection_not_found_returns_none(
        self, mock_repo: AsyncMock, service: WebhookService
    ) -> None:
        mock_repo.get_connection.return_value = None
        result = await service.handle_webhook_sync(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_sync_failure_returns_none(
        self, mock_repo: AsyncMock, service: WebhookService
    ) -> None:
        conn = _mock_connection()
        mock_repo.get_connection.return_value = conn
        with patch.object(
            ConnectionService,
            "sync_connection",
            new_callable=AsyncMock,
            side_effect=RuntimeError("fail"),
        ):
            result = await service.handle_webhook_sync(1)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_changes_returns_none(
        self, mock_repo: AsyncMock, service: WebhookService
    ) -> None:
        conn = _mock_connection()
        mock_repo.get_connection.return_value = conn
        empty_diff = TokenDiffResponse(
            connection_id=1,
            current_extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
            entries=[],
        )
        with (
            patch.object(ConnectionService, "sync_connection", new_callable=AsyncMock),
            patch.object(
                TokenConversionService,
                "get_token_diff",
                new_callable=AsyncMock,
                return_value=empty_diff,
            ),
        ):
            result = await service.handle_webhook_sync(1)
        assert result is None

    @pytest.mark.asyncio
    async def test_changes_return_update_message(
        self, mock_repo: AsyncMock, service: WebhookService
    ) -> None:
        conn = _mock_connection()
        mock_repo.get_connection.return_value = conn
        diff = TokenDiffResponse(
            connection_id=1,
            current_extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
            entries=[
                TokenDiffEntry(
                    category="color", name="primary", change="added", new_value="#FF0000"
                ),
                TokenDiffEntry(
                    category="color", name="secondary", change="removed", old_value="#00FF00"
                ),
                TokenDiffEntry(
                    category="spacing",
                    name="gap",
                    change="changed",
                    old_value="8px",
                    new_value="16px",
                ),
            ],
            has_previous=True,
        )
        with (
            patch.object(ConnectionService, "sync_connection", new_callable=AsyncMock),
            patch.object(
                TokenConversionService,
                "get_token_diff",
                new_callable=AsyncMock,
                return_value=diff,
            ),
        ):
            result = await service.handle_webhook_sync(1)

        assert result is not None
        assert result.type == "design_sync_update"
        assert result.connection_id == 1
        assert result.total_changes == 3
        assert "added" in result.diff_summary
        assert "removed" in result.diff_summary


# ── format_diff_summary ──


class TestFormatDiffSummary:
    def test_empty(self) -> None:
        assert format_diff_summary([]) == "no changes"

    def test_mixed(self) -> None:
        entries = [
            TokenDiffEntry(category="color", name="a", change="added"),
            TokenDiffEntry(category="color", name="b", change="added"),
            TokenDiffEntry(category="spacing", name="c", change="removed"),
        ]
        result = format_diff_summary(entries)
        assert "2 added" in result
        assert "1 removed" in result


# ── Repository: get_connection_by_file_ref ──


class TestRepositoryGetByFileRef:
    @pytest.mark.asyncio
    async def test_finds_connection(self) -> None:
        from app.design_sync.repository import DesignSyncRepository

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _mock_connection()
        mock_db.execute = AsyncMock(return_value=mock_result)

        repo = DesignSyncRepository(mock_db)
        result = await repo.get_connection_by_file_ref("figma", "abc123")
        assert result is not None
        assert result.file_ref == "abc123"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        from app.design_sync.repository import DesignSyncRepository

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        repo = DesignSyncRepository(mock_db)
        result = await repo.get_connection_by_file_ref("figma", "nonexistent")
        assert result is None


# ── Debounced Sync Worker ──


class TestDebouncedSyncWorker:
    """Tests for debounced_sync_worker background task."""

    @pytest.mark.asyncio
    async def test_skips_when_new_event_arrived(self) -> None:
        """If Redis key still exists after sleep, another event arrived — skip."""
        from app.design_sync.webhook import debounced_sync_worker

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1:2026-03-27T10:00:00")

        with (
            patch("app.design_sync.webhook.get_settings") as mock_settings,
            patch(
                "app.design_sync.webhook.get_redis", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch("app.design_sync.webhook.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_settings.return_value.design_sync.webhook_debounce_seconds = 1
            await debounced_sync_worker(1, "abc123", project_id=1)

        # Should NOT have called sync — key was still present
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_runs_sync_when_debounce_expired(self) -> None:
        """If Redis key expired, run sync and broadcast."""
        from app.design_sync.schemas import DesignSyncUpdateMessage
        from app.design_sync.webhook import debounced_sync_worker

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Key expired

        mock_msg = DesignSyncUpdateMessage(
            connection_id=1,
            diff_summary="1 added",
            total_changes=1,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mock_service = AsyncMock()
        mock_service.handle_webhook_sync = AsyncMock(return_value=mock_msg)

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.design_sync.webhook.get_settings") as mock_settings,
            patch(
                "app.design_sync.webhook.get_redis", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch("app.design_sync.webhook.asyncio.sleep", new_callable=AsyncMock),
            patch("app.core.database.get_db_context", return_value=mock_db),
            patch("app.design_sync.services.WebhookService", return_value=mock_service),
            patch(
                "app.design_sync.webhook._broadcast_update", new_callable=AsyncMock
            ) as mock_broadcast,
        ):
            mock_settings.return_value.design_sync.webhook_debounce_seconds = 1
            await debounced_sync_worker(1, "abc123", project_id=5)

        mock_service.handle_webhook_sync.assert_called_once_with(1)
        mock_broadcast.assert_called_once_with(5, mock_msg)

    @pytest.mark.asyncio
    async def test_no_broadcast_when_no_project(self) -> None:
        """If connection has no project_id, skip broadcast."""
        from app.design_sync.schemas import DesignSyncUpdateMessage
        from app.design_sync.webhook import debounced_sync_worker

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        mock_msg = DesignSyncUpdateMessage(
            connection_id=1,
            diff_summary="1 added",
            total_changes=1,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mock_service = AsyncMock()
        mock_service.handle_webhook_sync = AsyncMock(return_value=mock_msg)

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.design_sync.webhook.get_settings") as mock_settings,
            patch(
                "app.design_sync.webhook.get_redis", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch("app.design_sync.webhook.asyncio.sleep", new_callable=AsyncMock),
            patch("app.core.database.get_db_context", return_value=mock_db),
            patch("app.design_sync.services.WebhookService", return_value=mock_service),
            patch(
                "app.design_sync.webhook._broadcast_update", new_callable=AsyncMock
            ) as mock_broadcast,
        ):
            mock_settings.return_value.design_sync.webhook_debounce_seconds = 1
            await debounced_sync_worker(1, "abc123", project_id=None)

        mock_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_broadcast_when_sync_returns_none(self) -> None:
        """If sync finds no changes, skip broadcast."""
        from app.design_sync.webhook import debounced_sync_worker

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        mock_service = AsyncMock()
        mock_service.handle_webhook_sync = AsyncMock(return_value=None)

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.design_sync.webhook.get_settings") as mock_settings,
            patch(
                "app.design_sync.webhook.get_redis", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch("app.design_sync.webhook.asyncio.sleep", new_callable=AsyncMock),
            patch("app.core.database.get_db_context", return_value=mock_db),
            patch("app.design_sync.services.WebhookService", return_value=mock_service),
            patch(
                "app.design_sync.webhook._broadcast_update", new_callable=AsyncMock
            ) as mock_broadcast,
        ):
            mock_settings.return_value.design_sync.webhook_debounce_seconds = 1
            await debounced_sync_worker(1, "abc123", project_id=1)

        mock_broadcast.assert_not_called()


# ── Broadcast Update ──


class TestBroadcastUpdate:
    """Tests for _broadcast_update WebSocket broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcasts_to_project_room(self) -> None:
        from app.design_sync.schemas import DesignSyncUpdateMessage
        from app.design_sync.webhook import _broadcast_update

        msg = DesignSyncUpdateMessage(
            connection_id=1,
            diff_summary="2 added",
            total_changes=2,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mock_manager = AsyncMock()

        with patch("app.streaming.websocket.routes.get_collab_manager", return_value=mock_manager):
            await _broadcast_update(project_id=5, msg=msg)

        mock_manager.broadcast_json.assert_called_once()
        call_args = mock_manager.broadcast_json.call_args
        assert call_args[0][0] == "project:5"
        payload = call_args[0][1]
        assert payload["type"] == "design_sync_update"
        assert payload["connection_id"] == 1
        assert payload["total_changes"] == 2
