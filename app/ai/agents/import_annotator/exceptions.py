"""Import annotator exceptions."""

from app.core.exceptions import AppError


class ImportAnnotationError(AppError):
    """Raised when import annotation fails."""

    status_code = 422
    detail = "Failed to annotate imported HTML"
