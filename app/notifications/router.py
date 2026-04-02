"""Notification router — broadcasts to all configured channels."""

from __future__ import annotations

from app.core.config import NotificationsConfig
from app.core.logging import get_logger

from .channels import Notification, NotificationChannel, NotificationResult
from .email_channel import EmailChannel
from .slack import SlackChannel
from .teams import TeamsChannel

logger = get_logger(__name__)


class NotificationRouter:
    """Routes notifications to configured channels."""

    def __init__(self, channels: list[NotificationChannel]) -> None:
        self._channels = channels

    @classmethod
    def from_settings(cls, config: NotificationsConfig) -> NotificationRouter:
        """Build router from app settings, instantiating enabled channels."""
        channels: list[NotificationChannel] = []
        if config.slack_enabled and config.slack_webhook_url:
            channels.append(
                SlackChannel(url=config.slack_webhook_url, timeout=config.slack_timeout)
            )
        if config.teams_enabled and config.teams_webhook_url:
            channels.append(
                TeamsChannel(url=config.teams_webhook_url, timeout=config.teams_timeout)
            )
        if config.email_enabled and config.email_smtp_host:
            channels.append(
                EmailChannel(
                    smtp_host=config.email_smtp_host,
                    smtp_port=config.email_smtp_port,
                    from_addr=config.email_from_addr,
                    to_addrs=config.email_to_addrs,
                )
            )
        return cls(channels)

    async def notify(self, notification: Notification) -> list[NotificationResult]:
        """Send notification to all configured channels. Fire-and-forget with logging."""
        results: list[NotificationResult] = []
        for channel in self._channels:
            try:
                result = await channel.send(notification)
            except Exception:
                logger.exception(
                    "notifications.channel_send_failed",
                    channel=channel.name,
                )
                result = NotificationResult(
                    channel=channel.name, success=False, error="unexpected error"
                )
            results.append(result)
            if not result.success:
                logger.warning(
                    "notifications.delivery_failed",
                    channel=result.channel,
                    notification_event=notification.event,
                    error=result.error,
                )
        return results
