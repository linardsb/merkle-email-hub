"""Feature-specific exceptions for item management.

Inherits from core exceptions for automatic HTTP status code mapping:
- ItemNotFoundError -> 404
- ItemAlreadyExistsError -> 422
"""

from app.core.exceptions import DomainValidationError, NotFoundError


class ItemNotFoundError(NotFoundError):
    """Raised when an item is not found by ID."""


class ItemAlreadyExistsError(DomainValidationError):
    """Raised when creating an item with a duplicate name."""
