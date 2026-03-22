"""Async SMTP client for sending test emails to sandbox mail server."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from email.message import EmailMessage

import aiosmtplib

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.exceptions import SandboxSMTPError

logger = get_logger(__name__)


async def send_test_email(
    html: str,
    subject: str,
    *,
    from_addr: str | None = None,
    to_addr: str | None = None,
) -> str:
    """Send an HTML email to the sandbox mail server via SMTP.

    Returns the Message-ID header value for later retrieval.
    """
    settings = get_settings()
    cfg = settings.rendering.sandbox

    sender = from_addr or cfg.from_addr
    recipient = to_addr or cfg.to_addr

    message_id = f"<{uuid.uuid4().hex}@sandbox.local>"

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Date"] = datetime.now(tz=UTC).strftime("%a, %d %b %Y %H:%M:%S %z")
    msg["Message-ID"] = message_id
    msg["MIME-Version"] = "1.0"
    msg.set_content(subject, subtype="plain")
    msg.add_alternative(html, subtype="html", charset="utf-8")

    try:
        await aiosmtplib.send(
            msg,
            hostname=cfg.smtp_host,
            port=cfg.smtp_port,
            start_tls=False,
            use_tls=False,
        )
    except (aiosmtplib.SMTPException, OSError) as exc:
        raise SandboxSMTPError(
            f"Failed to send email to sandbox SMTP ({cfg.smtp_host}:{cfg.smtp_port}): {exc}"
        ) from exc

    logger.info(
        "sandbox.smtp_sent",
        message_id=message_id,
        host=cfg.smtp_host,
        port=cfg.smtp_port,
    )
    return message_id
