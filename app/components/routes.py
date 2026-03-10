# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for email component library."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.components.schemas import (
    ComponentCompatibilityResponse,
    ComponentCreate,
    ComponentResponse,
    ComponentUpdate,
    VersionCreate,
    VersionResponse,
)
from app.components.service import ComponentService
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.shared.schemas import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/api/v1/components", tags=["components"])


def get_service(db: AsyncSession = Depends(get_db)) -> ComponentService:  # noqa: B008
    return ComponentService(db)


@router.get("/", response_model=PaginatedResponse[ComponentResponse])
@limiter.limit("30/minute")
async def list_components(
    request: Request,
    pagination: PaginationParams = Depends(),  # noqa: B008
    category: str | None = Query(None, max_length=50),
    search: str | None = Query(None, max_length=200),
    service: ComponentService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> PaginatedResponse[ComponentResponse]:
    """List email components."""
    _ = request
    return await service.list_components(pagination, category=category, search=search)


@router.get("/{component_id}", response_model=ComponentResponse)
@limiter.limit("30/minute")
async def get_component(
    request: Request,
    component_id: int,
    service: ComponentService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> ComponentResponse:
    """Get a component by ID."""
    _ = request
    return await service.get_component(component_id)


@router.post("/", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_component(
    request: Request,
    data: ComponentCreate,
    service: ComponentService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ComponentResponse:
    """Create a new email component with initial version."""
    _ = request
    return await service.create_component(data, user_id=current_user.id)


@router.patch("/{component_id}", response_model=ComponentResponse)
@limiter.limit("10/minute")
async def update_component(
    request: Request,
    component_id: int,
    data: ComponentUpdate,
    service: ComponentService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ComponentResponse:
    """Update component metadata."""
    _ = request
    return await service.update_component(component_id, data)


@router.delete("/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_component(
    request: Request,
    component_id: int,
    service: ComponentService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> None:
    """Delete a component and all its versions."""
    _ = request
    await service.delete_component(component_id)


@router.get("/{component_id}/versions", response_model=list[VersionResponse])
@limiter.limit("30/minute")
async def list_versions(
    request: Request,
    component_id: int,
    service: ComponentService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[VersionResponse]:
    """List all versions of a component."""
    _ = request
    return await service.list_versions(component_id)


@router.post(
    "/{component_id}/versions", response_model=VersionResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def create_version(
    request: Request,
    component_id: int,
    data: VersionCreate,
    service: ComponentService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> VersionResponse:
    """Create a new version of a component."""
    _ = request
    return await service.create_version(component_id, data, user_id=current_user.id)


@router.post(
    "/{component_id}/versions/{version_number}/qa",
    response_model=ComponentCompatibilityResponse,
    status_code=200,
)
@limiter.limit("10/minute")
async def run_component_qa(
    request: Request,
    component_id: int,
    version_number: int,
    service: ComponentService = Depends(get_service),  # noqa: B008
    _user: User = Depends(require_role("developer")),  # noqa: B008
) -> ComponentCompatibilityResponse:
    """Run QA checks on a component version and generate compatibility data."""
    _ = request
    return await service.run_qa_for_version(component_id, version_number)


@router.get(
    "/{component_id}/compatibility",
    response_model=ComponentCompatibilityResponse,
    status_code=200,
)
@limiter.limit("30/minute")
async def get_component_compatibility(
    request: Request,
    component_id: int,
    service: ComponentService = Depends(get_service),  # noqa: B008
    _user: User = Depends(get_current_user),  # noqa: B008
) -> ComponentCompatibilityResponse:
    """Get aggregated compatibility badge data for a component."""
    _ = request
    return await service.get_compatibility(component_id)
