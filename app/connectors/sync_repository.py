"""Database operations for ESP sync connections."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.sync_models import ESPConnection
from app.projects.models import Project


class ESPSyncRepository:
    """CRUD operations for ESP sync connections."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_connection(
        self,
        *,
        esp_type: str,
        name: str,
        encrypted_credentials: str,
        credentials_hint: str,
        project_id: int,
        created_by_id: int,
    ) -> ESPConnection:
        conn = ESPConnection(
            esp_type=esp_type,
            name=name,
            encrypted_credentials=encrypted_credentials,
            credentials_hint=credentials_hint,
            status="connected",
            project_id=project_id,
            created_by_id=created_by_id,
        )
        self.db.add(conn)
        await self.db.commit()
        await self.db.refresh(conn)
        return conn

    async def get_connection(self, connection_id: int) -> ESPConnection | None:
        result = await self.db.execute(
            select(ESPConnection).where(ESPConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def list_connections_for_user(
        self,
        user_id: int,
        accessible_project_ids: list[int],
    ) -> list[tuple[ESPConnection, str | None]]:
        """List connections the user owns or belonging to accessible projects.

        Returns tuples of (connection, project_name).
        """
        stmt = (
            select(ESPConnection, Project.name)
            .outerjoin(Project, ESPConnection.project_id == Project.id)
            .where(
                or_(
                    ESPConnection.created_by_id == user_id,
                    ESPConnection.project_id.in_(accessible_project_ids),
                )
            )
            .order_by(ESPConnection.created_at.desc())
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
        connection: ESPConnection,
        status: str,
        error_message: str | None = None,
    ) -> None:
        connection.status = status
        connection.error_message = error_message
        if status == "connected":
            connection.last_synced_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(connection)
