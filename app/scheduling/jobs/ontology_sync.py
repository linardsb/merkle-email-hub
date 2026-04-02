"""Scheduled CanIEmail ontology sync.

Weekly sync of CSS property support data from the Can I Email repository.
Wraps CanIEmailSyncService and stores run results in Redis for the
notification layer (45.5).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.knowledge.ontology.sync.schemas import SyncReport
from app.knowledge.ontology.sync.service import CanIEmailSyncService
from app.scheduling.registry import scheduled_job

logger = get_logger(__name__)

_KEY_PREFIX = "scheduling:ontology_sync"
_LATEST_KEY = f"{_KEY_PREFIX}:latest"
_RESULT_TTL_SECONDS = 30 * 86400  # 30 days


@scheduled_job(cron="0 3 * * 0")
async def ontology_sync() -> None:
    """Sync CSS property support data from Can I Email, store results."""
    settings = get_settings()

    if not settings.ontology_sync.enabled:
        logger.info("ontology_sync.skipped", reason="disabled")
        return

    redis = await get_redis()
    started_at = datetime.now(UTC)

    try:
        service = CanIEmailSyncService()
        report = await service.sync(dry_run=settings.ontology_sync.dry_run)

        result = _build_result(started_at, report)
        await _store_result(redis, result)

        logger.info(
            "ontology_sync.completed",
            new_properties=report.new_properties,
            updated_levels=report.updated_levels,
            new_clients=report.new_clients,
            errors=len(report.errors),
            commit_sha=report.commit_sha,
            dry_run=report.dry_run,
            duration_ms=result["duration_ms"],
        )
    except Exception:
        logger.exception("ontology_sync.failed")
        raise


def _build_result(
    started_at: datetime,
    report: SyncReport,
) -> dict[str, Any]:
    finished_at = datetime.now(UTC)
    return {
        "sync_date": started_at.isoformat(),
        "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
        "new_properties": report.new_properties,
        "updated_levels": report.updated_levels,
        "new_clients": report.new_clients,
        "errors": report.errors,
        "commit_sha": report.commit_sha,
        "dry_run": report.dry_run,
    }


async def _store_result(redis: Redis, result: dict[str, Any]) -> None:
    """Store sync result in Redis with date key + latest pointer."""
    sync_date = str(result["sync_date"])[:10]  # YYYY-MM-DD
    date_key = f"{_KEY_PREFIX}:{sync_date}"
    payload = json.dumps(result, default=str)

    await redis.set(date_key, payload, ex=_RESULT_TTL_SECONDS)
    await redis.set(_LATEST_KEY, payload)
