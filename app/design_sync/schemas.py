"""Pydantic schemas for design sync."""

import datetime
from typing import cast

from pydantic import BaseModel, ConfigDict, Field

# ── Requests ──


class ConnectionCreateRequest(BaseModel):
    """Request to create a design tool connection."""

    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    provider: str = Field(default="figma", max_length=50, description="Design tool provider")
    file_url: str = Field(..., min_length=1, max_length=500, description="Design file URL")
    access_token: str = Field(..., min_length=1, description="Provider access token / PAT")
    project_id: int | None = Field(default=None, description="Link to a project")


class ConnectionDeleteRequest(BaseModel):
    """Request to delete a connection."""

    id: int = Field(..., description="Connection ID to delete")


class ConnectionSyncRequest(BaseModel):
    """Request to sync tokens from a connection."""

    id: int = Field(..., description="Connection ID to sync")


# ── Responses ──


class ConnectionResponse(BaseModel):
    """Design connection response (maps DB fields for frontend compat)."""

    id: int
    name: str
    provider: str
    file_key: str = Field(description="Provider file reference")
    file_url: str
    access_token_last4: str = Field(description="Last 4 chars of token for display")
    status: str
    error_message: str | None = None
    last_synced_at: datetime.datetime | None = None
    project_id: int | None = None
    project_name: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(
        cls,
        conn: "object",
        project_name: str | None = None,
    ) -> "ConnectionResponse":
        """Build response from a DesignConnection model, mapping field names."""
        from app.design_sync.models import DesignConnection

        if not isinstance(conn, DesignConnection):
            msg = "Expected DesignConnection instance"
            raise TypeError(msg)
        return cls(
            id=conn.id,
            name=conn.name,
            provider=conn.provider,
            file_key=conn.file_ref,
            file_url=conn.file_url,
            access_token_last4=conn.token_last4,
            status=conn.status,
            error_message=conn.error_message,
            last_synced_at=conn.last_synced_at,
            project_id=conn.project_id,
            project_name=project_name,
            created_at=cast(datetime.datetime, conn.created_at),
            updated_at=cast(datetime.datetime, conn.updated_at),
        )


class DesignColorResponse(BaseModel):
    """Single design colour."""

    name: str
    hex: str
    opacity: float


class DesignTypographyResponse(BaseModel):
    """Single typography style."""

    name: str
    family: str
    weight: str
    size: float
    lineHeight: float


class DesignSpacingResponse(BaseModel):
    """Single spacing value."""

    name: str
    value: float


class DesignTokensResponse(BaseModel):
    """Design tokens extracted from a connection."""

    connection_id: int
    colors: list[DesignColorResponse]
    typography: list[DesignTypographyResponse]
    spacing: list[DesignSpacingResponse]
    extracted_at: datetime.datetime
