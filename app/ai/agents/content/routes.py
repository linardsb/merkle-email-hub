# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Content agent API routes.

Endpoints:
- POST /api/v1/agents/content/generate - Generate or refine email marketing copy
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.ai.agents.content.schemas import ContentRequest, ContentResponse
from app.ai.agents.content.service import ContentService, get_content_service
from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.logging import get_logger
from app.core.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/agents/content", tags=["agents"])


@router.post("/generate", response_model=None)
@limiter.limit("5/minute")
async def generate_content(
    request: Request,  # noqa: ARG001 — required by @limiter.limit
    body: ContentRequest,
    service: ContentService = Depends(get_content_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin", "developer")),  # noqa: B008
) -> ContentResponse | StreamingResponse:
    """Generate or refine email marketing copy.

    When body.stream is True, returns SSE StreamingResponse.
    When body.stream is False, returns ContentResponse with generated
    text alternatives and spam warnings.
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
