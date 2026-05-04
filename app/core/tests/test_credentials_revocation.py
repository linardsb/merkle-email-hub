# pyright: reportUnknownMemberType=false
"""Tests for Phase 51.1 — credential revocation on kill.

Covers the public API in ``app.core.credentials`` (revoke_for_agent /
is_revoked / restore_for_agent + the get_key opt-in check) and the
admin-only ``POST /api/v1/credentials/revoke`` endpoint.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.core.credentials as credentials_mod
from app.auth.dependencies import get_current_user
from app.core.credentials import (
    CredentialPool,
    CredentialRevokedError,
    is_revoked,
    reset_revocations,
    restore_for_agent,
    revoke_for_agent,
)
from app.core.rate_limit import limiter


def _mock_config() -> MagicMock:
    cfg = MagicMock()
    cfg.cooldown_initial_seconds = 30
    cfg.cooldown_max_seconds = 300
    cfg.failure_threshold = 3
    cfg.unhealthy_ttl_seconds = 3600
    return cfg


def _mock_redis_with_state() -> tuple[AsyncMock, dict[str, str]]:
    """Redis mock supporting get/set/setex/delete against an in-process dict."""
    store: dict[str, str] = {}
    redis = AsyncMock()

    async def _get(key: str) -> str | None:
        return store.get(key)

    async def _set(key: str, value: str) -> None:
        store[key] = value

    async def _setex(key: str, ttl: int, value: str) -> None:
        store[key] = value

    async def _delete(key: str) -> int:
        if key in store:
            del store[key]
            return 1
        return 0

    redis.get = AsyncMock(side_effect=_get)
    redis.set = AsyncMock(side_effect=_set)
    redis.setex = AsyncMock(side_effect=_setex)
    redis.delete = AsyncMock(side_effect=_delete)
    return redis, store


@pytest.fixture(autouse=True)
def _clear_revocations() -> Generator[None]:
    """Always start each test with empty in-memory revocation state."""
    reset_revocations()
    yield
    reset_revocations()


# ── Module-level revocation API ──────────────────────────────────────


class TestRevocationApi:
    @pytest.mark.asyncio
    async def test_active_lease_completes_next_lease_blocked(self) -> None:
        """Revoke during lease — active lease completes, next get_key raises."""
        redis, _store = _mock_redis_with_state()
        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("anthropic", ["key-a", "key-b"], _mock_config())
            # First lease succeeds — caller has a key in hand.
            lease = await pool.get_key(agent_id="scaffolder")
            assert lease.key == "key-a"

            # Admin revokes mid-flight; the existing lease handle is unaffected.
            await revoke_for_agent("scaffolder", "kill_switch")
            await lease.report_success()  # in-flight call still completes

            # Next lease for the revoked agent must fail.
            with pytest.raises(CredentialRevokedError) as exc_info:
                await pool.get_key(agent_id="scaffolder")
            assert exc_info.value.agent_id == "scaffolder"
            assert "kill_switch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_revocation_persisted_to_redis_for_global_visibility(self) -> None:
        """Revoke is global across replicas via Redis-stored record."""
        redis, store = _mock_redis_with_state()
        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            await revoke_for_agent("dark_mode", "manual_admin_revocation")

        assert "credentials:revoked:dark_mode" in store
        record = json.loads(store["credentials:revoked:dark_mode"])
        assert record["reason"] == "manual_admin_revocation"
        assert record["ttl_s"] is None  # default when no TTL configured

    @pytest.mark.asyncio
    async def test_ttl_none_uses_redis_set_not_setex(self) -> None:
        """ttl=None => permanent revocation (SET, no expiry)."""
        redis, _store = _mock_redis_with_state()
        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            await revoke_for_agent("scaffolder", "kill_switch", ttl=None)

        redis.set.assert_awaited_once()
        redis.setex.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ttl_positive_uses_setex_with_that_ttl(self) -> None:
        """ttl=N (positive) => SETEX with the supplied TTL."""
        redis, _store = _mock_redis_with_state()
        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            await revoke_for_agent("scaffolder", "rate_limit_breach", ttl=600)

        redis.setex.assert_awaited_once()
        args, _ = redis.setex.call_args
        assert args[0] == "credentials:revoked:scaffolder"
        assert args[1] == 600
        redis.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_audit_log_emitted_on_revoke(self) -> None:
        """Audit line ``credentials.revoked_for_agent`` is emitted."""
        redis, _store = _mock_redis_with_state()
        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch.object(credentials_mod, "logger") as mock_logger,
        ):
            await revoke_for_agent("content", "kill_switch", ttl=300)

        mock_logger.warning.assert_called_once()
        event = mock_logger.warning.call_args[0][0]
        kwargs = mock_logger.warning.call_args[1]
        assert event == "credentials.revoked_for_agent"
        assert kwargs["agent_id"] == "content"
        assert kwargs["reason"] == "kill_switch"
        assert kwargs["ttl_s"] == 300

    @pytest.mark.asyncio
    async def test_restore_lifts_revocation_and_re_enables_leasing(self) -> None:
        """After restore, ``get_key`` succeeds again for the same agent."""
        redis, _store = _mock_redis_with_state()
        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("anthropic", ["key-a"], _mock_config())

            await revoke_for_agent("scaffolder", "kill_switch")
            assert await is_revoked("scaffolder") is True
            with pytest.raises(CredentialRevokedError):
                await pool.get_key(agent_id="scaffolder")

            was_revoked = await restore_for_agent("scaffolder")
            assert was_revoked is True
            assert await is_revoked("scaffolder") is False

            lease = await pool.get_key(agent_id="scaffolder")
            assert lease.key == "key-a"

    @pytest.mark.asyncio
    async def test_get_key_without_agent_id_bypasses_revocation_check(self) -> None:
        """Backwards compat: callers that don't supply agent_id are unaffected."""
        redis, _store = _mock_redis_with_state()
        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("anthropic", ["key-a"], _mock_config())
            await revoke_for_agent("scaffolder", "kill_switch")

            # No agent_id => revocation is not consulted.
            lease = await pool.get_key()
            assert lease.key == "key-a"

    @pytest.mark.asyncio
    async def test_redis_unavailable_falls_back_to_in_memory(self) -> None:
        """When Redis raises, revocation still tracked in the process."""
        broken = AsyncMock()
        broken.get = AsyncMock(side_effect=RuntimeError("redis down"))
        broken.set = AsyncMock(side_effect=RuntimeError("redis down"))
        broken.setex = AsyncMock(side_effect=RuntimeError("redis down"))
        broken.delete = AsyncMock(side_effect=RuntimeError("redis down"))

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=broken):
            pool = CredentialPool("anthropic", ["key-a"], _mock_config())
            await revoke_for_agent("scaffolder", "kill_switch")
            assert await is_revoked("scaffolder") is True
            with pytest.raises(CredentialRevokedError):
                await pool.get_key(agent_id="scaffolder")


