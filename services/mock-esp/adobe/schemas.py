"""Adobe Campaign Standard API schemas."""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86399


class DeliveryCreate(BaseModel):
    name: str
    content: str
    label: str = ""
    folder_id: str = ""


class DeliveryUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    label: str | None = None


class DeliveryResponse(BaseModel):
    PKey: str
    name: str
    content: str
    label: str
    folder_id: str
    created_at: str
    updated_at: str


class DeliveryListResponse(BaseModel):
    count: int
    content: list[DeliveryResponse]
