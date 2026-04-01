"""REST endpoints for unified progress tracking."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.exceptions import NotFoundError
from app.core.progress import OperationStatus, ProgressTracker

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


class ProgressResponse(BaseModel):
    """Lightweight progress payload (~200 bytes)."""

    operation_id: str
    operation_type: str
    status: OperationStatus
    progress: int
    message: str
    error: str | None = None


@router.get("/{operation_id}", response_model=ProgressResponse)
async def get_progress(
    operation_id: str,
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> ProgressResponse:
    """Get progress for a single operation."""
    entry = ProgressTracker.get(operation_id)
    if not entry:
        raise NotFoundError(f"Operation {operation_id} not found")
    return ProgressResponse(
        operation_id=entry.operation_id,
        operation_type=entry.operation_type,
        status=entry.status,
        progress=entry.progress,
        message=entry.message,
        error=entry.error,
    )


@router.get("/active/list", response_model=list[ProgressResponse])
async def get_active_operations(
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[ProgressResponse]:
    """List all in-flight operations."""
    entries = ProgressTracker.get_active()
    return [
        ProgressResponse(
            operation_id=e.operation_id,
            operation_type=e.operation_type,
            status=e.status,
            progress=e.progress,
            message=e.message,
            error=e.error,
        )
        for e in entries
    ]
