"""Tests for MCP auth middleware."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.mcp.auth import _role_to_scopes, verify_mcp_token


class TestRoleToScopes:
    def test_admin_gets_all_scopes(self) -> None:
        assert _role_to_scopes("admin") == ["read", "write", "admin"]

    def test_developer_gets_read_write(self) -> None:
        assert _role_to_scopes("developer") == ["read", "write"]

    def test_viewer_gets_read_only(self) -> None:
        assert _role_to_scopes("viewer") == ["read"]

    def test_unknown_role_gets_read_only(self) -> None:
        assert _role_to_scopes("unknown") == ["read"]


class TestVerifyMCPToken:
    """Async token verification tests."""

    @pytest.mark.anyio
    async def test_valid_token_returns_access_info(self) -> None:
        """Valid JWT returns client_id, role, and scopes."""
        mock_payload = MagicMock()
        mock_payload.sub = "user-123"
        mock_payload.role = "developer"

        with patch("app.auth.token.decode_token", return_value=mock_payload):
            result = await verify_mcp_token("valid-jwt-token")
            assert result is not None
            assert result["client_id"] == "user-123"
            assert result["role"] == "developer"
            assert "read" in result["scopes"]
            assert "write" in result["scopes"]

    @pytest.mark.anyio
    async def test_invalid_token_returns_none(self) -> None:
        """Invalid/expired token returns None."""
        with patch("app.auth.token.decode_token", side_effect=Exception("expired")):
            result = await verify_mcp_token("bad-token")
            assert result is None

    @pytest.mark.anyio
    async def test_auth_failure_does_not_leak_details(self) -> None:
        """Auth errors return None with no internal details exposed."""
        with patch(
            "app.auth.token.decode_token",
            side_effect=ValueError("secret key mismatch"),
        ):
            result = await verify_mcp_token("bad-token")
            assert result is None  # No error details returned
