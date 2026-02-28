"""Data access layer for projects and client organizations."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.models import ClientOrg, Project, ProjectMember
from app.projects.schemas import ClientOrgCreate, ProjectCreate, ProjectUpdate
from app.shared.models import utcnow
from app.shared.utils import escape_like


class ClientOrgRepository:
    """Database operations for client organizations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, org_id: int) -> ClientOrg | None:
        result = await self.db.execute(select(ClientOrg).where(ClientOrg.id == org_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> ClientOrg | None:
        result = await self.db.execute(select(ClientOrg).where(ClientOrg.slug == slug))
        return result.scalar_one_or_none()

    async def list(
        self, *, offset: int = 0, limit: int = 100, active_only: bool = True
    ) -> list[ClientOrg]:
        query = select(ClientOrg)
        if active_only:
            query = query.where(ClientOrg.is_active.is_(True))
        query = query.order_by(ClientOrg.name).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, *, active_only: bool = True) -> int:
        query = select(func.count()).select_from(ClientOrg)
        if active_only:
            query = query.where(ClientOrg.is_active.is_(True))
        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, data: ClientOrgCreate) -> ClientOrg:
        org = ClientOrg(**data.model_dump())
        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)
        return org


class ProjectRepository:
    """Database operations for projects."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, project_id: int) -> Project | None:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        client_org_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
        active_only: bool = True,
        search: str | None = None,
    ) -> list[Project]:
        query = select(Project).where(Project.deleted_at.is_(None))
        if active_only:
            query = query.where(Project.is_active.is_(True))
        if client_org_id is not None:
            query = query.where(Project.client_org_id == client_org_id)
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(Project.name.ilike(pattern))
        query = query.order_by(Project.name).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        client_org_id: int | None = None,
        active_only: bool = True,
        search: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(Project).where(Project.deleted_at.is_(None))
        if active_only:
            query = query.where(Project.is_active.is_(True))
        if client_org_id is not None:
            query = query.where(Project.client_org_id == client_org_id)
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(Project.name.ilike(pattern))
        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, data: ProjectCreate, created_by_id: int) -> Project:
        project = Project(**data.model_dump(), created_by_id=created_by_id)
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(self, project: Project, data: ProjectUpdate) -> Project:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, project: Project) -> None:
        project.deleted_at = utcnow()
        await self.db.commit()
        await self.db.refresh(project)

    async def add_member(
        self, project_id: int, user_id: int, role: str = "developer"
    ) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def get_member(self, project_id: int, user_id: int) -> ProjectMember | None:
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_members(self, project_id: int) -> list[ProjectMember]:
        result = await self.db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id)
        )
        return list(result.scalars().all())
