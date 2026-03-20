"""Database operations for briefs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.briefs.models import BriefAttachment, BriefConnection, BriefItem, BriefResource


class BriefRepository:
    """CRUD operations for brief connections and items."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Connections ──

    async def create_connection(
        self,
        *,
        name: str,
        platform: str,
        project_url: str,
        external_project_id: str,
        encrypted_credentials: str,
        credential_last4: str,
        project_id: int | None,
        created_by_id: int,
    ) -> BriefConnection:
        conn = BriefConnection(
            name=name,
            platform=platform,
            project_url=project_url,
            external_project_id=external_project_id,
            encrypted_credentials=encrypted_credentials,
            credential_last4=credential_last4,
            status="connected",
            project_id=project_id,
            created_by_id=created_by_id,
        )
        self.db.add(conn)
        await self.db.commit()
        await self.db.refresh(conn)
        return conn

    async def get_connection(self, connection_id: int) -> BriefConnection | None:
        result = await self.db.execute(
            select(BriefConnection).where(BriefConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def list_connections(self, user_id: int, role: str) -> list[BriefConnection]:
        """List connections. Admins see all, others see own only."""
        stmt = select(BriefConnection).order_by(BriefConnection.created_at.desc())
        if role != "admin":
            stmt = stmt.where(BriefConnection.created_by_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_connection(self, connection_id: int) -> bool:
        conn = await self.get_connection(connection_id)
        if conn is None:
            return False
        await self.db.delete(conn)
        await self.db.commit()
        return True

    async def update_connection_status(
        self,
        connection: BriefConnection,
        status: str,
        *,
        error_message: str | None = None,
    ) -> None:
        connection.status = status
        connection.error_message = error_message
        if status == "connected":
            connection.last_synced_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(connection)

    # ── Items ──

    async def upsert_item(
        self,
        *,
        connection_id: int,
        external_id: str,
        title: str,
        description: str | None,
        status: str,
        priority: str | None,
        assignees: list[str],
        labels: list[str],
        due_date: datetime | None,
        thumbnail_url: str | None,
    ) -> BriefItem:
        """Upsert an item by (connection_id, external_id). Caller must commit."""
        result = await self.db.execute(
            select(BriefItem).where(
                BriefItem.connection_id == connection_id,
                BriefItem.external_id == external_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.title = title
            existing.description = description
            existing.status = status
            existing.priority = priority
            existing.assignees = assignees
            existing.labels = labels
            existing.due_date = due_date
            existing.thumbnail_url = thumbnail_url
            await self.db.flush()
            return existing

        item = BriefItem(
            connection_id=connection_id,
            external_id=external_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignees=assignees,
            labels=labels,
            due_date=due_date,
            thumbnail_url=thumbnail_url,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def commit(self) -> None:
        """Commit the current transaction (call after batch upserts)."""
        await self.db.commit()

    async def list_items_for_connection(self, connection_id: int) -> list[BriefItem]:
        result = await self.db.execute(
            select(BriefItem)
            .where(BriefItem.connection_id == connection_id)
            .order_by(BriefItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_items(
        self,
        *,
        user_id: int,
        role: str,
        platform: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[BriefItem]:
        """List items scoped to connections the user can access."""
        stmt = select(BriefItem).join(BriefConnection)

        # BOLA: non-admins only see items from their own connections
        if role != "admin":
            stmt = stmt.where(BriefConnection.created_by_id == user_id)

        if platform is not None:
            stmt = stmt.where(BriefConnection.platform == platform)
        if status is not None:
            stmt = stmt.where(BriefItem.status == status)
        if search is not None:
            from app.shared.utils import escape_like

            stmt = stmt.where(BriefItem.title.ilike(f"%{escape_like(search)}%"))

        stmt = stmt.order_by(BriefItem.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_item(self, item_id: int) -> BriefItem | None:
        result = await self.db.execute(select(BriefItem).where(BriefItem.id == item_id))
        return result.scalar_one_or_none()

    async def get_item_with_details(self, item_id: int) -> BriefItem | None:
        """Get item with eagerly loaded resources and attachments."""
        result = await self.db.execute(
            select(BriefItem)
            .options(selectinload(BriefItem.resources), selectinload(BriefItem.attachments))
            .where(BriefItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_items_by_ids(self, item_ids: list[int]) -> list[BriefItem]:
        result = await self.db.execute(select(BriefItem).where(BriefItem.id.in_(item_ids)))
        return list(result.scalars().all())

    # ── Resources & Attachments ──

    async def replace_resources(self, item_id: int, resources: list[dict[str, Any]]) -> None:
        """Delete existing resources and insert new ones."""
        result = await self.db.execute(
            select(BriefResource).where(BriefResource.item_id == item_id)
        )
        for existing in result.scalars().all():
            await self.db.delete(existing)

        for rdata in resources:
            self.db.add(
                BriefResource(
                    item_id=item_id,
                    type=str(rdata["type"]),
                    filename=str(rdata["filename"]),
                    url=str(rdata["url"]),
                    size_bytes=rdata.get("size_bytes"),
                )
            )
        await self.db.flush()

    async def replace_attachments(self, item_id: int, attachments: list[dict[str, Any]]) -> None:
        """Delete existing attachments and insert new ones. Caller must commit."""
        result = await self.db.execute(
            select(BriefAttachment).where(BriefAttachment.item_id == item_id)
        )
        for existing in result.scalars().all():
            await self.db.delete(existing)

        for adata in attachments:
            self.db.add(
                BriefAttachment(
                    item_id=item_id,
                    filename=str(adata["filename"]),
                    url=str(adata["url"]),
                    size_bytes=adata.get("size_bytes"),
                )
            )
        await self.db.flush()

    # ── Project lookups ──

    async def get_accessible_project_ids(self, user_id: int, role: str) -> list[int]:
        """Get IDs of projects the user can access."""
        if role == "admin":
            from app.projects.models import Project

            result = await self.db.execute(select(Project.id))
            return [row[0] for row in result.all()]

        from app.projects.models import ProjectMember

        result = await self.db.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        )
        return [row[0] for row in result.all()]
