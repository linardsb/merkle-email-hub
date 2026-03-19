"""ESP push task — wraps connector export for Kestra orchestration."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.workflows.exceptions import WorkflowValidationError

logger = get_logger(__name__)


class ESPPushTask:
    """Wraps ESP connector export as a workflow task."""

    task_type: str = "hub.esp_push"

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        required = {"html", "connector_type", "content_block_name"}
        missing = required - inputs.keys()
        if missing:
            raise WorkflowValidationError(f"Missing required inputs: {', '.join(sorted(missing))}")
        return inputs

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_inputs(inputs)

        from app.connectors.schemas import ExportRequest
        from app.connectors.service import ConnectorService
        from app.core.database import get_db_context

        async with get_db_context() as db:
            service = ConnectorService(db)

            logger.info(
                "workflow.task.esp_push.started",
                connector_type=validated["connector_type"],
            )

            export_request = ExportRequest(
                connector_type=validated["connector_type"],
                content_block_name=validated["content_block_name"],
                build_id=validated.get("build_id"),
            )

            # Resolve the user from workflow inputs (_user_id injected by service layer)
            from app.auth.repository import UserRepository

            user_id: int | None = validated.get("_user_id")
            if user_id is None:
                raise WorkflowValidationError("ESP push requires '_user_id' in workflow context")

            user_repo = UserRepository(db)
            user = await user_repo.find_by_id(user_id)
            if user is None:
                raise WorkflowValidationError(f"User {user_id} not found for ESP push")

            result = await service.export(export_request, user)

            logger.info(
                "workflow.task.esp_push.completed",
                external_id=result.external_id,
            )

            return {
                "external_id": result.external_id,
                "status": result.status,
            }
