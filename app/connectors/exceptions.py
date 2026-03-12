"""Feature-specific exceptions for connectors."""

from app.core.exceptions import AppError, DomainValidationError, NotFoundError


class ExportFailedError(AppError):
    """Raised when an export operation fails."""


class UnsupportedConnectorError(DomainValidationError):
    """Raised when an unsupported connector type is requested."""


class ESPConnectionNotFoundError(NotFoundError):
    """Raised when an ESP connection is not found."""


class ESPSyncFailedError(AppError):
    """Raised when an ESP sync operation fails."""


class InvalidESPCredentialsError(DomainValidationError):
    """Raised when ESP credentials are invalid."""
