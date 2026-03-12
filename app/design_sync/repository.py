"""Database operations for design sync."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.design_sync.models import DesignConnection, DesignTokenSnapshot


class DesignSyncRepository:
    """CRUD operations for design connections and token snapshots."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_connection(
        self,
        *,
        name: str,
        provider: str,
        file_ref: str,
        file_url: str,
        encrypted_token: str,
        token_last4: str,
        project_id: int | None,
        created_by_id: int,
    ) -> DesignConnection:
        conn = DesignConnection(
            name=name,
            provider=provider,
            file_ref=file_ref,
            file_url=file_url,
            encrypted_token=encrypted_token,
            token_last4=token_last4,
            status="connected",
            project_id=project_id,
            created_by_id=created_by_id,
        )
        self.db.add(conn)
        await self.db.commit()
        await self.db.refresh(conn)
        return conn

    async def get_connection(self, connection_id: int) -> DesignConnection | None:
        result = await self.db.execute(
            select(DesignConnection).where(DesignConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def list_connections_for_user(
        self,
        user_id: int,
        accessible_project_ids: list[int],
    ) -> list[tuple[DesignConnection, str | None]]:
        """List connections the user owns or that belong to accessible projects.

        Returns tuples of (connection, project_name) to avoid N+1 queries.
        """
        from sqlalchemy import or_

        from app.projects.models import Project

        stmt = (
            select(DesignConnection, Project.name)
            .outerjoin(Project, DesignConnection.project_id == Project.id)
            .where(
                or_(
                    DesignConnection.created_by_id == user_id,
                    DesignConnection.project_id.in_(accessible_project_ids),
                )
            )
            .order_by(DesignConnection.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def delete_connection(self, connection_id: int) -> bool:
        conn = await self.get_connection(connection_id)
        if conn is None:
            return False
        await self.db.delete(conn)
        await self.db.commit()
        return True

    async def update_status(
        self,
        connection: DesignConnection,
        status: str,
        error_message: str | None = None,
    ) -> None:
        connection.status = status
        connection.error_message = error_message
        if status == "connected":
            connection.last_synced_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(connection)

    async def save_snapshot(
        self,
        connection_id: int,
        tokens_json: dict[str, object],
    ) -> DesignTokenSnapshot:
        snapshot = DesignTokenSnapshot(
            connection_id=connection_id,
            tokens_json=tokens_json,
            extracted_at=datetime.now(UTC),
        )
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    async def get_latest_snapshot(self, connection_id: int) -> DesignTokenSnapshot | None:
        result = await self.db.execute(
            select(DesignTokenSnapshot)
            .where(DesignTokenSnapshot.connection_id == connection_id)
            .order_by(DesignTokenSnapshot.extracted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
