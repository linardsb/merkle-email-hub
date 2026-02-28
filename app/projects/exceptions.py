"""Feature-specific exceptions for project management."""

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError


class ProjectNotFoundError(NotFoundError):
    """Raised when a project is not found."""


class ProjectAccessDeniedError(ForbiddenError):
    """Raised when user is not a member of the project."""


class ClientOrgNotFoundError(NotFoundError):
    """Raised when a client organization is not found."""


class ClientOrgAlreadyExistsError(ConflictError):
    """Raised when creating a client org with a duplicate slug."""
