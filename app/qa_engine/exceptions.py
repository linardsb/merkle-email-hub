"""Feature-specific exceptions for QA engine."""

from app.core.exceptions import AppError, ForbiddenError, NotFoundError


class QARunFailedError(AppError):
    """Raised when a QA run fails unexpectedly."""


class QAResultNotFoundError(NotFoundError):
    """Raised when a QA result is not found."""


class QAOverrideNotAllowedError(ForbiddenError):
    """Override attempted on a passing QA result or with invalid check names."""
