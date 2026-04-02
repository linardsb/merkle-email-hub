"""Scheduled rendering baseline regeneration.

Biweekly regeneration of visual regression baselines using the golden
template library and all configured email client profiles.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.rendering.tests.visual_regression.baseline_generator import BaselineGenerator
from app.rendering.tests.visual_regression.schemas import BaselineManifest
from app.scheduling.registry import scheduled_job

logger = get_logger(__name__)

_KEY_PREFIX = "scheduling:rendering_baselines"
_LATEST_KEY = f"{_KEY_PREFIX}:latest"
_RESULT_TTL_SECONDS = 30 * 86400  # 30 days


@scheduled_job(cron="0 4 1,15 * *")
async def rendering_baselines() -> None:
    """Regenerate visual regression baselines for golden templates."""
    settings = get_settings()

    if settings.rendering.provider == "mock":
        logger.info("rendering_baselines.skipped", reason="mock_provider")
        return

    redis = await get_redis()
    started_at = datetime.now(UTC)

    try:
        generator = BaselineGenerator()
        manifest = await generator.generate_baselines()

        result = _build_result(started_at, manifest)
        await _store_result(redis, result)

        logger.info(
            "rendering_baselines.completed",
            baseline_count=len(manifest.baselines),
            template_slugs=manifest.template_slugs,
            profile_ids=manifest.profile_ids,
            duration_ms=result["duration_ms"],
        )
    except Exception:
        logger.exception("rendering_baselines.failed")
        raise


def _build_result(
    started_at: datetime,
    manifest: BaselineManifest,
) -> dict[str, Any]:
    finished_at = datetime.now(UTC)
    return {
        "regen_date": started_at.isoformat(),
        "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
        "baseline_count": len(manifest.baselines),
        "template_slugs": manifest.template_slugs,
        "profile_ids": manifest.profile_ids,
        "emulator_versions": manifest.emulator_versions,
    }


async def _store_result(redis: Redis, result: dict[str, Any]) -> None:
    """Store baseline result in Redis with date key + latest pointer."""
    regen_date = str(result["regen_date"])[:10]  # YYYY-MM-DD
    date_key = f"{_KEY_PREFIX}:{regen_date}"
    payload = json.dumps(result, default=str)

    await redis.set(date_key, payload, ex=_RESULT_TTL_SECONDS)
    await redis.set(_LATEST_KEY, payload)
