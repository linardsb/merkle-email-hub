"""Pydantic schemas for email build pipeline."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class BuildRequest(BaseModel):
    """Request to build an email template."""

    project_id: int = Field(..., description="Project ID")
    template_name: str = Field(..., min_length=1, max_length=200)
    source_html: str = Field(..., min_length=1, description="Maizzle template source")
    config_overrides: dict | None = Field(None, description="Maizzle config overrides")
    is_production: bool = Field(default=False, description="Use production config")


class PreviewRequest(BaseModel):
    """Request for a live preview build."""

    source_html: str = Field(..., min_length=1)
    config_overrides: dict | None = None


class BuildResponse(BaseModel):
    """Response from a build execution."""

    id: int
    project_id: int
    template_name: str
    status: str
    compiled_html: str | None = None
    error_message: str | None = None
    is_production: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class PreviewResponse(BaseModel):
    """Response from a preview build."""

    compiled_html: str
    build_time_ms: float
