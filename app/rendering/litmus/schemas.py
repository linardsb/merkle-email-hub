"""Litmus API-specific schemas."""

from pydantic import BaseModel


class LitmusTestPayload(BaseModel):
    """Payload for Litmus Instant API submission."""

    html_text: str
    subject: str
    applications: list[str]
