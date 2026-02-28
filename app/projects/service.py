"""Business logic for project and client organization management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.projects.exceptions import (
    ClientOrgAlreadyExistsError,
    ClientOrgNotFoundError,
    ProjectNotFoundError,
)
from app.projects.repository import ClientOrgRepository, ProjectRepository
from app.projects.schemas import (
    ClientOrgCreate,
    ClientOrgResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.shared.schemas import PaginatedResponse, PaginationParams

logger = get_logger(__name__)


class ProjectService:
    """Business logic for project management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.orgs = ClientOrgRepository(db)

    async def get_project(self, project_id: int) -> ProjectResponse:
        logger.info("projects.fetch_started", project_id=project_id)
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        return ProjectResponse.model_validate(project)

    async def list_projects(
        self,
        pagination: PaginationParams,
        *,
        client_org_id: int | None = None,
        search: str | None = None,
        active_only: bool = True,
    ) -> PaginatedResponse[ProjectResponse]:
        logger.info("projects.list_started", page=pagination.page)
        items = await self.projects.list(
            client_org_id=client_org_id,
            offset=pagination.offset,
            limit=pagination.page_size,
            active_only=active_only,
            search=search,
        )
        total = await self.projects.count(
            client_org_id=client_org_id,
            active_only=active_only,
            search=search,
        )
        response_items = [ProjectResponse.model_validate(p) for p in items]
        return PaginatedResponse[ProjectResponse](
            items=response_items, total=total, page=pagination.page, page_size=pagination.page_size
        )

    async def create_project(self, data: ProjectCreate, user_id: int) -> ProjectResponse:
        logger.info("projects.create_started", name=data.name, client_org_id=data.client_org_id)
        org = await self.orgs.get(data.client_org_id)
        if not org:
            raise ClientOrgNotFoundError(f"Client org {data.client_org_id} not found")
        project = await self.projects.create(data, created_by_id=user_id)
        await self.projects.add_member(project.id, user_id, role="admin")
        logger.info("projects.create_completed", project_id=project.id)
        return ProjectResponse.model_validate(project)

    async def update_project(self, project_id: int, data: ProjectUpdate) -> ProjectResponse:
        logger.info("projects.update_started", project_id=project_id)
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        project = await self.projects.update(project, data)
        return ProjectResponse.model_validate(project)

    async def delete_project(self, project_id: int) -> None:
        logger.info("projects.delete_started", project_id=project_id)
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        await self.projects.delete(project)

    async def create_org(self, data: ClientOrgCreate) -> ClientOrgResponse:
        logger.info("orgs.create_started", name=data.name)
        existing = await self.orgs.get_by_slug(data.slug)
        if existing:
            raise ClientOrgAlreadyExistsError(f"Org with slug '{data.slug}' already exists")
        org = await self.orgs.create(data)
        return ClientOrgResponse.model_validate(org)

    async def list_orgs(
        self, pagination: PaginationParams, *, active_only: bool = True
    ) -> PaginatedResponse[ClientOrgResponse]:
        items = await self.orgs.list(offset=pagination.offset, limit=pagination.page_size, active_only=active_only)
        total = await self.orgs.count(active_only=active_only)
        return PaginatedResponse[ClientOrgResponse](
            items=[ClientOrgResponse.model_validate(o) for o in items],
            total=total, page=pagination.page, page_size=pagination.page_size,
        )
