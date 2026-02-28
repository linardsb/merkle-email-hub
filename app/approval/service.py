"""Business logic for client approval portal."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.approval.exceptions import ApprovalNotFoundError
from app.approval.repository import ApprovalRepository
from app.approval.schemas import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalResponse,
    AuditResponse,
    FeedbackCreate,
    FeedbackResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ApprovalService:
    """Business logic for approval workflows."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ApprovalRepository(db)

    async def create_approval(self, data: ApprovalCreate, user_id: int) -> ApprovalResponse:
        logger.info("approval.create_started", build_id=data.build_id)
        approval = await self.repository.create(data.build_id, data.project_id, user_id)
        await self.repository.add_audit(approval.id, "submitted", user_id)
        return ApprovalResponse.model_validate(approval)

    async def get_approval(self, approval_id: int) -> ApprovalResponse:
        approval = await self.repository.get(approval_id)
        if not approval:
            raise ApprovalNotFoundError(f"Approval {approval_id} not found")
        return ApprovalResponse.model_validate(approval)

    async def decide(
        self, approval_id: int, decision: ApprovalDecision, reviewer_id: int
    ) -> ApprovalResponse:
        approval = await self.repository.get(approval_id)
        if not approval:
            raise ApprovalNotFoundError(f"Approval {approval_id} not found")
        approval = await self.repository.update_status(
            approval, decision.status, reviewer_id, decision.review_note
        )
        await self.repository.add_audit(
            approval_id, decision.status, reviewer_id, decision.review_note
        )
        logger.info("approval.decided", approval_id=approval_id, status=decision.status)
        return ApprovalResponse.model_validate(approval)

    async def add_feedback(
        self, approval_id: int, data: FeedbackCreate, user_id: int
    ) -> FeedbackResponse:
        approval = await self.repository.get(approval_id)
        if not approval:
            raise ApprovalNotFoundError(f"Approval {approval_id} not found")
        fb = await self.repository.add_feedback(
            approval_id, user_id, data.content, data.feedback_type
        )
        await self.repository.add_audit(approval_id, "feedback_added", user_id)
        return FeedbackResponse.model_validate(fb)

    async def get_feedback(self, approval_id: int) -> list[FeedbackResponse]:
        return [
            FeedbackResponse.model_validate(f)
            for f in await self.repository.get_feedback(approval_id)
        ]

    async def get_audit_trail(self, approval_id: int) -> list[AuditResponse]:
        return [
            AuditResponse.model_validate(a)
            for a in await self.repository.get_audit_trail(approval_id)
        ]
