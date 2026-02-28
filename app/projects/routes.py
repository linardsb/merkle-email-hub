# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for project and client organization management."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.projects.schemas import (
    ClientOrgCreate,
    ClientOrgResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.projects.service import ProjectService
from app.shared.schemas import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/api/v1", tags=["projects"])


def get_service(db: AsyncSession = Depends(get_db)) -> ProjectService:  # noqa: B008
    return ProjectService(db)


# ── Client Organizations ──


@router.get("/orgs", response_model=PaginatedResponse[ClientOrgResponse])
@limiter.limit("30/minute")
async def list_orgs(
    request: Request,
    pagination: PaginationParams = Depends(),  # noqa: B008
    service: ProjectService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> PaginatedResponse[ClientOrgResponse]:
    """List client organizations."""
    _ = request
    return await service.list_orgs(pagination)


@router.post("/orgs", response_model=ClientOrgResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_org(
    request: Request,
    data: ClientOrgCreate,
    service: ProjectService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> ClientOrgResponse:
    """Create a new client organization."""
    _ = request
    return await service.create_org(data)


# ── Projects ──


@router.get("/projects", response_model=PaginatedResponse[ProjectResponse])
@limiter.limit("30/minute")
async def list_projects(
    request: Request,
    pagination: PaginationParams = Depends(),  # noqa: B008
    client_org_id: int | None = Query(None),
    search: str | None = Query(None, max_length=200),
    service: ProjectService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> PaginatedResponse[ProjectResponse]:
    """List projects with optional client org filter."""
    _ = request
    return await service.list_projects(pagination, client_org_id=client_org_id, search=search)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
@limiter.limit("30/minute")
async def get_project(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> ProjectResponse:
    """Get a project by ID."""
    _ = request
    return await service.get_project(project_id)


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_project(
    request: Request,
    data: ProjectCreate,
    service: ProjectService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ProjectResponse:
    """Create a new project."""
    _ = request
    return await service.create_project(data, user_id=current_user.id)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
@limiter.limit("10/minute")
async def update_project(
    request: Request,
    project_id: int,
    data: ProjectUpdate,
    service: ProjectService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ProjectResponse:
    """Update a project."""
    _ = request
    return await service.update_project(project_id, data)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_project(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> None:
    """Delete a project."""
    _ = request
    await service.delete_project(project_id)
