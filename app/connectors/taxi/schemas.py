"""Taxi for Email-specific schemas."""

from pydantic import BaseModel, Field


class TaxiTemplate(BaseModel):
    """Schema representing a Taxi for Email template."""

    name: str = Field(..., min_length=1, max_length=200)
    content_type: str = "html"
    content: str = Field(..., min_length=1)
    syntax_version: str = "3.0"
