"""Slack notification channel — posts to an incoming webhook with Block Kit formatting."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.logging import get_logger

from .channels import Notification, NotificationResult

logger = get_logger(__name__)

_SEVERITY_EMOJI: dict[str, str] = {
    "info": ":information_source:",
    "warning": ":warning:",
    "error": ":rotating_light:",
}


class SlackChannel:
    """Send notifications to Slack via incoming webhook."""

    def __init__(self, *, url: str, timeout: float = 30.0) -> None:
        self._url = url
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "slack"

    def _build_payload(self, notification: Notification) -> dict[str, object]:
        emoji = _SEVERITY_EMOJI.get(notification.severity, ":bell:")
        timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {notification.title}",
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": notification.body},
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Event:* `{notification.event}` | *Severity:* {notification.severity} | {timestamp}",
                        }
                    ],
                },
            ]
        }

    async def send(self, notification: Notification) -> NotificationResult:
        payload = self._build_payload(notification)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._url, json=payload)
                if response.status_code >= 400:
                    return NotificationResult(
                        channel="slack",
                        success=False,
                        error=f"HTTP {response.status_code}: {response.text[:200]}",
                    )
        except httpx.HTTPError as exc:
            logger.warning("notifications.slack_send_failed", error=str(exc))
            return NotificationResult(channel="slack", success=False, error=str(exc))
        return NotificationResult(channel="slack", success=True)
