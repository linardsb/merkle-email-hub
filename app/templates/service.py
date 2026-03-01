"""Business logic for email template management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.logging import get_logger
from app.projects.service import ProjectService
from app.shared.schemas import PaginatedResponse, PaginationParams
from app.templates.exceptions import TemplateNotFoundError, TemplateVersionNotFoundError
from app.templates.models import Template
from app.templates.repository import TemplateRepository
from app.templates.schemas import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
    VersionCreate,
    VersionResponse,
)

logger = get_logger(__name__)


class TemplateService:
    """Business logic for template management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.templates = TemplateRepository(db)
        self.project_service = ProjectService(db)

    def _to_response(
        self, template: Template, latest_version: int | None = None
    ) -> TemplateResponse:
        """Convert Template model to TemplateResponse with computed latest_version."""
        response = TemplateResponse.model_validate(template)
        response.latest_version = latest_version
        return response

    async def _get_template_or_404(self, template_id: int) -> Template:
        """Fetch template and verify it exists and isn't soft-deleted."""
        template = await self.templates.get(template_id)
        if not template or template.deleted_at is not None:  # pyright: ignore[reportUnnecessaryComparison]
            raise TemplateNotFoundError(f"Template {template_id} not found")
        return template

    async def _verify_template_access(self, template_id: int, user: User) -> Template:
        """Fetch template and verify user has access to its project."""
        template = await self._get_template_or_404(template_id)
        await self.project_service.verify_project_access(template.project_id, user)
        return template

    async def list_templates(
        self,
        project_id: int,
        user: User,
        pagination: PaginationParams,
        *,
        search: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[TemplateResponse]:
        logger.info("templates.list_started", project_id=project_id, page=pagination.page)
        await self.project_service.verify_project_access(project_id, user)
        items = await self.templates.list(
            project_id=project_id,
            offset=pagination.offset,
            limit=pagination.page_size,
            search=search,
            status=status,
        )
        total = await self.templates.count(
            project_id=project_id,
            search=search,
            status=status,
        )
        response_items: list[TemplateResponse] = []
        for t in items:
            latest = await self.templates.get_latest_version_number(t.id)
            response_items.append(self._to_response(t, latest or None))
        return PaginatedResponse[TemplateResponse](
            items=response_items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_template(self, template_id: int, user: User) -> TemplateResponse:
        logger.info("templates.fetch_started", template_id=template_id)
        template = await self._verify_template_access(template_id, user)
        latest = await self.templates.get_latest_version_number(template_id)
        return self._to_response(template, latest or None)

    async def create_template(
        self, project_id: int, data: TemplateCreate, user: User
    ) -> TemplateResponse:
        logger.info("templates.create_started", project_id=project_id, name=data.name)
        await self.project_service.verify_project_access(project_id, user)
        template = await self.templates.create(project_id, data, user.id)
        logger.info("templates.create_completed", template_id=template.id)
        return self._to_response(template, 1)

    async def update_template(
        self, template_id: int, data: TemplateUpdate, user: User
    ) -> TemplateResponse:
        logger.info("templates.update_started", template_id=template_id)
        template = await self._verify_template_access(template_id, user)
        template = await self.templates.update(template, data)
        latest = await self.templates.get_latest_version_number(template_id)
        logger.info("templates.update_completed", template_id=template_id)
        return self._to_response(template, latest or None)

    async def delete_template(self, template_id: int, user: User) -> None:
        logger.info("templates.delete_started", template_id=template_id)
        template = await self._verify_template_access(template_id, user)
        await self.templates.delete(template)
        logger.info("templates.delete_completed", template_id=template_id)

    # -- Versions --

    async def create_version(
        self, template_id: int, data: VersionCreate, user: User
    ) -> VersionResponse:
        logger.info("templates.version_create_started", template_id=template_id)
        await self._verify_template_access(template_id, user)
        version = await self.templates.create_version(template_id, data, user.id)
        logger.info(
            "templates.version_create_completed",
            template_id=template_id,
            version=version.version_number,
        )
        return VersionResponse.model_validate(version)

    async def list_versions(self, template_id: int, user: User) -> list[VersionResponse]:
        logger.info("templates.versions_list_started", template_id=template_id)
        await self._verify_template_access(template_id, user)
        versions = await self.templates.get_versions(template_id)
        return [VersionResponse.model_validate(v) for v in versions]

    async def get_version(
        self, template_id: int, version_number: int, user: User
    ) -> VersionResponse:
        logger.info(
            "templates.version_fetch_started",
            template_id=template_id,
            version=version_number,
        )
        await self._verify_template_access(template_id, user)
        version = await self.templates.get_version(template_id, version_number)
        if not version:
            raise TemplateVersionNotFoundError(
                f"Version {version_number} not found for template {template_id}"
            )
        return VersionResponse.model_validate(version)

    async def restore_version(
        self, template_id: int, version_number: int, user: User
    ) -> VersionResponse:
        """Restore a previous version by creating a new version with its content."""
        logger.info(
            "templates.restore_started",
            template_id=template_id,
            from_version=version_number,
        )
        await self._verify_template_access(template_id, user)
        source_version = await self.templates.get_version(template_id, version_number)
        if not source_version:
            raise TemplateVersionNotFoundError(
                f"Version {version_number} not found for template {template_id}"
            )
        # Restore = create a NEW version with the old content (immutable history)
        restore_data = VersionCreate(
            html_source=source_version.html_source,
            css_source=source_version.css_source,
            changelog=f"Restored from version {version_number}",
        )
        new_version = await self.templates.create_version(template_id, restore_data, user.id)
        logger.info(
            "templates.restore_completed",
            template_id=template_id,
            from_version=version_number,
            new_version=new_version.version_number,
        )
        return VersionResponse.model_validate(new_version)
