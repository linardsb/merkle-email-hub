# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""AI chat API routes following OpenAI-compatible format.

Endpoints:
- POST /v1/chat/completions - Send messages and receive AI responses
- GET /v1/models - List available models
"""

import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.ai.schemas import ChatCompletionRequest, ChatCompletionResponse
from app.ai.service import ChatService, get_chat_service
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.rate_limit import _get_client_ip, limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["ai"])


# ── In-memory daily quota tracker ──

_SECONDS_PER_DAY: int = 86_400


@dataclass
class _QuotaEntry:
    """Tracks query count and reset time for a single IP."""

    count: int = 0
    reset_at: float = field(default_factory=lambda: time.monotonic() + _SECONDS_PER_DAY)


class _QuotaTracker:
    """In-memory daily query quota tracker per IP address.

    For production deployments with multiple workers, replace with a
    Redis-backed implementation (see VTV's quota.py for reference).
    """

    def __init__(self, daily_limit: int) -> None:
        self._daily_limit = daily_limit
        self._entries: dict[str, _QuotaEntry] = {}

    async def check_and_increment(self, client_ip: str) -> bool:
        """Check quota and increment if allowed.

        Args:
            client_ip: The client's IP address.

        Returns:
            True if the request is allowed, False if quota exceeded.
        """
        now = time.monotonic()
        entry = self._entries.get(client_ip)

        if entry is None or now >= entry.reset_at:
            self._entries[client_ip] = _QuotaEntry(count=1, reset_at=now + _SECONDS_PER_DAY)
            return True

        if entry.count >= self._daily_limit:
            logger.warning(
                "ai.quota_exceeded",
                client_ip=client_ip,
                daily_limit=self._daily_limit,
                current_count=entry.count,
            )
            return False

        entry.count += 1
        return True

    async def get_remaining(self, client_ip: str) -> int:
        """Get remaining quota count for a client.

        Args:
            client_ip: The client's IP address.

        Returns:
            Number of queries remaining in the current period.
        """
        now = time.monotonic()
        entry = self._entries.get(client_ip)
        if entry is None or now >= entry.reset_at:
            return self._daily_limit
        return max(0, self._daily_limit - entry.count)


_quota_tracker: _QuotaTracker | None = None


def _get_quota_tracker() -> _QuotaTracker:
    """Get or create the quota tracker singleton."""
    global _quota_tracker
    if _quota_tracker is None:
        settings = get_settings()
        _quota_tracker = _QuotaTracker(daily_limit=settings.ai.daily_quota)
    return _quota_tracker


# ── Routes ──


@router.post("/chat/completions", response_model=ChatCompletionResponse)
@limiter.limit("10/minute")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    service: ChatService = Depends(get_chat_service),
    _current_user: User = Depends(get_current_user),
) -> ChatCompletionResponse:
    """Create a chat completion.

    Accepts a list of messages and returns the AI provider's response
    in OpenAI-compatible format.

    Args:
        request: The incoming HTTP request (used for rate limiting).
        body: Chat completion request with messages.
        service: Chat service instance (injected).
        _current_user: Authenticated user (injected, enforces auth).

    Returns:
        Chat completion response with the provider's message.
    """
    # Check daily quota before expensive LLM call
    client_ip = _get_client_ip(request)
    tracker = _get_quota_tracker()
    if not await tracker.check_and_increment(client_ip):
        remaining = await tracker.get_remaining(client_ip)
        logger.warning("ai.quota_exceeded_http", client_ip=client_ip, remaining=remaining)
        raise HTTPException(
            status_code=429,
            detail=f"Daily query quota exceeded. Remaining: {remaining}. Resets in 24 hours.",
        )

    return await service.chat(body)


@router.get("/models")
@limiter.limit("60/minute")
async def list_models(
    request: Request,
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List available models.

    Returns the currently configured AI provider and model information.

    Returns:
        Dictionary with model list in OpenAI-compatible format.
    """
    settings = get_settings()
    model_id = f"{settings.ai.provider}:{settings.ai.model}"

    return {
        "object": "list",
        "data": [
            {
                "id": model_id,
                "object": "model",
            }
        ],
    }
