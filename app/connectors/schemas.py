"""Pydantic schemas for ESP connectors."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExportRequest(BaseModel):
    """Request to export an email build to an ESP."""

    build_id: int = Field(..., description="Email build ID to export")
    connector_type: str = Field(default="braze", max_length=50)
    content_block_name: str = Field(
        ..., min_length=1, max_length=200, description="Name for the ESP content block"
    )


class ExportResponse(BaseModel):
    """Response from an export operation."""

    id: int
    build_id: int
    connector_type: str
    status: str
    external_id: str | None = None
    error_message: str | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
