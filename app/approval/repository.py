"""Data access layer for approval portal."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.approval.models import ApprovalRequest, AuditEntry, Feedback
from app.core.scoped_db import scoped_access


class ApprovalRepository:
    """Database operations for approval requests."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, approval_id: int) -> ApprovalRequest | None:
        access = scoped_access(self.db)
        query = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        if access.project_ids is not None:
            query = query.where(ApprovalRequest.project_id.in_(access.project_ids))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_by_build_id(self, build_id: int) -> ApprovalRequest | None:
        """Get the most recent approval request for a build."""
        access = scoped_access(self.db)
        query = (
            select(ApprovalRequest)
            .where(ApprovalRequest.build_id == build_id)
            .where(ApprovalRequest.deleted_at.is_(None))
            .order_by(ApprovalRequest.created_at.desc())
            .limit(1)
        )
        if access.project_ids is not None:
            query = query.where(ApprovalRequest.project_id.in_(access.project_ids))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: int) -> list[ApprovalRequest]:
        access = scoped_access(self.db)
        query = (
            select(ApprovalRequest)
            .where(ApprovalRequest.project_id == project_id)
            .where(ApprovalRequest.deleted_at.is_(None))
            .order_by(ApprovalRequest.created_at.desc())
        )
        if access.project_ids is not None:
            query = query.where(ApprovalRequest.project_id.in_(access.project_ids))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, build_id: int, project_id: int, user_id: int) -> ApprovalRequest:
        approval = ApprovalRequest(
            build_id=build_id, project_id=project_id, requested_by_id=user_id
        )
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def update_status(
        self, approval: ApprovalRequest, status: str, reviewer_id: int, note: str | None
    ) -> ApprovalRequest:
        approval.status = status
        approval.reviewed_by_id = reviewer_id
        approval.review_note = note
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def add_feedback(
        self, approval_id: int, author_id: int, content: str, feedback_type: str
    ) -> Feedback:
        fb = Feedback(
            approval_id=approval_id,
            author_id=author_id,
            content=content,
            feedback_type=feedback_type,
        )
        self.db.add(fb)
        await self.db.commit()
        await self.db.refresh(fb)
        return fb

    async def get_feedback(self, approval_id: int) -> list[Feedback]:
        result = await self.db.execute(
            select(Feedback)
            .where(Feedback.approval_id == approval_id)
            .order_by(Feedback.created_at)
        )
        return list(result.scalars().all())

    async def add_audit(
        self, approval_id: int, action: str, actor_id: int, details: str | None = None
    ) -> AuditEntry:
        entry = AuditEntry(
            approval_id=approval_id, action=action, actor_id=actor_id, details=details
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_audit_trail(self, approval_id: int) -> list[AuditEntry]:
        result = await self.db.execute(
            select(AuditEntry)
            .where(AuditEntry.approval_id == approval_id)
            .order_by(AuditEntry.created_at)
        )
        return list(result.scalars().all())
