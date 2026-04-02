"""Tests for the CronScheduler engine."""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.core.config import SchedulingConfig
from app.scheduling.engine import CronScheduler
from app.scheduling.registry import scheduled_job


class TestStartStop:
    async def test_start_stop_clean(self, scheduling_config: SchedulingConfig) -> None:
        """Scheduler starts a background task and stops cleanly."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.exists = AsyncMock(return_value=0)
        mock_redis.hset = AsyncMock()

        with patch("app.scheduling.engine.get_redis", return_value=mock_redis):
            scheduler = CronScheduler(scheduling_config)
            await scheduler.start()
            assert scheduler._running is True
            assert scheduler._task is not None

            await scheduler.stop()
            assert scheduler._running is False
            assert scheduler._task is None


class TestEvaluateJobs:
    async def test_fires_due_job(
        self, scheduling_config: SchedulingConfig, mock_redis: AsyncMock
    ) -> None:
        """A job whose cron time has passed gets executed."""
        executed = False

        @scheduled_job(cron="* * * * *")
        async def every_minute() -> None:
            nonlocal executed
            executed = True

        # Set up Redis mock with an overdue job
        past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        job_data = {
            b"name": b"every_minute",
            b"cron_expr": b"* * * * *",
            b"callable_name": b"every_minute",
            b"enabled": b"1",
            b"last_run": past.encode(),
            b"last_status": b"success",
            b"run_count": b"3",
        }

        async def _scan_iter(match: str = "*") -> AsyncGenerator[bytes]:
            yield b"scheduling:jobs:every_minute"

        mock_redis.scan_iter = _scan_iter
        mock_redis.hgetall = AsyncMock(return_value=job_data)
        mock_redis.set = AsyncMock(return_value=True)  # Leader lock

        with patch("app.scheduling.engine.get_redis", return_value=mock_redis):
            scheduler = CronScheduler(scheduling_config)
            await scheduler._acquire_leader()
            await scheduler._evaluate_jobs()

        assert executed is True

    async def test_skips_disabled_job(
        self, scheduling_config: SchedulingConfig, mock_redis: AsyncMock
    ) -> None:
        """A disabled job is not executed."""
        executed = False

        @scheduled_job(cron="* * * * *")
        async def disabled_task() -> None:
            nonlocal executed
            executed = True

        job_data = {
            b"name": b"disabled_task",
            b"cron_expr": b"* * * * *",
            b"callable_name": b"disabled_task",
            b"enabled": b"0",
            b"last_run": b"",
            b"last_status": b"",
            b"run_count": b"0",
        }

        async def _scan_iter(match: str = "*") -> AsyncGenerator[bytes]:
            yield b"scheduling:jobs:disabled_task"

        mock_redis.scan_iter = _scan_iter
        mock_redis.hgetall = AsyncMock(return_value=job_data)

        with patch("app.scheduling.engine.get_redis", return_value=mock_redis):
            scheduler = CronScheduler(scheduling_config)
            await scheduler._evaluate_jobs()

        assert executed is False


class TestExecuteJob:
    async def test_records_success(
        self, scheduling_config: SchedulingConfig, mock_redis: AsyncMock
    ) -> None:
        """Successful job execution records success in Redis."""

        @scheduled_job(cron="* * * * *")
        async def success_task() -> None:
            pass

        mock_redis.set = AsyncMock(return_value=True)

        with patch("app.scheduling.engine.get_redis", return_value=mock_redis):
            scheduler = CronScheduler(scheduling_config)
            await scheduler._execute_job("success_task", "scheduling:jobs:success_task")

        # Check that hset was called with success status
        hset_calls = mock_redis.hset.call_args_list
        status_update = next(
            c for c in hset_calls if c.kwargs.get("mapping", {}).get("last_status") == "success"
        )
        assert status_update is not None
        mock_redis.hincrby.assert_called_once_with("scheduling:jobs:success_task", "run_count", 1)
        mock_redis.lpush.assert_called_once()

    async def test_records_failure(
        self, scheduling_config: SchedulingConfig, mock_redis: AsyncMock
    ) -> None:
        """Failed job execution records error in Redis."""

        @scheduled_job(cron="* * * * *")
        async def failing_task() -> None:
            msg = "boom"
            raise RuntimeError(msg)

        mock_redis.set = AsyncMock(return_value=True)

        with patch("app.scheduling.engine.get_redis", return_value=mock_redis):
            scheduler = CronScheduler(scheduling_config)
            await scheduler._execute_job("failing_task", "scheduling:jobs:failing_task")

        # Check that hset was called with failed status
        hset_calls = mock_redis.hset.call_args_list
        status_update = next(
            c for c in hset_calls if c.kwargs.get("mapping", {}).get("last_status") == "failed"
        )
        assert status_update is not None

        # Check run history includes error
        lpush_call = mock_redis.lpush.call_args
        run_record = json.loads(lpush_call[0][1])
        assert run_record["status"] == "failed"
        assert "boom" in run_record["error"]
