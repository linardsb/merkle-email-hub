"""Pydantic schemas for client approval portal."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApprovalCreate(BaseModel):
    build_id: int = Field(..., description="Email build to submit for approval")
    project_id: int = Field(..., description="Project ID")


class ApprovalDecision(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected|revision_requested)$")
    review_note: str | None = None


class FeedbackCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    feedback_type: str = Field(default="comment", max_length=20)


class ApprovalResponse(BaseModel):
    id: int
    build_id: int
    project_id: int
    status: str
    requested_by_id: int
    reviewed_by_id: int | None = None
    review_note: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackResponse(BaseModel):
    id: int
    approval_id: int
    author_id: int
    content: str
    feedback_type: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AuditResponse(BaseModel):
    id: int
    approval_id: int
    action: str
    actor_id: int
    details: str | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
