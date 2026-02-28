"""Feature-specific exceptions for component library."""

from app.core.exceptions import ConflictError, NotFoundError


class ComponentNotFoundError(NotFoundError):
    """Raised when a component is not found."""


class ComponentAlreadyExistsError(ConflictError):
    """Raised when creating a component with a duplicate slug."""
