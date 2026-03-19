"""Reporting feature exceptions."""

from app.core.exceptions import AppError


class ReportNotFoundError(AppError):
    """Raised when a cached report is not found."""


class TypstCompilationError(AppError):
    """Raised when Typst CLI fails to compile a template."""


class ReportTooLargeError(AppError):
    """Raised when generated PDF exceeds size limit."""
