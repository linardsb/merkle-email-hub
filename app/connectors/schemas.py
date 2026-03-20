"""Pydantic schemas for ESP connectors."""

import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExportRequest(BaseModel):
    """Request to export an email build to an ESP."""

    build_id: int | None = Field(default=None, description="Email build ID to export")
    template_version_id: int | None = Field(
        default=None, description="Template version ID to export (alternative to build_id)"
    )
    connector_type: str = Field(default="braze", max_length=50)
    content_block_name: str = Field(
        default="email", max_length=200, description="Name for the ESP content block"
    )
    connection_id: int | None = Field(
        default=None,
        description="ESP connection ID — when provided, uses real credentials for the API call",
    )

    @model_validator(mode="after")
    def _require_at_least_one_source(self) -> "ExportRequest":
        if self.build_id is None and self.template_version_id is None:
            msg = "Either build_id or template_version_id must be provided"
            raise ValueError(msg)
        return self


class ExportResponse(BaseModel):
    """Response from an export operation."""

    id: int | None = None
    build_id: int | None = None
    template_version_id: int | None = None
    connector_type: str
    status: str
    external_id: str | None = None
    error_message: str | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
