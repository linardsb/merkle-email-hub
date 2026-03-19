"""Pydantic request/response schemas for template upload pipeline."""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field


class UploadStatus(enum.StrEnum):
    """Status of a template upload."""

    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class SlotPreview(BaseModel):
    """Preview of a detected template slot."""

    slot_id: str
    slot_type: str
    selector: str
    required: bool
    max_chars: int | None = None
    content_preview: str = ""


class TokenPreview(BaseModel):
    """Preview of extracted design tokens."""

    colors: dict[str, str] = Field(default_factory=dict)
    fonts: dict[str, str] = Field(default_factory=dict)
    font_sizes: dict[str, str] = Field(default_factory=dict)
    spacing: dict[str, str] = Field(default_factory=dict)


class SectionPreview(BaseModel):
    """Preview of a detected template section."""

    section_id: str
    component_name: str
    element_count: int
    layout_type: str


class AnalysisPreview(BaseModel):
    """Full analysis preview returned after upload."""

    upload_id: int
    sections: list[SectionPreview]
    slots: list[SlotPreview]
    tokens: TokenPreview
    esp_platform: str | None = None
    layout_type: str
    column_count: int
    complexity_score: int
    suggested_name: str
    suggested_description: str


class ConfirmRequest(BaseModel):
    """Request body for confirming a template upload."""

    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    slot_edits: dict[str, dict[str, object]] = Field(default_factory=dict)
    token_edits: dict[str, dict[str, str]] = Field(default_factory=dict)
    project_id: int | None = None


class TemplateUploadResponse(BaseModel):
    """Response after confirming a template upload."""

    id: int
    status: UploadStatus
    template_name: str
    created_at: datetime
