"""Email on Acid API-specific schemas."""

from pydantic import BaseModel


class EoATestPayload(BaseModel):
    """Payload for Email on Acid API submission."""

    html: str
    subject: str
    clients: list[str]
