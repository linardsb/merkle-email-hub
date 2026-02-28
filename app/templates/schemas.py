"""Pydantic schemas for email templates."""

import datetime

from pydantic import BaseModel, ConfigDict, Field

# -- Template Schemas --


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    subject_line: str | None = Field(None, max_length=500)
    preheader_text: str | None = Field(None, max_length=500)


class TemplateCreate(TemplateBase):
    html_source: str = Field(default="", description="Initial HTML source for version 1")
    css_source: str | None = None


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    subject_line: str | None = Field(None, max_length=500)
    preheader_text: str | None = Field(None, max_length=500)
    status: str | None = Field(None, pattern=r"^(draft|active|archived)$")


class TemplateResponse(TemplateBase):
    id: int
    project_id: int
    status: str
    created_by_id: int
    latest_version: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# -- Version Schemas --


class VersionCreate(BaseModel):
    html_source: str = Field(..., min_length=1)
    css_source: str | None = None
    changelog: str | None = None


class VersionResponse(BaseModel):
    id: int
    template_id: int
    version_number: int
    html_source: str
    css_source: str | None
    changelog: str | None
    created_by_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
