# pyright: reportUnknownMemberType=false
"""Tests for the distributed debounce layer."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.debounce import Debouncer, _debounce_tasks


async def _drain_tasks() -> None:
    """Await all pending debounce tasks so assertions can check results."""
    tasks = list(_debounce_tasks)
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def _mock_settings(*, enabled: bool = True) -> MagicMock:
    settings = MagicMock()
    settings.debounce.enabled = enabled
    return settings


def _mock_redis(get_return: str | bytes | None = None) -> AsyncMock:
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock(return_value=get_return)
    return redis


class TestDebouncerTrigger:
    """Tests for Debouncer.trigger() and worker lifecycle."""

    @pytest.mark.asyncio
    async def test_single_trigger_executes_callback(self) -> None:
        """A single trigger fires the callback after the debounce window."""
        callback = AsyncMock()
        redis = _mock_redis(get_return=None)  # Key expired → token matched

        with (
            patch("app.core.debounce.get_settings", return_value=_mock_settings()),
            patch("app.core.debounce.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.debounce.asyncio.sleep", new_callable=AsyncMock),
        ):
            d = Debouncer(key_prefix="test", window_ms=2000, callback=callback)
            await d.trigger(dedup_key="k1", foo="bar")
            # Let the background task run
            await _drain_tasks()

        callback.assert_called_once_with(foo="bar")

    @pytest.mark.asyncio
    async def test_rapid_triggers_coalesce(self) -> None:
        """10 rapid triggers with the same key → only the last one executes."""
        callback = AsyncMock()
        # Simulate: each trigger writes a new token. Worker checks if its token
        # is still current. Only the last token will match.
        stored_token: dict[str, str] = {}

        async def fake_setex(key: str, _ttl: int, value: str) -> None:
            stored_token[key] = value

        async def fake_get(key: str) -> str | None:
            return stored_token.get(key)

        redis = AsyncMock()
        redis.setex = AsyncMock(side_effect=fake_setex)
        redis.get = AsyncMock(side_effect=fake_get)

        with (
            patch("app.core.debounce.get_settings", return_value=_mock_settings()),
            patch("app.core.debounce.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.debounce.asyncio.sleep", new_callable=AsyncMock),
        ):
            d = Debouncer(key_prefix="test", window_ms=2000, callback=callback)
            for i in range(10):
                await d.trigger(dedup_key="k1", iteration=i)
            # Let all background tasks run
            await _drain_tasks()

        # Only the last trigger's callback should fire (token match)
        assert callback.call_count == 1
        callback.assert_called_once_with(iteration=9)

    @pytest.mark.asyncio
    async def test_different_keys_execute_independently(self) -> None:
        """Different dedup keys fire independent callbacks."""
        callback = AsyncMock()
        # Each key gets its own token
        stored: dict[str, str] = {}

        async def fake_setex(key: str, _ttl: int, value: str) -> None:
            stored[key] = value

        async def fake_get(key: str) -> str | None:
            return stored.get(key)

        redis = AsyncMock()
        redis.setex = AsyncMock(side_effect=fake_setex)
        redis.get = AsyncMock(side_effect=fake_get)

        with (
            patch("app.core.debounce.get_settings", return_value=_mock_settings()),
            patch("app.core.debounce.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.debounce.asyncio.sleep", new_callable=AsyncMock),
        ):
            d = Debouncer(key_prefix="test", window_ms=2000, callback=callback)
            await d.trigger(dedup_key="a", val="first")
            await d.trigger(dedup_key="b", val="second")
            await _drain_tasks()

        assert callback.call_count == 2

    @pytest.mark.asyncio
    async def test_disabled_executes_immediately(self) -> None:
        """When debounce is disabled, callback fires immediately without Redis."""
        callback = AsyncMock()

        with patch(
            "app.core.debounce.get_settings",
            return_value=_mock_settings(enabled=False),
        ):
            d = Debouncer(key_prefix="test", window_ms=2000, callback=callback)
            await d.trigger(dedup_key="k1", val="immediate")

        callback.assert_called_once_with(val="immediate")

    @pytest.mark.asyncio
    async def test_callback_exception_logged_not_raised(self) -> None:
        """Exception in callback is logged but does not propagate."""
        callback = AsyncMock(side_effect=RuntimeError("boom"))
        redis = _mock_redis(get_return=None)

        with (
            patch("app.core.debounce.get_settings", return_value=_mock_settings()),
            patch("app.core.debounce.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.debounce.asyncio.sleep", new_callable=AsyncMock),
            patch("app.core.debounce.log") as mock_log,
        ):
            d = Debouncer(key_prefix="test", window_ms=2000, callback=callback)
            await d.trigger(dedup_key="k1")
            await _drain_tasks()

        callback.assert_called_once()
        mock_log.warning.assert_called_once()
        assert "core.debounce_failed" in mock_log.warning.call_args[0]

    @pytest.mark.asyncio
    async def test_redis_key_format(self) -> None:
        """Redis key follows debounce:{prefix}:{dedup_key} pattern."""
        d = Debouncer(key_prefix="figma_webhook", window_ms=3000, callback=AsyncMock())
        assert d._redis_key("abc123") == "debounce:figma_webhook:abc123"

    @pytest.mark.asyncio
    async def test_token_mismatch_skips_execution(self) -> None:
        """Worker finds a different token → skips callback."""
        callback = AsyncMock()
        redis = _mock_redis(get_return="different-token:2026-01-01T00:00:00")

        with (
            patch("app.core.debounce.get_settings", return_value=_mock_settings()),
            patch("app.core.debounce.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.debounce.asyncio.sleep", new_callable=AsyncMock),
        ):
            d = Debouncer(key_prefix="test", window_ms=2000, callback=callback)
            await d.trigger(dedup_key="k1", val="x")
            await _drain_tasks()

        # Callback should NOT fire — token didn't match
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_token_expired_executes(self) -> None:
        """Worker finds key gone (expired) → executes callback."""
        callback = AsyncMock()
        redis = _mock_redis(get_return=None)  # Key expired

        with (
            patch("app.core.debounce.get_settings", return_value=_mock_settings()),
            patch("app.core.debounce.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.debounce.asyncio.sleep", new_callable=AsyncMock),
        ):
            d = Debouncer(key_prefix="test", window_ms=2000, callback=callback)
            await d.trigger(dedup_key="k1", val="expired")
            await _drain_tasks()

        callback.assert_called_once_with(val="expired")

    @pytest.mark.asyncio
    async def test_task_cleanup(self) -> None:
        """Tasks are removed from _debounce_tasks after completion."""
        callback = AsyncMock()
        redis = _mock_redis(get_return=None)

        initial_count = len(_debounce_tasks)

        with (
            patch("app.core.debounce.get_settings", return_value=_mock_settings()),
            patch("app.core.debounce.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.debounce.asyncio.sleep", new_callable=AsyncMock),
        ):
            d = Debouncer(key_prefix="test", window_ms=2000, callback=callback)
            await d.trigger(dedup_key="k1")
            # Task is in set while running
            await _drain_tasks()

        # After completion, task should be cleaned up
        assert len(_debounce_tasks) == initial_count

    @pytest.mark.asyncio
    async def test_custom_window_ms(self) -> None:
        """Different window values are respected in sleep duration."""
        callback = AsyncMock()
        redis = _mock_redis(get_return=None)

        with (
            patch("app.core.debounce.get_settings", return_value=_mock_settings()),
            patch("app.core.debounce.get_redis", new_callable=AsyncMock, return_value=redis),
            patch("app.core.debounce.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            d = Debouncer(key_prefix="test", window_ms=5000, callback=callback)
            await d.trigger(dedup_key="k1")
            await _drain_tasks()

        # Sleep should be window_ms/1000 + 0.5 = 5.5
        mock_sleep.assert_called_once_with(5.5)
