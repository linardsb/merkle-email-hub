"""Feature-specific exceptions for personas."""

from app.core.exceptions import NotFoundError


class PersonaNotFoundError(NotFoundError):
    """Raised when a persona is not found."""
