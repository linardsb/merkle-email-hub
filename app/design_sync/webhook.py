"""Figma webhook signature verification, event handling, and debounced sync."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.design_sync.exceptions import WebhookSignatureError

if TYPE_CHECKING:
    from app.design_sync.schemas import DesignSyncUpdateMessage

logger = get_logger(__name__)


def verify_signature(payload: bytes, signature: str, passcode: str) -> None:
    """Verify Figma webhook HMAC-SHA256 signature.

    Raises WebhookSignatureError if validation fails.
    """
    if not signature:
        raise WebhookSignatureError("Missing webhook signature")
    expected = hmac.new(passcode.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise WebhookSignatureError("Invalid webhook signature")


async def enqueue_debounced_sync(file_key: str, connection_id: int) -> None:
    """Set Redis debounce key with TTL. Background task triggers sync after expiry."""
    settings = get_settings()
    ttl = settings.design_sync.webhook_debounce_seconds
    redis = await get_redis()
    key = f"figma_webhook:{file_key}"
    value = f"{connection_id}:{datetime.now(UTC).isoformat()}"
    await redis.setex(key, ttl, value)
    logger.info("design_sync.webhook_debounced", file_key=file_key, connection_id=connection_id)


async def debounced_sync_worker(
    connection_id: int,
    file_key: str,
    project_id: int | None,
) -> None:
    """Wait for debounce window, then run sync + broadcast if no new events arrived."""
    from app.core.scoped_db import get_system_db_context
    from app.design_sync.services import DesignSyncContext, WebhookService

    settings = get_settings()
    ttl = settings.design_sync.webhook_debounce_seconds
    await asyncio.sleep(ttl + 0.5)

    redis = await get_redis()
    if await redis.get(f"figma_webhook:{file_key}") is not None:
        # New event arrived during sleep — another worker will handle it
        return

    async with get_system_db_context() as db:
        ctx = DesignSyncContext(db)
        msg = await WebhookService(ctx).handle_webhook_sync(connection_id)

    if msg is None:
        return

    # Broadcast via WebSocket to project room
    if project_id is not None:
        await _broadcast_update(project_id, msg)


async def _broadcast_update(project_id: int, msg: DesignSyncUpdateMessage) -> None:
    """Broadcast a design sync update to all users in the project's collab room."""
    from app.streaming.websocket.routes import get_collab_manager

    room_id = f"project:{project_id}"
    manager = get_collab_manager()
    await manager.broadcast_json(room_id, msg.model_dump(mode="json"))
    logger.info(
        "design_sync.webhook_broadcast",
        connection_id=msg.connection_id,
        room=room_id,
        total_changes=msg.total_changes,
    )
