# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for email template management."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.templates import get_template_registry
from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.shared.schemas import PaginatedResponse, PaginationParams
from app.templates.schemas import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
    VersionCreate,
    VersionResponse,
)
from app.templates.service import TemplateService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["templates"])


def get_service(db: AsyncSession = Depends(get_db)) -> TemplateService:  # noqa: B008
    return TemplateService(db)


# -- Project-scoped (list + create) --


@router.get(
    "/projects/{project_id}/templates",
    response_model=PaginatedResponse[TemplateResponse],
)
@limiter.limit("30/minute")
async def list_templates(
    request: Request,
    project_id: int,
    pagination: PaginationParams = Depends(),  # noqa: B008
    search: str | None = Query(None, max_length=200),
    status_filter: str | None = Query(None, alias="status", pattern=r"^(draft|active|archived)$"),
    service: TemplateService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> PaginatedResponse[TemplateResponse]:
    """List templates in a project."""
    _ = request
    return await service.list_templates(
        project_id, current_user, pagination, search=search, status=status_filter
    )


@router.post(
    "/projects/{project_id}/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_template(
    request: Request,
    project_id: int,
    data: TemplateCreate,
    service: TemplateService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> TemplateResponse:
    """Create a new template in a project."""
    _ = request
    return await service.create_template(project_id, data, current_user)


# -- Template-scoped (get/update/delete) --


@router.get("/templates/{template_id}", response_model=TemplateResponse)
@limiter.limit("30/minute")
async def get_template(
    request: Request,
    template_id: int,
    service: TemplateService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> TemplateResponse:
    """Get a template by ID. Verifies project access."""
    _ = request
    return await service.get_template(template_id, current_user)


@router.patch("/templates/{template_id}", response_model=TemplateResponse)
@limiter.limit("10/minute")
async def update_template(
    request: Request,
    template_id: int,
    data: TemplateUpdate,
    service: TemplateService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> TemplateResponse:
    """Update template metadata."""
    _ = request
    return await service.update_template(template_id, data, current_user)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_template(
    request: Request,
    template_id: int,
    service: TemplateService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> None:
    """Soft delete a template."""
    _ = request
    await service.delete_template(template_id, current_user)


# -- Versions --


@router.post(
    "/templates/{template_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_version(
    request: Request,
    template_id: int,
    data: VersionCreate,
    service: TemplateService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> VersionResponse:
    """Save a new version of the template (each save = new version)."""
    _ = request
    return await service.create_version(template_id, data, current_user)


@router.get(
    "/templates/{template_id}/versions",
    response_model=list[VersionResponse],
)
@limiter.limit("30/minute")
async def list_versions(
    request: Request,
    template_id: int,
    service: TemplateService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[VersionResponse]:
    """List all versions of a template (newest first)."""
    _ = request
    return await service.list_versions(template_id, current_user)


@router.get(
    "/templates/{template_id}/versions/{version_number}",
    response_model=VersionResponse,
)
@limiter.limit("30/minute")
async def get_version(
    request: Request,
    template_id: int,
    version_number: int,
    service: TemplateService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VersionResponse:
    """Get a specific version of a template."""
    _ = request
    return await service.get_version(template_id, version_number, current_user)


@router.post(
    "/templates/{template_id}/restore/{version_number}",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def restore_version(
    request: Request,
    template_id: int,
    version_number: int,
    service: TemplateService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> VersionResponse:
    """Restore template to a previous version (creates a new version with old content)."""
    _ = request
    return await service.restore_version(template_id, version_number, current_user)


# -- Golden template precompilation --


@router.post(
    "/templates/precompile",
    response_model=dict[str, object],
    status_code=200,
)
@limiter.limit("2/minute")
async def precompile_templates(
    request: Request,
    current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> dict[str, object]:
    """Trigger batch precompilation of all golden templates. Admin only."""
    _ = request
    registry = get_template_registry()
    report = registry.precompile_all()

    logger.info(
        "templates.precompile_endpoint",
        user_id=current_user.id,
        total=report.total,
        succeeded=report.succeeded,
        failed=report.failed,
    )

    return {
        "total": report.total,
        "succeeded": report.succeeded,
        "failed": report.failed,
        "total_size_reduction_bytes": report.total_size_reduction_bytes,
        "avg_compile_time_ms": report.avg_compile_time_ms,
        "errors": report.errors,
    }
