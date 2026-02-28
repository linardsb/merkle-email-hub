"""Pydantic schemas for projects and client organizations."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = Field(None, max_length=20)
    is_active: bool | None = None


class ProjectResponse(ProjectBase):
    id: int
    status: str
    created_by_id: int
    is_active: bool
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
