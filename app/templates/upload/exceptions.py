"""Domain exceptions for template upload operations."""

from app.core.exceptions import AppError, DomainValidationError


class TemplateUploadError(AppError):
    """Base error for template upload operations."""


class TemplateTooLargeError(DomainValidationError):
    """Uploaded HTML exceeds size limit."""


class TemplateAlreadyConfirmedError(DomainValidationError):
    """Upload has already been confirmed."""


class UploadNotFoundError(AppError):
    """Template upload not found."""

    status_code = 404


class UploadRateLimitError(AppError):
    """User exceeded upload rate limit."""

    status_code = 429


class TemplateDuplicateNameError(DomainValidationError):
    """A template with this name already exists."""
