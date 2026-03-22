"""Export approval gate — checks approval status before ESP export."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.approval_gate_schemas import ApprovalGateResult
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExportApprovalGate:
    """Evaluates approval status for export gate."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def evaluate(self, build_id: int | None, project_id: int | None) -> ApprovalGateResult:
        """Check if build has required approval for export."""
        # No build_id → template_version export, skip approval
        if build_id is None:
            return ApprovalGateResult(required=False, passed=True)

        # Check if project requires approval
        if not await self._project_requires_approval(project_id):
            return ApprovalGateResult(required=False, passed=True)

        # Look up latest approval for this build
        from app.approval.repository import ApprovalRepository

        repo = ApprovalRepository(self.db)
        approval = await repo.get_latest_by_build_id(build_id)

        if approval is None:
            return ApprovalGateResult(
                required=True,
                passed=False,
                reason="No approval request submitted",
            )

        status_map = {
            "pending": "Approval pending review",
            "revision_requested": "Revisions requested",
            "rejected": "Approval rejected",
        }
        if approval.status in status_map:
            return ApprovalGateResult(
                required=True,
                passed=False,
                approval_id=approval.id,
                reason=status_map[approval.status],
            )

        # approved
        return ApprovalGateResult(
            required=True,
            passed=True,
            approval_id=approval.id,
            approved_by=str(approval.reviewed_by_id),
            approved_at=approval.updated_at,  # pyright: ignore[reportArgumentType]
        )

    async def _project_requires_approval(self, project_id: int | None) -> bool:
        """Check if the project has require_approval_for_export enabled."""
        if project_id is None:
            return False
        from app.projects.models import Project

        result = await self.db.execute(
            select(Project.require_approval_for_export).where(Project.id == project_id)
        )
        value = result.scalar_one_or_none()
        return bool(value)
