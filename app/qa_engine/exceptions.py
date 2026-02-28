"""Feature-specific exceptions for QA engine."""

from app.core.exceptions import AppError, NotFoundError


class QARunFailedError(AppError):
    """Raised when a QA run fails unexpectedly."""


class QAResultNotFoundError(NotFoundError):
    """Raised when a QA result is not found."""
