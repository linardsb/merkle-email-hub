"""Custom exception classes and global exception handlers."""

from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Exception Hierarchy ──


class AppError(Exception):
    """Base exception for all application errors."""


class NotFoundError(AppError):
    """Resource not found (404)."""


class DomainValidationError(AppError):
    """Business rule validation failure (422)."""


class ForbiddenError(AppError):
    """Access denied (403)."""


class ConflictError(AppError):
    """Resource conflict, e.g. duplicate entry (409)."""


class ServiceUnavailableError(AppError):
    """External dependency unavailable (503)."""


class PromptInjectionError(DomainValidationError):
    """Prompt injection detected in user input (422)."""

    def __init__(self, *, flags: list[str]) -> None:
        self.flags = flags
        super().__init__(f"Prompt injection detected: {', '.join(flags)}")


# ── Exception Handlers ──


def _is_sync_error(exc: AppError) -> bool:
    """Check if exception is a SyncFailedError (avoids circular import)."""
    return any(cls.__name__ == "SyncFailedError" for cls in type(exc).__mro__)


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle application exceptions globally."""
    logger.error(
        "app.error",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, DomainValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(exc, ForbiddenError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, ServiceUnavailableError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif _is_sync_error(exc):
        status_code = status.HTTP_502_BAD_GATEWAY

    from app.core.error_sanitizer import get_safe_error_message, get_safe_error_type

    return JSONResponse(
        status_code=status_code,
        content={
            "error": get_safe_error_message(exc),
            "type": get_safe_error_type(exc),
        },
    )


async def invalid_credentials_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle invalid credentials with 401 Unauthorized."""
    logger.warning(
        "auth.invalid_credentials",
        extra={"path": request.url.path, "method": request.method},
    )
    from app.core.error_sanitizer import get_safe_error_message, get_safe_error_type

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": get_safe_error_message(exc),
            "type": get_safe_error_type(exc),
        },
    )


async def account_locked_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle locked accounts with 423 Locked."""
    logger.warning(
        "auth.account_locked",
        extra={"path": request.url.path, "method": request.method},
    )
    from app.core.error_sanitizer import get_safe_error_message, get_safe_error_type

    return JSONResponse(
        status_code=status.HTTP_423_LOCKED,
        content={
            "error": get_safe_error_message(exc),
            "type": get_safe_error_type(exc),
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers with the FastAPI application."""
    from app.auth.exceptions import AccountLockedError, InvalidCredentialsError

    handler: Any = cast(Any, app_exception_handler)

    app.add_exception_handler(AppError, handler)
    app.add_exception_handler(NotFoundError, handler)
    app.add_exception_handler(ForbiddenError, handler)
    app.add_exception_handler(DomainValidationError, handler)
    app.add_exception_handler(ConflictError, handler)
    app.add_exception_handler(ServiceUnavailableError, handler)

    # Auth-specific handlers (401, 423)
    app.add_exception_handler(InvalidCredentialsError, cast(Any, invalid_credentials_handler))
    app.add_exception_handler(AccountLockedError, cast(Any, account_locked_handler))
