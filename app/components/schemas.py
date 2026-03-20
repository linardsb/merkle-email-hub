"""Pydantic schemas for email component library."""

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ai.templates.models import SlotType


class SlotHintSchema(BaseModel):
    """Slot annotation for a component version."""

    slot_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    slot_type: SlotType
    selector: str = Field(..., min_length=1, max_length=200)
    required: bool = True
    max_chars: int | None = Field(None, ge=1, le=5000)


class DesignOrigin(BaseModel):
    """Design tool origin metadata parsed from compatibility JSON."""

    provider: str = Field(..., description="Design tool provider (e.g. figma, penpot)")
    file_key: str = Field(..., description="Design file identifier")
    component_id: str = Field(..., description="Component ID within the design file")
    component_name: str | None = Field(None, description="Human-readable component name")


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
    design_origin: DesignOrigin | None = None

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
    slot_definitions: list[SlotHintSchema] | None = None
    default_tokens: dict[str, Any] | None = None


class VersionResponse(BaseModel):
    id: int
    component_id: int
    version_number: int
    html_source: str
    css_source: str | None
    changelog: str | None
    compatibility: dict[str, str] | None = None
    slot_definitions: list[SlotHintSchema] | None = None
    default_tokens: dict[str, Any] | None = None
    design_origin: DesignOrigin | None = None
    created_by_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AssignDesignOriginRequest(BaseModel):
    """Request to assign a design component to a Hub component."""

    connection_id: int = Field(..., description="Design connection ID")
    design_component_id: str = Field(
        ..., min_length=1, max_length=500, description="Component ID in the design tool"
    )
    design_component_name: str | None = Field(
        None, max_length=200, description="Human-readable component name"
    )
