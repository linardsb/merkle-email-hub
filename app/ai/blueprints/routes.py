# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Blueprint API routes — synchronous run endpoint for v1."""

import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import distinct, func, literal, select, type_coerce
from sqlalchemy.dialects.postgresql import JSONB as JSONB_TYPE
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.ai.blueprints.checkpoint_models import BlueprintCheckpoint
from app.ai.blueprints.schemas import (
    BlueprintResumeRequest,
    BlueprintRunListResponse,
    BlueprintRunRecord,
    BlueprintRunRequest,
    BlueprintRunResponse,
    CheckpointListResponse,
    CheckpointResponse,
    FailurePatternListResponse,
    FailurePatternResponse,
    FailurePatternStats,
)
from app.ai.blueprints.service import get_blueprint_service
from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.core.scoped_db import get_scoped_db
from app.memory.models import MemoryEntry

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprints"])


@router.post(
    "/run",
    response_model=BlueprintRunResponse,
    dependencies=[Depends(require_role("admin", "developer"))],
)
@limiter.limit("3/minute")
async def run_blueprint(
    request: Request,
    body: BlueprintRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_scoped_db),
) -> BlueprintRunResponse:
    """Execute a named blueprint and return the full run result.

    Synchronous for v1 — progress is included in the response body.
    """
    service = get_blueprint_service()
    return await service.run(body, user_id=current_user.id, db=db)


@router.post(
    "/resume",
    response_model=BlueprintRunResponse,
    dependencies=[Depends(require_role("admin", "developer"))],
)
@limiter.limit("3/minute")
async def resume_blueprint(
    request: Request,
    body: BlueprintResumeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_scoped_db),
) -> BlueprintRunResponse:
    """Resume a blueprint run from its latest checkpoint."""
    service = get_blueprint_service()
    return await service.resume(body, user_id=current_user.id, db=db)


def _build_failure_pattern_query(
    project_id: int | None,
    agent_name: str | None,
    qa_check: str | None,
    client_id: str | None,
) -> Select[Any]:
    """Build the base query for failure pattern memory entries."""
    query = select(MemoryEntry).where(
        MemoryEntry.memory_type == "semantic",
        MemoryEntry.metadata_json["source"].astext == "failure_pattern",  # pyright: ignore[reportIndexIssue,reportUnknownMemberType]
    )
    if project_id is not None:
        query = query.where(MemoryEntry.project_id == project_id)
    if agent_name is not None:
        query = query.where(MemoryEntry.agent_type == agent_name)
    if qa_check is not None:
        query = query.where(
            MemoryEntry.metadata_json["qa_check"].astext == qa_check  # pyright: ignore[reportIndexIssue,reportUnknownMemberType]
        )
    if client_id is not None:
        # Use proper JSON parameter binding — never interpolate user input into JSON literals
        query = query.where(
            MemoryEntry.metadata_json["client_ids"].contains(  # pyright: ignore[reportIndexIssue,reportUnknownMemberType]
                type_coerce(json.dumps([client_id]), JSONB_TYPE)
            )
        )
    return query


