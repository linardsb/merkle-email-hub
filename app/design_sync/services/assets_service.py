"""Asset access: file structure, components, image export, downloads."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx
from sqlalchemy.orm.attributes import flag_modified

from app.core.logging import get_logger
from app.design_sync.assets import DesignAssetService
from app.design_sync.crypto import decrypt_token
from app.design_sync.exceptions import ConnectionNotFoundError
from app.design_sync.protocol import (
    DesignFileStructure,
    DesignSyncProvider,
)
from app.design_sync.schemas import (
    ComponentListResponse,
    DesignComponentResponse,
    DownloadAssetsResponse,
    ExportedImageResponse,
    FileStructureResponse,
    ImageExportResponse,
    StoredAssetResponse,
)
from app.design_sync.services._serialization import (
    cached_dict_to_node,
    collect_top_frame_ids,
    deserialize_node,
    node_to_response,
)

if TYPE_CHECKING:
    from app.auth.models import User
    from app.design_sync.models import DesignConnection, DesignTokenSnapshot
    from app.design_sync.services._context import DesignSyncContext


logger = get_logger(__name__)


class AssetsService:
    """Read-side asset access for design connections."""

    def __init__(self, ctx: DesignSyncContext) -> None:
        self._ctx = ctx

    async def get_file_structure(
        self, connection_id: int, user: User, *, depth: int | None = 2
    ) -> FileStructureResponse:
        """Get the file structure for a connection."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        snapshot = await self._ctx.repo.get_latest_snapshot(connection_id)
        if snapshot is not None:
            cached: dict[str, Any] | None = snapshot.tokens_json.get("_file_structure")
            if cached is not None:
                raw_thumbs = snapshot.tokens_json.get("_thumbnails")
                thumbs: dict[str, str] = (
                    cast(dict[str, str], raw_thumbs) if isinstance(raw_thumbs, dict) else {}
                )
                cached_pages = cast(
                    list[dict[str, Any]],
                    [p for p in cached.get("pages", []) if isinstance(p, dict)],
                )
                if thumbs:
                    thumbs = await self._refresh_thumbnails_if_stale(
                        conn, snapshot, thumbs, cached_pages
                    )
                return FileStructureResponse(
                    connection_id=connection_id,
                    file_name=str(cached.get("file_name", "")),
                    pages=[deserialize_node(p) for p in cached_pages],
                    thumbnails=thumbs,
                )

        provider = self._ctx.get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        structure = await provider.get_file_structure(conn.file_ref, access_token, depth=depth)

        return FileStructureResponse(
            connection_id=connection_id,
            file_name=structure.file_name,
            pages=[node_to_response(p) for p in structure.pages],
        )

    async def _refresh_thumbnails_if_stale(
        self,
        conn: DesignConnection,
        snapshot: DesignTokenSnapshot,
        thumbs: dict[str, str],
        cached_pages: list[dict[str, Any]],
    ) -> dict[str, str]:
        """HEAD-check one cached thumbnail; re-export & persist all if expired.

        Provider signed URLs (Figma S3, Penpot CDN) expire after weeks. Cached
        snapshot URLs surface as broken images in the UI. On a single 4xx we
        re-export every top frame and update the snapshot in place. Best-effort
        — any failure returns the original thumbs so the request still succeeds.
        """
        sentinel_url = next(iter(thumbs.values()), None)
        if sentinel_url is None:
            return thumbs
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                head_resp = await client.head(sentinel_url)
            if head_resp.status_code < 400:
                return thumbs
        except httpx.HTTPError:
            return thumbs

        top_frame_ids = collect_top_frame_ids(cached_pages)
        if not top_frame_ids:
            return thumbs

        try:
            provider = self._ctx.get_provider(conn.provider)
            access_token = decrypt_token(conn.encrypted_token)
            images = await provider.export_images(
                conn.file_ref, access_token, top_frame_ids, format="png", scale=1.0
            )
        except Exception:
            logger.warning(
                "design_sync.thumbnail_refresh_failed",
                connection_id=conn.id,
                exc_info=True,
            )
            return thumbs

        refreshed = {img.node_id: img.url for img in images}
        if not refreshed:
            return thumbs

        snapshot.tokens_json["_thumbnails"] = refreshed
        flag_modified(snapshot, "tokens_json")
        try:
            await self._ctx.db.commit()
        except Exception:
            logger.warning(
                "design_sync.thumbnail_refresh_persist_failed",
                connection_id=conn.id,
                exc_info=True,
            )
            await self._ctx.db.rollback()
            return refreshed
        logger.info(
            "design_sync.thumbnails_refreshed",
            connection_id=conn.id,
            count=len(refreshed),
        )
        return refreshed

    async def list_components(self, connection_id: int, user: User) -> ComponentListResponse:
        """List components for a connection."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        provider = self._ctx.get_provider(conn.provider)
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
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        snapshot = await self._ctx.repo.get_latest_snapshot(connection_id)
        cached_thumbs: dict[str, str] = {}
        if snapshot is not None:
            raw = snapshot.tokens_json.get("_thumbnails")
            if isinstance(raw, dict):
                cached_thumbs = cast(dict[str, str], raw)

        cached_images: list[ExportedImageResponse] = []
        uncached_ids: list[str] = []
        for nid in node_ids:
            url = cached_thumbs.get(nid)
            if url:
                cached_images.append(ExportedImageResponse(node_id=nid, url=url, format="png"))
            else:
                uncached_ids.append(nid)

        live_images: list[ExportedImageResponse] = []
        if uncached_ids:
            provider = self._ctx.get_provider(conn.provider)
            access_token = decrypt_token(conn.encrypted_token)
            images = await provider.export_images(
                conn.file_ref, access_token, uncached_ids, format=format, scale=scale
            )
            live_images = [
                ExportedImageResponse(
                    node_id=img.node_id,
                    url=img.url,
                    format=img.format,
                    expires_at=img.expires_at,
                )
                for img in images
            ]

        all_images = cached_images + live_images
        return ImageExportResponse(
            connection_id=connection_id,
            images=all_images,
            total=len(all_images),
        )

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
        export_result = await self.export_images(
            connection_id, user, node_ids, format=format, scale=scale
        )

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

    async def get_design_structure(
        self,
        connection_id: int,
        user: User,
        *,
        selected_node_ids: list[str] | None = None,
    ) -> DesignFileStructure:
        """Get the raw design file structure for the converter pipeline."""
        from app.design_sync.service import _filter_structure

        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)
        provider = self._ctx.get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        structure = await self.get_cached_structure(
            conn.id, conn.file_ref, access_token, provider, depth=None
        )
        if selected_node_ids:
            structure = _filter_structure(structure, selected_node_ids)
        return structure

    async def get_cached_structure(
        self,
        conn_id: int,
        file_ref: str,
        access_token: str,
        provider: DesignSyncProvider,
        *,
        depth: int | None = 3,
    ) -> DesignFileStructure:
        """Get file structure from cache if available, otherwise fetch live."""
        snapshot = await self._ctx.repo.get_latest_snapshot(conn_id)
        if snapshot is not None:
            cached: dict[str, Any] | None = snapshot.tokens_json.get("_file_structure")
            if cached is not None:
                pages_cached = cast(
                    list[dict[str, Any]],
                    [p for p in cached.get("pages", []) if isinstance(p, dict)],
                )
                return DesignFileStructure(
                    file_name=str(cached.get("file_name", "")),
                    pages=[cached_dict_to_node(p) for p in pages_cached],
                )
        return await provider.get_file_structure(file_ref, access_token, depth=depth)
