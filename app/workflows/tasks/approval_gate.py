"""Approval gate task — creates approval request for Kestra pause integration."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.workflows.exceptions import WorkflowValidationError

logger = get_logger(__name__)


class ApprovalGateTask:
    """Creates an approval request; Kestra flow pauses until webhook fires."""

    task_type: str = "hub.approval_gate"

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        required = {"project_id", "build_id"}
        missing = required - inputs.keys()
        if missing:
            raise WorkflowValidationError(
                f"Approval gate requires inputs: {', '.join(sorted(missing))}"
            )
        return inputs

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_inputs(inputs)

        from app.approval.schemas import ApprovalCreate
        from app.approval.service import ApprovalService
        from app.auth.models import User
        from app.core.scoped_db import get_system_db_context

        async with get_system_db_context() as db:
            service = ApprovalService(db)

            logger.info(
                "workflow.task.approval_gate.started",
                project_id=validated["project_id"],
            )

            data = ApprovalCreate(
                build_id=validated["build_id"],
                project_id=validated["project_id"],
            )

            # Workflow tasks run as system — fetch or create a system user
            user_id: int = validated.get("user_id", 0)
            user = await db.get(User, user_id)
            if user is None:
                raise WorkflowValidationError(f"User {user_id} not found for approval gate")

            approval = await service.create_approval(data, user)

            logger.info(
                "workflow.task.approval_gate.created",
                approval_id=approval.id,
            )

            return {
                "approval_id": approval.id,
                "status": "pending",
            }
