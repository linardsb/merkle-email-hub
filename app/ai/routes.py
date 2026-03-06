# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""AI chat API routes following OpenAI-compatible format.

Endpoints:
- POST /v1/chat/completions - Send messages / stream AI responses
- GET /v1/models - List available models
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ChatCompletionRequest, ChatCompletionResponse
from app.ai.service import ChatService, get_chat_service
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.quota import UserQuotaTracker
from app.core.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["ai"])


# ── Per-user daily quota (Redis-backed) ──

_user_quota: UserQuotaTracker | None = None


def _get_user_quota() -> UserQuotaTracker:
    """Get or create the per-user quota tracker singleton."""
    global _user_quota
    if _user_quota is None:
        settings = get_settings()
        _user_quota = UserQuotaTracker(daily_limit=settings.ai.daily_quota)
    return _user_quota


# ── Routes ──


@router.post("/chat/completions", response_model=None)
@limiter.limit("20/minute")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    db: AsyncSession = Depends(get_db),
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_user),
) -> ChatCompletionResponse | StreamingResponse:
    """Create a chat completion (streaming or non-streaming).

    When body.stream is True, returns SSE StreamingResponse.
    When body.stream is False, returns ChatCompletionResponse.

    Args:
        request: The incoming HTTP request (used for rate limiting).
        body: Chat completion request with messages.
        service: Chat service instance (injected).
        _current_user: Authenticated user (injected, enforces auth).

    Returns:
        Chat completion response or SSE streaming response.
    """
    # Check daily quota (per-user, Redis-backed)
    tracker = _get_user_quota()
    if not await tracker.check_and_increment(current_user.id):
        remaining = await tracker.get_remaining(current_user.id)
        raise HTTPException(
            status_code=429,
            detail=f"Daily query quota exceeded. Remaining: {remaining}. Resets in 24 hours.",
        )

    # BOLA: verify project access when project_id is provided
    if body.project_id is not None:
        from app.projects.service import ProjectService

        project_service = ProjectService(db)
        await project_service.verify_project_access(body.project_id, current_user)

    # Streaming response
    if body.stream:
        return StreamingResponse(
            service.stream_chat(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    # Non-streaming response
    return await service.chat(body)


@router.get("/models")
@limiter.limit("60/minute")
async def list_models(
    request: Request,
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List available models including tier-routed models.

    Returns the currently configured AI provider and model information
    in OpenAI-compatible format.

    Returns:
        Dictionary with model list in OpenAI-compatible format.
    """
    settings = get_settings()

    models: list[dict[str, str]] = [
        {"id": f"{settings.ai.provider}:{settings.ai.model}", "object": "model"},
    ]

    # Include tier models if configured
    for tier_attr in ("model_complex", "model_standard", "model_lightweight"):
        tier_model: str = getattr(settings.ai, tier_attr, "")
        if tier_model:
            model_id = f"{settings.ai.provider}:{tier_model}"
            if not any(m["id"] == model_id for m in models):
                models.append({"id": model_id, "object": "model"})

    return {"object": "list", "data": models}
