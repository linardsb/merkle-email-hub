"""Data access layer for email components."""

from __future__ import annotations

import builtins
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.components.models import Component, ComponentQAResult, ComponentVersion
from app.components.schemas import ComponentCreate, ComponentUpdate, VersionCreate
from app.shared.models import utcnow
from app.shared.utils import escape_like


class ComponentRepository:
    """Database operations for email components."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, component_id: int) -> Component | None:
        result = await self.db.execute(
            select(Component)
            .where(Component.id == component_id, Component.deleted_at.is_(None))
            .options(selectinload(Component.versions))
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Component | None:
        result = await self.db.execute(
            select(Component).where(Component.slug == slug, Component.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        category: str | None = None,
        search: str | None = None,
    ) -> Sequence[Component]:
        query = select(Component).where(Component.deleted_at.is_(None))
        if category:
            query = query.where(Component.category == category)
        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(Component.name.ilike(pattern))
        query = query.order_by(Component.name).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, *, category: str | None = None, search: str | None = None) -> int:
        query = select(func.count()).select_from(Component).where(Component.deleted_at.is_(None))
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
        """Soft delete a component by setting deleted_at timestamp."""
        component.deleted_at = utcnow()
        await self.db.commit()

    async def get_latest_version_number(self, component_id: int) -> int:
        result = await self.db.execute(
            select(func.max(ComponentVersion.version_number)).where(
                ComponentVersion.component_id == component_id
            )
        )
        return result.scalar_one() or 0

    async def create_version(
        self, component_id: int, data: VersionCreate, user_id: int
    ) -> ComponentVersion:
        next_version = await self.get_latest_version_number(component_id) + 1
        version = ComponentVersion(
            component_id=component_id,
            version_number=next_version,
            html_source=data.html_source,
            css_source=data.css_source,
            changelog=data.changelog,
            compatibility=data.compatibility,
            created_by_id=user_id,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def get_versions(self, component_id: int) -> Sequence[ComponentVersion]:
        result = await self.db.execute(
            select(ComponentVersion)
            .where(ComponentVersion.component_id == component_id)
            .order_by(ComponentVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, component_id: int, version_number: int) -> ComponentVersion | None:
        result = await self.db.execute(
            select(ComponentVersion).where(
                ComponentVersion.component_id == component_id,
                ComponentVersion.version_number == version_number,
            )
        )
        return result.scalar_one_or_none()

    async def search_with_compatibility(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        compatible_with: builtins.list[str] | None = None,
        limit: int = 5,
    ) -> builtins.list[tuple[Component, ComponentVersion]]:
        """Search components with latest version, filtering by compatibility.

        Returns components whose latest version does NOT have "none" support
        for the specified clients. Components with NULL compatibility pass
        (no QA data = don't exclude).
        """
        latest_version_sq = (
            select(
                ComponentVersion.component_id,
                func.max(ComponentVersion.version_number).label("max_version"),
            )
            .group_by(ComponentVersion.component_id)
            .subquery()
        )
        query = (
            select(Component, ComponentVersion)
            .join(latest_version_sq, Component.id == latest_version_sq.c.component_id)
            .join(
                ComponentVersion,
                sa.and_(
                    ComponentVersion.component_id == Component.id,
                    ComponentVersion.version_number == latest_version_sq.c.max_version,
                ),
            )
            .where(Component.deleted_at.is_(None))
        )

        if search:
            pattern = f"%{escape_like(search)}%"
            query = query.where(
                sa.or_(
                    Component.name.ilike(pattern),
                    Component.description.ilike(pattern),
                )
            )
        if category:
            query = query.where(Component.category == category)
        if compatible_with is not None:
            for client in compatible_with:
                # Exclude components where latest version has "none" for this client.
                # NULL compatibility passes (no QA data = don't exclude).
                query = query.where(
                    sa.or_(
                        ComponentVersion.compatibility.is_(None),
                        ComponentVersion.compatibility[client].as_string() != "none",
                    )
                )

        query = query.order_by(Component.name).limit(limit)
        result = await self.db.execute(query)
        return list(result.tuples().all())

    async def search_by_embedding(
        self,
        embedding: builtins.list[float],
        *,
        limit: int = 5,
    ) -> builtins.list[tuple[Component, float]]:
        """Search components by vector similarity (cosine distance)."""
        distance = Component.search_embedding.cosine_distance(embedding).label("distance")
        query = (
            select(Component, distance)
            .where(Component.deleted_at.is_(None))
            .where(Component.search_embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.tuples().all())

    async def get_latest_compatibility_batch(
        self, component_ids: builtins.list[int]
    ) -> dict[int, dict[str, str]]:
        """Get latest QA compatibility for multiple components in one query.

        Returns dict mapping component_id → compatibility dict.
        Components without QA data are omitted from the result.
        """
        if not component_ids:
            return {}

        latest_qa = (
            select(
                ComponentVersion.component_id,
                ComponentQAResult.compatibility,
                func.row_number()
                .over(
                    partition_by=ComponentVersion.component_id,
                    order_by=ComponentVersion.version_number.desc(),
                )
                .label("rn"),
            )
            .join(ComponentQAResult, ComponentQAResult.component_version_id == ComponentVersion.id)
            .where(ComponentVersion.component_id.in_(component_ids))
            .subquery()
        )

        query = select(latest_qa.c.component_id, latest_qa.c.compatibility).where(
            latest_qa.c.rn == 1
        )
        result = await self.db.execute(query)
        return {row.component_id: row.compatibility for row in result.all()}

    async def get_latest_compatibility(self, component_id: int) -> dict[str, str] | None:
        """Get compatibility from the latest version that has QA results."""
        result = await self.db.execute(
            select(ComponentQAResult.compatibility)
            .join(ComponentVersion, ComponentVersion.id == ComponentQAResult.component_version_id)
            .where(ComponentVersion.component_id == component_id)
            .order_by(ComponentVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_version_compatibility_batch(
        self, component_ids: builtins.list[int]
    ) -> dict[int, dict[str, object] | None]:
        """Get latest ComponentVersion.compatibility for multiple components.

        This returns the version-level compatibility JSON (which may contain
        design origin data), NOT the QA result compatibility.
        """
        if not component_ids:
            return {}

        latest_version_sq = (
            select(
                ComponentVersion.component_id,
                func.max(ComponentVersion.version_number).label("max_version"),
            )
            .where(ComponentVersion.component_id.in_(component_ids))
            .group_by(ComponentVersion.component_id)
            .subquery()
        )

        query = select(ComponentVersion.component_id, ComponentVersion.compatibility).join(
            latest_version_sq,
            sa.and_(
                ComponentVersion.component_id == latest_version_sq.c.component_id,
                ComponentVersion.version_number == latest_version_sq.c.max_version,
            ),
        )
        result = await self.db.execute(query)
        return {row.component_id: row.compatibility for row in result.all()}

    async def get_latest_version(self, component_id: int) -> ComponentVersion | None:
        """Get the latest version of a component."""
        result = await self.db.execute(
            select(ComponentVersion)
            .where(ComponentVersion.component_id == component_id)
            .order_by(ComponentVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_version_compatibility(
        self, version: ComponentVersion, compatibility: dict[str, object] | None
    ) -> None:
        """Update the compatibility JSON on a component version."""
        version.compatibility = compatibility  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(version)