# ── Admin endpoint ───────────────────────────────────────────────────


def _admin_user() -> MagicMock:
    user = MagicMock()
    user.role = "admin"
    user.id = 1
    user.email = "admin@example.com"
    user.is_active = True
    return user


def _viewer_user() -> MagicMock:
    user = MagicMock()
    user.role = "viewer"
    user.id = 2
    user.email = "viewer@example.com"
    user.is_active = True
    return user


@pytest.fixture
def admin_client() -> Generator[TestClient]:
    from app.core.credentials_routes import router

    app = FastAPI()
    app.include_router(router)
    limiter.enabled = False
    app.dependency_overrides[get_current_user] = _admin_user
    yield TestClient(app)
    limiter.enabled = True
    app.dependency_overrides.clear()


@pytest.fixture
def viewer_client() -> Generator[TestClient]:
    from app.core.credentials_routes import router

    app = FastAPI()
    app.include_router(router)
    limiter.enabled = False
    app.dependency_overrides[get_current_user] = _viewer_user
    yield TestClient(app)
    limiter.enabled = True
    app.dependency_overrides.clear()


class TestRevokeEndpoint:
    def test_revoke_endpoint_rejects_non_admin(self, viewer_client: TestClient) -> None:
        """Viewer role => 403, no Redis call attempted."""
        redis, _store = _mock_redis_with_state()
        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            resp = viewer_client.post(
                "/api/v1/credentials/revoke",
                json={"agent_id": "scaffolder", "reason": "kill_switch"},
            )
        assert resp.status_code == 403
        redis.set.assert_not_awaited()

    def test_revoke_endpoint_persists_revocation(self, admin_client: TestClient) -> None:
        """Admin POST /revoke writes to Redis and returns revoked=true."""
        redis, store = _mock_redis_with_state()
        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            resp = admin_client.post(
                "/api/v1/credentials/revoke",
                json={"agent_id": "scaffolder", "reason": "kill_switch", "ttl_s": 300},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"agent_id": "scaffolder", "revoked": True, "restored": False}
        assert "credentials:revoked:scaffolder" in store

    def test_restore_endpoint_lifts_existing_revocation(self, admin_client: TestClient) -> None:
        """``restore=true`` deletes the Redis record and reports restored=true."""
        redis, store = _mock_redis_with_state()
        store["credentials:revoked:scaffolder"] = json.dumps(
            {"reason": "kill_switch", "revoked_at": 0.0, "ttl_s": None}
        )
        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            resp = admin_client.post(
                "/api/v1/credentials/revoke",
                json={"agent_id": "scaffolder", "restore": True},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"agent_id": "scaffolder", "revoked": False, "restored": True}
        assert "credentials:revoked:scaffolder" not in store
