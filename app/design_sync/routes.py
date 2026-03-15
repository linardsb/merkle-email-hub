# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for design sync."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.design_sync.schemas import (
    ComponentListResponse,
    ConnectionCreateRequest,
    ConnectionDeleteRequest,
    ConnectionResponse,
    ConnectionSyncRequest,
    DesignTokensResponse,
    ExportImageRequest,
    FileStructureResponse,
    ImageExportResponse,
)
from app.design_sync.service import DesignSyncService

router = APIRouter(prefix="/api/v1/design-sync", tags=["design-sync"])


def get_service(db: AsyncSession = Depends(get_db)) -> DesignSyncService:
    return DesignSyncService(db)


@router.get("/connections", response_model=list[ConnectionResponse])
@limiter.limit("30/minute")
async def list_connections(
    request: Request,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> list[ConnectionResponse]:
    """List all design tool connections."""
    _ = request
    return await service.list_connections(current_user)


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
@limiter.limit("30/minute")
async def get_connection(
    connection_id: int,
    request: Request,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> ConnectionResponse:
    """Get a single design connection."""
    _ = request
    return await service.get_connection(connection_id, current_user)


@router.get("/connections/{connection_id}/tokens", response_model=DesignTokensResponse)
@limiter.limit("30/minute")
async def get_tokens(
    connection_id: int,
    request: Request,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> DesignTokensResponse:
    """Get design tokens for a connection."""
    _ = request
    return await service.get_tokens(connection_id, current_user)


@router.post("/connections", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_connection(
    request: Request,
    data: ConnectionCreateRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ConnectionResponse:
    """Create a new design tool connection."""
    _ = request
    return await service.create_connection(data, current_user)


@router.post("/connections/delete")
@limiter.limit("10/minute")
async def delete_connection(
    request: Request,
    data: ConnectionDeleteRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> dict[str, bool]:
    """Delete a design connection."""
    _ = request
    result = await service.delete_connection(data.id, current_user)
    return {"success": result}


@router.post("/connections/sync", response_model=ConnectionResponse)
@limiter.limit("5/minute")
async def sync_connection(
    request: Request,
    data: ConnectionSyncRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ConnectionResponse:
    """Trigger a design token sync."""
    _ = request
    return await service.sync_connection(data.id, current_user)


# ── Phase 12.1: File Structure, Components, Image Export ──


@router.get(
    "/connections/{connection_id}/file-structure",
    response_model=FileStructureResponse,
)
@limiter.limit("15/minute")
async def get_file_structure(
    connection_id: int,
    request: Request,
    depth: int | None = Query(default=2, ge=1, description="Max tree depth (None = unlimited)"),
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> FileStructureResponse:
    """Get the hierarchical file structure of a design file."""
    _ = request
    return await service.get_file_structure(connection_id, current_user, depth=depth)


@router.get(
    "/connections/{connection_id}/components",
    response_model=ComponentListResponse,
)
@limiter.limit("20/minute")
async def list_components(
    connection_id: int,
    request: Request,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> ComponentListResponse:
    """List reusable components defined in the design file."""
    _ = request
    return await service.list_components(connection_id, current_user)


@router.post(
    "/connections/export-images",
    response_model=ImageExportResponse,
)
@limiter.limit("5/minute")
async def export_images(
    request: Request,
    data: ExportImageRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ImageExportResponse:
    """Export design nodes as images."""
    _ = request
    return await service.export_images(
        data.connection_id,
        current_user,
        data.node_ids,
        format=data.format,
        scale=data.scale,
    )
