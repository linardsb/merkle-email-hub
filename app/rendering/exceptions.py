"""Feature-specific exceptions for rendering tests."""

from app.core.exceptions import AppError, DomainValidationError, ServiceUnavailableError


class RenderingTestNotFoundError(AppError):
    """Raised when a rendering test is not found."""


class RenderingSubmitError(ServiceUnavailableError):
    """Raised when submitting HTML to rendering service fails."""


class RenderingPollTimeoutError(AppError):
    """Raised when polling for results exceeds timeout."""


class RenderingProviderError(DomainValidationError):
    """Raised for unsupported rendering provider."""
