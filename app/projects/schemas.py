"""Pydantic schemas for projects and client organizations."""

import datetime
from typing import Annotated

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
        description="Target email client IDs from ontology (e.g. gmail_web, outlook_2019_win)",
        max_length=50,
    )


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    target_clients: list[ClientId] | None = None


class ProjectResponse(ProjectBase):
    id: int
    status: str
    created_by_id: int
    is_active: bool
    target_clients: list[str] | None = None
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
