"""Feature-specific exceptions for approval portal."""

from app.core.exceptions import DomainValidationError, NotFoundError


class ApprovalNotFoundError(NotFoundError):
    """Raised when an approval request is not found."""


class InvalidStateTransitionError(DomainValidationError):
    """Raised when an approval state transition is invalid."""
