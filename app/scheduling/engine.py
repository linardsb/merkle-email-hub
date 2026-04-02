# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportGeneralTypeIssues=false
"""Cron scheduling engine — lightweight in-process asyncio scheduler.

Evaluates registered jobs against their cron expressions every
``check_interval_seconds`` and executes due jobs.  Job definitions and
run history are persisted in Redis.  Leader election prevents duplicate
execution across multiple workers.
"""

import asyncio
import contextlib
import json
import os
from datetime import UTC, datetime

from croniter import croniter

from app.core.config import SchedulingConfig
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.scheduling.registry import get_registry
from app.scheduling.schemas import JOBS_PREFIX, LEADER_KEY, RUNS_PREFIX, JobStatus

logger = get_logger(__name__)


class CronScheduler:
    """Lightweight asyncio cron scheduler with Redis persistence."""

    def __init__(self, config: SchedulingConfig) -> None:
        self._config = config
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the scheduler background task and sync registry to Redis."""
        if self._running:
            return
        self._running = True
        await self._sync_registry()
        self._task = asyncio.create_task(self._loop())
        logger.info("scheduling.started", interval=self._config.check_interval_seconds)

    async def stop(self) -> None:
        """Stop the scheduler background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("scheduling.stopped")

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        """Main scheduler loop — sleep, acquire lock, evaluate jobs."""
        while self._running:
            try:
                if await self._acquire_leader():
                    await self._evaluate_jobs()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("scheduling.loop_error", exc_info=True)
            await asyncio.sleep(self._config.check_interval_seconds)

    # ------------------------------------------------------------------
    # Leader election
    # ------------------------------------------------------------------

    async def _acquire_leader(self) -> bool:
        """Acquire leader lock via Redis SET NX."""
        try:
            redis = await get_redis()
            leader_ttl = int(self._config.check_interval_seconds * 1.5)
            identity = str(os.getpid())
            acquired = await redis.set(LEADER_KEY, identity, nx=True, ex=leader_ttl)
            return bool(acquired)
        except Exception:
            # Redis unavailable — become leader anyway (single-worker fallback)
            return True

    # ------------------------------------------------------------------
    # Job evaluation
    # ------------------------------------------------------------------

    async def _evaluate_jobs(self) -> None:
        """Load jobs from Redis and execute any that are due."""
        try:
            redis = await get_redis()
        except Exception:
            logger.warning("scheduling.redis_unavailable")
            return

        keys: list[str] = []
        async for key in redis.scan_iter(match=f"{JOBS_PREFIX}:*"):
            if isinstance(key, bytes):
                keys.append(key.decode())
            else:
                keys.append(key)

        now = datetime.now(UTC)

        for key in keys:
            raw = await redis.hgetall(key)
            if not raw:
                continue

            # Decode bytes if needed
            data: dict[str, str] = {}
            for k, v in raw.items():
                dk = k.decode() if isinstance(k, bytes) else k
                dv = v.decode() if isinstance(v, bytes) else v
                data[dk] = dv

            if data.get("enabled") != "1":
                continue

            name = data.get("name", "")
            cron_expr = data.get("cron_expr", "")
            last_run_str = data.get("last_run", "")
            last_status = data.get("last_status", "")

            if last_status == JobStatus.running:
                continue

            base_time = (
                datetime.fromisoformat(last_run_str)
                if last_run_str
                else now.replace(hour=0, minute=0, second=0)
            )
            cron = croniter(cron_expr, base_time)
            next_run = cron.get_next(datetime)
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=UTC)

            if next_run <= now:
                await self._execute_job(name, key)

    async def _execute_job(self, name: str, redis_key: str) -> None:
        """Execute a job, recording start/end and result in Redis."""
        registry = get_registry()
        entry = registry.get(name)
        if entry is None:
            logger.warning("scheduling.callable_not_found", job=name)
            return

        callable_fn = entry[0]

        try:
            redis = await get_redis()
        except Exception:
            logger.warning("scheduling.redis_unavailable_for_run", job=name)
            return

        started_at = datetime.now(UTC)
        await redis.hset(redis_key, "last_status", JobStatus.running)

        error_msg: str | None = None
        status = JobStatus.success

        try:
            await asyncio.wait_for(
                callable_fn(),
                timeout=self._config.job_timeout_seconds,
            )
        except TimeoutError:
            status = JobStatus.failed
            error_msg = f"Job timed out after {self._config.job_timeout_seconds}s"
            logger.error("scheduling.job_timeout", job=name)
        except Exception as exc:
            status = JobStatus.failed
            error_msg = str(exc)
            logger.error("scheduling.job_failed", job=name, error=str(exc), exc_info=True)

        ended_at = datetime.now(UTC)
        duration_ms = int((ended_at - started_at).total_seconds() * 1000)

        # Update job hash
        await redis.hset(
            redis_key,
            mapping={
                "last_run": started_at.isoformat(),
                "last_status": status.value,
            },
        )
        await redis.hincrby(redis_key, "run_count", 1)

        # Append to run history
        run_record = json.dumps(
            {
                "job_name": name,
                "started_at": started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
                "status": status.value,
                "error": error_msg,
                "duration_ms": duration_ms,
            }
        )
        runs_key = f"{RUNS_PREFIX}:{name}"
        await redis.lpush(runs_key, run_record)
        await redis.ltrim(runs_key, 0, self._config.max_run_history - 1)
        await redis.expire(runs_key, self._config.run_history_ttl_seconds)

        logger.info(
            "scheduling.job_completed",
            job=name,
            status=status.value,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Registry sync
    # ------------------------------------------------------------------

    async def _sync_registry(self) -> None:
        """Sync ``_JOB_REGISTRY`` entries to Redis, preserving existing state."""
        registry = get_registry()
        if not registry:
            return

        try:
            redis = await get_redis()
        except Exception:
            logger.warning("scheduling.sync_registry_redis_unavailable")
            return

        for name, (_callable, default_cron) in registry.items():
            key = f"{JOBS_PREFIX}:{name}"
            exists = await redis.exists(key)

            if not exists:
                await redis.hset(
                    key,
                    mapping={
                        "name": name,
                        "cron_expr": default_cron,
                        "callable_name": name,
                        "enabled": "1",
                        "last_run": "",
                        "last_status": "",
                        "run_count": "0",
                    },
                )
                logger.info("scheduling.job_registered", job=name, cron=default_cron)
            else:
                # Preserve existing state, just ensure callable_name is up to date
                await redis.hset(key, "callable_name", name)
