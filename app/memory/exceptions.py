"""Memory module exceptions."""

from app.core.exceptions import AppError, DomainValidationError, NotFoundError


class MemoryNotFoundError(NotFoundError):
    """Memory entry not found."""


class MemoryValidationError(DomainValidationError):
    """Memory validation failure."""


class MemoryLimitExceededError(AppError):
    """Project memory limit exceeded."""
