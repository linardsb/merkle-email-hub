# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for ESP bidirectional sync."""

from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.connectors.sync_schemas import (
    BulkExportRequest,
    BulkExportResponse,
    ESPConnectionCreate,
    ESPConnectionResponse,
    ESPImportRequest,
    ESPPushRequest,
    ESPTemplate,
    ESPTemplateList,
    ExportRequest,
    ExportResponse,
    TokenRewriteRequest,
    TokenRewriteResponse,
)
from app.connectors.sync_service import ConnectorSyncService
from app.core.database import get_db
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/v1/connectors/sync", tags=["esp-sync"])


def get_service(db: AsyncSession = Depends(get_db)) -> ConnectorSyncService:  # noqa: B008
    return ConnectorSyncService(db)


# ── Connection CRUD ──


@router.post(
    "/connections",
    response_model=ESPConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_connection(
    request: Request,
    data: ESPConnectionCreate,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ESPConnectionResponse:
    """Create a new ESP connection with validated credentials."""
    _ = request
    return await service.create_connection(data, current_user)


@router.get("/connections", response_model=list[ESPConnectionResponse])
@limiter.limit("30/minute")
async def list_connections(
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("viewer")),  # noqa: B008
) -> list[ESPConnectionResponse]:
    """List all ESP connections accessible to the current user."""
    _ = request
    return await service.list_connections(current_user)


@router.get("/connections/{connection_id}", response_model=ESPConnectionResponse)
@limiter.limit("30/minute")
async def get_connection(
    connection_id: int,
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("viewer")),  # noqa: B008
) -> ESPConnectionResponse:
    """Get a single ESP connection."""
    _ = request
    return await service.get_connection(connection_id, current_user)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_connection(
    connection_id: int,
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> None:
    """Delete an ESP connection."""
    _ = request
    await service.delete_connection(connection_id, current_user)


# ── Remote Template Operations ──


@router.get("/connections/{connection_id}/templates", response_model=ESPTemplateList)
@limiter.limit("20/minute")
async def list_remote_templates(
    connection_id: int,
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ESPTemplateList:
    """List templates from the remote ESP."""
    _ = request
    return await service.list_remote_templates(connection_id, current_user)


@router.get(
    "/connections/{connection_id}/templates/{template_id}",
    response_model=ESPTemplate,
)
@limiter.limit("20/minute")
async def get_remote_template(
    connection_id: int,
    template_id: str,
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ESPTemplate:
    """Get a single template from the remote ESP."""
    _ = request
    return await service.get_remote_template(connection_id, template_id, current_user)


@router.post(
    "/connections/{connection_id}/import",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def import_template(
    connection_id: int,
    data: ESPImportRequest,
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> dict[str, int]:
    """Import a remote ESP template into the local Hub."""
    _ = request
    local_id = await service.import_template(connection_id, data.template_id, current_user)
    return {"template_id": local_id}


@router.post(
    "/connections/{connection_id}/push",
    response_model=ESPTemplate,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def push_template(
    connection_id: int,
    data: ESPPushRequest,
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ESPTemplate:
    """Push a local Hub template to the remote ESP."""
    _ = request
    return await service.push_template(connection_id, data.template_id, current_user)


# ── Export Orchestration ──


@router.post("/export", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def export_template(
    data: ExportRequest,
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ExportResponse:
    """Export HTML to an ESP with optional token rewriting."""
    _ = request
    return await service.export_template(
        html=data.html,
        template_id=data.template_id,
        target_esp=data.target_esp,
        connection_id=data.connection_id,
        template_name=data.template_name,
        source_esp=data.source_esp,
        rewrite_tokens=data.rewrite_tokens,
        user=current_user,
    )


@router.post("/export-bulk", response_model=BulkExportResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def export_templates_bulk(
    data: BulkExportRequest,
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> BulkExportResponse:
    """Export multiple templates to an ESP with per-item error isolation."""
    _ = request
    return await service.export_templates_bulk(
        template_ids=data.template_ids,
        target_esp=data.target_esp,
        connection_id=data.connection_id,
        rewrite_tokens=data.rewrite_tokens,
        user=current_user,
    )


# ── Token Rewriting ──


@router.post("/rewrite-tokens", response_model=TokenRewriteResponse)
@limiter.limit("30/minute")
async def rewrite_tokens(
    data: TokenRewriteRequest,
    request: Request,
    service: ConnectorSyncService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> TokenRewriteResponse:
    """Rewrite ESP personalisation tokens from one format to another."""
    _ = request
    _ = current_user
    result = await service.rewrite_tokens(data.html, data.target_esp, data.source_esp)
    return TokenRewriteResponse(
        html=result.html,
        source_esp=result.source_esp,
        target_esp=result.target_esp,
        tokens_rewritten=result.tokens_rewritten,
        warnings=list(result.warnings),
    )
