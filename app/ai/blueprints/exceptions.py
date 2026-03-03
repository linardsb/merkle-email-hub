"""Blueprint-specific exception hierarchy.

All exceptions inherit from AIError for automatic HTTP status mapping.
"""

from app.ai.exceptions import AIError


class BlueprintError(AIError):
    """Base exception for all blueprint failures."""


class BlueprintEscalatedError(BlueprintError):
    """Self-correction rounds exhausted — human intervention required."""

    def __init__(self, node_name: str, iterations: int) -> None:
        self.node_name = node_name
        self.iterations = iterations
        super().__init__(f"Node '{node_name}' exhausted {iterations} self-correction rounds")


class BlueprintNodeError(BlueprintError):
    """A specific node failed during blueprint execution."""

    def __init__(self, node_name: str, reason: str) -> None:
        self.node_name = node_name
        super().__init__(f"Node '{node_name}' failed: {reason}")
