"""Taxi for Email API schemas."""

from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    content: str
    syntax_version: str = "2"


class TemplateUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    syntax_version: str | None = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    content: str
    syntax_version: str
    created_at: str
    updated_at: str


class TemplateListResponse(BaseModel):
    count: int
    templates: list[TemplateResponse]
