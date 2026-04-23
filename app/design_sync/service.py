"""Business logic for design sync operations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import get_settings
from app.core.exceptions import ConflictError
from app.core.logging import get_logger
from app.core.progress import OperationStatus, ProgressTracker
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
    CompatibilityHintResponse,
    ComponentListResponse,
    ConnectionCreateRequest,
    ConnectionResponse,
    DesignColorResponse,
    DesignComponentResponse,
    DesignFileResponse,
    DesignGradientResponse,
    DesignGradientStopResponse,
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
    TokenDiffEntry,
    TokenDiffResponse,
    W3cImportResponse,
)
from app.design_sync.sketch.service import SketchDesignSyncService
from app.projects.service import ProjectService

if TYPE_CHECKING:
    from app.design_sync.schemas import DesignSyncUpdateMessage, ImportW3cTokensRequest

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

    SUPPORTED_PROVIDERS["mock"] = MockDesignSyncService  # type: ignore[assignment]  # structural Protocol subtype


async def fetch_target_clients(
    db: AsyncSession,
    project_id: int | None,
) -> list[str] | None:
    """Fetch project target clients for compatibility checks (best-effort).

    Returns None if no project or if the lookup fails for any reason.
    """
    if not project_id:
        return None
    try:
        from app.projects.repository import ProjectRepository

        project = await ProjectRepository(db).get(project_id)
        return project.target_clients if project else None
    except Exception:
        logger.debug("design_sync.target_clients_skip", exc_info=True)
        return None


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

        config_json = data.config.model_dump(exclude_none=True) if data.config else None

        conn = await self._repo.create_connection(
            name=data.name,
            provider=provider_name,
            file_ref=file_ref,
            file_url=data.file_url,
            encrypted_token=encrypted,
            token_last4=token_last4,
            project_id=data.project_id,
            created_by_id=user.id,
            config_json=config_json,
        )

        # Auto-sync tokens and file structure on creation
        try:
            return await self.sync_connection(conn.id, user)
        except Exception:
            logger.warning(
                "design_sync.auto_sync_failed",
                connection_id=conn.id,
                exc_info=True,
            )
            # Return the connection even if sync fails — user can retry manually
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

    async def sync_connection(self, connection_id: int, user: User | None) -> ConnectionResponse:
        """Trigger a token sync for a connection."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None and user is not None:
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

        target_clients = await fetch_target_clients(self.db, conn.project_id)

        try:
            # New path: adapter builds full document (Figma, Penpot)
            if hasattr(provider, "build_document"):
                from app.design_sync.email_design_document import EmailDesignDocument
                from app.design_sync.token_transforms import TokenWarning

                _raw = await provider.build_document(
                    conn.file_ref,
                    access_token,
                    connection_config=conn.config_json,
                    target_clients=target_clients,
                )
                document = cast(EmailDesignDocument, _raw[0])
                tokens = cast(ExtractedTokens, _raw[1])
                token_warnings = cast(list[TokenWarning], _raw[2])
                structure = cast(DesignFileStructure, _raw[3])
                doc_json: dict[str, object] | None = document.to_json()
            else:
                # Legacy path for stub providers (Sketch, Canva)
                tokens, structure = await provider.sync_tokens_and_structure(
                    conn.file_ref, access_token
                )
                from app.design_sync.token_transforms import validate_and_transform

                tokens, token_warnings = validate_and_transform(
                    tokens, target_clients=target_clients
                )
                doc_json = None
                try:
                    from app.design_sync.email_design_document import (
                        EmailDesignDocument,
                    )

                    document = EmailDesignDocument.from_legacy(
                        structure,
                        tokens,
                        connection_config=conn.config_json,
                        source_provider=conn.provider,
                    )
                    doc_json = document.to_json()
                except (ValueError, KeyError, TypeError):
                    logger.warning(
                        "design_sync.document_json_build_failed",
                        connection_id=connection_id,
                        exc_info=True,
                    )

            # Structure cache + thumbnails (shared by both paths)
            structure_cache: dict[str, Any] = {
                "file_name": structure.file_name,
                "pages": [self._serialize_node(p) for p in structure.pages],
            }

            thumbnail_cache: dict[str, str] | None = None
            try:
                top_frame_ids = self._collect_top_frame_ids(structure_cache["pages"])
                if top_frame_ids:
                    images = await provider.export_images(
                        conn.file_ref, access_token, top_frame_ids, format="png", scale=1.0
                    )
                    thumbnail_cache = {img.node_id: img.url for img in images}
            except Exception:
                logger.warning(
                    "design_sync.thumbnail_cache_failed",
                    connection_id=connection_id,
                    exc_info=True,
                )

            tokens_dict = asdict(tokens)
            tokens_dict["_file_structure"] = structure_cache
            if thumbnail_cache:
                tokens_dict["_thumbnails"] = thumbnail_cache
            if token_warnings:
                tokens_dict["_token_warnings"] = [
                    {
                        "level": w.level,
                        "field": w.field,
                        "message": w.message,
                        "original_value": w.original_value,
                        "fixed_value": w.fixed_value,
                    }
                    for w in token_warnings
                ]
                # Store client-aware warnings as compatibility hints
                if target_clients:
                    client_hints = [
                        {
                            "level": w.level,
                            "css_property": w.field,
                            "message": w.message,
                            "affected_clients": [],
                        }
                        for w in token_warnings
                        if "font-face" in w.message.lower()
                        or "Word engine" in w.message
                        or "opacity" in w.field
                    ]
                    if client_hints:
                        tokens_dict["_compatibility_hints"] = client_hints

            await self._repo.save_snapshot(conn.id, tokens_dict, document_json=doc_json)
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

    async def link_connection_to_project(
        self, connection_id: int, project_id: int | None, user: User
    ) -> ConnectionResponse:
        """Link or unlink a connection to a project."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        # Verify access to current project if linked
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)
        # Verify access to target project
        if project_id is not None:
            await self._verify_access(project_id, user)

        conn.project_id = project_id
        await self.db.commit()

        logger.info(
            "design_sync.connection_linked",
            connection_id=connection_id,
            project_id=project_id,
        )

        project_name = await self._get_project_name(project_id)
        return ConnectionResponse.from_model(conn, project_name=project_name)

    async def get_diagnostic_data(
        self, connection_id: int, user: User
    ) -> tuple[DesignFileStructure, ExtractedTokens]:
        """Return protocol-level structure + tokens for diagnostic pipeline.

        Reads from the cached snapshot to get full-fidelity data (all node fields).
        Raises ConnectionNotFoundError if connection doesn't exist.
        Raises ConflictError if no snapshot is available yet.
        """
        from app.design_sync.diagnose.report import _dict_to_tokens, _node_from_dict

        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)

        snapshot = await self._repo.get_latest_snapshot(connection_id)
        if snapshot is None:
            raise ConflictError("No sync snapshot available — sync the connection first")

        tokens_json = snapshot.tokens_json
        cached_structure = tokens_json.get("_file_structure")
        if isinstance(cached_structure, dict):
            pages = [
                _node_from_dict(p) for p in cached_structure.get("pages", []) if isinstance(p, dict)
            ]
            structure = DesignFileStructure(
                file_name=str(cached_structure.get("file_name", "")),
                pages=pages,
            )
        else:
            structure = DesignFileStructure(file_name="", pages=[])

        tokens = _dict_to_tokens(tokens_json)
        return structure, tokens

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
        # Extract token warnings from snapshot (stored by sync_connection)
        raw_warnings = tj.get("_token_warnings", [])
        warning_strings: list[str] | None = None
        if raw_warnings:
            warning_strings = [
                f"[{w.get('level', 'info')}] {w.get('field', '?')}: {w.get('message', '')}"
                for w in raw_warnings
                if isinstance(w, dict)
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
                    letterSpacing=t.get("letter_spacing", t.get("letterSpacing")),
                    textTransform=t.get("text_transform", t.get("textTransform")),
                    textDecoration=t.get("text_decoration", t.get("textDecoration")),
                )
                for t in typography_list
            ],
            spacing=[
                DesignSpacingResponse(name=str(s["name"]), value=float(s["value"]))
                for s in spacing_list
            ],
            dark_colors=[
                DesignColorResponse(
                    name=str(c["name"]),
                    hex=str(c["hex"]),
                    opacity=float(c.get("opacity", 1.0)),
                )
                for c in tj.get("dark_colors", [])
                if isinstance(c, dict)
            ],
            gradients=[
                DesignGradientResponse(
                    name=str(g["name"]),
                    type=str(g.get("type", "linear")),
                    angle=float(g.get("angle", 180)),
                    stops=[
                        DesignGradientStopResponse(
                            hex=str(s.get("hex", "")),
                            position=float(s.get("position", 0)),
                        )
                        for s in g.get("stops", [])
                        if isinstance(s, dict)
                    ],
                    fallback_hex=str(g.get("fallback_hex", "#808080")),
                )
                for g in tj.get("gradients", [])
                if isinstance(g, dict)
            ],
            extracted_at=snapshot.extracted_at,
            warnings=warning_strings or None,
            compatibility_hints=self._read_compatibility_hints(tj),
        )

    @staticmethod
    def _read_compatibility_hints(
        tj: dict[str, Any],
    ) -> list[CompatibilityHintResponse] | None:
        """Read stored compatibility hints from snapshot JSON."""
        raw = tj.get("_compatibility_hints", [])
        if not raw:
            return None
        return [
            CompatibilityHintResponse(
                level=str(h.get("level", "info")),
                css_property=str(h.get("css_property", "")),
                message=str(h.get("message", "")),
                affected_clients=list(h.get("affected_clients", [])),
            )
            for h in raw
            if isinstance(h, dict)
        ]

    # ── Token Diff ──

    async def get_token_diff(
        self, connection_id: int, user: User | None = None
    ) -> TokenDiffResponse:
        """Compare current token snapshot vs previous."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None and user is not None:
            await self._verify_access(conn.project_id, user)

        current = await self._repo.get_latest_snapshot(connection_id)
        if current is None:
            return TokenDiffResponse(
                connection_id=connection_id,
                current_extracted_at=cast(datetime, conn.created_at),
                entries=[],
            )

        previous = await self._repo.get_previous_snapshot(connection_id)
        entries = self._compute_token_diff(
            current.tokens_json,
            previous.tokens_json if previous else {},
        )

        return TokenDiffResponse(
            connection_id=connection_id,
            current_extracted_at=current.extracted_at,
            previous_extracted_at=previous.extracted_at if previous else None,
            entries=entries,
            has_previous=previous is not None,
        )

    @staticmethod
    def _compute_token_diff(
        current: dict[str, Any], previous: dict[str, Any]
    ) -> list[TokenDiffEntry]:
        """Diff two token snapshot JSON dicts."""
        entries: list[TokenDiffEntry] = []

        diff_specs: list[tuple[str, str, Callable[[dict[str, Any]], tuple[str, ...]]]] = [
            ("color", "colors", lambda c: (c.get("name", ""), c.get("hex", ""))),
            (
                "typography",
                "typography",
                lambda t: (t.get("name", ""), t.get("family", ""), str(t.get("size", ""))),
            ),
            ("spacing", "spacing", lambda s: (s.get("name", ""), str(s.get("value", "")))),
            ("dark_color", "dark_colors", lambda c: (c.get("name", ""), c.get("hex", ""))),
        ]

        for category, json_key, key_fn in diff_specs:
            cur_items = [i for i in current.get(json_key, []) if isinstance(i, dict)]
            prev_items = [i for i in previous.get(json_key, []) if isinstance(i, dict)]

            cur_keys = {key_fn(i): i for i in cur_items}
            prev_keys = {key_fn(i): i for i in prev_items}

            for k in cur_keys:
                if k not in prev_keys:
                    entries.append(
                        TokenDiffEntry(
                            category=category,
                            name=cur_keys[k].get("name", "?"),
                            change="added",
                            new_value=str(k),
                        )
                    )
            for k in prev_keys:
                if k not in cur_keys:
                    entries.append(
                        TokenDiffEntry(
                            category=category,
                            name=prev_keys[k].get("name", "?"),
                            change="removed",
                            old_value=str(k),
                        )
                    )

        return entries

    # ── Phase 35.8: W3C Design Tokens ──

    async def import_w3c_tokens(
        self, body: ImportW3cTokensRequest, user: User
    ) -> W3cImportResponse:
        """Parse W3C Design Tokens v1.0 JSON and return validated tokens."""
        from app.design_sync.token_transforms import validate_and_transform
        from app.design_sync.w3c_tokens import parse_w3c_tokens

        result = parse_w3c_tokens(dict(body.tokens_json))

        # Load caniemail data for compatibility enrichment
        caniemail_data = None
        if body.target_clients:
            from app.design_sync.caniemail import load_caniemail_data

            caniemail_data = load_caniemail_data()

        tokens, validation_warnings = validate_and_transform(
            result.tokens,
            target_clients=body.target_clients or None,
            caniemail_data=caniemail_data,
        )

        warnings = [w.message for w in result.warnings] + [w.message for w in validation_warnings]

        # Optionally store as snapshot against a connection
        if body.connection_id is not None:
            conn = await self._repo.get_connection(body.connection_id)
            if conn is None:
                raise ConnectionNotFoundError(f"Connection {body.connection_id} not found")
            if conn.project_id is not None:
                await self._verify_access(conn.project_id, user)
            await self._repo.save_snapshot(body.connection_id, asdict(tokens))

        response = W3cImportResponse(
            colors=[
                DesignColorResponse(name=c.name, hex=c.hex, opacity=c.opacity)
                for c in tokens.colors
            ],
            dark_colors=[
                DesignColorResponse(name=c.name, hex=c.hex, opacity=c.opacity)
                for c in tokens.dark_colors
            ],
            typography=[
                DesignTypographyResponse(
                    name=t.name,
                    family=t.family,
                    weight=t.weight,
                    size=t.size,
                    lineHeight=t.line_height,
                    letterSpacing=t.letter_spacing,
                    textTransform=t.text_transform,
                    textDecoration=t.text_decoration,
                )
                for t in tokens.typography
            ],
            spacing=[DesignSpacingResponse(name=s.name, value=s.value) for s in tokens.spacing],
            gradients=[
                DesignGradientResponse(
                    name=g.name,
                    type=g.type,
                    angle=g.angle,
                    stops=[
                        DesignGradientStopResponse(hex=hex_val, position=pos)
                        for hex_val, pos in g.stops
                    ],
                    fallback_hex=g.fallback_hex,
                )
                for g in tokens.gradients
            ],
            warnings=warnings,
        )

        logger.info(
            "design_sync.w3c_import_completed",
            colors=len(tokens.colors),
            typography=len(tokens.typography),
            spacing=len(tokens.spacing),
            warnings=len(warnings),
            connection_id=body.connection_id,
        )

        return response

    async def export_w3c_tokens(self, connection_id: int, user: User) -> dict[str, object]:
        """Export tokens for a connection in W3C Design Tokens v1.0 format."""
        from app.design_sync.w3c_export import export_w3c_tokens

        # Reuse get_tokens to fetch validated tokens
        tokens_response = await self.get_tokens(connection_id, user)

        # Reconstruct ExtractedTokens from response
        from app.design_sync.protocol import (
            ExtractedGradient,
        )

        tokens = ExtractedTokens(
            colors=[
                ExtractedColor(name=c.name, hex=c.hex, opacity=c.opacity)
                for c in tokens_response.colors
            ],
            dark_colors=[
                ExtractedColor(name=c.name, hex=c.hex, opacity=c.opacity)
                for c in tokens_response.dark_colors
            ],
            typography=[
                ExtractedTypography(
                    name=t.name,
                    family=t.family,
                    weight=t.weight,
                    size=t.size,
                    line_height=t.lineHeight,
                    letter_spacing=t.letterSpacing,
                    text_transform=t.textTransform,
                    text_decoration=t.textDecoration,
                )
                for t in tokens_response.typography
            ],
            spacing=[ExtractedSpacing(name=s.name, value=s.value) for s in tokens_response.spacing],
            gradients=[
                ExtractedGradient(
                    name=g.name,
                    type=g.type,
                    angle=g.angle,
                    stops=tuple((s.hex, s.position) for s in g.stops),
                    fallback_hex=g.fallback_hex,
                )
                for g in tokens_response.gradients
            ],
        )

        result = export_w3c_tokens(tokens)
        logger.info("design_sync.w3c_export_completed", connection_id=connection_id)
        return result

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
                    cast(dict[str, str], raw_thumbs) if isinstance(raw_thumbs, dict) else {}
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
        d: dict[str, Any] = {
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
        # Preserve rich properties for the converter pipeline
        if node.fill_color is not None:
            d["fill_color"] = node.fill_color
        if node.text_color is not None:
            d["text_color"] = node.text_color
        if node.padding_top is not None:
            d["padding_top"] = node.padding_top
        if node.padding_right is not None:
            d["padding_right"] = node.padding_right
        if node.padding_bottom is not None:
            d["padding_bottom"] = node.padding_bottom
        if node.padding_left is not None:
            d["padding_left"] = node.padding_left
        if node.item_spacing is not None:
            d["item_spacing"] = node.item_spacing
        if node.counter_axis_spacing is not None:
            d["counter_axis_spacing"] = node.counter_axis_spacing
        if node.layout_mode is not None:
            d["layout_mode"] = node.layout_mode
        if node.font_family is not None:
            d["font_family"] = node.font_family
        if node.font_size is not None:
            d["font_size"] = node.font_size
        if node.font_weight is not None:
            d["font_weight"] = node.font_weight
        if node.line_height_px is not None:
            d["line_height_px"] = node.line_height_px
        if node.letter_spacing_px is not None:
            d["letter_spacing_px"] = node.letter_spacing_px
        if node.text_transform is not None:
            d["text_transform"] = node.text_transform
        if node.text_decoration is not None:
            d["text_decoration"] = node.text_decoration
        return d

    _THUMBNAIL_NODE_TYPES: ClassVar[set[str]] = {
        "FRAME",
        "COMPONENT",
        "INSTANCE",
        "GROUP",
        "SECTION",
    }
    _MAX_THUMBNAIL_CACHE = 100  # Single Figma API call (100 IDs per batch)

    def _collect_top_frame_ids(self, pages: list[dict[str, Any]]) -> list[str]:
        """Collect frame IDs from cached structure, prioritising top-level email sections."""
        scored: list[tuple[float, str]] = []

        def walk(node: dict[str, Any], depth: int) -> None:
            ntype = str(node.get("type", ""))
            if ntype in self._THUMBNAIL_NODE_TYPES:
                area = float(node.get("width", 0)) * float(node.get("height", 0))
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
                cached_images.append(ExportedImageResponse(node_id=nid, url=url, format="png"))
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

    async def get_design_structure(
        self,
        connection_id: int,
        user: User,
        *,
        selected_node_ids: list[str] | None = None,
    ) -> DesignFileStructure:
        """Get the raw design file structure for the converter pipeline."""
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
        return structure

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
                        colors=[
                            ExtractedColor(**c) for c in snapshot.tokens_json.get("colors", [])
                        ],
                        typography=[
                            ExtractedTypography(**t)
                            for t in snapshot.tokens_json.get("typography", [])
                        ],
                        spacing=[
                            ExtractedSpacing(**s) for s in snapshot.tokens_json.get("spacing", [])
                        ],
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
        output_format: Literal["html", "mjml"] = "html",
        score_fidelity: bool = False,
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
        operation_id = f"design-sync-{import_id}"
        ProgressTracker.start(operation_id, "design_sync")
        ProgressTracker.update(
            operation_id,
            status=OperationStatus.PROCESSING,
            progress=10,
            message="Starting conversion...",
        )
        logger.info("design_sync.conversion_started", import_id=import_id)

        # Launch background pipeline with its own DB session
        from app.design_sync.import_service import DesignImportService

        import_service = DesignImportService(
            design_service_factory=type(self),
            user=user,
        )

        def _on_task_done(task: asyncio.Task[None]) -> None:
            if task.cancelled():
                ProgressTracker.update(
                    operation_id,
                    status=OperationStatus.FAILED,
                    error="Conversion cancelled",
                )
                logger.warning("design_sync.conversion_cancelled", import_id=import_id)
            elif task.exception() is not None:
                ProgressTracker.update(
                    operation_id,
                    status=OperationStatus.FAILED,
                    error=str(task.exception()),
                )
                logger.error(
                    "design_sync.conversion_task_failed",
                    import_id=import_id,
                    error=str(task.exception()),
                )
            else:
                ProgressTracker.update(
                    operation_id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    message="Conversion complete",
                )

        task = asyncio.create_task(
            import_service.run_conversion(
                import_id=import_id,
                run_qa=run_qa,
                output_mode=output_mode,
                output_format=output_format,
                score_fidelity=score_fidelity,
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
        self,
        conn_id: int,
        file_ref: str,
        access_token: str,
        provider: DesignSyncProvider,
        *,
        depth: int | None = 3,
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

        raw_fw = data.get("font_weight")
        return DesignNode(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            type=node_type,
            children=[
                self._cached_dict_to_node(c)
                for c in data.get("children", [])
                if isinstance(c, dict)
            ],
            width=data.get("width"),
            height=data.get("height"),
            x=data.get("x"),
            y=data.get("y"),
            text_content=data.get("text_content"),
            fill_color=data.get("fill_color"),
            text_color=data.get("text_color"),
            padding_top=data.get("padding_top"),
            padding_right=data.get("padding_right"),
            padding_bottom=data.get("padding_bottom"),
            padding_left=data.get("padding_left"),
            item_spacing=data.get("item_spacing"),
            counter_axis_spacing=data.get("counter_axis_spacing"),
            layout_mode=data.get("layout_mode"),
            font_family=data.get("font_family"),
            font_size=data.get("font_size"),
            font_weight=int(raw_fw) if isinstance(raw_fw, (int, float)) else None,
            line_height_px=data.get("line_height_px"),
            letter_spacing_px=data.get("letter_spacing_px"),
            text_transform=data.get("text_transform"),
            text_decoration=data.get("text_decoration"),
        )

    # ── Helpers ──

    # ── Figma Webhooks ──

    async def register_figma_webhook(self, connection_id: int, *, team_id: str, user: User) -> str:
        """Register a Figma FILE_UPDATE webhook for a connection. Returns webhook_id."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)
        if conn.provider != "figma":
            raise UnsupportedProviderError("Webhooks are only supported for Figma connections")

        access_token = decrypt_token(conn.encrypted_token)
        figma = FigmaDesignSyncService()
        settings = get_settings()

        callback_url = settings.design_sync.figma_webhook_callback_url
        if not callback_url:
            raise SyncFailedError("DESIGN_SYNC__FIGMA_WEBHOOK_CALLBACK_URL is not configured")

        webhook_id = await figma.register_webhook(
            access_token,
            team_id=team_id,
            endpoint=f"{callback_url}/api/v1/design-sync/webhooks/figma",
            passcode=settings.design_sync.figma_webhook_passcode,
        )
        await self._repo.update_webhook_id(conn, webhook_id)
        await self.db.commit()
        logger.info(
            "design_sync.webhook_registered",
            connection_id=connection_id,
            webhook_id=webhook_id,
        )
        return webhook_id

    async def unregister_figma_webhook(self, connection_id: int, *, user: User) -> None:
        """Remove a Figma webhook for a connection."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._verify_access(conn.project_id, user)
        if not conn.webhook_id:
            return

        access_token = decrypt_token(conn.encrypted_token)
        figma = FigmaDesignSyncService()
        await figma.delete_webhook(access_token, conn.webhook_id)
        await self._repo.update_webhook_id(conn, None)
        await self.db.commit()
        logger.info("design_sync.webhook_unregistered", connection_id=connection_id)

    async def handle_webhook_sync(self, connection_id: int) -> DesignSyncUpdateMessage | None:
        """Run sync triggered by webhook, compute diff, return WS message if changes."""
        from app.design_sync.schemas import DesignSyncUpdateMessage

        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            return None

        try:
            await self.sync_connection(connection_id, user=None)
        except Exception:
            logger.warning(
                "design_sync.webhook_sync_failed",
                connection_id=connection_id,
                exc_info=True,
            )
            return None

        diff = await self.get_token_diff(connection_id)
        if not diff.entries:
            return None

        return DesignSyncUpdateMessage(
            connection_id=connection_id,
            diff_summary=self._format_diff_summary(diff.entries),
            total_changes=len(diff.entries),
            timestamp=datetime.now(UTC),
        )

    @staticmethod
    def _format_diff_summary(entries: list[TokenDiffEntry]) -> str:
        """Build a human-readable summary like '3 colors added, 1 removed'."""
        from collections import Counter

        counts: Counter[str] = Counter()
        for e in entries:
            counts[e.change] += 1
        parts = [f"{count} {change}" for change, count in sorted(counts.items())]
        return ", ".join(parts) if parts else "no changes"

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
            return replace(node, children=filtered_children)
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
                    font_family=t.font_family,
                    font_weight=t.font_weight,
                    line_height=t.line_height,
                    letter_spacing=t.letter_spacing,
                )
                for t in s.texts
            ],
            images=[
                ImagePlaceholderResponse(
                    node_id=img.node_id,
                    node_name=img.node_name,
                    width=img.width,
                    height=img.height,
                    export_node_id=img.export_node_id,
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
            bg_color=s.bg_color,
            classification_confidence=s.classification_confidence,
            content_roles=list(s.content_roles),
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


# ── Training case persistence (HTML upload → learning loop) ──────


import re  # noqa: E402

_CASE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEBUG_DIR = _PROJECT_ROOT / "data" / "debug"
_MANIFEST_PATH = _DEBUG_DIR / "manifest.yaml"


def _validate_case_id(case_id: str) -> None:
    """Validate case_id to prevent path traversal."""
    from app.design_sync.exceptions import TrainingCaseError

    if not _CASE_ID_PATTERN.match(case_id):
        msg = f"Invalid case_id '{case_id}': must be alphanumeric, hyphens, underscores (max 64 chars)"
        raise TrainingCaseError(msg)


async def create_training_case(
    *,
    case_id: str,
    case_name: str,
    html_content: str,
    source_name: str = "training",
    figma_url: str | None = None,
    figma_node: str | None = None,
    screenshot_data: bytes | None = None,
) -> dict[str, Any]:
    """Save an HTML email + optional screenshot as a training case on disk.

    Creates ``data/debug/{case_id}/`` with ``expected.html`` (and optionally
    ``design.png``), then appends the case to the global manifest.
    """
    from app.design_sync.exceptions import TrainingCaseError, TrainingCaseExistsError

    _validate_case_id(case_id)

    case_dir = _DEBUG_DIR / case_id
    if case_dir.exists():
        raise TrainingCaseExistsError(f"Training case '{case_id}' already exists")

    if not html_content.strip():
        raise TrainingCaseError("HTML content is empty")

    # Check manifest for duplicate BEFORE creating the directory. If the
    # manifest carries a stale id whose dir was deleted out-of-band, writing
    # files first would leave partial state on disk — the case_dir.exists()
    # guard above would then permanently reject retries.
    if _MANIFEST_PATH.exists():
        existing_text = _MANIFEST_PATH.read_text()
        if f'id: "{case_id}"' in existing_text:
            raise TrainingCaseExistsError(f"Case '{case_id}' already in manifest")

    log = get_logger(__name__)
    files_written: list[str] = []

    case_dir.mkdir(parents=True, exist_ok=True)

    # Write expected.html
    (case_dir / "expected.html").write_text(html_content, encoding="utf-8")
    files_written.append("expected.html")

    # Write screenshot if provided
    has_screenshot = False
    if screenshot_data:
        (case_dir / "design.png").write_bytes(screenshot_data)
        files_written.append("design.png")
        has_screenshot = True

    # Append to global manifest (preserves existing YAML comments by appending text)
    entry_yaml = (
        f'\n  - id: "{case_id}"\n'
        f'    name: "{case_name}"\n'
        f'    source: "{source_name}"\n'
        f'    figma_node: "{figma_node or "unknown"}"\n'
        f"    status: active\n"
        f"    design_image: {'true' if has_screenshot else 'false'}\n"
        f"    visual_threshold: 0.95\n"
        f"    reference_only: true\n"
    )

    if _MANIFEST_PATH.exists():
        with _MANIFEST_PATH.open("a", encoding="utf-8") as f:
            f.write(entry_yaml)
    else:
        _MANIFEST_PATH.write_text(f"cases:{entry_yaml}", encoding="utf-8")
    files_written.append("manifest.yaml (updated)")

    # Write figma metadata if provided
    if figma_url or figma_node:
        import json

        meta = {"figma_url": figma_url, "figma_node": figma_node}
        (case_dir / "figma_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        files_written.append("figma_meta.json")

    log.info(
        "training_case.created",
        case_id=case_id,
        files=files_written,
    )

    return {
        "case_id": case_id,
        "case_dir": str(case_dir),
        "files_written": files_written,
        "manifest_updated": True,
    }


async def backfill_training_case(
    case_id: str,
    *,
    traces_only: bool = False,
) -> dict[str, Any]:
    """Backfill a single training case into the learning loop.

    For cases with ``structure.json`` (Figma-sourced), runs the full converter.
    For HTML-only cases, parses ``expected.html`` to build a synthetic
    ConversionResult and persists traces/memory/insights from it.
    """
    from app.design_sync.converter_memory import (
        _CLEAN_CONFIDENCE_THRESHOLD,
        build_conversion_metadata,
        format_conversion_quality,
    )
    from app.design_sync.converter_service import ConversionResult, DesignConverterService
    from app.design_sync.converter_traces import append_trace, build_trace
    from app.design_sync.exceptions import TrainingCaseError

    _validate_case_id(case_id)

    log = get_logger(__name__)
    case_dir = _DEBUG_DIR / case_id

    if not case_dir.exists():
        raise TrainingCaseError(f"Training case '{case_id}' not found at {case_dir}")

    has_structure = (case_dir / "structure.json").exists()
    has_html = (case_dir / "expected.html").exists()

    if not has_structure and not has_html:
        raise TrainingCaseError(f"Case '{case_id}' has neither structure.json nor expected.html")

    result: ConversionResult

    if has_structure:
        # Figma-sourced case: run full converter
        from app.design_sync.diagnose.report import (
            load_structure_from_json,
            load_tokens_from_json,
        )

        structure = load_structure_from_json(case_dir / "structure.json")
        tokens = load_tokens_from_json(case_dir / "tokens.json")
        converter = DesignConverterService()
        result = converter.convert(structure, tokens)
    else:
        # HTML-only case: parse expected.html for a synthetic result
        from app.design_sync.html_import.adapter import HtmlImportAdapter

        html = (case_dir / "expected.html").read_text(encoding="utf-8")
        adapter = HtmlImportAdapter()
        document = await adapter.parse(html, use_ai=False, source_name=case_id)
        section_count = len(document.sections)

        # Build a synthetic ConversionResult from the analysis
        result = ConversionResult(
            html=html,
            sections_count=section_count,
            warnings=[],
            match_confidences=dict.fromkeys(range(section_count), 1.0),
            quality_warnings=[],
        )

    # Persist trace (always)
    trace = build_trace(result, f"snapshot_{case_id}")
    append_trace(trace)
    traces_written = 1

    memory_stored = False
    insights_count = 0

    if not traces_only:
        # Persist memory
        confidences = list(result.match_confidences.values())
        has_issues = bool(result.quality_warnings) or any(
            c < _CLEAN_CONFIDENCE_THRESHOLD for c in confidences
        )

        if has_issues:
            content = format_conversion_quality(result)
            if content is not None:
                metadata = build_conversion_metadata(result, f"snapshot_{case_id}")
                from app.core.database import get_db_context
                from app.knowledge.embedding import get_embedding_provider
                from app.memory.schemas import MemoryCreate
                from app.memory.service import MemoryService

                settings = get_settings()
                async with get_db_context() as db:
                    embedding_provider = get_embedding_provider(settings)
                    service = MemoryService(db, embedding_provider)
                    await service.store(
                        MemoryCreate(
                            agent_type="design_sync",
                            memory_type="semantic",
                            content=content,
                            project_id=None,
                            metadata=metadata,
                            is_evergreen=False,
                        ),
                    )
                memory_stored = True

        # Persist insights
        from app.design_sync.converter_insights import persist_conversion_insights

        insights_count = await persist_conversion_insights(result, f"snapshot_{case_id}", None)

    log.info(
        "training_case.backfill_completed",
        case_id=case_id,
        traces_written=traces_written,
        memory_stored=memory_stored,
        insights_count=insights_count,
        source="structure" if has_structure else "html_only",
    )

    return {
        "case_id": case_id,
        "sections_count": result.sections_count,
        "traces_written": traces_written,
        "memory_stored": memory_stored,
        "insights_count": insights_count,
        "source": "structure" if has_structure else "html_only",
    }
