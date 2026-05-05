"""REST API for skill amendment review (admin-only)."""

# pyright: reportUntypedFunctionDecorator=false, reportUnknownMemberType=false

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.skills.schemas import (
    AmendmentActionRequest,
    AmendmentListResponse,
    AmendmentReport,
    BatchAmendmentRequest,
    BatchAmendmentResponse,
    StatusResponse,
)
from app.ai.skills.service import SkillExtractionService
from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.rate_limit import limiter
from app.core.scoped_db import get_scoped_db

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

_admin = require_role("admin")


def _get_service(db: AsyncSession = Depends(get_scoped_db)) -> SkillExtractionService:
    return SkillExtractionService(db)


@router.get("/amendments/pending", response_model=AmendmentListResponse)
@limiter.limit("60/minute")
async def list_pending_amendments(
    request: Request,
    agent_name: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(_admin),
    service: SkillExtractionService = Depends(_get_service),
) -> AmendmentListResponse:
    """List pending skill amendments from template uploads."""
    amendments, total = await service.list_pending(
        agent_name=agent_name, limit=limit, offset=offset
    )
    return AmendmentListResponse(amendments=amendments, total=total)


@router.post("/amendments/{amendment_id}/approve")
@limiter.limit("10/minute")
async def approve_amendment(
    request: Request,
    amendment_id: str,
    body: AmendmentActionRequest | None = None,
    _user: User = Depends(_admin),
    service: SkillExtractionService = Depends(_get_service),
) -> AmendmentReport:
    """Approve and apply a skill amendment."""
    reason = body.reason if body else ""
    return await service.approve(amendment_id, reason)


@router.post("/amendments/{amendment_id}/reject")
@limiter.limit("10/minute")
async def reject_amendment(
    request: Request,
    amendment_id: str,
    body: AmendmentActionRequest | None = None,
    _user: User = Depends(_admin),
    service: SkillExtractionService = Depends(_get_service),
) -> StatusResponse:
    """Reject a skill amendment."""
    reason = body.reason if body else ""
    await service.reject(amendment_id, reason)
    return StatusResponse(status="rejected")


@router.post("/amendments/batch", response_model=BatchAmendmentResponse)
@limiter.limit("5/minute")
async def batch_amendments(
    request: Request,
    body: BatchAmendmentRequest,
    _user: User = Depends(_admin),
    service: SkillExtractionService = Depends(_get_service),
) -> BatchAmendmentResponse:
    """Approve or reject multiple amendments at once."""
    actions = body.actions
    processed, errors = await service.batch_action(actions)
    return BatchAmendmentResponse(processed=processed, errors=errors)
