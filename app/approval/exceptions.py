"""Feature-specific exceptions for approval portal."""

from app.core.exceptions import NotFoundError


class ApprovalNotFoundError(NotFoundError):
    """Raised when an approval request is not found."""
