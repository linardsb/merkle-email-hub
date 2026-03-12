"""Feature-specific exceptions for design sync."""

from app.core.exceptions import AppError, DomainValidationError, NotFoundError


class ConnectionNotFoundError(NotFoundError):
    """Raised when a design connection is not found."""


class SyncFailedError(AppError):
    """Raised when a design token sync operation fails."""


class UnsupportedProviderError(DomainValidationError):
    """Raised when an unsupported design tool provider is requested."""
