"""Tests for Redis-backed per-user quota and blueprint cost tracking."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.quota import BlueprintCostTracker, UserQuotaTracker

# ── UserQuotaTracker ──


@pytest.mark.asyncio
async def test_allows_within_limit() -> None:
    tracker = UserQuotaTracker(daily_limit=5)
    # Use in-memory path by patching Redis to fail
    with patch("app.core.redis.get_redis", side_effect=Exception("no redis")):
        for _ in range(5):
            assert tracker._check_memory(1) is True


@pytest.mark.asyncio
async def test_blocks_over_limit() -> None:
    tracker = UserQuotaTracker(daily_limit=3)
    with patch("app.core.redis.get_redis", side_effect=Exception("no redis")):
        for _ in range(3):
            result = await tracker.check_and_increment(1)
            assert result is True
        assert await tracker.check_and_increment(1) is False


@pytest.mark.asyncio
async def test_separate_users() -> None:
    tracker = UserQuotaTracker(daily_limit=2)
    with patch("app.core.redis.get_redis", side_effect=Exception("no redis")):
        # User 1 exhausts quota
        await tracker.check_and_increment(1)
        await tracker.check_and_increment(1)
        assert await tracker.check_and_increment(1) is False

        # User 2 still has quota
        assert await tracker.check_and_increment(2) is True


@pytest.mark.asyncio
async def test_remaining_decrements() -> None:
    tracker = UserQuotaTracker(daily_limit=5)
    with patch("app.core.redis.get_redis", side_effect=Exception("no redis")):
        assert await tracker.get_remaining(1) == 5
        await tracker.check_and_increment(1)
        assert await tracker.get_remaining(1) == 4
        await tracker.check_and_increment(1)
        assert await tracker.get_remaining(1) == 3


@pytest.mark.asyncio
async def test_redis_path() -> None:
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock()
    mock_redis.get = AsyncMock(return_value="1")

    tracker = UserQuotaTracker(daily_limit=50)
    with patch("app.core.redis.get_redis", return_value=mock_redis):
        result = await tracker.check_and_increment(42)
        assert result is True
        mock_redis.incr.assert_called_once_with("ai:quota:42")
        mock_redis.expire.assert_called_once_with("ai:quota:42", 86_400)


@pytest.mark.asyncio
async def test_redis_path_blocks_over_limit() -> None:
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=51)

    tracker = UserQuotaTracker(daily_limit=50)
    with patch("app.core.redis.get_redis", return_value=mock_redis):
        result = await tracker.check_and_increment(42)
        assert result is False


@pytest.mark.asyncio
async def test_fallback_when_redis_unavailable() -> None:
    tracker = UserQuotaTracker(daily_limit=2)

    # First call — Redis fails, falls back to in-memory
    with patch("app.core.redis.get_redis", side_effect=ConnectionError("down")):
        assert await tracker.check_and_increment(1) is True
        assert await tracker.check_and_increment(1) is True
        assert await tracker.check_and_increment(1) is False


# ── BlueprintCostTracker ──


@pytest.mark.asyncio
async def test_cost_tracker_within_cap() -> None:
    tracker = BlueprintCostTracker(daily_cap=10_000)
    with patch("app.core.redis.get_redis", side_effect=Exception("no redis")):
        assert await tracker.check_budget(1) == 10_000
        await tracker.record_usage(1, 3_000)
        assert await tracker.check_budget(1) == 7_000


@pytest.mark.asyncio
async def test_cost_tracker_exhausted() -> None:
    tracker = BlueprintCostTracker(daily_cap=1_000)
    with patch("app.core.redis.get_redis", side_effect=Exception("no redis")):
        await tracker.record_usage(1, 1_000)
        assert await tracker.check_budget(1) == 0


@pytest.mark.asyncio
async def test_cost_tracker_redis_path() -> None:
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="200000")
    mock_redis.incrby = AsyncMock(return_value=250000)
    mock_redis.expire = AsyncMock()

    tracker = BlueprintCostTracker(daily_cap=500_000)
    with patch("app.core.redis.get_redis", return_value=mock_redis):
        remaining = await tracker.check_budget(1)
        assert remaining == 300_000

        await tracker.record_usage(1, 50_000)
        mock_redis.incrby.assert_called_once_with("blueprint:tokens:1", 50_000)


@pytest.mark.asyncio
async def test_cost_tracker_separate_users() -> None:
    tracker = BlueprintCostTracker(daily_cap=5_000)
    with patch("app.core.redis.get_redis", side_effect=Exception("no redis")):
        await tracker.record_usage(1, 5_000)
        assert await tracker.check_budget(1) == 0
        # User 2 unaffected
        assert await tracker.check_budget(2) == 5_000
