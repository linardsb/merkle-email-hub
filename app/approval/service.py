"""Business logic for client approval portal."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.approval.exceptions import ApprovalNotFoundError
from app.approval.models import ApprovalRequest
from app.approval.repository import ApprovalRepository
from app.approval.schemas import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalResponse,
    AuditResponse,
    FeedbackCreate,
    FeedbackResponse,
)
from app.auth.models import User
from app.core.logging import get_logger
from app.projects.service import ProjectService

logger = get_logger(__name__)


class ApprovalService:
    """Business logic for approval workflows."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ApprovalRepository(db)

    async def _verify_approval_access(self, approval_id: int, user: User) -> ApprovalRequest:
        """Fetch approval and verify user has access to its project."""
        approval = await self.repository.get(approval_id)
        if not approval:
            raise ApprovalNotFoundError(f"Approval {approval_id} not found")
        project_service = ProjectService(self.db)
        await project_service.verify_project_access(approval.project_id, user)
        return approval

    async def create_approval(self, data: ApprovalCreate, user: User) -> ApprovalResponse:
        logger.info("approval.create_started", build_id=data.build_id)
        project_service = ProjectService(self.db)
        await project_service.verify_project_access(data.project_id, user)
        approval = await self.repository.create(data.build_id, data.project_id, user.id)
        await self.repository.add_audit(approval.id, "submitted", user.id)
        return ApprovalResponse.model_validate(approval)

    async def get_approval(self, approval_id: int, user: User) -> ApprovalResponse:
        approval = await self._verify_approval_access(approval_id, user)
        return ApprovalResponse.model_validate(approval)

    async def decide(
        self, approval_id: int, decision: ApprovalDecision, user: User
    ) -> ApprovalResponse:
        approval = await self._verify_approval_access(approval_id, user)
        approval = await self.repository.update_status(
            approval, decision.status, user.id, decision.review_note
        )
        await self.repository.add_audit(approval_id, decision.status, user.id, decision.review_note)
        logger.info("approval.decided", approval_id=approval_id, status=decision.status)
        return ApprovalResponse.model_validate(approval)

    async def add_feedback(
        self, approval_id: int, data: FeedbackCreate, user: User
    ) -> FeedbackResponse:
        await self._verify_approval_access(approval_id, user)
        fb = await self.repository.add_feedback(
            approval_id, user.id, data.content, data.feedback_type
        )
        await self.repository.add_audit(approval_id, "feedback_added", user.id)
        return FeedbackResponse.model_validate(fb)

    async def list_by_project(self, project_id: int, user: User) -> list[ApprovalResponse]:
        """List approval requests for a project."""
        project_service = ProjectService(self.db)
        await project_service.verify_project_access(project_id, user)
        approvals = await self.repository.list_by_project(project_id)
        return [ApprovalResponse.model_validate(a) for a in approvals]

    async def get_feedback(self, approval_id: int, user: User) -> list[FeedbackResponse]:
        await self._verify_approval_access(approval_id, user)
        return [
            FeedbackResponse.model_validate(f)
            for f in await self.repository.get_feedback(approval_id)
        ]

    async def get_audit_trail(self, approval_id: int, user: User) -> list[AuditResponse]:
        await self._verify_approval_access(approval_id, user)
        return [
            AuditResponse.model_validate(a)
            for a in await self.repository.get_audit_trail(approval_id)
        ]
