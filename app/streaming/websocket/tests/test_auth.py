"""Unit tests for WebSocket authentication."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.streaming.websocket.auth import authenticate_websocket, verify_room_access


def _make_user(user_id: int = 1, role: str = "admin") -> SimpleNamespace:
    return SimpleNamespace(id=user_id, name="Test", role=role, email="test@test.com")


def _make_payload(sub: int = 1, token_type: str = "access", jti: str = "abc123") -> SimpleNamespace:  # noqa: S107
    return SimpleNamespace(sub=sub, type=token_type, jti=jti)


@pytest.mark.anyio
async def test_authenticate_missing_token() -> None:
    result = await authenticate_websocket(None)
    assert result is None


@pytest.mark.anyio
@patch("app.streaming.websocket.auth.decode_token", return_value=None)
async def test_authenticate_invalid_token(mock_decode: AsyncMock) -> None:
    result = await authenticate_websocket("bad-token")
    assert result is None


@pytest.mark.anyio
@patch("app.streaming.websocket.auth.is_token_revoked", new_callable=AsyncMock, return_value=True)
@patch("app.streaming.websocket.auth.decode_token")
async def test_authenticate_revoked_token(mock_decode: AsyncMock, mock_revoked: AsyncMock) -> None:
    mock_decode.return_value = _make_payload()
    result = await authenticate_websocket("revoked-token")
    assert result is None


@pytest.mark.anyio
@patch("app.streaming.websocket.auth.AsyncSessionLocal")
@patch("app.streaming.websocket.auth.is_token_revoked", new_callable=AsyncMock, return_value=False)
@patch("app.streaming.websocket.auth.decode_token")
async def test_authenticate_user_not_found(
    mock_decode: AsyncMock,
    mock_revoked: AsyncMock,
    mock_session_cls: AsyncMock,
) -> None:
    mock_decode.return_value = _make_payload()

    mock_db = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.streaming.websocket.auth.UserRepository") as mock_repo_cls:
        mock_repo_cls.return_value.find_by_id = AsyncMock(return_value=None)
        result = await authenticate_websocket("valid-token")

    assert result is None


@pytest.mark.anyio
@patch("app.streaming.websocket.auth.AsyncSessionLocal")
@patch("app.streaming.websocket.auth.is_token_revoked", new_callable=AsyncMock, return_value=False)
@patch("app.streaming.websocket.auth.decode_token")
async def test_authenticate_success_admin(
    mock_decode: AsyncMock,
    mock_revoked: AsyncMock,
    mock_session_cls: AsyncMock,
) -> None:
    mock_decode.return_value = _make_payload()
    user = _make_user(role="admin")

    mock_db = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.streaming.websocket.auth.UserRepository") as mock_repo_cls:
        mock_repo_cls.return_value.find_by_id = AsyncMock(return_value=user)
        result = await authenticate_websocket("valid-token")

    assert result is not None
    assert result.can_edit is True
    assert result.user.role == "admin"


@pytest.mark.anyio
@patch("app.streaming.websocket.auth.AsyncSessionLocal")
@patch("app.streaming.websocket.auth.is_token_revoked", new_callable=AsyncMock, return_value=False)
@patch("app.streaming.websocket.auth.decode_token")
async def test_authenticate_success_viewer(
    mock_decode: AsyncMock,
    mock_revoked: AsyncMock,
    mock_session_cls: AsyncMock,
) -> None:
    mock_decode.return_value = _make_payload()
    user = _make_user(role="viewer")

    mock_db = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.streaming.websocket.auth.UserRepository") as mock_repo_cls:
        mock_repo_cls.return_value.find_by_id = AsyncMock(return_value=user)
        result = await authenticate_websocket("valid-token")

    assert result is not None
    assert result.can_edit is False


@pytest.mark.anyio
@patch("app.streaming.websocket.auth.AsyncSessionLocal")
async def test_verify_room_access_valid(mock_session_cls: AsyncMock) -> None:
    user = _make_user()
    mock_db = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.streaming.websocket.auth.ProjectService") as mock_svc_cls:
        mock_svc_cls.return_value.verify_project_access = AsyncMock()
        result = await verify_room_access(user, "project:1:template:10")  # type: ignore[arg-type]

    assert result is True


@pytest.mark.anyio
@patch("app.streaming.websocket.auth.AsyncSessionLocal")
async def test_verify_room_access_denied(mock_session_cls: AsyncMock) -> None:
    user = _make_user()
    mock_db = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.streaming.websocket.auth.ProjectService") as mock_svc_cls:
        mock_svc_cls.return_value.verify_project_access = AsyncMock(
            side_effect=PermissionError("No access")
        )
        result = await verify_room_access(user, "project:1:template:10")  # type: ignore[arg-type]

    assert result is False


@pytest.mark.anyio
async def test_verify_room_access_invalid_format() -> None:
    user = _make_user()
    assert await verify_room_access(user, "invalid-room") is False  # type: ignore[arg-type]
    assert await verify_room_access(user, "project:abc:template:10") is False  # type: ignore[arg-type]
    assert await verify_room_access(user, "") is False  # type: ignore[arg-type]
