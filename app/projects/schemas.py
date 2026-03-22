"""Pydantic schemas for projects and client organizations."""

import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ClientOrgBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Client organization name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-safe slug")


class ClientOrgCreate(ClientOrgBase):
    pass


class ClientOrgResponse(ClientOrgBase):
    id: int
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str | None = Field(None, description="Project description")
    client_org_id: int = Field(..., description="Client organization ID")


ClientId = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")]


class ProjectCreate(ProjectBase):
    target_clients: list[ClientId] | None = Field(
        None,
        description="Priority email client IDs from ontology (e.g. gmail_web, outlook_2019_win). QA checks all 25 clients; priority clients get prominent display and agent focus.",
        max_length=50,
    )


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    target_clients: list[ClientId] | None = None
    require_approval_for_export: bool | None = None


class ProjectResponse(ProjectBase):
    id: int
    status: str
    created_by_id: int
    is_active: bool
    target_clients: list[str] | None = None
    design_system: dict[str, Any] | None = None
    template_config: dict[str, Any] | None = None
    require_approval_for_export: bool = False
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ── Compatibility Brief ──


class UnsupportedPropertySchema(BaseModel):
    css: str
    fallback: str | None
    technique: str | None


class ClientProfileSchema(BaseModel):
    id: str
    name: str
    platform: str
    engine: str
    market_share: float
    notes: str | None
    unsupported_count: int
    unsupported_properties: list[UnsupportedPropertySchema]


class RiskMatrixEntrySchema(BaseModel):
    css: str
    unsupported_in: list[str]
    fallback: str | None


class CompatibilityBriefResponse(BaseModel):
    client_count: int
    total_risky_properties: int
    dark_mode_warning: bool
    clients: list[ClientProfileSchema]
    risk_matrix: list[RiskMatrixEntrySchema]
