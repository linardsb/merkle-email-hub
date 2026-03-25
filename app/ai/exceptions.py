"""AI-specific exceptions and exception handlers.

Exception hierarchy:
- AIError (base)
  - AIConfigurationError (invalid provider config, missing API key) -> 500
  - AIExecutionError (LLM call failed, timeout, rate limit) -> 502
  - BudgetExceededError (monthly AI budget exceeded) -> 429
"""

from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AIError(Exception):
    """Base exception for all AI layer errors."""



class AIConfigurationError(AIError):
    """Invalid AI configuration (wrong provider, missing API key, bad base_url)."""



class AIExecutionError(AIError):
    """AI execution failed (LLM timeout, rate limit, API error)."""



class BudgetExceededError(AIError):
    """Monthly AI budget exceeded (429)."""



async def ai_exception_handler(request: Request, exc: AIError) -> JSONResponse:
    """Handle AI exceptions globally.

    Args:
        request: The incoming request.
        exc: The AI exception that was raised.

    Returns:
        JSONResponse with error details and appropriate status code.
    """
    logger.error(
        "ai.error",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    from app.ai.voice.exceptions import AudioValidationError, VoiceDisabledError

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, VoiceDisabledError):
        status_code = status.HTTP_501_NOT_IMPLEMENTED
    elif isinstance(exc, AudioValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, BudgetExceededError):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(exc, AIExecutionError):
        status_code = status.HTTP_502_BAD_GATEWAY

    from app.core.error_sanitizer import get_safe_error_message, get_safe_error_type

    return JSONResponse(
        status_code=status_code,
        content={
            "error": get_safe_error_message(exc),
            "type": get_safe_error_type(exc),
        },
    )


def setup_ai_exception_handlers(app: FastAPI) -> None:
    """Register AI exception handlers with the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """
    handler: Any = cast(Any, ai_exception_handler)

    from app.ai.voice.exceptions import (
        AudioValidationError,
        BriefExtractionError,
        TranscriptionError,
        VoiceDisabledError,
        VoiceError,
    )

    app.add_exception_handler(AIError, handler)
    app.add_exception_handler(AIConfigurationError, handler)
    app.add_exception_handler(AIExecutionError, handler)
    app.add_exception_handler(BudgetExceededError, handler)
    app.add_exception_handler(VoiceError, handler)
    app.add_exception_handler(VoiceDisabledError, handler)
    app.add_exception_handler(AudioValidationError, handler)
    app.add_exception_handler(TranscriptionError, handler)
    app.add_exception_handler(BriefExtractionError, handler)