@router.get(
    "/failure-patterns/stats",
    response_model=FailurePatternStats,
    dependencies=[Depends(require_role("admin", "developer", "viewer"))],
)
@limiter.limit("30/minute")
async def get_failure_pattern_stats(
    request: Request,
    project_id: int | None = None,
    agent_name: str | None = None,
    qa_check: str | None = None,
    client_id: str | None = None,
    db: AsyncSession = Depends(get_scoped_db),
    _current_user: User = Depends(get_current_user),
) -> FailurePatternStats:
    """Aggregated failure pattern statistics with optional filters."""
    base = _build_failure_pattern_query(project_id, agent_name, qa_check, client_id)
    sub = base.subquery()

    # Single SQL query for all aggregations — no full-table scan into Python
    agg_q = select(
        func.count(literal(1)).label("total"),
        func.count(distinct(sub.c.agent_type)).label("unique_agents"),
    ).select_from(sub)
    agg_result = await db.execute(agg_q)
    row = agg_result.one()
    total_patterns: int = row.total  # pyright: ignore[reportAttributeAccessIssue]
    unique_agents: int = row.unique_agents  # pyright: ignore[reportAttributeAccessIssue]

    if total_patterns == 0:
        return FailurePatternStats(total_patterns=0, unique_agents=0, unique_checks=0)

    # Distinct qa_checks + top agent/check via subqueries (avoids loading all rows)
    check_col = sub.c.metadata_json["qa_check"].astext  # pyright: ignore[reportIndexIssue]
    unique_checks_q = select(func.count(distinct(check_col))).select_from(sub)
    unique_checks_result = await db.execute(unique_checks_q)
    unique_checks: int = unique_checks_result.scalar_one()

    # Top agent: most frequent agent_type
    top_agent_q = (
        select(sub.c.agent_type)
        .select_from(sub)
        .group_by(sub.c.agent_type)
        .order_by(func.count(literal(1)).desc())
        .limit(1)
    )
    top_agent_result = await db.execute(top_agent_q)
    top_agent: str | None = top_agent_result.scalar_one_or_none()

    # Top check: most frequent qa_check
    top_check_q = (
        select(check_col.label("qc"))
        .select_from(sub)
        .where(check_col.is_not(None))
        .group_by(check_col)
        .order_by(func.count(literal(1)).desc())
        .limit(1)
    )
    top_check_result = await db.execute(top_check_q)
    top_check: str | None = top_check_result.scalar_one_or_none()

    logger.info(
        "blueprints.failure_patterns_stats_fetched",
        total=total_patterns,
        unique_agents=unique_agents,
    )

    return FailurePatternStats(
        total_patterns=total_patterns,
        unique_agents=unique_agents,
        unique_checks=unique_checks,
        top_agent=top_agent,
        top_check=top_check,
    )


