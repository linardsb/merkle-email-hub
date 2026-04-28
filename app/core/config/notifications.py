"""Notification channel settings."""

from pydantic import BaseModel


class NotificationsConfig(BaseModel):
    """Notification channel settings."""

    enabled: bool = False  # NOTIFICATIONS__ENABLED
    default_severity: str = "warning"  # NOTIFICATIONS__DEFAULT_SEVERITY

    # Slack
    slack_enabled: bool = False  # NOTIFICATIONS__SLACK_ENABLED
    slack_webhook_url: str = ""  # NOTIFICATIONS__SLACK_WEBHOOK_URL
    slack_timeout: float = 30.0  # NOTIFICATIONS__SLACK_TIMEOUT

    # Teams
    teams_enabled: bool = False  # NOTIFICATIONS__TEAMS_ENABLED
    teams_webhook_url: str = ""  # NOTIFICATIONS__TEAMS_WEBHOOK_URL
    teams_timeout: float = 30.0  # NOTIFICATIONS__TEAMS_TIMEOUT

    # Email
    email_enabled: bool = False  # NOTIFICATIONS__EMAIL_ENABLED
    email_smtp_host: str = ""  # NOTIFICATIONS__EMAIL_SMTP_HOST
    email_smtp_port: int = 587  # NOTIFICATIONS__EMAIL_SMTP_PORT
    email_from_addr: str = "noreply@email-hub.local"  # NOTIFICATIONS__EMAIL_FROM_ADDR
    email_to_addrs: list[str] = []  # NOTIFICATIONS__EMAIL_TO_ADDRS
