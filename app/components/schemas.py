"""Pydantic schemas for email component library."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ComponentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    category: str = Field(default="general", max_length=50)


class ComponentCreate(ComponentBase):
    html_source: str = Field(..., min_length=1, description="Initial HTML source")
    css_source: str | None = None


class ComponentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(None, max_length=50)


class ComponentResponse(ComponentBase):
    id: int
    created_by_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    latest_version: int | None = None
    compatibility_badge: str | None = None  # "full" | "partial" | "issues" | None

    model_config = ConfigDict(from_attributes=True)


class ClientCompatibility(BaseModel):
    """Per-client compatibility entry."""

    client_id: str
    client_name: str
    level: str  # "full" | "partial" | "none"
    platform: str


class ComponentCompatibilityResponse(BaseModel):
    """Aggregated compatibility for a component."""

    component_id: int
    component_name: str
    version_number: int
    full_count: int
    partial_count: int
    none_count: int
    clients: list[ClientCompatibility]
    qa_score: float | None = None
    last_checked: datetime.datetime | None = None


class VersionCreate(BaseModel):
    html_source: str = Field(..., min_length=1)
    css_source: str | None = None
    changelog: str | None = None
    compatibility: dict[str, str] | None = None


class VersionResponse(BaseModel):
    id: int
    component_id: int
    version_number: int
    html_source: str
    css_source: str | None
    changelog: str | None
    compatibility: dict[str, str] | None = None
    created_by_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
