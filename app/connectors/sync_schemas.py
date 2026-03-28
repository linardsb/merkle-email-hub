"""Pydantic schemas for ESP bidirectional sync."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ESPTemplate(BaseModel):
    """A template stored in an external ESP."""

    id: str
    name: str
    html: str
    esp_type: str
    created_at: str
    updated_at: str


class ESPTemplateList(BaseModel):
    """Paginated list of ESP templates."""

    templates: list[ESPTemplate]
    count: int


class ESPConnectionCreate(BaseModel):
    """Request to create an ESP connection."""

    esp_type: str = Field(
        ..., pattern=r"^(braze|sfmc|adobe_campaign|taxi|klaviyo|hubspot)$", max_length=50
    )
    name: str = Field(..., min_length=1, max_length=200)
    project_id: int
    credentials: dict[str, str] = Field(
        ..., description="ESP-specific credentials (encrypted at rest)"
    )


class ESPConnectionResponse(BaseModel):
    """Response for an ESP connection."""

    id: int
    esp_type: str
    name: str
    status: str
    credentials_hint: str
    project_id: int
    project_name: str | None = None
    last_synced_at: datetime.datetime | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ESPImportRequest(BaseModel):
    """Request to import a template from an ESP into Hub."""

    template_id: str = Field(..., min_length=1, description="Remote ESP template ID")


class ESPPushRequest(BaseModel):
    """Request to push a local Hub template to an ESP."""

    template_id: int = Field(..., description="Local Hub template ID")
