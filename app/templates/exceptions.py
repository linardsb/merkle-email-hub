"""Template-specific exceptions."""

from app.core.exceptions import NotFoundError


class TemplateNotFoundError(NotFoundError):
    """Template not found (404)."""



class TemplateVersionNotFoundError(NotFoundError):
    """Template version not found (404)."""

