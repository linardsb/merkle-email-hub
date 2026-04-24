"""API routes for the scheduling engine."""

# pyright: reportUntypedFunctionDecorator=false, reportUnknownMemberType=false

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.rate_limit import limiter
from app.scheduling import service
from app.scheduling.schemas import (
    JobDefinitionResponse,
    JobRunResponse,
    JobUpdateRequest,
)

router = APIRouter(prefix="/api/v1/scheduling", tags=["scheduling"])

_admin = require_role("admin")


@router.get("/jobs", response_model=list[JobDefinitionResponse])
@limiter.limit("30/minute")
async def list_jobs(
    request: Request,
    _user: User = Depends(_admin),
) -> list[JobDefinitionResponse]:
    """List all registered scheduled jobs."""
    return await service.list_jobs()


@router.get("/jobs/{name}", response_model=JobDefinitionResponse)
@limiter.limit("30/minute")
async def get_job(
    name: str,
    request: Request,
    _user: User = Depends(_admin),
) -> JobDefinitionResponse:
    """Get a single scheduled job by name."""
    return await service.get_job(name)


@router.patch("/jobs/{name}", response_model=JobDefinitionResponse)
@limiter.limit("10/minute")
async def update_job(
    name: str,
    body: JobUpdateRequest,
    request: Request,
    _user: User = Depends(_admin),
) -> JobDefinitionResponse:
    """Update a job (enable/disable, change cron expression)."""
    return await service.update_job(name, body)


@router.post(
    "/jobs/{name}/trigger",
    response_model=JobRunResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
async def trigger_job(
    name: str,
    request: Request,
    _user: User = Depends(_admin),
) -> JobRunResponse:
    """Manually trigger a scheduled job."""
    return await service.trigger_job(name)


@router.get("/jobs/{name}/history", response_model=list[JobRunResponse])
@limiter.limit("30/minute")
async def get_run_history(
    name: str,
    request: Request,
    _user: User = Depends(_admin),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[JobRunResponse]:
    """Get recent run history for a scheduled job."""
    return await service.get_run_history(name, limit=limit)
