"""Redis-backed per-user daily quota and cost tracking.

Tracks AI request counts and blueprint token usage per user with automatic
24-hour TTL expiry. Falls back to in-memory tracking when Redis is unavailable.
"""

import time
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)

_SECONDS_PER_DAY: int = 86_400


@dataclass
class _InMemoryEntry:
    """Tracks count and reset time for a single user (in-memory fallback)."""

    count: int = 0
    reset_at: float = field(default_factory=lambda: time.monotonic() + _SECONDS_PER_DAY)


class UserQuotaTracker:
    """Per-user daily quota tracker backed by Redis.

    Redis key: ``ai:quota:{user_id}`` with 24h TTL.
    Falls back to in-memory dict if Redis is unavailable.

    Args:
        daily_limit: Maximum requests per user per day.
    """

    def __init__(self, daily_limit: int) -> None:
        self._daily_limit = daily_limit
        self._fallback: dict[int, _InMemoryEntry] = {}

    async def check_and_increment(self, user_id: int) -> bool:
        """Check quota and increment if allowed. Returns True if allowed."""
        try:
            return await self._check_redis(user_id)
        except Exception:
            logger.debug("quota.redis_fallback", user_id=user_id)
            return self._check_memory(user_id)

    async def get_remaining(self, user_id: int) -> int:
        """Get remaining quota for a user."""
        try:
            return await self._remaining_redis(user_id)
        except Exception:
            return self._remaining_memory(user_id)

    # -- Redis path --

    async def _check_redis(self, user_id: int) -> bool:
        from app.core.redis import get_redis

        r = await get_redis()
        key = f"ai:quota:{user_id}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, _SECONDS_PER_DAY)
        if count > self._daily_limit:
            logger.warning(
                "ai.quota_exceeded",
                user_id=user_id,
                daily_limit=self._daily_limit,
                current_count=count,
            )
            return False
        return True

    async def _remaining_redis(self, user_id: int) -> int:
        from app.core.redis import get_redis

        r = await get_redis()
        key = f"ai:quota:{user_id}"
        raw = await r.get(key)
        if raw is None:
            return self._daily_limit
        return max(0, self._daily_limit - int(raw))

    # -- In-memory fallback --

    def _check_memory(self, user_id: int) -> bool:
        now = time.monotonic()
        entry = self._fallback.get(user_id)
        if entry is None or now >= entry.reset_at:
            self._fallback[user_id] = _InMemoryEntry(count=1, reset_at=now + _SECONDS_PER_DAY)
            return True
        if entry.count >= self._daily_limit:
            return False
        entry.count += 1
        return True

    def _remaining_memory(self, user_id: int) -> int:
        now = time.monotonic()
        entry = self._fallback.get(user_id)
        if entry is None or now >= entry.reset_at:
            return self._daily_limit
        return max(0, self._daily_limit - entry.count)


class BlueprintCostTracker:
    """Tracks daily blueprint token usage per user via Redis.

    Redis key: ``blueprint:tokens:{user_id}`` with 24h TTL.
    Falls back to in-memory dict if Redis is unavailable.

    Args:
        daily_cap: Maximum total tokens per user per day.
    """

    def __init__(self, daily_cap: int) -> None:
        self._daily_cap = daily_cap
        self._fallback: dict[int, _InMemoryEntry] = {}

    async def check_budget(self, user_id: int) -> int:
        """Return remaining token budget. 0 means cap exhausted."""
        try:
            return await self._remaining_redis(user_id)
        except Exception:
            return self._remaining_memory(user_id)

    async def record_usage(self, user_id: int, tokens: int) -> None:
        """Record token usage for a blueprint run."""
        try:
            await self._record_redis(user_id, tokens)
        except Exception:
            self._record_memory(user_id, tokens)

    # -- Redis path --

    async def _remaining_redis(self, user_id: int) -> int:
        from app.core.redis import get_redis

        r = await get_redis()
        key = f"blueprint:tokens:{user_id}"
        raw = await r.get(key)
        if raw is None:
            return self._daily_cap
        return max(0, self._daily_cap - int(raw))

    async def _record_redis(self, user_id: int, tokens: int) -> None:
        from app.core.redis import get_redis

        r = await get_redis()
        key = f"blueprint:tokens:{user_id}"
        new_total = await r.incrby(key, tokens)
        if new_total == tokens:
            await r.expire(key, _SECONDS_PER_DAY)
        if new_total > self._daily_cap:
            logger.warning(
                "blueprint.cost_cap_exceeded",
                user_id=user_id,
                total_tokens=new_total,
                daily_cap=self._daily_cap,
            )

    # -- In-memory fallback --

    def _record_memory(self, user_id: int, tokens: int) -> None:
        now = time.monotonic()
        entry = self._fallback.get(user_id)
        if entry is None or now >= entry.reset_at:
            self._fallback[user_id] = _InMemoryEntry(count=tokens, reset_at=now + _SECONDS_PER_DAY)
        else:
            entry.count += tokens

    def _remaining_memory(self, user_id: int) -> int:
        now = time.monotonic()
        entry = self._fallback.get(user_id)
        if entry is None or now >= entry.reset_at:
            return self._daily_cap
        return max(0, self._daily_cap - entry.count)
