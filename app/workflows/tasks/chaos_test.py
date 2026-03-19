"""Chaos test task — wraps chaos engine for Kestra orchestration."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.workflows.exceptions import WorkflowValidationError

logger = get_logger(__name__)


class ChaosTestTask:
    """Wraps chaos engine testing as a workflow task."""

    task_type: str = "hub.chaos_test"

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if not inputs.get("html"):
            raise WorkflowValidationError("Chaos test requires 'html' input")
        return inputs

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_inputs(inputs)

        from app.qa_engine.chaos.engine import ChaosEngine

        engine = ChaosEngine()
        profiles = validated.get(
            "profiles",
            [
                "gmail_style_strip",
                "image_blocked",
                "dark_mode_inversion",
            ],
        )

        logger.info("workflow.task.chaos_test.started", profile_count=len(profiles))
        results = await engine.run_chaos_test(validated["html"], profiles=profiles)
        logger.info(
            "workflow.task.chaos_test.completed",
            resilience_score=results.resilience_score,
        )

        return {
            "resilience_score": results.resilience_score,
            "failures": [f.model_dump() for f in results.critical_failures],
        }
