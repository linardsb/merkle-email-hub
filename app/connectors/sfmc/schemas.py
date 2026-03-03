"""SFMC-specific schemas."""

from pydantic import BaseModel, Field


class SFMCContentArea(BaseModel):
    """Schema representing an SFMC Content Builder Content Area."""

    name: str = Field(..., min_length=1, max_length=200)
    content_type: str = "html"
    content: str = Field(..., min_length=1)
    category_id: int | None = None
    customer_key: str | None = None
