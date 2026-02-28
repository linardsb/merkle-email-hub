"""Feature-specific exceptions for email engine."""

from app.core.exceptions import AppError, ServiceUnavailableError


class BuildFailedError(AppError):
    """Raised when an email build fails."""


class BuildServiceUnavailableError(ServiceUnavailableError):
    """Raised when the Maizzle builder sidecar is unreachable."""
