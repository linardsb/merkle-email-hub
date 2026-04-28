"""Connection lifecycle: browse, list, create, sync, refresh, link, delete."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any, cast

from app.core.exceptions import ConflictError
from app.core.logging import get_logger
from app.design_sync.assets import DesignAssetService
from app.design_sync.crypto import decrypt_token, encrypt_token
from app.design_sync.exceptions import (
    ConnectionNotFoundError,
    SyncFailedError,
    TokenDecryptionError,
)
from app.design_sync.protocol import (
    BrowseableProvider,
    DesignFileStructure,
    ExtractedTokens,
)
from app.design_sync.schemas import (
    BrowseFilesResponse,
    ConnectionCreateRequest,
    ConnectionResponse,
    DesignFileResponse,
)
from app.design_sync.services._serialization import (
    collect_top_frame_ids,
    serialize_node,
)

if TYPE_CHECKING:
    from app.auth.models import User
    from app.design_sync.services._context import DesignSyncContext


logger = get_logger(__name__)


class ConnectionService:
    """CRUD + sync flows for design tool connections."""

    def __init__(self, ctx: DesignSyncContext) -> None:
        self._ctx = ctx

    async def browse_files(self, provider_name: str, access_token: str) -> BrowseFilesResponse:
        """Browse design files from a provider before creating a connection."""
        provider = self._ctx.get_provider(provider_name)

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

    async def list_connections(self, user: User) -> list[ConnectionResponse]:
        """List connections the user owns or has project access to."""
        accessible_ids = await self._ctx.get_accessible_project_ids(user)
        rows = await self._ctx.repo.list_connections_for_user(user.id, accessible_ids)
        return [
            ConnectionResponse.from_model(conn, project_name=project_name)
            for conn, project_name in rows
        ]

    async def get_connection(self, connection_id: int, user: User) -> ConnectionResponse:
        """Get a single connection by ID with BOLA check."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)
        project_name = await self._ctx.get_project_name(conn.project_id)
        return ConnectionResponse.from_model(conn, project_name=project_name)

    async def create_connection(
        self, data: ConnectionCreateRequest, user: User
    ) -> ConnectionResponse:
        """Create a new design tool connection."""
        provider_name = data.provider
        self._ctx.get_provider(provider_name)  # validate provider exists

        if data.project_id is not None:
            await self._ctx.verify_access(data.project_id, user)

        file_ref = self._ctx.extract_file_ref(provider_name, data.file_url)

        existing = await self._ctx.repo.get_connection_by_file_ref(provider_name, file_ref)
        if existing is not None:
            raise ConflictError(
                f"A connection to this file already exists ('{existing.name}', id={existing.id}). "
                "Use the token refresh endpoint to update credentials."
            )

        token_last4 = data.access_token[-4:] if len(data.access_token) >= 4 else data.access_token

        provider = self._ctx.get_provider(provider_name)
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

        conn = await self._ctx.repo.create_connection(
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

        try:
            return await self.sync_connection(conn.id, user)
        except Exception:
            logger.warning(
                "design_sync.auto_sync_failed",
                connection_id=conn.id,
                exc_info=True,
            )
            project_name = await self._ctx.get_project_name(conn.project_id)
            return ConnectionResponse.from_model(conn, project_name=project_name)

    async def delete_connection(self, connection_id: int, user: User) -> bool:
        """Delete a connection with BOLA check."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        asset_service = DesignAssetService()
        asset_service.delete_connection_assets(connection_id)

        logger.info("design_sync.connection_deleted", connection_id=connection_id)
        return await self._ctx.repo.delete_connection(connection_id)

    async def sync_connection(self, connection_id: int, user: User | None) -> ConnectionResponse:
        """Trigger a token sync for a connection."""
        from app.design_sync.service import fetch_target_clients

        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None and user is not None:
            await self._ctx.verify_access(conn.project_id, user)

        provider = self._ctx.get_provider(conn.provider)

        try:
            access_token = decrypt_token(conn.encrypted_token)
        except Exception as exc:
            await self._ctx.repo.update_status(
                conn,
                "error",
                error_message="Access token expired or encryption key changed. Please refresh your token.",
            )
            raise TokenDecryptionError(
                "Cannot decrypt stored access token. The encryption key may have changed. "
                "Please update your access token via the connection settings."
            ) from exc

        await self._ctx.repo.update_status(conn, "syncing")

        target_clients = await fetch_target_clients(self._ctx.db, conn.project_id)

        try:
            if hasattr(provider, "build_document"):
                from app.design_sync.email_design_document import EmailDesignDocument
                from app.design_sync.token_transforms import TokenWarning

                _raw: tuple[
                    EmailDesignDocument,
                    ExtractedTokens,
                    list[TokenWarning],
                    DesignFileStructure,
                ] = await cast(Any, provider).build_document(
                    conn.file_ref,
                    access_token,
                    connection_config=conn.config_json,
                    target_clients=target_clients,
                )
                document = _raw[0]
                tokens = _raw[1]
                token_warnings = _raw[2]
                structure = _raw[3]
                doc_json: dict[str, object] | None = document.to_json()
            else:
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

            structure_cache: dict[str, Any] = {
                "file_name": structure.file_name,
                "pages": [serialize_node(p) for p in structure.pages],
            }

            thumbnail_cache: dict[str, str] | None = None
            try:
                top_frame_ids = collect_top_frame_ids(structure_cache["pages"])
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
                if target_clients:
                    client_hints: list[dict[str, Any]] = [
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

            await self._ctx.repo.save_snapshot(conn.id, tokens_dict, document_json=doc_json)
            await self._ctx.repo.update_status(conn, "connected")

            logger.info(
                "design_sync.sync_completed",
                connection_id=connection_id,
                provider=conn.provider,
            )
        except Exception as exc:
            await self._ctx.repo.update_status(conn, "error", error_message="Sync failed")
            logger.error(
                "design_sync.sync_error",
                connection_id=connection_id,
                error=str(exc),
                exc_info=True,
            )
            raise SyncFailedError("Token sync failed") from exc

        project_name = await self._ctx.get_project_name(conn.project_id)
        return ConnectionResponse.from_model(conn, project_name=project_name)

    async def refresh_token(
        self, connection_id: int, new_access_token: str, user: User
    ) -> ConnectionResponse:
        """Update the access token for an existing connection."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        provider = self._ctx.get_provider(conn.provider)
        try:
            await provider.validate_connection(conn.file_ref, new_access_token)
        except SyncFailedError:
            raise
        except Exception as exc:
            raise SyncFailedError("Failed to validate new token") from exc

        encrypted = encrypt_token(new_access_token)
        token_last4 = new_access_token[-4:] if len(new_access_token) >= 4 else new_access_token
        await self._ctx.repo.update_connection_token(conn, encrypted, token_last4)
        await self._ctx.repo.update_status(conn, "connected")

        logger.info(
            "design_sync.token_refreshed",
            connection_id=connection_id,
            provider=conn.provider,
        )

        project_name = await self._ctx.get_project_name(conn.project_id)
        return ConnectionResponse.from_model(conn, project_name=project_name)

    async def link_connection_to_project(
        self, connection_id: int, project_id: int | None, user: User
    ) -> ConnectionResponse:
        """Link or unlink a connection to a project."""
        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)
        if project_id is not None:
            await self._ctx.verify_access(project_id, user)

        conn.project_id = project_id
        await self._ctx.db.commit()

        logger.info(
            "design_sync.connection_linked",
            connection_id=connection_id,
            project_id=project_id,
        )

        project_name = await self._ctx.get_project_name(project_id)
        return ConnectionResponse.from_model(conn, project_name=project_name)
