"""Pydantic schemas for test personas."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    email_client: str = Field(default="gmail", max_length=100)
    device_type: str = Field(default="desktop", max_length=50)
    dark_mode: bool = False
    viewport_width: int = Field(default=600, ge=200, le=2000)
    os_name: str = Field(default="macOS", max_length=50)


class PersonaCreate(PersonaBase):
    pass


class PersonaResponse(PersonaBase):
    id: int
    is_preset: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
