"""Pydantic schemas for briefs."""

import datetime
from typing import cast

from pydantic import BaseModel, ConfigDict, Field

# ── Constants ──

PLATFORMS = {"jira", "asana", "monday", "clickup", "trello", "notion", "wrike", "basecamp"}
ITEM_STATUSES = {"open", "in_progress", "done", "cancelled"}

# ── Requests ──


class ConnectionCreateRequest(BaseModel):
    """Request to create a brief connection."""

    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    platform: str = Field(..., min_length=1, max_length=20, description="Platform identifier")
    project_url: str = Field(..., min_length=1, max_length=500, description="External project URL")
    credentials: dict[str, str] = Field(..., description="Platform-specific credentials")
    project_id: int | None = Field(default=None, description="Link to a hub project")


class ConnectionDeleteRequest(BaseModel):
    """Request to delete a connection."""

    id: int = Field(..., description="Connection ID to delete")


class ConnectionSyncRequest(BaseModel):
    """Request to sync items from a connection."""

    id: int = Field(..., description="Connection ID to sync")


class ImportRequest(BaseModel):
    """Request to import brief items into a project."""

    brief_item_ids: list[int] = Field(..., min_length=1, description="Item IDs to import")
    project_name: str = Field(..., min_length=1, max_length=200, description="Target project name")


# ── Responses ──


class ConnectionResponse(BaseModel):
    """Brief connection response."""

    id: int
    name: str
    platform: str
    project_url: str
    external_project_id: str
    credential_last4: str
    status: str
    error_message: str | None = None
    last_synced_at: datetime.datetime | None = None
    project_id: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, conn: object) -> "ConnectionResponse":
        """Build response from a BriefConnection model."""
        from app.briefs.models import BriefConnection

        if not isinstance(conn, BriefConnection):
            msg = "Expected BriefConnection instance"
            raise TypeError(msg)
        return cls(
            id=conn.id,
            name=conn.name,
            platform=conn.platform,
            project_url=conn.project_url,
            external_project_id=conn.external_project_id,
            credential_last4=conn.credential_last4,
            status=conn.status,
            error_message=conn.error_message,
            last_synced_at=conn.last_synced_at,
            project_id=conn.project_id,
            created_at=cast(datetime.datetime, conn.created_at),
            updated_at=cast(datetime.datetime, conn.updated_at),
        )


class ResourceResponse(BaseModel):
    """Brief resource response."""

    id: int
    type: str
    filename: str
    url: str
    size_bytes: int | None = None

    model_config = ConfigDict(from_attributes=True)


class AttachmentResponse(BaseModel):
    """Brief attachment response."""

    id: int
    filename: str
    url: str
    size_bytes: int | None = None

    model_config = ConfigDict(from_attributes=True)


class BriefItemResponse(BaseModel):
    """Brief item response (list view)."""

    id: int
    connection_id: int
    external_id: str
    title: str
    status: str
    priority: str | None = None
    assignees: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    due_date: datetime.datetime | None = None
    thumbnail_url: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class BriefDetailResponse(BaseModel):
    """Brief item detail response (includes description, resources, attachments)."""

    id: int
    connection_id: int
    external_id: str
    title: str
    description: str | None = None
    status: str
    priority: str | None = None
    assignees: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    due_date: datetime.datetime | None = None
    thumbnail_url: str | None = None
    resources: list[ResourceResponse] = Field(default_factory=lambda: [])
    attachments: list[AttachmentResponse] = Field(default_factory=lambda: [])
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ImportResponse(BaseModel):
    """Response from importing brief items."""

    project_id: int