@router.get(
    "/failure-patterns",
    response_model=FailurePatternListResponse,
    dependencies=[Depends(require_role("admin", "developer", "viewer"))],
)
@limiter.limit("30/minute")
async def list_failure_patterns(
    request: Request,
    project_id: int | None = None,
    agent_name: str | None = None,
    qa_check: str | None = None,
    client_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_scoped_db),
    _current_user: User = Depends(get_current_user),
) -> FailurePatternListResponse:
    """List failure patterns from blueprint runs with optional filters."""
    query = _build_failure_pattern_query(project_id, agent_name, qa_check, client_id)

    # Count total matching rows
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    # Fetch paginated results
    query = query.order_by(MemoryEntry.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    entries = list(result.scalars().all())

    items: list[FailurePatternResponse] = []
    for entry in entries:
        meta = entry.metadata_json or {}
        content = entry.content or ""

        # Extract workaround from content — stored as "Agent context: ..." by
        # _format_pattern_for_memory() in failure_patterns.py
        workaround = ""
        for segment in content.split(". "):
            if segment.strip().startswith("Agent context:"):
                workaround = segment.split(":", 1)[1].strip()
                break

        items.append(
            FailurePatternResponse(
                id=entry.id,
                agent_name=entry.agent_type,
                qa_check=meta.get("qa_check", ""),
                client_ids=meta.get("client_ids", []),
                description=content,
                workaround=workaround,
                confidence=meta.get("confidence"),
                run_id=meta.get("run_id", ""),
                blueprint_name=meta.get("blueprint_name", ""),
                first_seen=entry.created_at,
                last_seen=entry.updated_at,
                frequency=1,
            )
        )

    logger.info(
        "blueprints.failure_patterns_listed",
        total=total,
        page=page,
        page_size=page_size,
    )

    return FailurePatternListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/runs/{run_id}/checkpoints",
    response_model=CheckpointListResponse,
    dependencies=[Depends(require_role("admin", "developer"))],
)
@limiter.limit("30/minute")
async def list_run_checkpoints(
    request: Request,
    run_id: str,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_scoped_db),
) -> CheckpointListResponse:
    """List all checkpoints for a blueprint run, ordered by node_index."""
    stmt = (
        select(BlueprintCheckpoint)
        .where(BlueprintCheckpoint.run_id == run_id)
        .order_by(BlueprintCheckpoint.node_index.asc())
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    items = [
        CheckpointResponse(
            node_name=row.node_name,
            node_index=row.node_index,
            status=row.state_json.get("status", "unknown"),
            html_hash=row.html_hash,
            created_at=row.created_at,  # pyright: ignore[reportArgumentType]
        )
        for row in rows
    ]

    logger.info(
        "blueprints.checkpoints_listed",
        extra={"run_id": run_id, "count": len(items)},
    )

    return CheckpointListResponse(
        run_id=run_id,
        checkpoints=items,
        count=len(items),
    )


# ── Blueprint run history (derived from checkpoints) ──

# Separate router for project-scoped blueprint runs
runs_router = APIRouter(tags=["blueprints"])


def _checkpoint_to_run_record(
    rows: list[BlueprintCheckpoint],
) -> BlueprintRunRecord:
    """Aggregate a set of checkpoints (same run_id) into a BlueprintRunRecord."""
    first = rows[0]
    last = rows[-1]
    state = last.state_json or {}

    model_usage = state.get("model_usage", {})
    total_tokens = int(model_usage.get("total_tokens", 0))

    # Duration: difference between first and last checkpoint timestamps
    duration_ms = 0
    if first.created_at and last.created_at:
        delta = last.created_at - first.created_at
        duration_ms = int(delta.total_seconds() * 1000)

    return BlueprintRunRecord(
        id=first.id,
        run_id=first.run_id,
        project_id=state.get("project_id"),
        blueprint_name=first.blueprint_name,
        brief_excerpt="",
        status=state.get("status", "unknown"),
        qa_passed=state.get("qa_passed"),
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        created_at=first.created_at,  # pyright: ignore[reportArgumentType]
        checkpoint_count=len(rows),
        resumed_from=state.get("resumed_from"),
    )


@runs_router.get(
    "/api/v1/projects/{project_id}/blueprint-runs",
    response_model=BlueprintRunListResponse,
    dependencies=[Depends(require_role("admin", "developer", "viewer"))],
)
@limiter.limit("30/minute")
async def list_blueprint_runs(
    request: Request,
    project_id: int,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_scoped_db),
) -> BlueprintRunListResponse:
    """List blueprint runs for a project, derived from checkpoint data."""
    from app.projects.service import ProjectService

    await ProjectService(db).verify_project_access(project_id, current_user)

    # Load all checkpoints grouped by run_id, then build records.
    # Checkpoint tables are bounded (max ~25 per run * N runs) so this is safe.
    base_q = select(BlueprintCheckpoint).order_by(
        BlueprintCheckpoint.run_id,
        BlueprintCheckpoint.node_index.asc(),
    )
    result = await db.execute(base_q)
    all_rows = list(result.scalars().all())

    # Group by run_id
    runs_map: dict[str, list[BlueprintCheckpoint]] = {}
    for row in all_rows:
        runs_map.setdefault(row.run_id, []).append(row)

    # Build records with project_id and status filtering
    records: list[BlueprintRunRecord] = []
    for rows in runs_map.values():
        record = _checkpoint_to_run_record(rows)
        if record.project_id is not None and record.project_id != project_id:
            continue
        if status and status != "all" and record.status != status:
            continue
        records.append(record)

    # Sort by created_at descending, then paginate
    records.sort(key=lambda r: r.created_at, reverse=True)
    total = len(records)
    start = (page - 1) * page_size
    page_items = records[start : start + page_size]

    logger.info(
        "blueprints.runs_listed",
        project_id=project_id,
        total=total,
        page=page,
    )

    return BlueprintRunListResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@runs_router.get(
    "/api/v1/blueprint-runs/{run_id}",
    response_model=BlueprintRunRecord,
    dependencies=[Depends(require_role("admin", "developer", "viewer"))],
)
@limiter.limit("30/minute")
async def get_blueprint_run(
    request: Request,
    run_id: int,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_scoped_db),
) -> BlueprintRunRecord:
    """Get a single blueprint run detail by checkpoint ID."""
    # The frontend uses a numeric ID (first checkpoint ID for the run)
    stmt = select(BlueprintCheckpoint).where(BlueprintCheckpoint.id == run_id)
    result = await db.execute(stmt)
    first_cp = result.scalar_one_or_none()
    if not first_cp:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(f"Blueprint run {run_id} not found")

    # Fetch all checkpoints for this run_id
    all_stmt = (
        select(BlueprintCheckpoint)
        .where(BlueprintCheckpoint.run_id == first_cp.run_id)
        .order_by(BlueprintCheckpoint.node_index.asc())
    )
    all_result = await db.execute(all_stmt)
    rows = list(all_result.scalars().all())

    return _checkpoint_to_run_record(rows)
