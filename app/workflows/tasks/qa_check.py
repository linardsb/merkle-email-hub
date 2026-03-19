"""QA check task — wraps QAEngineService.run_checks() for Kestra orchestration."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.workflows.exceptions import WorkflowValidationError

logger = get_logger(__name__)


class QACheckTask:
    """Wraps QA engine checks as a workflow task."""

    task_type: str = "hub.qa_check"

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if not inputs.get("html"):
            raise WorkflowValidationError("QA check requires 'html' input")
        return inputs

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_inputs(inputs)

        from app.core.database import get_db_context
        from app.qa_engine.schemas import QARunRequest
        from app.qa_engine.service import QAEngineService

        async with get_db_context() as db:
            service = QAEngineService(db)
            request = QARunRequest(
                html=validated["html"],
                project_id=validated.get("project_id"),
            )

            logger.info("workflow.task.qa_check.started")
            result = await service.run_checks(request)
            logger.info(
                "workflow.task.qa_check.completed",
                score=result.overall_score,
                passed=result.passed,
            )

            return {
                "passed": result.passed,
                "overall_score": result.overall_score,
                "check_results": [r.model_dump() for r in result.checks],
            }
