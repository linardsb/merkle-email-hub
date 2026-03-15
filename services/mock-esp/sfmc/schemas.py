"""SFMC Content Builder Asset API schemas."""

from pydantic import BaseModel


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str
    grant_type: str = "client_credentials"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"  # noqa: S105
    expires_in: int = 3600


class AssetCreate(BaseModel):
    name: str
    content: str
    category_id: int = 0
    customer_key: str | None = None


class AssetUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    category_id: int | None = None


class AssetResponse(BaseModel):
    id: str
    name: str
    content: str
    category_id: int
    customer_key: str | None
    created_at: str
    updated_at: str


class AssetListResponse(BaseModel):
    count: int
    items: list[AssetResponse]
