"""Hub workflow task registry."""

from __future__ import annotations

from typing import Any

from app.workflows.tasks.approval_gate import ApprovalGateTask
from app.workflows.tasks.blueprint_run import BlueprintRunTask
from app.workflows.tasks.chaos_test import ChaosTestTask
from app.workflows.tasks.esp_push import ESPPushTask
from app.workflows.tasks.locale_build import LocaleBuildTask
from app.workflows.tasks.qa_check import QACheckTask

TASK_REGISTRY: dict[str, Any] = {
    "hub.blueprint_run": BlueprintRunTask,
    "hub.qa_check": QACheckTask,
    "hub.chaos_test": ChaosTestTask,
    "hub.esp_push": ESPPushTask,
    "hub.locale_build": LocaleBuildTask,
    "hub.approval_gate": ApprovalGateTask,
}

ALLOWED_TASK_TYPES: frozenset[str] = frozenset(TASK_REGISTRY.keys())
