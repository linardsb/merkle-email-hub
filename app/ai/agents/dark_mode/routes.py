# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Dark Mode agent API routes.

Endpoints:
- POST /api/v1/agents/dark-mode/process - Enhance email HTML with dark mode support
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.ai.agents.dark_mode.schemas import DarkModeRequest, DarkModeResponse
from app.ai.agents.dark_mode.service import DarkModeService, get_dark_mode_service
from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.logging import get_logger
from app.core.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/agents/dark-mode", tags=["agents"])


@router.post("/process", response_model=None)
@limiter.limit("5/minute")
async def process_dark_mode(
    request: Request,  # noqa: ARG001 — required by @limiter.limit
    body: DarkModeRequest,
    service: DarkModeService = Depends(get_dark_mode_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin", "developer")),  # noqa: B008
) -> DarkModeResponse | StreamingResponse:
    """Enhance email HTML with dark mode support.

    When body.stream is True, returns SSE StreamingResponse.
    When body.stream is False, returns DarkModeResponse with enhanced HTML
    and optional QA results.

    Args:
        request: The incoming HTTP request (used for rate limiting).
        body: Dark mode request with HTML and options.
        service: Dark mode service instance (injected).
        _current_user: Authenticated admin or developer user (injected).

    Returns:
        Dark mode response or SSE streaming response.
    """
    if body.stream:
        return StreamingResponse(
            service.stream_process(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await service.process(body)
