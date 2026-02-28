# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for client approval portal."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.approval.schemas import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalResponse,
    AuditResponse,
    FeedbackCreate,
    FeedbackResponse,
)
from app.approval.service import ApprovalService
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


def get_service(db: AsyncSession = Depends(get_db)) -> ApprovalService:  # noqa: B008
    return ApprovalService(db)


@router.post("/", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_approval(
    request: Request,
    data: ApprovalCreate,
    service: ApprovalService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ApprovalResponse:
    """Submit an email build for client approval."""
    _ = request
    return await service.create_approval(data, user_id=current_user.id)


@router.get("/{approval_id}", response_model=ApprovalResponse)
@limiter.limit("30/minute")
async def get_approval(
    request: Request,
    approval_id: int,
    service: ApprovalService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> ApprovalResponse:
    """Get an approval request by ID."""
    _ = request
    return await service.get_approval(approval_id)


@router.post("/{approval_id}/decide", response_model=ApprovalResponse)
@limiter.limit("10/minute")
async def decide_approval(
    request: Request,
    approval_id: int,
    decision: ApprovalDecision,
    service: ApprovalService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ApprovalResponse:
    """Approve, reject, or request revision on an approval."""
    _ = request
    return await service.decide(approval_id, decision, reviewer_id=current_user.id)


@router.post("/{approval_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def add_feedback(
    request: Request,
    approval_id: int,
    data: FeedbackCreate,
    service: ApprovalService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> FeedbackResponse:
    """Add feedback to an approval request."""
    _ = request
    return await service.add_feedback(approval_id, data, user_id=current_user.id)


@router.get("/{approval_id}/feedback", response_model=list[FeedbackResponse])
@limiter.limit("30/minute")
async def list_feedback(
    request: Request,
    approval_id: int,
    service: ApprovalService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[FeedbackResponse]:
    """List feedback for an approval request."""
    _ = request
    return await service.get_feedback(approval_id)


@router.get("/{approval_id}/audit", response_model=list[AuditResponse])
@limiter.limit("30/minute")
async def get_audit_trail(
    request: Request,
    approval_id: int,
    service: ApprovalService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[AuditResponse]:
    """Get the audit trail for an approval request."""
    _ = request
    return await service.get_audit_trail(approval_id)
