"""Business logic for project and client organization management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.exceptions import DomainValidationError
from app.core.logging import get_logger
from app.projects.design_system import DesignSystem, load_design_system
from app.projects.exceptions import (
    ClientOrgAlreadyExistsError,
    ClientOrgNotFoundError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
)
from app.projects.repository import ClientOrgRepository, ProjectRepository
from app.projects.schemas import (
    ClientOrgCreate,
    ClientOrgResponse,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.projects.template_config import ProjectTemplateConfig, load_template_config
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

    async def verify_project_access(self, project_id: int, user: User) -> ProjectResponse:
        """Verify user has access to project. Returns project if allowed.

        Admin users can access any project. Other users must be a project member.
        """
        logger.info("projects.access_check_started", project_id=project_id, user_id=user.id)
        project = await self.projects.get(project_id)
        if not project or project.deleted_at is not None:  # pyright: ignore[reportUnnecessaryComparison]
            raise ProjectNotFoundError(f"Project {project_id} not found")

        if user.role != "admin":
            member = await self.projects.get_member(project_id, user.id)
            if not member:
                logger.warning(
                    "projects.access_denied",
                    project_id=project_id,
                    user_id=user.id,
                )
                raise ProjectAccessDeniedError(f"User does not have access to project {project_id}")

        return ProjectResponse.model_validate(project)

    async def list_project_members(self, project_id: int) -> list[ProjectMemberResponse]:
        logger.info("projects.members_list_started", project_id=project_id)
        project = await self.projects.get(project_id)
        if not project or project.deleted_at is not None:  # pyright: ignore[reportUnnecessaryComparison]
            raise ProjectNotFoundError(f"Project {project_id} not found")
        members = await self.projects.get_members(project_id)
        return [ProjectMemberResponse.model_validate(m) for m in members]

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

        # Fire-and-forget: generate client-specific subgraph if target clients specified
        if data.target_clients:
            from app.projects.onboarding import generate_and_store_subgraph

            await generate_and_store_subgraph(
                project_id=project.id,
                project_name=data.name,
                client_ids=data.target_clients,
            )

        return ProjectResponse.model_validate(project)

    async def update_project(
        self, project_id: int, data: ProjectUpdate, user: User
    ) -> ProjectResponse:
        logger.info("projects.update_started", project_id=project_id, user_id=user.id)
        await self.verify_project_access(project_id, user)
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        project = await self.projects.update(project, data)

        # Regenerate subgraph if target_clients changed
        if data.target_clients is not None:
            from app.projects.onboarding import generate_and_store_subgraph

            await generate_and_store_subgraph(
                project_id=project_id,
                project_name=project.name,
                client_ids=data.target_clients,
            )

        return ProjectResponse.model_validate(project)

    async def delete_project(self, project_id: int, user: User) -> None:
        logger.info("projects.delete_started", project_id=project_id, user_id=user.id)
        await self.verify_project_access(project_id, user)
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        await self.projects.delete(project)

    async def get_design_system(self, project_id: int, user: User) -> DesignSystem | None:
        """Get the design system for a project. Returns None if not configured."""
        logger.info("projects.design_system_fetch_started", project_id=project_id)
        project_response = await self.verify_project_access(project_id, user)
        return load_design_system(project_response.design_system)

    async def update_design_system(
        self, project_id: int, design_system: DesignSystem, user: User
    ) -> DesignSystem:
        """Set or update the design system for a project."""
        logger.info("projects.design_system_update_started", project_id=project_id, user_id=user.id)
        await self.verify_project_access(project_id, user)
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        await self.projects.update_design_system(project, design_system.model_dump())
        logger.info("projects.design_system_update_completed", project_id=project_id)
        return design_system

    async def delete_design_system(self, project_id: int, user: User) -> None:
        """Remove the design system from a project."""
        logger.info("projects.design_system_delete_started", project_id=project_id, user_id=user.id)
        await self.verify_project_access(project_id, user)
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        await self.projects.update_design_system(project, None)
        logger.info("projects.design_system_delete_completed", project_id=project_id)

    # ── Template Config ──

    async def get_template_config(
        self, project_id: int, user: User
    ) -> ProjectTemplateConfig | None:
        """Get the template config for a project. Returns None if not configured."""
        logger.info("projects.template_config_fetch_started", project_id=project_id)
        project_response = await self.verify_project_access(project_id, user)
        return load_template_config(project_response.template_config)

    async def update_template_config(
        self, project_id: int, config: ProjectTemplateConfig, user: User
    ) -> ProjectTemplateConfig:
        """Set or update the template config for a project."""
        logger.info(
            "projects.template_config_update_started",
            project_id=project_id,
            user_id=user.id,
        )
        await self.verify_project_access(project_id, user)
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")

        from app.ai.templates.registry import get_template_registry

        registry = get_template_registry()
        known_names = set(registry.names())

        for name in config.disabled_templates:
            if name not in known_names:
                raise DomainValidationError(
                    f"Unknown template name in disabled_templates: '{name}'. "
                    f"Available: {sorted(known_names)}"
                )
        for name in config.preferred_templates:
            if name not in known_names:
                raise DomainValidationError(
                    f"Unknown template name in preferred_templates: '{name}'. "
                    f"Available: {sorted(known_names)}"
                )

        await self.projects.update_template_config(project, config.model_dump())
        logger.info("projects.template_config_update_completed", project_id=project_id)
        return config

    async def delete_template_config(self, project_id: int, user: User) -> None:
        """Remove the template config from a project."""
        logger.info(
            "projects.template_config_delete_started",
            project_id=project_id,
            user_id=user.id,
        )
        await self.verify_project_access(project_id, user)
        project = await self.projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        await self.projects.update_template_config(project, None)
        logger.info("projects.template_config_delete_completed", project_id=project_id)

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
        items = await self.orgs.list(
            offset=pagination.offset, limit=pagination.page_size, active_only=active_only
        )
        total = await self.orgs.count(active_only=active_only)
        return PaginatedResponse[ClientOrgResponse](
            items=[ClientOrgResponse.model_validate(o) for o in items],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
