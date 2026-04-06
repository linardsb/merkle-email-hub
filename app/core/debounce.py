"""Distributed debounce layer using Redis.

Coalesces rapid-fire events into a single deferred execution.
Pattern: on trigger → set/reset Redis key with TTL. Background task
sleeps for window, then checks if key is still current (no newer event).
If current → execute. If superseded → exit silently.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import get_redis

log = get_logger(__name__)

# Track background tasks to prevent GC
_debounce_tasks: set[asyncio.Task[None]] = set()


class Debouncer:
    """Redis-backed debounce manager.

    Each call to ``trigger()`` resets the debounce window. After the window
    expires with no new triggers, the callback executes exactly once.
    """

    def __init__(
        self,
        key_prefix: str,
        window_ms: int,
        callback: Callable[..., Awaitable[Any]],
    ) -> None:
        self._key_prefix = key_prefix
        self._window_ms = window_ms
        self._callback = callback

    def _redis_key(self, dedup_key: str) -> str:
        return f"debounce:{self._key_prefix}:{dedup_key}"

    async def trigger(self, dedup_key: str, **kwargs: object) -> None:
        """Enqueue a debounced execution.

        Sets/resets Redis key. Spawns background worker that fires
        callback after window if no newer trigger arrives.
        """
        settings = get_settings()
        if not settings.debounce.enabled:
            # Debounce disabled — execute immediately
            await self._callback(**kwargs)
            return

        redis = await get_redis()
        rkey = self._redis_key(dedup_key)
        token = f"{uuid.uuid4().hex}:{datetime.now(UTC).isoformat()}"
        ttl_seconds = max(1, self._window_ms // 1000)

        await redis.setex(rkey, ttl_seconds + 1, token)

        task = asyncio.create_task(
            self._worker(rkey, token, kwargs),
        )
        _debounce_tasks.add(task)
        task.add_done_callback(_debounce_tasks.discard)

        log.info(
            "core.debounce_enqueued",
            key_prefix=self._key_prefix,
            dedup_key=dedup_key,
            window_ms=self._window_ms,
        )

    async def _worker(
        self,
        rkey: str,
        expected_token: str,
        kwargs: dict[str, Any],
    ) -> None:
        """Sleep for window, then execute if no newer trigger arrived."""
        await asyncio.sleep(self._window_ms / 1000 + 0.5)

        redis = await get_redis()
        current = await redis.get(rkey)

        if current is not None:
            current_str = current if isinstance(current, str) else current.decode()
            if current_str != expected_token:
                log.debug(
                    "core.debounce_superseded",
                    key_prefix=self._key_prefix,
                    rkey=rkey,
                )
                return

        # Token matched or key expired — we are the latest, execute
        try:
            await self._callback(**kwargs)
            log.info(
                "core.debounce_executed",
                key_prefix=self._key_prefix,
                rkey=rkey,
            )
        except Exception:
            log.warning(
                "core.debounce_failed",
                key_prefix=self._key_prefix,
                rkey=rkey,
                exc_info=True,
            )
