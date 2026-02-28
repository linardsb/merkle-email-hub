"""Pydantic schemas for the example items feature."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    """Shared item attributes for create and response schemas."""

    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    description: str | None = Field(None, description="Item description")
    status: str = Field(default="active", max_length=20, description="Status: active/archived")


class ItemCreate(ItemBase):
    """Schema for creating an item."""


class ItemUpdate(BaseModel):
    """Schema for updating an item. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = Field(None, max_length=20)
    is_active: bool | None = None


class ItemResponse(ItemBase):
    """Schema for item responses."""

    id: int
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
