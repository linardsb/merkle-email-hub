"""Locale build task — wraps Tolgee locale builder for Kestra orchestration.

Stub until Phase 25.3 (Tolgee TMS) is fully implemented.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.workflows.exceptions import WorkflowValidationError

logger = get_logger(__name__)


class LocaleBuildTask:
    """Wraps Tolgee locale builder as a workflow task."""

    task_type: str = "hub.locale_build"

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        if not inputs.get("template_id"):
            raise WorkflowValidationError("Locale build requires 'template_id' input")
        if not inputs.get("locales"):
            raise WorkflowValidationError("Locale build requires 'locales' input")
        return inputs

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        validated = self.validate_inputs(inputs)
        locales: list[str] = validated["locales"]

        logger.info(
            "workflow.task.locale_build.started",
            template_id=validated["template_id"],
            locale_count=len(locales),
        )

        # Stub: Tolgee integration will be wired when Phase 25.3 is complete.
        # For now, return placeholder HTML per locale.
        locale_html_map: dict[str, str] = {locale: f"<!-- stub: {locale} -->" for locale in locales}

        logger.info(
            "workflow.task.locale_build.completed",
            locale_count=len(locale_html_map),
        )

        return {"locale_html": locale_html_map}
