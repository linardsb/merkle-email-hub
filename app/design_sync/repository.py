"""Database operations for design sync."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.design_sync.models import (
    DesignConnection,
    DesignImport,
    DesignImportAsset,
    DesignTokenSnapshot,
)


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

    # ── Design Imports ──

    async def create_import(
        self,
        *,
        connection_id: int,
        project_id: int,
        selected_node_ids: list[str],
        created_by_id: int,
    ) -> DesignImport:
        design_import = DesignImport(
            connection_id=connection_id,
            project_id=project_id,
            status="pending",
            selected_node_ids=selected_node_ids,
            created_by_id=created_by_id,
        )
        self.db.add(design_import)
        await self.db.commit()
        await self.db.refresh(design_import)
        return design_import

    async def get_import(self, import_id: int) -> DesignImport | None:
        result = await self.db.execute(select(DesignImport).where(DesignImport.id == import_id))
        return result.scalar_one_or_none()

    async def get_import_with_assets(self, import_id: int) -> DesignImport | None:
        """Get import with eagerly loaded assets."""
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(DesignImport)
            .options(selectinload(DesignImport.assets))
            .where(DesignImport.id == import_id)
        )
        return result.scalar_one_or_none()

    async def get_import_by_template_id(
        self, template_id: int, project_id: int
    ) -> DesignImport | None:
        """Get the completed design import that produced a given template."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(DesignImport)
            .options(selectinload(DesignImport.assets))
            .where(
                DesignImport.result_template_id == template_id,
                DesignImport.project_id == project_id,
                DesignImport.status == "completed",
            )
            .order_by(DesignImport.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_imports_for_project(self, project_id: int) -> list[DesignImport]:
        result = await self.db.execute(
            select(DesignImport)
            .where(DesignImport.project_id == project_id)
            .order_by(DesignImport.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_import_status(
        self,
        design_import: DesignImport,
        status: str,
        *,
        error_message: str | None = None,
        structure_json: dict[str, object] | None = None,
        generated_brief: str | None = None,
        result_template_id: int | None = None,
    ) -> None:
        design_import.status = status
        if error_message is not None:
            design_import.error_message = error_message
        if structure_json is not None:
            design_import.structure_json = structure_json
        if generated_brief is not None:
            design_import.generated_brief = generated_brief
        if result_template_id is not None:
            design_import.result_template_id = result_template_id
        await self.db.commit()
        await self.db.refresh(design_import)

    async def cancel_import(self, design_import: DesignImport) -> None:
        """Cancel an import if it's still in a cancellable state."""
        if design_import.status in ("pending", "extracting"):
            design_import.status = "cancelled"
            await self.db.commit()
            await self.db.refresh(design_import)

    # ── Import Assets ──

    async def create_import_asset(
        self,
        *,
        import_id: int,
        node_id: str,
        node_name: str,
        file_path: str,
        width: int | None = None,
        height: int | None = None,
        format: str = "png",
        usage: str | None = None,
    ) -> DesignImportAsset:
        asset = DesignImportAsset(
            import_id=import_id,
            node_id=node_id,
            node_name=node_name,
            file_path=file_path,
            width=width,
            height=height,
            format=format,
            usage=usage,
        )
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def bulk_create_import_assets(
        self,
        import_id: int,
        assets: list[dict[str, object]],
    ) -> list[DesignImportAsset]:
        """Create multiple assets in a single flush. Each dict must have
        node_id, node_name, file_path; optional: width, height, format, usage."""
        models = [
            DesignImportAsset(
                import_id=import_id,
                node_id=str(a["node_id"]),
                node_name=str(a["node_name"]),
                file_path=str(a["file_path"]),
                width=a.get("width"),
                height=a.get("height"),
                format=str(a.get("format", "png")),
                usage=a.get("usage"),
            )
            for a in assets
        ]
        self.db.add_all(models)
        await self.db.commit()
        for m in models:
            await self.db.refresh(m)
        return models

    async def list_import_assets(self, import_id: int) -> list[DesignImportAsset]:
        result = await self.db.execute(
            select(DesignImportAsset)
            .where(DesignImportAsset.import_id == import_id)
            .order_by(DesignImportAsset.id)
        )
        return list(result.scalars().all())

    # ── Project lookups (used by service layer) ──

    async def get_project_name(self, project_id: int | None) -> str | None:
        """Fetch a single project name by ID."""
        if project_id is None:
            return None
        from app.projects.models import Project

        result = await self.db.execute(select(Project.name).where(Project.id == project_id))
        row = result.scalar_one_or_none()
        return str(row) if row else None

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
