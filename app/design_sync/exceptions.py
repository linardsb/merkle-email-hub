"""Feature-specific exceptions for design sync."""

from app.core.exceptions import AppError, DomainValidationError, NotFoundError


class ConnectionNotFoundError(NotFoundError):
    """Raised when a design connection is not found."""


class SyncFailedError(AppError):
    """Raised when a design token sync operation fails."""


class UnsupportedProviderError(DomainValidationError):
    """Raised when an unsupported design tool provider is requested."""


class AssetDownloadError(AppError):
    """Raised when an asset download from a provider fails."""


class AssetNotFoundError(NotFoundError):
    """Raised when a stored asset is not found on disk."""


class ImportNotFoundError(NotFoundError):
    """Raised when a design import job is not found."""


class ImportStateError(DomainValidationError):
    """Raised when an import is in an invalid state for the requested operation."""


class TokenDecryptionError(AppError):
    """Raised when a stored access token cannot be decrypted (key rotation)."""


class MjmlCompileError(AppError):
    """Raised when MJML compilation via the Maizzle sidecar fails."""


class FidelityScoringError(SyncFailedError):
    """Raised when visual fidelity scoring fails."""


class WebhookSignatureError(AppError):
    """Raised when HMAC-SHA256 signature validation fails for a Figma webhook."""


class WebhookRegistrationError(SyncFailedError):
    """Raised when Figma API webhook registration fails."""


class W3cTokenParseError(DomainValidationError):
    """W3C Design Tokens JSON is malformed or contains unsupported types."""
