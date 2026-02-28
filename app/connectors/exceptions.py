"""Feature-specific exceptions for connectors."""

from app.core.exceptions import AppError, DomainValidationError


class ExportFailedError(AppError):
    """Raised when an export operation fails."""


class UnsupportedConnectorError(DomainValidationError):
    """Raised when an unsupported connector type is requested."""
