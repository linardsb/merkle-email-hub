"""Braze-specific schemas."""

from pydantic import BaseModel, Field


class BrazeContentBlock(BaseModel):
    """Schema representing a Braze Content Block."""

    name: str = Field(..., min_length=1, max_length=200)
    content_type: str = "html"
    content: str = Field(..., min_length=1)
    tags: list[str] = []
