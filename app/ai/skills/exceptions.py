from app.core.exceptions import AppError


class SkillExtractionError(AppError):
    """Failed to extract patterns from template HTML."""

    status_code = 422


class AmendmentConflictError(AppError):
    """Amendment conflicts with existing skill content."""

    status_code = 409


class AmendmentNotFoundError(AppError):
    """Amendment not found."""

    status_code = 404
