# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for project and client organization management."""

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.exceptions import DomainValidationError
from app.core.rate_limit import limiter
from app.projects.design_system import DesignSystem
from app.projects.schemas import (
    ClientOrgCreate,
    ClientOrgResponse,
    ClientProfileSchema,
    CompatibilityBriefResponse,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
    RiskMatrixEntrySchema,
    UnsupportedPropertySchema,
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
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ProjectResponse:
    """Get a project by ID. Validates user has access."""
    _ = request
    return await service.verify_project_access(project_id, current_user)


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberResponse])
@limiter.limit("30/minute")
async def list_project_members(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[ProjectMemberResponse]:
    """List members of a project. Requires project access."""
    _ = request
    await service.verify_project_access(project_id, current_user)
    return await service.list_project_members(project_id)


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
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ProjectResponse:
    """Update a project."""
    _ = request
    return await service.update_project(project_id, data, current_user)


@router.post("/projects/{project_id}/onboarding-brief", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
async def regenerate_onboarding_brief(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Regenerate the client-specific compatibility subgraph for this project."""
    _ = request
    project = await service.verify_project_access(project_id, current_user)

    if not project.target_clients:
        raise DomainValidationError("Project has no target clients configured")

    from app.projects.onboarding import generate_and_store_subgraph

    await generate_and_store_subgraph(
        project_id=project_id,
        project_name=project.name,
        client_ids=project.target_clients,
    )

    return {"status": "accepted", "message": "Onboarding brief regeneration started"}


@router.get(
    "/projects/{project_id}/compatibility-brief",
    response_model=CompatibilityBriefResponse,
)
@limiter.limit("30/minute")
async def get_compatibility_brief(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> CompatibilityBriefResponse:
    """Return structured compatibility brief for project's target clients."""
    _ = request
    project = await service.verify_project_access(project_id, current_user)

    if not project.target_clients:
        raise DomainValidationError("No target clients configured")

    from app.projects.compatibility_brief import generate_compatibility_brief

    brief = generate_compatibility_brief(project.target_clients)
    if not brief:
        raise DomainValidationError("No valid clients found in target list")

    return CompatibilityBriefResponse(
        client_count=brief.client_count,
        total_risky_properties=brief.total_risky_properties,
        dark_mode_warning=brief.dark_mode_warning,
        clients=[
            ClientProfileSchema(
                id=c.id,
                name=c.name,
                platform=c.platform,
                engine=c.engine,
                market_share=c.market_share,
                notes=c.notes,
                unsupported_count=c.unsupported_count,
                unsupported_properties=[
                    UnsupportedPropertySchema(
                        css=p.css,
                        fallback=p.fallback,
                        technique=p.technique,
                    )
                    for p in c.unsupported_properties
                ],
            )
            for c in brief.clients
        ],
        risk_matrix=[
            RiskMatrixEntrySchema(
                css=r.css,
                unsupported_in=r.unsupported_in,
                fallback=r.fallback,
            )
            for r in brief.risk_matrix
        ],
    )


# ── Design System ──


@router.get("/projects/{project_id}/design-system")
@limiter.limit("30/minute")
async def get_design_system(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """Get the design system for a project."""
    _ = request
    ds = await service.get_design_system(project_id, current_user)
    if ds is None:
        return {}
    return ds.model_dump()


@router.put("/projects/{project_id}/design-system")
@limiter.limit("10/minute")
async def update_design_system(
    request: Request,
    project_id: int,
    data: DesignSystem,
    service: ProjectService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> dict[str, Any]:
    """Set or update the design system for a project."""
    _ = request
    ds = await service.update_design_system(project_id, data, current_user)
    return ds.model_dump()


@router.delete("/projects/{project_id}/design-system", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_design_system(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> None:
    """Remove the design system from a project."""
    _ = request
    await service.delete_design_system(project_id, current_user)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_project(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> None:
    """Delete a project."""
    _ = request
    await service.delete_project(project_id, current_user)
