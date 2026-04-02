"""Microsoft Teams notification channel — posts Adaptive Cards to an incoming webhook."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.logging import get_logger

from .channels import Notification, NotificationResult

logger = get_logger(__name__)

_SEVERITY_COLOR: dict[str, str] = {
    "info": "good",
    "warning": "attention",
    "error": "default",
}


class TeamsChannel:
    """Send notifications to Teams via incoming webhook."""

    def __init__(self, *, url: str, timeout: float = 30.0) -> None:
        self._url = url
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "teams"

    def _build_payload(self, notification: Notification) -> dict[str, object]:
        timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
        color = _SEVERITY_COLOR.get(notification.severity, "default")
        facts = [
            {"title": "Event", "value": notification.event},
            {"title": "Severity", "value": notification.severity},
            {"title": "Time", "value": timestamp},
        ]
        if notification.project_id is not None:
            facts.append({"title": "Project", "value": str(notification.project_id)})

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": notification.title,
                                "weight": "bolder",
                                "size": "medium",
                                "color": color,
                            },
                            {
                                "type": "TextBlock",
                                "text": notification.body,
                                "wrap": True,
                            },
                            {
                                "type": "FactSet",
                                "facts": facts,
                            },
                        ],
                    },
                }
            ],
        }

    async def send(self, notification: Notification) -> NotificationResult:
        payload = self._build_payload(notification)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._url, json=payload)
                if response.status_code >= 400:
                    return NotificationResult(
                        channel="teams",
                        success=False,
                        error=f"HTTP {response.status_code}: {response.text[:200]}",
                    )
        except httpx.HTTPError as exc:
            logger.warning("notifications.teams_send_failed", error=str(exc))
            return NotificationResult(channel="teams", success=False, error=str(exc))
        return NotificationResult(channel="teams", success=True)
