"""Feature-specific exceptions for briefs."""

from app.core.exceptions import AppError, DomainValidationError, NotFoundError


class BriefConnectionNotFoundError(NotFoundError):
    """Raised when a brief connection is not found."""


class BriefItemNotFoundError(NotFoundError):
    """Raised when a brief item is not found."""


class BriefSyncFailedError(AppError):
    """Raised when syncing items from a platform fails."""


class BriefValidationError(DomainValidationError):
    """Raised when brief business rule validation fails."""


class UnsupportedPlatformError(DomainValidationError):
    """Raised when an unsupported platform is requested."""
