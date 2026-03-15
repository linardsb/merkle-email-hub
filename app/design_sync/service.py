"""Business logic for design sync operations."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.logging import get_logger
from app.design_sync.assets import DesignAssetService
from app.design_sync.canva.service import CanvaDesignSyncService
from app.design_sync.crypto import decrypt_token, encrypt_token
from app.design_sync.exceptions import (
    ConnectionNotFoundError,
    SyncFailedError,
    UnsupportedProviderError,
)
from app.design_sync.figma.service import FigmaDesignSyncService, extract_file_key
from app.design_sync.protocol import DesignNode, DesignSyncProvider
from app.design_sync.repository import DesignSyncRepository
from app.design_sync.schemas import (
    ComponentListResponse,
    ConnectionCreateRequest,
    ConnectionResponse,
    DesignColorResponse,
    DesignComponentResponse,
    DesignNodeResponse,
    DesignSpacingResponse,
    DesignTokensResponse,
    DesignTypographyResponse,
    DownloadAssetsResponse,
    ExportedImageResponse,
    FileStructureResponse,
    ImageExportResponse,
    StoredAssetResponse,
)
from app.design_sync.sketch.service import SketchDesignSyncService
from app.projects.service import ProjectService

logger = get_logger(__name__)

SUPPORTED_PROVIDERS: dict[str, type[DesignSyncProvider]] = {
    "figma": FigmaDesignSyncService,
    "sketch": SketchDesignSyncService,
    "canva": CanvaDesignSyncService,
}


class DesignSyncService:
    """Orchestrates design tool connections and token extraction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = DesignSyncRepository(db)
        self._providers: dict[str, DesignSyncProvider] = {}

    def _get_provider(self, provider_name: str) -> DesignSyncProvider:
        if provider_name not in self._providers:
            provider_cls = SUPPORTED_PROVIDERS.get(provider_name)
            if provider_cls is None:
                raise UnsupportedProviderError(
                    f"Provider '{provider_name}' is not supported. "
                    f"Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
                )
            self._providers[provider_name] = provider_cls()
        return self._providers[provider_name]

    def _extract_file_ref(self, provider: str, file_url: str) -> str:
        """Extract provider-specific file reference from URL."""
        if provider == "figma":
            return extract_file_key(file_url)
        # Stub providers: use the URL itself as the ref
        return file_url

    # ── CRUD ──

    async def list_connections(self, user: User) -> list[ConnectionResponse]:
        """List connections the user owns or has project access to."""
        accessible_ids = await self._get_accessible_project_ids(user)
        rows = await self._repo.list_connections_for_user(user.id, accessible_ids)
        return [
            ConnectionResponse.from_model(conn, project_name=project_name)
            for conn, project_name in rows
        ]

    async def get_connection(self, connection_id: int, user: User) -> ConnectionResponse:
        """Get a single connection by ID with BOLA check."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)
        project_name = await self._get_project_name(conn.project_id)
        return ConnectionResponse.from_model(conn, project_name=project_name)

    async def create_connection(
        self, data: ConnectionCreateRequest, user: User
    ) -> ConnectionResponse:
        """Create a new design tool connection."""
        provider_name = data.provider
        self._get_provider(provider_name)  # validate provider exists

        if data.project_id is not None:
            await self._verify_access(data.project_id, user)

        file_ref = self._extract_file_ref(provider_name, data.file_url)
        token_last4 = data.access_token[-4:] if len(data.access_token) >= 4 else data.access_token

        # Validate credentials with provider
        provider = self._get_provider(provider_name)
        try:
            await provider.validate_connection(file_ref, data.access_token)
        except SyncFailedError:
            raise
        except Exception as exc:
            raise SyncFailedError("Failed to validate connection") from exc

        encrypted = encrypt_token(data.access_token)

        logger.info(
            "design_sync.connection_created",
            provider=provider_name,
            file_ref=file_ref,
        )

        conn = await self._repo.create_connection(
            name=data.name,
            provider=provider_name,
            file_ref=file_ref,
            file_url=data.file_url,
            encrypted_token=encrypted,
            token_last4=token_last4,
            project_id=data.project_id,
            created_by_id=user.id,
        )
        project_name = await self._get_project_name(conn.project_id)
        return ConnectionResponse.from_model(conn, project_name=project_name)

    async def delete_connection(self, connection_id: int, user: User) -> bool:
        """Delete a connection with BOLA check."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        # Delete stored assets
        asset_service = DesignAssetService()
        asset_service.delete_connection_assets(connection_id)

        logger.info("design_sync.connection_deleted", connection_id=connection_id)
        return await self._repo.delete_connection(connection_id)

    async def sync_connection(self, connection_id: int, user: User) -> ConnectionResponse:
        """Trigger a token sync for a connection."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        provider = self._get_provider(conn.provider)
        await self._repo.update_status(conn, "syncing")

        try:
            access_token = decrypt_token(conn.encrypted_token)
            tokens = await provider.sync_tokens(conn.file_ref, access_token)

            tokens_dict = asdict(tokens)
            await self._repo.save_snapshot(conn.id, tokens_dict)
            await self._repo.update_status(conn, "connected")

            logger.info(
                "design_sync.sync_completed",
                connection_id=connection_id,
                provider=conn.provider,
            )
        except Exception as exc:
            await self._repo.update_status(conn, "error", error_message="Sync failed")
            logger.error(
                "design_sync.sync_error",
                connection_id=connection_id,
                error=str(exc),
                exc_info=True,
            )
            raise SyncFailedError("Token sync failed") from exc

        project_name = await self._get_project_name(conn.project_id)
        return ConnectionResponse.from_model(conn, project_name=project_name)

    async def get_tokens(self, connection_id: int, user: User) -> DesignTokensResponse:
        """Get the latest design tokens for a connection."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        snapshot = await self._repo.get_latest_snapshot(connection_id)
        if snapshot is None:
            return DesignTokensResponse(
                connection_id=connection_id,
                colors=[],
                typography=[],
                spacing=[],
                extracted_at=cast(datetime, conn.created_at),
            )

        tj: dict[str, Any] = snapshot.tokens_json
        colors_list: list[dict[str, Any]] = [c for c in tj.get("colors", []) if isinstance(c, dict)]
        typography_list: list[dict[str, Any]] = [
            t for t in tj.get("typography", []) if isinstance(t, dict)
        ]
        spacing_list: list[dict[str, Any]] = [
            s for s in tj.get("spacing", []) if isinstance(s, dict)
        ]
        return DesignTokensResponse(
            connection_id=connection_id,
            colors=[
                DesignColorResponse(
                    name=str(c["name"]),
                    hex=str(c["hex"]),
                    opacity=float(c.get("opacity", 1.0)),
                )
                for c in colors_list
            ],
            typography=[
                DesignTypographyResponse(
                    name=str(t["name"]),
                    family=str(t["family"]),
                    weight=str(t["weight"]),
                    size=float(t["size"]),
                    lineHeight=float(t.get("line_height", t.get("lineHeight", 24))),
                )
                for t in typography_list
            ],
            spacing=[
                DesignSpacingResponse(name=str(s["name"]), value=float(s["value"]))
                for s in spacing_list
            ],
            extracted_at=snapshot.extracted_at,
        )

    # ── Phase 12.1: File Structure, Components, Image Export ──

    async def get_file_structure(
        self, connection_id: int, user: User, *, depth: int | None = 2
    ) -> FileStructureResponse:
        """Get the file structure for a connection."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        provider = self._get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        structure = await provider.get_file_structure(conn.file_ref, access_token, depth=depth)

        return FileStructureResponse(
            connection_id=connection_id,
            file_name=structure.file_name,
            pages=[self._node_to_response(p) for p in structure.pages],
        )

    def _node_to_response(self, node: DesignNode) -> DesignNodeResponse:
        """Recursively convert protocol DesignNode to response schema."""
        return DesignNodeResponse(
            id=node.id,
            name=node.name,
            type=str(node.type),
            children=[self._node_to_response(c) for c in node.children],
            width=node.width,
            height=node.height,
        )

    async def list_components(self, connection_id: int, user: User) -> ComponentListResponse:
        """List components for a connection."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        provider = self._get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        components = await provider.list_components(conn.file_ref, access_token)

        return ComponentListResponse(
            connection_id=connection_id,
            components=[
                DesignComponentResponse(
                    component_id=c.component_id,
                    name=c.name,
                    description=c.description,
                    thumbnail_url=c.thumbnail_url,
                    containing_page=c.containing_page,
                )
                for c in components
            ],
            total=len(components),
        )

    async def export_images(
        self,
        connection_id: int,
        user: User,
        node_ids: list[str],
        *,
        format: str = "png",
        scale: float = 2.0,
    ) -> ImageExportResponse:
        """Export images for nodes in a connection."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        provider = self._get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        images = await provider.export_images(
            conn.file_ref, access_token, node_ids, format=format, scale=scale
        )

        return ImageExportResponse(
            connection_id=connection_id,
            images=[
                ExportedImageResponse(
                    node_id=img.node_id,
                    url=img.url,
                    format=img.format,
                    expires_at=img.expires_at,
                )
                for img in images
            ],
            total=len(images),
        )

    # ── Phase 12.2: Asset Storage ──

    async def download_assets(
        self,
        connection_id: int,
        user: User,
        node_ids: list[str],
        *,
        format: str = "png",
        scale: float = 2.0,
    ) -> DownloadAssetsResponse:
        """Export images from provider and download+store locally."""
        # First export to get temporary URLs
        export_result = await self.export_images(
            connection_id, user, node_ids, format=format, scale=scale
        )

        # Download and store
        asset_service = DesignAssetService()
        images_to_download = [
            {"node_id": img.node_id, "url": img.url} for img in export_result.images
        ]
        stored = await asset_service.download_and_store(
            connection_id, images_to_download, fmt=format
        )

        return DownloadAssetsResponse(
            connection_id=connection_id,
            assets=[
                StoredAssetResponse(node_id=s["node_id"], filename=s["filename"]) for s in stored
            ],
            total=len(stored),
            skipped=len(node_ids) - len(stored),
        )

    def get_asset_path(self, connection_id: int, filename: str) -> Path:
        """Get path to a stored asset (for serving)."""
        asset_service = DesignAssetService()
        return asset_service.get_stored_path(connection_id, filename)

    # ── Helpers ──

    async def _verify_access(self, project_id: int, user: User) -> None:
        project_service = ProjectService(self.db)
        await project_service.verify_project_access(project_id, user)

    async def _get_project_name(self, project_id: int | None) -> str | None:
        """Fetch a single project name by ID."""
        if project_id is None:
            return None
        from sqlalchemy import select

        from app.projects.models import Project

        result = await self.db.execute(select(Project.name).where(Project.id == project_id))
        row = result.scalar_one_or_none()
        return str(row) if row else None

    async def _get_accessible_project_ids(self, user: User) -> list[int]:
        """Get IDs of projects the user can access."""
        if user.role == "admin":
            from sqlalchemy import select

            from app.projects.models import Project

            result = await self.db.execute(select(Project.id))
            return [row[0] for row in result.all()]

        from sqlalchemy import select

        from app.projects.models import ProjectMember

        result = await self.db.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        )
        return [row[0] for row in result.all()]
