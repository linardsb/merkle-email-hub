"""Blueprint run task — wraps BlueprintService.run() for Kestra orchestration."""

from __future__ import annotations

from typing import Any

from app.ai.blueprints.schemas import BlueprintRunRequest
from app.ai.blueprints.service import get_blueprint_service
from app.core.logging import get_logger
from app.workflows.exceptions import WorkflowValidationError

logger = get_logger(__name__)


class BlueprintRunTask:
    """Wraps blueprint execution as a workflow task."""

    task_type: str = "hub.blueprint_run"

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        required = {"brief", "blueprint_name"}
        missing = required - inputs.keys()
        if missing:
            raise WorkflowValidationError(f"Missing required inputs: {', '.join(sorted(missing))}")
        return inputs

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_inputs(inputs)
        service = get_blueprint_service()

        request = BlueprintRunRequest(
            brief=validated["brief"],
            blueprint_name=validated["blueprint_name"],
            options=validated.get("options", {}),
            persona_ids=validated.get("persona_ids", []),
        )

        logger.info("workflow.task.blueprint_run.started", blueprint=request.blueprint_name)

        result = await service.run(
            request=request,
            user_id=validated.get("user_id"),
            db=None,  # Task uses its own session
        )

        logger.info(
            "workflow.task.blueprint_run.completed",
            run_id=result.run_id,
            qa_passed=result.qa_passed,
        )

        return {
            "run_id": result.run_id,
            "html": result.html,
            "qa_passed": result.qa_passed,
            "status": result.status,
        }
