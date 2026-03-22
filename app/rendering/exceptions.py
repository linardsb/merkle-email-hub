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


class ScreenshotRenderError(ServiceUnavailableError):
    """Raised when local screenshot rendering fails."""


class ScreenshotTimeoutError(AppError):
    """Raised when screenshot rendering exceeds timeout."""


class VisualDiffError(ServiceUnavailableError):
    """Raised when ODiff binary fails or is unavailable."""


class BaselineNotFoundError(AppError):
    """Raised when a screenshot baseline is not found."""


class SandboxUnavailableError(ServiceUnavailableError):
    """Raised when sandbox infrastructure (Mailpit/Roundcube) is unreachable."""


class SandboxSMTPError(ServiceUnavailableError):
    """Raised when SMTP send to sandbox mail server fails."""


class SandboxCaptureError(AppError):
    """Raised when Playwright DOM extraction from webmail fails."""
