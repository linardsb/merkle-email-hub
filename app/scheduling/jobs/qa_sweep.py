"""Scheduled QA sweep across active templates.

Runs configured QA checks on the latest version of every active template,
detects score regressions against the previous sweep, and stores results
in Redis for the notification layer (45.5).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.core.config import get_settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.qa_engine.schemas import QARunRequest
from app.qa_engine.service import QAEngineService
from app.scheduling.registry import scheduled_job
from app.templates.models import Template, TemplateVersion

logger = get_logger(__name__)

_SWEEP_KEY_PREFIX = "scheduling:qa_sweep"
_LATEST_KEY = f"{_SWEEP_KEY_PREFIX}:latest"
_RESULT_TTL_SECONDS = 30 * 86400  # 30 days


@scheduled_job(cron="0 6 * * *")
async def qa_sweep() -> None:
    """Run QA checks on all active project templates, detect regressions."""
    settings = get_settings()
    redis = await get_redis()
    threshold = settings.scheduling.qa_sweep_regression_threshold
    check_names = set(settings.scheduling.qa_sweep_checks)
    started_at = datetime.now(UTC)

    # 1. Load previous sweep baseline from Redis
    prev_raw = await redis.get(_LATEST_KEY)
    prev_scores: dict[str, dict[str, float]] = json.loads(prev_raw) if prev_raw else {}

    # 2. Query active templates with their latest version (highest version_number)
    templates_with_versions: list[tuple[Template, TemplateVersion]] = []
    async with get_db_context() as db:
        # Subquery: max version_number per template
        latest_version_sq = (
            select(
                TemplateVersion.template_id,
                TemplateVersion.version_number,
            )
            .distinct(TemplateVersion.template_id)
            .order_by(TemplateVersion.template_id, TemplateVersion.version_number.desc())
            .subquery()
        )
        stmt = (
            select(Template, TemplateVersion)
            .join(TemplateVersion, TemplateVersion.template_id == Template.id)
            .join(
                latest_version_sq,
                (TemplateVersion.template_id == latest_version_sq.c.template_id)
                & (TemplateVersion.version_number == latest_version_sq.c.version_number),
            )
            .where(
                Template.deleted_at.is_(None),
                Template.status != "archived",
            )
            .options(
                load_only(Template.id, Template.name, Template.project_id, Template.status),
            )
        )
        rows = (await db.execute(stmt)).all()
        templates_with_versions = [(row[0], row[1]) for row in rows]

    total_templates = len(templates_with_versions)
    logger.info("qa_sweep.started", total_templates=total_templates)

    if total_templates == 0:
        # Store empty result and exit
        result = _build_result(started_at, 0, [], {})
        await _store_result(redis, result)
        logger.info("qa_sweep.completed", total_templates=0, regressions=0)
        return

    # 3. Run QA checks (bounded concurrency)
    sem = asyncio.Semaphore(5)
    current_scores: dict[str, dict[str, float]] = {}
    regressions: list[dict[str, Any]] = []
    template_names: dict[str, str] = {}
    template_projects: dict[str, int | None] = {}

    async def check_one(template: Template, version: TemplateVersion) -> None:
        key = f"tmpl:{template.id}"
        template_names[key] = template.name
        template_projects[key] = template.project_id
        try:
            async with sem:
                async with get_db_context() as db:
                    svc = QAEngineService(db)
                    req = QARunRequest(
                        html=version.html_source,
                        template_version_id=version.id,
                        project_id=template.project_id,
                    )
                    result = await svc.run_checks(req)

            # Extract scores for configured checks only
            scores: dict[str, float] = {}
            for check in result.checks:
                if check.check_name in check_names:
                    scores[check.check_name] = check.score
            current_scores[key] = scores
        except Exception:
            logger.exception("qa_sweep.template_failed", template_id=template.id)

    await asyncio.gather(*(check_one(t, v) for t, v in templates_with_versions))

    # 4. Detect regressions
    for key, scores in current_scores.items():
        prev = prev_scores.get(key, {})
        for check_name, current_score in scores.items():
            previous_score = prev.get(check_name)
            if previous_score is None:
                continue
            delta = previous_score - current_score
            if delta > threshold:
                regression = {
                    "template_id": int(key.split(":")[1]),
                    "template_name": template_names.get(key, ""),
                    "project_id": template_projects.get(key),
                    "check_name": check_name,
                    "previous_score": previous_score,
                    "current_score": current_score,
                    "delta": round(-delta, 4),
                }
                regressions.append(regression)
                logger.warning(
                    "qa_sweep.regression_detected",
                    **regression,
                )

    # 5. Store results in Redis
    result = _build_result(started_at, total_templates, regressions, current_scores)
    await _store_result(redis, result)

    logger.info(
        "qa_sweep.completed",
        total_templates=total_templates,
        regressions=len(regressions),
        duration_ms=int((datetime.now(UTC) - started_at).total_seconds() * 1000),
    )


def _build_result(
    started_at: datetime,
    total_templates: int,
    regressions: list[dict[str, Any]],
    scores: dict[str, dict[str, float]],
) -> dict[str, Any]:
    finished_at = datetime.now(UTC)
    return {
        "sweep_date": started_at.isoformat(),
        "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
        "total_templates": total_templates,
        "regressions": regressions,
        "scores": scores,
    }


async def _store_result(redis: Redis, result: dict[str, Any]) -> None:
    """Store sweep result in Redis with date key + latest pointer."""
    sweep_date = str(result["sweep_date"])[:10]  # YYYY-MM-DD
    date_key = f"{_SWEEP_KEY_PREFIX}:{sweep_date}"
    payload = json.dumps(result, default=str)

    # Store dated result with TTL
    await redis.set(date_key, payload, ex=_RESULT_TTL_SECONDS)
    # Update latest scores for next sweep's baseline
    await redis.set(_LATEST_KEY, json.dumps(result["scores"]))


if __name__ == "__main__":
    asyncio.run(qa_sweep())  # type: ignore[arg-type]
