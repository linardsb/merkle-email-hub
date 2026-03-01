# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Scaffolder agent API routes.

Endpoints:
- POST /api/v1/agents/scaffolder/generate - Generate email HTML from a brief
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.ai.agents.scaffolder.schemas import ScaffolderRequest, ScaffolderResponse
from app.ai.agents.scaffolder.service import ScaffolderService, get_scaffolder_service
from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.logging import get_logger
from app.core.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/agents/scaffolder", tags=["agents"])


@router.post("/generate", response_model=None)
@limiter.limit("5/minute")
async def generate_email(
    request: Request,  # noqa: ARG001 — required by @limiter.limit
    body: ScaffolderRequest,
    service: ScaffolderService = Depends(get_scaffolder_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin", "developer")),  # noqa: B008
) -> ScaffolderResponse | StreamingResponse:
    """Generate Maizzle email HTML from a campaign brief.

    When body.stream is True, returns SSE StreamingResponse.
    When body.stream is False, returns ScaffolderResponse with HTML
    and optional QA results.

    Args:
        request: The incoming HTTP request (used for rate limiting).
        body: Scaffolder request with brief and options.
        service: Scaffolder service instance (injected).
        _current_user: Authenticated admin or developer user (injected).

    Returns:
        Scaffolder response or SSE streaming response.
    """
    if body.stream:
        return StreamingResponse(
            service.stream_generate(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await service.generate(body)
