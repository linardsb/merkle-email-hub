# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for design sync."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.design_sync.schemas import (
    AnalyzeLayoutRequest,
    BrowseFilesRequest,
    BrowseFilesResponse,
    ComponentListResponse,
    ConnectionCreateRequest,
    ConnectionDeleteRequest,
    ConnectionLinkProjectRequest,
    ConnectionResponse,
    ConnectionSyncRequest,
    ConnectionUpdateTokenRequest,
    ConvertImportRequest,
    DesignTokensResponse,
    DownloadAssetsRequest,
    DownloadAssetsResponse,
    ExportImageRequest,
    ExtractComponentsRequest,
    ExtractComponentsResponse,
    FileStructureResponse,
    GenerateBriefRequest,
    GenerateBriefResponse,
    ImageExportResponse,
    ImportResponse,
    LayoutAnalysisResponse,
    StartImportRequest,
    UpdateImportBriefRequest,
)
from app.design_sync.service import DesignSyncService

router = APIRouter(prefix="/api/v1/design-sync", tags=["design-sync"])


def get_service(db: AsyncSession = Depends(get_db)) -> DesignSyncService:
    return DesignSyncService(db)


@router.post("/browse-files", response_model=BrowseFilesResponse)
@limiter.limit("30/minute")
async def browse_files(
    request: Request,
    data: BrowseFilesRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> BrowseFilesResponse:
    """Browse design files from a provider before creating a connection.

    Token is passed in the request body, NOT logged or persisted.
    """
    _ = request
    _ = current_user  # auth required but no BOLA check (pre-connection)
    return await service.browse_files(data.provider, data.access_token)


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


@router.patch(
    "/connections/{connection_id}/token",
    response_model=ConnectionResponse,
)
@limiter.limit("10/minute")
async def refresh_connection_token(
    connection_id: int,
    request: Request,
    data: ConnectionUpdateTokenRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ConnectionResponse:
    """Refresh the access token for a design connection."""
    _ = request
    return await service.refresh_token(connection_id, data.access_token, current_user)


@router.patch(
    "/connections/{connection_id}/project",
    response_model=ConnectionResponse,
)
@limiter.limit("10/minute")
async def link_connection_to_project(
    connection_id: int,
    request: Request,
    data: ConnectionLinkProjectRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ConnectionResponse:
    """Link or unlink a design connection to a project."""
    _ = request
    return await service.link_connection_to_project(connection_id, data.project_id, current_user)


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
@limiter.limit("20/minute")
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


# ── Phase 12.2: Asset Storage ──


@router.post(
    "/connections/download-assets",
    response_model=DownloadAssetsResponse,
)
@limiter.limit("5/minute")
async def download_assets(
    request: Request,
    data: DownloadAssetsRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> DownloadAssetsResponse:
    """Export and download design assets to local storage."""
    _ = request
    return await service.download_assets(
        data.connection_id,
        current_user,
        data.node_ids,
        format=data.format,
        scale=data.scale,
    )


@router.get(
    "/assets/{connection_id}/{filename}",
)
@limiter.limit("60/minute")
async def serve_asset(
    connection_id: int,
    filename: str,
    request: Request,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> FileResponse:
    """Serve a stored design asset file."""
    _ = request
    # BOLA check: verify user can access this connection
    await service.get_connection(connection_id, current_user)
    # Get validated path
    path = service.get_asset_path(connection_id, filename)
    # Determine media type from extension
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
    }
    media_type = media_types.get(path.suffix, "application/octet-stream")
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Content-Security-Policy": "default-src 'none'"},
    )


# ── Phase 12.4: Layout Analysis & Brief Generation ──


@router.post(
    "/connections/analyze-layout",
    response_model=LayoutAnalysisResponse,
)
@limiter.limit("10/minute")
async def analyze_layout(
    request: Request,
    data: AnalyzeLayoutRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> LayoutAnalysisResponse:
    """Analyze design file layout and detect email sections (preview)."""
    _ = request
    return await service.analyze_layout(
        data.connection_id,
        current_user,
        selected_node_ids=data.selected_node_ids or None,
    )


@router.post(
    "/connections/generate-brief",
    response_model=GenerateBriefResponse,
)
@limiter.limit("5/minute")
async def generate_brief(
    request: Request,
    data: GenerateBriefRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> GenerateBriefResponse:
    """Generate a Scaffolder-compatible campaign brief from design analysis."""
    _ = request
    return await service.generate_brief(
        data.connection_id,
        current_user,
        selected_node_ids=data.selected_node_ids or None,
        include_tokens=data.include_tokens,
    )


# ── Phase 12.6: Component Extraction ──


@router.post(
    "/connections/{connection_id}/extract-components",
    response_model=ExtractComponentsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("5/minute")
async def extract_components(
    connection_id: int,
    request: Request,
    body: ExtractComponentsRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ExtractComponentsResponse:
    """Extract Figma components into Hub components with AI-generated HTML.

    Returns immediately with import_id for polling status via
    GET /imports/{import_id}.
    """
    _ = request
    return await service.extract_components(
        connection_id=connection_id,
        user=current_user,
        component_ids=body.component_ids,
        generate_html=body.generate_html,
    )


# ── Phase 12.5: Design Import & Conversion Pipeline ──


@router.post("/imports", response_model=ImportResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_import(
    request: Request,
    data: StartImportRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ImportResponse:
    """Create a design import job with a brief for Scaffolder conversion."""
    _ = request
    return await service.create_design_import(data, current_user)


@router.get("/imports/by-template/{template_id}", response_model=ImportResponse | None)
@limiter.limit("30/minute")
async def get_import_by_template(
    template_id: int,
    request: Request,
    project_id: int = Query(..., description="Project ID for BOLA check"),
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> ImportResponse | None:
    """Get the design import that produced a template (for design reference panel)."""
    _ = request
    return await service.get_import_by_template(template_id, project_id, current_user)


@router.get("/imports/{import_id}", response_model=ImportResponse)
@limiter.limit("30/minute")
async def get_import(
    import_id: int,
    request: Request,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("viewer")),
) -> ImportResponse:
    """Get import status and result (poll this until completed/failed)."""
    _ = request
    return await service.get_design_import(import_id, current_user)


@router.patch("/imports/{import_id}/brief", response_model=ImportResponse)
@limiter.limit("10/minute")
async def update_import_brief(
    import_id: int,
    request: Request,
    data: UpdateImportBriefRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ImportResponse:
    """Edit the brief before triggering conversion. Only works in 'pending' state."""
    _ = request
    return await service.update_import_brief(import_id, data.generated_brief, current_user)


@router.post(
    "/imports/{import_id}/convert",
    response_model=ImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("3/minute")
async def convert_import(
    import_id: int,
    request: Request,
    body: ConvertImportRequest,
    service: DesignSyncService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> ImportResponse:
    """Trigger the Scaffolder conversion pipeline. Returns immediately; poll GET /imports/{id}."""
    _ = request
    return await service.start_conversion(
        import_id,
        current_user,
        run_qa=body.run_qa,
        output_mode=body.output_mode,
    )
