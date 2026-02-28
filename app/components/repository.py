"""Data access layer for email components."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.models import Component, ComponentVersion
from app.components.schemas import ComponentCreate, ComponentUpdate, VersionCreate
from app.shared.utils import escape_like


class ComponentRepository:
    """Database operations for email components."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, component_id: int) -> Component | None:
        result = await self.db.execute(select(Component).where(Component.id == component_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Component | None:
        result = await self.db.execute(select(Component).where(Component.slug == slug))
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        category: str | None = None,
        search: str | None = None,
    ) -> list[Component]:
        query = select(Component)
        if category:
            query = query.where(Component.category == category)
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(Component.name.ilike(pattern))
        query = query.order_by(Component.name).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, *, category: str | None = None, search: str | None = None) -> int:
        query = select(func.count()).select_from(Component)
        if category:
            query = query.where(Component.category == category)
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(Component.name.ilike(pattern))
        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, data: ComponentCreate, user_id: int) -> Component:
        component = Component(
            name=data.name,
            slug=data.slug,
            description=data.description,
            category=data.category,
            created_by_id=user_id,
        )
        self.db.add(component)
        await self.db.commit()
        await self.db.refresh(component)
        # Create initial version
        version = ComponentVersion(
            component_id=component.id,
            version_number=1,
            html_source=data.html_source,
            css_source=data.css_source,
            created_by_id=user_id,
        )
        self.db.add(version)
        await self.db.commit()
        return component

    async def update(self, component: Component, data: ComponentUpdate) -> Component:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(component, field, value)
        await self.db.commit()
        await self.db.refresh(component)
        return component

    async def delete(self, component: Component) -> None:
        await self.db.delete(component)
        await self.db.commit()

    async def get_latest_version_number(self, component_id: int) -> int:
        result = await self.db.execute(
            select(func.max(ComponentVersion.version_number)).where(
                ComponentVersion.component_id == component_id
            )
        )
        return result.scalar_one() or 0

    async def create_version(self, component_id: int, data: VersionCreate, user_id: int) -> ComponentVersion:
        next_version = await self.get_latest_version_number(component_id) + 1
        version = ComponentVersion(
            component_id=component_id,
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

    async def get_versions(self, component_id: int) -> list[ComponentVersion]:
        result = await self.db.execute(
            select(ComponentVersion)
            .where(ComponentVersion.component_id == component_id)
            .order_by(ComponentVersion.version_number.desc())
        )
        return list(result.scalars().all())
