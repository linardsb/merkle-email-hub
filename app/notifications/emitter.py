"""Fire-and-forget notification emitter with Redis dedup."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.notifications.channels import Notification
from app.notifications.router import NotificationRouter

logger = get_logger(__name__)

_DEDUP_WINDOW_SECONDS = 300  # 5 minutes


async def emit_notification(notification: Notification) -> bool:
    """Emit notification with dedup. Returns True if sent, False if skipped/disabled."""
    settings = get_settings()
    if not settings.notifications.enabled:
        return False

    # Dedup: same event+project within window → skip
    from app.core.redis import get_redis

    redis = await get_redis()
    dedup_key = f"notif:dedup:{notification.event}:{notification.project_id or 'global'}"
    if await redis.get(dedup_key):
        logger.debug(
            "notification.deduped",
            notification_event=notification.event,
            project_id=notification.project_id,
        )
        return False
    await redis.setex(dedup_key, _DEDUP_WINDOW_SECONDS, "1")

    # Send (fire-and-forget: log errors, never raise)
    try:
        router = NotificationRouter.from_settings(settings.notifications)
        await router.notify(notification)
        logger.info(
            "notification.emitted",
            notification_event=notification.event,
            project_id=notification.project_id,
        )
        return True
    except Exception:
        logger.exception("notification.emit_failed", notification_event=notification.event)
        return False
