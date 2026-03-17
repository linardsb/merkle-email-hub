"""Pydantic schemas for the prompt template store API."""

from datetime import datetime

from pydantic import BaseModel, Field


class PromptTemplateCreate(BaseModel):
    agent_id: str = Field(max_length=64)
    variant: str = Field(default="default", max_length=64)
    content: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=500)


class PromptTemplateResponse(BaseModel):
    id: int
    agent_id: str
    variant: str
    version: int
    content: str
    description: str | None
    active: bool
    created_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptTemplateListResponse(BaseModel):
    templates: list[PromptTemplateResponse]


class PromptActivateRequest(BaseModel):
    template_id: int


class PromptSeedResponse(BaseModel):
    seeded: dict[str, int]
