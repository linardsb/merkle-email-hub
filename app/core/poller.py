"""Generic background data poller with leader election.

Provides a base class for background tasks that periodically fetch data from
external sources, enrich it, and store results in Redis. Supports leader
election to prevent duplicate work across multiple workers.

Usage:
    class WeatherPoller(DataPoller):
        async def fetch(self) -> dict:
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.weather.com/current")
                return resp.json()

        async def enrich(self, raw: dict) -> dict:
            return {**raw, "fetched_at": utcnow().isoformat()}

        async def store(self, data: dict) -> None:
            redis = await get_redis()
            await redis.setex("weather:current", 60, json.dumps(data))

    poller = WeatherPoller(name="weather", interval_seconds=30)
    await poller.start()
"""

import asyncio
from abc import ABC, abstractmethod

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)


class DataPoller(ABC):
    """Abstract base class for background data pollers with leader election.

    Subclass and implement fetch(), enrich(), and store() to create a poller
    that periodically pulls data from an external source.
    """

    def __init__(
        self,
        name: str,
        interval_seconds: int = 10,
        leader_lock_ttl: int = 60,
    ) -> None:
        self.name = name
        self.interval_seconds = interval_seconds
        self.leader_lock_ttl = leader_lock_ttl
        self._task: asyncio.Task[None] | None = None
        self._running = False

    @abstractmethod
    async def fetch(self) -> object:
        """Fetch raw data from the external source.

        Returns:
            Raw data in any format (dict, list, bytes, etc.)
        """
        ...

    async def enrich(self, raw: object) -> object:
        """Optionally enrich or transform raw data before storage.

        Override this to add computed fields, normalize data, etc.
        Default implementation passes data through unchanged.

        Args:
            raw: Raw data from fetch().

        Returns:
            Enriched data ready for storage.
        """
        return raw

    @abstractmethod
    async def store(self, data: object) -> None:
        """Store enriched data (e.g., in Redis cache).

        Args:
            data: Enriched data from enrich().
        """
        ...

    async def on_error(self, error: Exception) -> None:
        """Called when a poll cycle fails. Override for custom error handling.

        Default implementation logs the error and continues polling.
        """
        logger.error(
            f"poller.{self.name}.cycle_failed",
            error=str(error),
            error_type=type(error).__name__,
            exc_info=True,
        )

    async def _acquire_leader_lock(self) -> bool:
        """Try to acquire leader lock via Redis SET NX."""
        try:
            redis = await get_redis()
            lock_key = f"poller:{self.name}:leader"
            acquired = await redis.set(
                lock_key,
                "1",
                nx=True,
                ex=self.leader_lock_ttl,
            )
            return bool(acquired)
        except Exception:
            # Redis unavailable — become leader anyway (single-worker fallback)
            return True

    async def _renew_leader_lock(self) -> None:
        """Renew the leader lock TTL."""
        try:
            redis = await get_redis()
            lock_key = f"poller:{self.name}:leader"
            await redis.expire(lock_key, self.leader_lock_ttl)
        except Exception:
            logger.debug("poller.renew_lock_failed", poller=self.name)

    async def _poll_loop(self) -> None:
        """Main polling loop with leader election."""
        logger.info(f"poller.{self.name}.started", interval=self.interval_seconds)

        while self._running:
            try:
                if not await self._acquire_leader_lock():
                    await asyncio.sleep(self.interval_seconds)
                    continue

                raw = await self.fetch()
                enriched = await self.enrich(raw)
                await self.store(enriched)
                await self._renew_leader_lock()

                logger.debug(f"poller.{self.name}.cycle_completed")
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.on_error(e)

            await asyncio.sleep(self.interval_seconds)

        logger.info(f"poller.{self.name}.stopped")

    async def start(self) -> None:
        """Start the polling background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop the polling background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
