"""Feature-specific exceptions for workflow orchestration."""

from app.core.exceptions import (
    AppError,
    DomainValidationError,
    NotFoundError,
    ServiceUnavailableError,
)


class WorkflowNotFoundError(NotFoundError):
    """Raised when a workflow or execution is not found."""


class WorkflowTriggerError(AppError):
    """Raised when a workflow execution fails to start."""


class WorkflowValidationError(DomainValidationError):
    """Raised when workflow YAML or inputs fail validation."""


class KestraUnavailableError(ServiceUnavailableError):
    """Raised when the Kestra API is unreachable."""


class InvalidFlowDefinitionError(DomainValidationError):
    """Raised when a custom flow YAML uses disallowed task types."""
