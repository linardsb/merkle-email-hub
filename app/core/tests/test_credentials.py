# pyright: reportUnknownMemberType=false
"""Tests for credential pool rotation, cooldown, and recovery."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.credentials import CredentialPool, _hash_key
from app.core.exceptions import NoHealthyCredentialsError


def _mock_config(
    *,
    enabled: bool = True,
    cooldown_initial_seconds: int = 30,
    cooldown_max_seconds: int = 300,
    failure_threshold: int = 3,
    unhealthy_ttl_seconds: int = 3600,
) -> MagicMock:
    cfg = MagicMock()
    cfg.enabled = enabled
    cfg.cooldown_initial_seconds = cooldown_initial_seconds
    cfg.cooldown_max_seconds = cooldown_max_seconds
    cfg.failure_threshold = failure_threshold
    cfg.unhealthy_ttl_seconds = unhealthy_ttl_seconds
    return cfg


def _mock_redis_with_state() -> tuple[AsyncMock, dict[str, str]]:
    """Redis mock with stateful get/setex via side_effect dict."""
    store: dict[str, str] = {}
    redis = AsyncMock()

    async def _get(key: str) -> str | None:
        return store.get(key)

    async def _setex(key: str, ttl: int, value: str) -> None:
        store[key] = value

    redis.get = AsyncMock(side_effect=_get)
    redis.setex = AsyncMock(side_effect=_setex)
    return redis, store


class TestCredentialPoolRotation:
    """Tests for round-robin key selection."""

    @pytest.mark.asyncio
    async def test_round_robin_three_keys(self) -> None:
        """3 keys, 6 calls -> each key used twice in order."""
        keys = ["key-a", "key-b", "key-c"]
        redis, _store = _mock_redis_with_state()
        config = _mock_config()

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("anthropic", keys, config)
            results = []
            for _ in range(6):
                lease = await pool.get_key()
                results.append(lease.key)

        assert results == ["key-a", "key-b", "key-c", "key-a", "key-b", "key-c"]

    @pytest.mark.asyncio
    async def test_single_key_pool(self) -> None:
        """Pool of 1 returns same key every time."""
        redis, _store = _mock_redis_with_state()
        config = _mock_config()

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("openai", ["only-key"], config)
            results = [((await pool.get_key()).key) for _ in range(3)]

        assert results == ["only-key", "only-key", "only-key"]

    @pytest.mark.asyncio
    async def test_skip_cooled_down_key(self) -> None:
        """Key in cooldown is skipped, next healthy key returned."""
        keys = ["key-a", "key-b"]
        redis, store = _mock_redis_with_state()
        config = _mock_config()

        # Pre-set key-a as in cooldown (far future)
        key_a_hash = _hash_key("key-a")
        store[f"credentials:svc:{key_a_hash}"] = json.dumps(
            {
                "healthy": True,
                "cooldown_until": 9999999999.0,
                "failure_count": 1,
                "last_failure_code": 429,
            }
        )

        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 1000.0
            pool = CredentialPool("svc", keys, config)
            lease = await pool.get_key()

        assert lease.key == "key-b"

    @pytest.mark.asyncio
    async def test_all_keys_cooled_down_raises(self) -> None:
        """NoHealthyCredentialsError when no healthy keys available."""
        keys = ["key-a", "key-b"]
        redis, store = _mock_redis_with_state()
        config = _mock_config()

        for k in keys:
            h = _hash_key(k)
            store[f"credentials:svc:{h}"] = json.dumps(
                {
                    "healthy": True,
                    "cooldown_until": 9999999999.0,
                    "failure_count": 1,
                    "last_failure_code": 429,
                }
            )

        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 1000.0
            pool = CredentialPool("svc", keys, config)

            with pytest.raises(NoHealthyCredentialsError):
                await pool.get_key()

    @pytest.mark.asyncio
    async def test_wraps_around_after_last_key(self) -> None:
        """Index resets to 0 after cycling through all keys."""
        keys = ["a", "b"]
        redis, _store = _mock_redis_with_state()
        config = _mock_config()

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("svc", keys, config)
            first = (await pool.get_key()).key
            second = (await pool.get_key()).key
            third = (await pool.get_key()).key

        assert [first, second, third] == ["a", "b", "a"]


class TestCooldownAndRecovery:
    """Tests for cooldown triggers, backoff, and recovery."""

    @pytest.mark.asyncio
    async def test_cooldown_on_429(self) -> None:
        """429 -> key enters cooldown for initial_seconds."""
        redis, store = _mock_redis_with_state()
        config = _mock_config(cooldown_initial_seconds=30)

        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 1000.0
            pool = CredentialPool("svc", ["key-a"], config)
            await pool._record_failure(_hash_key("key-a"), 429)

        state_raw = store[f"credentials:svc:{_hash_key('key-a')}"]
        state = json.loads(state_raw)
        assert state["failure_count"] == 1
        # cooldown_until = 1000.0 + 30 * 2^0 = 1030.0
        assert state["cooldown_until"] == 1030.0

    @pytest.mark.asyncio
    async def test_cooldown_on_401(self) -> None:
        """401 -> same cooldown behavior as 429."""
        redis, store = _mock_redis_with_state()
        config = _mock_config(cooldown_initial_seconds=30)

        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 500.0
            pool = CredentialPool("svc", ["key-a"], config)
            await pool._record_failure(_hash_key("key-a"), 401)

        state = json.loads(store[f"credentials:svc:{_hash_key('key-a')}"])
        assert state["cooldown_until"] == 530.0

    @pytest.mark.asyncio
    async def test_cooldown_exponential_backoff(self) -> None:
        """Successive failures -> 30s, 60s, 120s, 300s (capped)."""
        redis, store = _mock_redis_with_state()
        config = _mock_config(cooldown_initial_seconds=30, cooldown_max_seconds=300)
        key_hash = _hash_key("key-a")

        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 0.0
            pool = CredentialPool("svc", ["key-a"], config)

            expected_backoffs = [30, 60, 120, 240, 300]  # 5th capped at 300
            for i, expected in enumerate(expected_backoffs):
                await pool._record_failure(key_hash, 429)
                state = json.loads(store[f"credentials:svc:{key_hash}"])
                assert state["cooldown_until"] == float(expected), (
                    f"Failure {i + 1}: expected {expected}"
                )

    @pytest.mark.asyncio
    async def test_unhealthy_after_threshold(self) -> None:
        """3 consecutive failures -> key marked unhealthy."""
        redis, store = _mock_redis_with_state()
        config = _mock_config(failure_threshold=3)
        key_hash = _hash_key("key-a")

        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 0.0
            pool = CredentialPool("svc", ["key-a"], config)

            for _ in range(3):
                await pool._record_failure(key_hash, 429)

        state = json.loads(store[f"credentials:svc:{key_hash}"])
        assert state["healthy"] is False
        assert state["failure_count"] == 3

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self) -> None:
        """report_success clears failure_count and cooldown."""
        redis, store = _mock_redis_with_state()
        config = _mock_config()
        key_hash = _hash_key("key-a")

        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 0.0
            pool = CredentialPool("svc", ["key-a"], config)

            # Fail twice then succeed
            await pool._record_failure(key_hash, 429)
            await pool._record_failure(key_hash, 429)
            await pool._record_success(key_hash)

        state = json.loads(store[f"credentials:svc:{key_hash}"])
        assert state["failure_count"] == 0
        assert state["healthy"] is True
        assert state["cooldown_until"] == 0.0

    @pytest.mark.asyncio
    async def test_unhealthy_key_recovers_after_ttl(self) -> None:
        """Unhealthy key with expired Redis TTL is treated as healthy (new _KeyState)."""
        redis, _store = _mock_redis_with_state()
        config = _mock_config()

        # Key was unhealthy, but Redis TTL expired -> get returns None -> new healthy state
        # Store is empty for this key, simulating TTL expiry

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("svc", ["key-a"], config)
            lease = await pool.get_key()

        assert lease.key == "key-a"

    @pytest.mark.asyncio
    async def test_redis_fallback_in_memory(self) -> None:
        """Redis unavailable -> uses in-memory state."""
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        redis.setex = AsyncMock(side_effect=ConnectionError("Redis down"))
        config = _mock_config()

        with patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis):
            pool = CredentialPool("svc", ["key-a", "key-b"], config)

            # Should still work via in-memory fallback
            lease1 = await pool.get_key()
            lease2 = await pool.get_key()

        assert lease1.key == "key-a"
        assert lease2.key == "key-b"

    @pytest.mark.asyncio
    async def test_lease_report_success(self) -> None:
        """CredentialLease.report_success() delegates to pool."""
        redis, store = _mock_redis_with_state()
        config = _mock_config()

        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 0.0
            pool = CredentialPool("svc", ["key-a"], config)

            # Create some failure state first (500 doesn't trigger cooldown)
            await pool._record_failure(_hash_key("key-a"), 500)
            await pool._record_failure(_hash_key("key-a"), 500)

            lease = await pool.get_key()
            await lease.report_success()

        state = json.loads(store[f"credentials:svc:{_hash_key('key-a')}"])
        assert state["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_lease_report_failure(self) -> None:
        """CredentialLease.report_failure(429) delegates to pool."""
        redis, store = _mock_redis_with_state()
        config = _mock_config()

        with (
            patch("app.core.redis.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.credentials.time") as mock_time,
        ):
            mock_time.monotonic.return_value = 0.0
            pool = CredentialPool("svc", ["key-a"], config)
            lease = await pool.get_key()
            await lease.report_failure(429)

        state = json.loads(store[f"credentials:svc:{_hash_key('key-a')}"])
        assert state["failure_count"] == 1
        assert state["last_failure_code"] == 429
