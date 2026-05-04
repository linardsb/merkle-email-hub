# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for briefs."""

from fastapi import APIRouter, Depends, Query
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.briefs.schemas import (
    BriefDetailResponse,
    BriefItemResponse,
    ConnectionCreateRequest,
    ConnectionDeleteRequest,
    ConnectionResponse,
    ConnectionSyncRequest,
    ImportRequest,
    ImportResponse,
)
from app.briefs.service import BriefService
from app.core.rate_limit import limiter
from app.core.scoped_db import get_scoped_db

router = APIRouter(prefix="/api/v1/briefs", tags=["briefs"])


def get_service(db: AsyncSession = Depends(get_scoped_db)) -> BriefService:
    return BriefService(db)


# ── Connections ──


@router.post("/connections", response_model=ConnectionResponse)
@limiter.limit("10/minute")
async def create_connection(
    request: Request,
    data: ConnectionCreateRequest,
    service: BriefService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ConnectionResponse:
    """Create a new brief connection to a project management platform."""
    _ = request
    return await service.create_connection(data, current_user)


@router.get("/connections", response_model=list[ConnectionResponse])
@limiter.limit("30/minute")
async def list_connections(
    request: Request,
    service: BriefService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> list[ConnectionResponse]:
    """List all brief connections."""
    _ = request
    return await service.list_connections(current_user)


@router.post("/connections/delete")
@limiter.limit("10/minute")
async def delete_connection(
    request: Request,
    data: ConnectionDeleteRequest,
    service: BriefService = Depends(get_service),
    current_user: User = Depends(require_role("admin")),
) -> dict[str, bool]:
    """Delete a brief connection."""
    _ = request
    result = await service.delete_connection(data.id, current_user)
    return {"success": result}


@router.post("/connections/sync", response_model=ConnectionResponse)
@limiter.limit("10/minute")
async def sync_connection(
    request: Request,
    data: ConnectionSyncRequest,
    service: BriefService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ConnectionResponse:
    """Trigger a sync for a brief connection."""
    _ = request
    return await service.sync_connection(data.id, current_user)


# ── Items ──


@router.get("/connections/{connection_id}/items", response_model=list[BriefItemResponse])
@limiter.limit("30/minute")
async def list_items_for_connection(
    connection_id: int,
    request: Request,
    service: BriefService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> list[BriefItemResponse]:
    """List items for a specific connection."""
    _ = request
    return await service.list_items_for_connection(connection_id, current_user)


@router.get("/items", response_model=list[BriefItemResponse])
@limiter.limit("30/minute")
async def list_items(
    request: Request,
    platform: str | None = Query(default=None, description="Filter by platform"),
    status: str | None = Query(default=None, description="Filter by status"),
    search: str | None = Query(default=None, max_length=200, description="Search by title"),
    service: BriefService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> list[BriefItemResponse]:
    """List all brief items with optional filters."""
    _ = request
    return await service.list_items(current_user, platform=platform, status=status, search=search)


@router.get("/items/{item_id}", response_model=BriefDetailResponse)
@limiter.limit("30/minute")
async def get_item_detail(
    item_id: int,
    request: Request,
    service: BriefService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> BriefDetailResponse:
    """Get item detail with description, resources, and attachments."""
    _ = request
    return await service.get_item_detail(item_id, current_user)


# ── Import ──


@router.post("/import", response_model=ImportResponse)
@limiter.limit("10/minute")
async def import_items(
    request: Request,
    data: ImportRequest,
    service: BriefService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ImportResponse:
    """Import brief items into a project."""
    _ = request
    return await service.import_items(data.brief_item_ids, data.project_name, current_user)
