"""Data access layer for email templates."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scoped_db import scoped_access
from app.shared.models import utcnow
from app.shared.utils import escape_like
from app.templates.models import Template, TemplateVersion
from app.templates.schemas import TemplateCreate, TemplateUpdate, VersionCreate


class TemplateRepository:
    """Database operations for email templates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, template_id: int) -> Template | None:
        access = scoped_access(self.db)
        query = select(Template).where(Template.id == template_id)
        if access.project_ids is not None:
            query = query.where(Template.project_id.in_(access.project_ids))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        project_id: int,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: str | None = None,
    ) -> Sequence[Template]:
        access = scoped_access(self.db)
        query = select(Template).where(
            Template.project_id == project_id,
            Template.deleted_at.is_(None),
        )
        if access.project_ids is not None:
            query = query.where(Template.project_id.in_(access.project_ids))
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(Template.name.ilike(pattern))
        if status:
            query = query.where(Template.status == status)
        query = query.order_by(Template.updated_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        project_id: int,
        search: str | None = None,
        status: str | None = None,
    ) -> int:
        access = scoped_access(self.db)
        query = (
            select(func.count())
            .select_from(Template)
            .where(
                Template.project_id == project_id,
                Template.deleted_at.is_(None),
            )
        )
        if access.project_ids is not None:
            query = query.where(Template.project_id.in_(access.project_ids))
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(Template.name.ilike(pattern))
        if status:
            query = query.where(Template.status == status)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, project_id: int, data: TemplateCreate, user_id: int) -> Template:
        template = Template(
            project_id=project_id,
            name=data.name,
            description=data.description,
            subject_line=data.subject_line,
            preheader_text=data.preheader_text,
            created_by_id=user_id,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        # Create initial version (v1)
        version = TemplateVersion(
            template_id=template.id,
            version_number=1,
            html_source=data.html_source,
            css_source=data.css_source,
            created_by_id=user_id,
        )
        self.db.add(version)
        await self.db.commit()
        return template

    async def update(self, template: Template, data: TemplateUpdate) -> Template:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(template, field, value)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete(self, template: Template) -> None:
        """Soft delete -- sets deleted_at timestamp."""
        template.deleted_at = utcnow()
        await self.db.commit()
        await self.db.refresh(template)

    # -- Versions --

    async def get_latest_version_number(self, template_id: int) -> int:
        access = scoped_access(self.db)
        query = (
            select(func.max(TemplateVersion.version_number))
            .join(Template, Template.id == TemplateVersion.template_id)
            .where(TemplateVersion.template_id == template_id)
        )
        if access.project_ids is not None:
            query = query.where(Template.project_id.in_(access.project_ids))
        result = await self.db.execute(query)
        return result.scalar_one() or 0

    async def create_version(
        self, template_id: int, data: VersionCreate, user_id: int
    ) -> TemplateVersion:
        next_version = await self.get_latest_version_number(template_id) + 1
        version = TemplateVersion(
            template_id=template_id,
            version_number=next_version,
            html_source=data.html_source,
            css_source=data.css_source,
            changelog=data.changelog,
            created_by_id=user_id,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def get_versions(self, template_id: int) -> Sequence[TemplateVersion]:
        access = scoped_access(self.db)
        query = (
            select(TemplateVersion)
            .join(Template, Template.id == TemplateVersion.template_id)
            .where(TemplateVersion.template_id == template_id)
            .order_by(TemplateVersion.version_number.desc())
        )
        if access.project_ids is not None:
            query = query.where(Template.project_id.in_(access.project_ids))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_version(self, template_id: int, version_number: int) -> TemplateVersion | None:
        access = scoped_access(self.db)
        query = (
            select(TemplateVersion)
            .join(Template, Template.id == TemplateVersion.template_id)
            .where(
                TemplateVersion.template_id == template_id,
                TemplateVersion.version_number == version_number,
            )
        )
        if access.project_ids is not None:
            query = query.where(Template.project_id.in_(access.project_ids))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
