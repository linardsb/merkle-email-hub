"""Email notification channel — sends via aiosmtplib."""

from __future__ import annotations

from datetime import UTC, datetime
from email.message import EmailMessage

import aiosmtplib

from app.core.logging import get_logger

from .channels import Notification, NotificationResult

logger = get_logger(__name__)


class EmailChannel:
    """Send notifications via SMTP email."""

    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int = 587,
        from_addr: str = "noreply@email-hub.local",
        to_addrs: list[str],
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._from_addr = from_addr
        self._to_addrs = to_addrs

    @property
    def name(self) -> str:
        return "email"

    def _build_message(self, notification: Notification) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = self._from_addr
        msg["To"] = ", ".join(self._to_addrs)
        msg["Subject"] = f"[{notification.severity.upper()}] {notification.title}"
        msg["Date"] = datetime.now(tz=UTC).strftime("%a, %d %b %Y %H:%M:%S %z")

        plain = (
            f"{notification.title}\n\n"
            f"{notification.body}\n\n"
            f"Event: {notification.event}\n"
            f"Severity: {notification.severity}\n"
        )
        msg.set_content(plain, subtype="plain")

        html = (
            f"<h2>{notification.title}</h2>"
            f"<p>{notification.body}</p>"
            f"<hr><p><small>Event: <code>{notification.event}</code> "
            f"| Severity: {notification.severity}</small></p>"
        )
        msg.add_alternative(html, subtype="html", charset="utf-8")
        return msg

    async def send(self, notification: Notification) -> NotificationResult:
        msg = self._build_message(notification)
        try:
            await aiosmtplib.send(
                msg,
                hostname=self._smtp_host,
                port=self._smtp_port,
                start_tls=False,
                use_tls=False,
            )
        except (aiosmtplib.SMTPException, OSError) as exc:
            logger.warning(
                "notifications.email_send_failed",
                error=str(exc),
                host=self._smtp_host,
                port=self._smtp_port,
            )
            return NotificationResult(channel="email", success=False, error=str(exc))
        return NotificationResult(channel="email", success=True)
