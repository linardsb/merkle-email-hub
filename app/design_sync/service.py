"""Business logic for design sync operations."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import get_settings
from app.core.exceptions import ConflictError
from app.core.logging import get_logger
from app.design_sync.assets import DesignAssetService
from app.design_sync.brief_generator import generate_brief as generate_brief_text
from app.design_sync.canva.service import CanvaDesignSyncService
from app.design_sync.crypto import decrypt_token, encrypt_token
from app.design_sync.exceptions import (
    ConnectionNotFoundError,
    ImportNotFoundError,
    ImportStateError,
    SyncFailedError,
    TokenDecryptionError,
    UnsupportedProviderError,
)
from app.design_sync.figma.layout_analyzer import (
    DesignLayoutDescription,
)
from app.design_sync.figma.layout_analyzer import (
    analyze_layout as run_layout_analysis,
)
from app.design_sync.figma.service import FigmaDesignSyncService, extract_file_key
from app.design_sync.penpot.service import extract_file_id as extract_penpot_id
from app.design_sync.protocol import (
    BrowseableProvider,
    DesignFileStructure,
    DesignNode,
    DesignNodeType,
    DesignSyncProvider,
    ExtractedColor,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)
from app.design_sync.repository import DesignSyncRepository
from app.design_sync.schemas import (
    AnalyzedSectionResponse,
    BrowseFilesResponse,
    ButtonElementResponse,
    ComponentListResponse,
    ConnectionCreateRequest,
    ConnectionResponse,
    DesignColorResponse,
    DesignComponentResponse,
    DesignFileResponse,
    DesignNodeResponse,
    DesignSpacingResponse,
    DesignTokensResponse,
    DesignTypographyResponse,
    DownloadAssetsResponse,
    ExportedImageResponse,
    ExtractComponentsResponse,
    FileStructureResponse,
    GenerateBriefResponse,
    ImageExportResponse,
    ImagePlaceholderResponse,
    ImportResponse,
    LayoutAnalysisResponse,
    StartImportRequest,
    StoredAssetResponse,
    TextBlockResponse,
)
from app.design_sync.sketch.service import SketchDesignSyncService
from app.projects.service import ProjectService

logger = get_logger(__name__)

SUPPORTED_PROVIDERS: dict[str, type[DesignSyncProvider]] = {
    "figma": FigmaDesignSyncService,
    "sketch": SketchDesignSyncService,
    "canva": CanvaDesignSyncService,
}

# Register Penpot provider when enabled (self-hosted design tool)
if get_settings().design_sync.penpot_enabled:
    from app.design_sync.penpot.service import PenpotDesignSyncService

    SUPPORTED_PROVIDERS["penpot"] = PenpotDesignSyncService

# Register mock provider in development mode
if get_settings().environment == "development":
    from app.design_sync.mock.service import MockDesignSyncService

    SUPPORTED_PROVIDERS["mock"] = MockDesignSyncService


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
        if provider == "penpot":
            return extract_penpot_id(file_url)
        # Stub providers: use the URL itself as the ref
        return file_url

    # ── Browse Files (pre-connection) ──

    async def browse_files(self, provider_name: str, access_token: str) -> BrowseFilesResponse:
        """Browse design files from a provider before creating a connection.

        No DB session needed — operates pre-connection.
        """
        provider = self._get_provider(provider_name)

        if not isinstance(provider, BrowseableProvider):
            logger.info("design_sync.browse_not_supported", provider=provider_name)
            return BrowseFilesResponse(provider=provider_name, files=[], total=0)

        files = await provider.list_files(access_token)
        logger.info(
            "design_sync.browse_files_completed",
            provider=provider_name,
            count=len(files),
        )
        return BrowseFilesResponse(
            provider=provider_name,
            files=[
                DesignFileResponse(
                    file_id=f.file_id,
                    name=f.name,
                    url=f.url,
                    thumbnail_url=f.thumbnail_url,
                    last_modified=f.last_modified,
                    folder=f.folder,
                )
                for f in files
            ],
            total=len(files),
        )

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

        # Check for duplicate connection to the same file
        existing = await self._repo.get_connection_by_file_ref(provider_name, file_ref)
        if existing is not None:
            raise ConflictError(
                f"A connection to this file already exists ('{existing.name}', id={existing.id}). "
                "Use the token refresh endpoint to update credentials."
            )

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

        # Decrypt the stored token — fails if encryption key has rotated
        try:
            access_token = decrypt_token(conn.encrypted_token)
        except Exception as exc:
            await self._repo.update_status(
                conn,
                "error",
                error_message="Access token expired or encryption key changed. Please refresh your token.",
            )
            raise TokenDecryptionError(
                "Cannot decrypt stored access token. The encryption key may have changed. "
                "Please update your access token via the connection settings."
            ) from exc

        await self._repo.update_status(conn, "syncing")

        try:
            tokens = await provider.sync_tokens(conn.file_ref, access_token)

            # Also fetch and cache file structure during sync to avoid extra API calls
            structure_cache = None
            try:
                structure = await provider.get_file_structure(conn.file_ref, access_token, depth=3)
                structure_cache = {
                    "file_name": structure.file_name,
                    "pages": [self._serialize_node(p) for p in structure.pages],
                }
            except Exception:
                pass

            # Cache thumbnail URLs for top-level frames (avoids Figma API on every page load)
            thumbnail_cache: dict[str, str] | None = None
            if structure_cache is not None:
                try:
                    top_frame_ids = self._collect_top_frame_ids(structure_cache["pages"])
                    if top_frame_ids:
                        images = await provider.export_images(
                            conn.file_ref, access_token, top_frame_ids, format="png", scale=1.0
                        )
                        thumbnail_cache = {img.node_id: img.url for img in images}
                except Exception:
                    pass  # Thumbnails are non-critical

            tokens_dict = asdict(tokens)
            if structure_cache is not None:
                tokens_dict["_file_structure"] = structure_cache
            if thumbnail_cache:
                tokens_dict["_thumbnails"] = thumbnail_cache
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

    async def refresh_token(
        self, connection_id: int, new_access_token: str, user: User
    ) -> ConnectionResponse:
        """Update the access token for an existing connection."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        # Validate new token with provider
        provider = self._get_provider(conn.provider)
        try:
            await provider.validate_connection(conn.file_ref, new_access_token)
        except SyncFailedError:
            raise
        except Exception as exc:
            raise SyncFailedError("Failed to validate new token") from exc

        # Re-encrypt and save
        encrypted = encrypt_token(new_access_token)
        token_last4 = new_access_token[-4:] if len(new_access_token) >= 4 else new_access_token
        await self._repo.update_connection_token(conn, encrypted, token_last4)
        await self._repo.update_status(conn, "connected")

        logger.info(
            "design_sync.token_refreshed",
            connection_id=connection_id,
            provider=conn.provider,
        )

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
        """Get the file structure for a connection.

        Serves from cached snapshot when available to avoid extra Figma API calls.
        Falls back to live API if no cache exists.
        """
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        # Try cached structure from last sync
        snapshot = await self._repo.get_latest_snapshot(connection_id)
        if snapshot is not None:
            cached = snapshot.tokens_json.get("_file_structure")
            if isinstance(cached, dict):
                # Include cached thumbnails if available
                raw_thumbs = snapshot.tokens_json.get("_thumbnails")
                thumbs: dict[str, str] = (
                    cast(dict[str, str], raw_thumbs)
                    if isinstance(raw_thumbs, dict)
                    else {}
                )
                return FileStructureResponse(
                    connection_id=connection_id,
                    file_name=str(cached.get("file_name", "")),
                    pages=[
                        self._deserialize_node(p)
                        for p in cached.get("pages", [])
                        if isinstance(p, dict)
                    ],
                    thumbnails=thumbs,
                )

        # No cache — fetch live
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
            x=node.x,
            y=node.y,
            text_content=node.text_content,
        )

    def _serialize_node(self, node: DesignNode) -> dict[str, Any]:
        """Serialize a DesignNode to a JSON-safe dict for caching."""
        return {
            "id": node.id,
            "name": node.name,
            "type": str(node.type),
            "children": [self._serialize_node(c) for c in node.children],
            "width": node.width,
            "height": node.height,
            "x": node.x,
            "y": node.y,
            "text_content": node.text_content,
        }

    _THUMBNAIL_NODE_TYPES = {"FRAME", "COMPONENT", "INSTANCE", "GROUP", "SECTION"}
    _MAX_THUMBNAIL_CACHE = 100  # Single Figma API call (100 IDs per batch)

    def _collect_top_frame_ids(self, pages: list[dict[str, Any]]) -> list[str]:
        """Collect frame IDs from cached structure, prioritising top-level email sections."""
        scored: list[tuple[float, str]] = []

        def walk(node: dict[str, Any], depth: int) -> None:
            ntype = str(node.get("type", ""))
            if ntype in self._THUMBNAIL_NODE_TYPES:
                area = float(node.get("width", 0) or 0) * float(node.get("height", 0) or 0)
                score = 0.0
                if depth == 0:
                    score += 1000
                score += min(200.0, area / 1000)
                score += max(0.0, 50 - depth * 10)
                scored.append((score, str(node.get("id", ""))))
            for child in node.get("children", []):
                if isinstance(child, dict):
                    walk(child, depth + 1)

        for page in pages:
            if isinstance(page, dict):
                for child in page.get("children", []):
                    if isinstance(child, dict):
                        walk(child, 0)

        scored.sort(key=lambda x: x[0], reverse=True)
        return [sid for _, sid in scored[: self._MAX_THUMBNAIL_CACHE]]

    def _deserialize_node(self, data: dict[str, Any]) -> DesignNodeResponse:
        """Deserialize a cached node dict to DesignNodeResponse."""
        return DesignNodeResponse(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            type=str(data.get("type", "OTHER")),
            children=[
                self._deserialize_node(c) for c in data.get("children", []) if isinstance(c, dict)
            ],
            width=data.get("width"),
            height=data.get("height"),
            x=data.get("x"),
            y=data.get("y"),
            text_content=data.get("text_content"),
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
        """Export images for nodes in a connection.

        Serves from cached thumbnail URLs when available (populated during sync).
        Falls back to live Figma API for cache misses.
        """
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        # Try cached thumbnails first (avoids Figma API calls on every page load)
        snapshot = await self._repo.get_latest_snapshot(connection_id)
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
                cached_images.append(
                    ExportedImageResponse(node_id=nid, url=url, format="png")
                )
            else:
                uncached_ids.append(nid)

        # Fetch uncached nodes from provider (if any)
        live_images: list[ExportedImageResponse] = []
        if uncached_ids:
            provider = self._get_provider(conn.provider)
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

    # ── Phase 12.4: Layout Analysis & Brief Generation ──

    async def analyze_layout(
        self,
        connection_id: int,
        user: User,
        *,
        selected_node_ids: list[str] | None = None,
        depth: int | None = 3,
    ) -> LayoutAnalysisResponse:
        """Analyze layout of a design file and return detected sections.

        Uses cached file structure when available to avoid Figma API calls.
        Falls back to live API if no cache exists.
        """
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        provider = self._get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        structure = await self._get_cached_structure(
            conn.id, conn.file_ref, access_token, provider, depth=depth
        )

        if selected_node_ids:
            structure = _filter_structure(structure, selected_node_ids)

        layout = run_layout_analysis(structure)
        return _layout_to_response(connection_id, layout)

    async def generate_brief(
        self,
        connection_id: int,
        user: User,
        *,
        selected_node_ids: list[str] | None = None,
        include_tokens: bool = True,
    ) -> GenerateBriefResponse:
        """Generate a Scaffolder-compatible brief from design analysis.

        Uses cached file structure and tokens to avoid Figma API calls.
        """
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        provider = self._get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        structure = await self._get_cached_structure(
            conn.id, conn.file_ref, access_token, provider, depth=None
        )

        if selected_node_ids:
            structure = _filter_structure(structure, selected_node_ids)

        layout = run_layout_analysis(structure)

        tokens: ExtractedTokens | None = None
        if include_tokens:
            # Try cached tokens first, fall back to live API
            snapshot = await self._repo.get_latest_snapshot(connection_id)
            if snapshot is not None:
                try:
                    tokens = ExtractedTokens(
                        colors=[ExtractedColor(**c) for c in snapshot.tokens_json.get("colors", [])],
                        typography=[ExtractedTypography(**t) for t in snapshot.tokens_json.get("typography", [])],
                        spacing=[ExtractedSpacing(**s) for s in snapshot.tokens_json.get("spacing", [])],
                    )
                except Exception:
                    tokens = None
            if tokens is None:
                try:
                    tokens = await provider.sync_tokens(conn.file_ref, access_token)
                except Exception:
                    logger.warning(
                        "design_sync.brief_tokens_skipped",
                        connection_id=connection_id,
                        exc_info=True,
                    )

        brief_text = generate_brief_text(
            layout,
            tokens=tokens,
            asset_url_prefix=f"/api/v1/design-sync/assets/{connection_id}",
            connection_id=connection_id,
        )

        sections_summary = ", ".join(s.section_type.value for s in layout.sections)

        return GenerateBriefResponse(
            connection_id=connection_id,
            brief=brief_text,
            sections_detected=len(layout.sections),
            layout_summary=sections_summary or "no sections detected",
        )

    # ── Phase 12.6: Component Extraction ──

    async def extract_components(
        self,
        connection_id: int,
        user: User,
        component_ids: list[str] | None = None,
        generate_html: bool = True,
    ) -> ExtractComponentsResponse:
        """Kick off background component extraction from a design connection."""
        from app.components.repository import ComponentRepository
        from app.core.exceptions import DomainValidationError, NotFoundError
        from app.design_sync.component_extractor import ComponentExtractor

        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        # List components first (synchronous) to get count
        provider = self._get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        components = await provider.list_components(conn.file_ref, access_token)
        if component_ids:
            components = [c for c in components if c.component_id in component_ids]

        if not components:
            raise NotFoundError("No components found in design file")

        # Create DesignImport record to track progress
        if conn.project_id is None:
            raise DomainValidationError("Connection must be linked to a project for extraction")
        design_import = await self._repo.create_import(
            connection_id=connection_id,
            project_id=conn.project_id,
            selected_node_ids=[c.component_id for c in components],
            created_by_id=user.id,
        )

        # Launch background extraction
        extractor = ComponentExtractor(
            provider=provider,
            design_repo=self._repo,
            component_repo=ComponentRepository(self.db),
            db=self.db,
        )
        _task = asyncio.create_task(  # noqa: RUF006
            extractor.extract(
                import_id=design_import.id,
                file_ref=conn.file_ref,
                access_token=access_token,
                user_id=user.id,
                component_ids=component_ids,
                generate_html=generate_html,
            )
        )

        return ExtractComponentsResponse(
            import_id=design_import.id,
            status="extracting",
            total_components=len(components),
            message=f"Extracting {len(components)} components in the background",
        )

    # ── Phase 12.5: Design Import & Conversion Pipeline ──

    async def create_design_import(
        self,
        data: StartImportRequest,
        user: User,
    ) -> ImportResponse:
        """Create a new import record with brief. Status = pending."""
        from app.core.exceptions import DomainValidationError

        conn = await self._repo.get_connection(data.connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {data.connection_id} not found")
        if conn.project_id is None:
            raise DomainValidationError("Connection must be linked to a project")
        await self._verify_access(conn.project_id, user)

        design_import = await self._repo.create_import(
            connection_id=data.connection_id,
            project_id=conn.project_id,
            selected_node_ids=data.selected_node_ids,
            created_by_id=user.id,
        )
        # Store brief and optional template name
        await self._repo.update_import_status(
            design_import,
            "pending",
            generated_brief=data.brief,
            structure_json={"template_name": data.template_name} if data.template_name else None,
        )

        logger.info(
            "design_sync.import_created",
            import_id=design_import.id,
            connection_id=data.connection_id,
        )
        # Re-fetch with assets eagerly loaded for async-safe serialization
        loaded = await self._repo.get_import(design_import.id)
        return self._import_to_response(loaded)

    async def get_design_import(self, import_id: int, user: User) -> ImportResponse:
        """Get import status with BOLA check."""
        design_import = await self._repo.get_import_with_assets(import_id)
        if design_import is None:
            raise ImportNotFoundError(f"Import {import_id} not found")
        await self._verify_access(design_import.project_id, user)
        return self._import_to_response(design_import)

    async def update_import_brief(self, import_id: int, brief: str, user: User) -> ImportResponse:
        """Update the brief on a pending import."""
        design_import = await self._repo.get_import(import_id)
        if design_import is None:
            raise ImportNotFoundError(f"Import {import_id} not found")
        await self._verify_access(design_import.project_id, user)
        if design_import.status != "pending":
            raise ImportStateError(
                f"Cannot edit brief: import is '{design_import.status}', expected 'pending'"
            )
        await self._repo.update_import_status(design_import, "pending", generated_brief=brief)
        logger.info("design_sync.import_brief_updated", import_id=import_id)
        # Re-fetch with assets eagerly loaded after commit expired relationships
        loaded = await self._repo.get_import(import_id)
        return self._import_to_response(loaded)

    async def start_conversion(
        self,
        import_id: int,
        user: User,
        *,
        run_qa: bool = True,
        output_mode: Literal["html", "structured"] = "structured",
    ) -> ImportResponse:
        """Kick off the background conversion pipeline."""
        from app.core.exceptions import DomainValidationError

        design_import = await self._repo.get_import(import_id)
        if design_import is None:
            raise ImportNotFoundError(f"Import {import_id} not found")
        await self._verify_access(design_import.project_id, user)
        if design_import.status not in ("pending", "failed"):
            raise ImportStateError(
                f"Cannot convert: import is '{design_import.status}', expected 'pending' or 'failed'"
            )
        if not design_import.generated_brief:
            raise DomainValidationError("Import has no brief — set one before converting")

        # Update status before launching background task to avoid race
        await self._repo.update_import_status(design_import, "converting")
        logger.info("design_sync.conversion_started", import_id=import_id)

        # Launch background pipeline with its own DB session
        from app.design_sync.import_service import DesignImportService

        import_service = DesignImportService(
            design_service_factory=type(self),
            user=user,
        )

        def _on_task_done(task: asyncio.Task[None]) -> None:
            if task.cancelled():
                logger.warning("design_sync.conversion_cancelled", import_id=import_id)
            elif task.exception() is not None:
                logger.error(
                    "design_sync.conversion_task_failed",
                    import_id=import_id,
                    error=str(task.exception()),
                )

        task = asyncio.create_task(
            import_service.run_conversion(
                import_id=import_id,
                run_qa=run_qa,
                output_mode=output_mode,
            )
        )
        task.add_done_callback(_on_task_done)

        # Re-fetch with assets eagerly loaded after commit expired relationships
        loaded = await self._repo.get_import(import_id)
        return self._import_to_response(loaded)

    async def get_import_by_template(
        self, template_id: int, project_id: int, user: User
    ) -> ImportResponse | None:
        """Get the completed design import for a template, if any."""
        await self._verify_access(project_id, user)
        design_import = await self._repo.get_import_by_template_id(template_id, project_id)
        if design_import is None:
            return None
        return self._import_to_response(design_import)

    def _import_to_response(self, design_import: object) -> ImportResponse:
        """Convert DesignImport model to response schema."""
        return ImportResponse.model_validate(design_import, from_attributes=True)

    async def _get_cached_structure(
        self, conn_id: int, file_ref: str, access_token: str, provider: DesignSyncProvider, *, depth: int | None = 3
    ) -> DesignFileStructure:
        """Get file structure from cache if available, otherwise fetch live."""
        snapshot = await self._repo.get_latest_snapshot(conn_id)
        if snapshot is not None:
            cached = snapshot.tokens_json.get("_file_structure")
            if isinstance(cached, dict):
                return DesignFileStructure(
                    file_name=str(cached.get("file_name", "")),
                    pages=[
                        self._cached_dict_to_node(p)
                        for p in cached.get("pages", [])
                        if isinstance(p, dict)
                    ],
                )
        return await provider.get_file_structure(file_ref, access_token, depth=depth)

    def _cached_dict_to_node(self, data: dict[str, Any]) -> DesignNode:
        """Convert a cached node dict back to a protocol DesignNode."""
        raw_type = str(data.get("type", "OTHER"))
        try:
            node_type = DesignNodeType(raw_type)
        except ValueError:
            node_type = DesignNodeType.OTHER
        return DesignNode(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            type=node_type,
            children=[self._cached_dict_to_node(c) for c in data.get("children", []) if isinstance(c, dict)],
            width=data.get("width"),
            height=data.get("height"),
            x=data.get("x"),
            y=data.get("y"),
            text_content=data.get("text_content"),
        )

    # ── Helpers ──

    async def _verify_access(self, project_id: int, user: User) -> None:
        project_service = ProjectService(self.db)
        await project_service.verify_project_access(project_id, user)

    async def _get_project_name(self, project_id: int | None) -> str | None:
        """Fetch a single project name by ID."""
        return await self._repo.get_project_name(project_id)

    async def _get_accessible_project_ids(self, user: User) -> list[int]:
        """Get IDs of projects the user can access."""
        return await self._repo.get_accessible_project_ids(user.id, user.role)


# ── Module-level helpers for 12.4 ──


def _filter_structure(
    structure: DesignFileStructure,
    selected_ids: list[str],
) -> DesignFileStructure:
    """Filter a DesignFileStructure to only include nodes with matching IDs."""
    id_set = set(selected_ids)

    def _filter_node(node: DesignNode) -> DesignNode | None:
        if node.id in id_set:
            return node
        filtered_children = [c for c in (_filter_node(ch) for ch in node.children) if c is not None]
        if filtered_children:
            return DesignNode(
                id=node.id,
                name=node.name,
                type=node.type,
                children=filtered_children,
                width=node.width,
                height=node.height,
                x=node.x,
                y=node.y,
                text_content=node.text_content,
            )
        return None

    filtered_pages: list[DesignNode] = []
    for page in structure.pages:
        filtered = _filter_node(page)
        if filtered is not None:
            filtered_pages.append(filtered)

    return DesignFileStructure(file_name=structure.file_name, pages=filtered_pages)


def _layout_to_response(
    connection_id: int,
    layout: DesignLayoutDescription,
) -> LayoutAnalysisResponse:
    """Convert DesignLayoutDescription to LayoutAnalysisResponse."""

    sections = [
        AnalyzedSectionResponse(
            section_type=s.section_type.value,
            node_id=s.node_id,
            node_name=s.node_name,
            y_position=s.y_position,
            width=s.width,
            height=s.height,
            column_layout=s.column_layout.value,
            column_count=s.column_count,
            texts=[
                TextBlockResponse(
                    node_id=t.node_id,
                    content=t.content,
                    font_size=t.font_size,
                    is_heading=t.is_heading,
                )
                for t in s.texts
            ],
            images=[
                ImagePlaceholderResponse(
                    node_id=img.node_id,
                    node_name=img.node_name,
                    width=img.width,
                    height=img.height,
                )
                for img in s.images
            ],
            buttons=[
                ButtonElementResponse(
                    node_id=btn.node_id,
                    text=btn.text,
                    width=btn.width,
                    height=btn.height,
                )
                for btn in s.buttons
            ],
            spacing_after=s.spacing_after,
        )
        for s in layout.sections
    ]

    return LayoutAnalysisResponse(
        connection_id=connection_id,
        file_name=layout.file_name,
        overall_width=layout.overall_width,
        sections=sections,
        total_text_blocks=layout.total_text_blocks,
        total_images=layout.total_images,
    )
