"""Base protocol for Hub workflow tasks."""

from __future__ import annotations

from typing import Any, Protocol


class HubTask(Protocol):
    """Interface for Hub-specific Kestra task wrappers."""

    task_type: str  # e.g. "hub.blueprint_run"

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute the task with validated inputs, return outputs."""
        ...

    def validate_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize task inputs. Raises WorkflowValidationError."""
        ...
