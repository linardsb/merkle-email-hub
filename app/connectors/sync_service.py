"""Business logic for ESP bidirectional sync."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.connectors.adobe.sync_provider import AdobeSyncProvider
from app.connectors.braze.sync_provider import BrazeSyncProvider
from app.connectors.exceptions import (
    ESPConnectionNotFoundError,
    ESPSyncFailedError,
    InvalidESPCredentialsError,
)
from app.connectors.sfmc.sync_provider import SFMCSyncProvider
from app.connectors.sync_models import ESPConnection
from app.connectors.sync_protocol import ESPSyncProvider
from app.connectors.sync_repository import ESPSyncRepository
from app.connectors.sync_schemas import (
    ESPConnectionCreate,
    ESPConnectionResponse,
    ESPTemplate,
    ESPTemplateList,
)
from app.connectors.taxi.sync_provider import TaxiSyncProvider
from app.core.logging import get_logger
from app.design_sync.crypto import decrypt_token, encrypt_token
from app.projects.service import ProjectService
from app.templates.schemas import TemplateCreate
from app.templates.service import TemplateService

logger = get_logger(__name__)

PROVIDER_REGISTRY: dict[str, type[ESPSyncProvider]] = {
    "braze": BrazeSyncProvider,
    "sfmc": SFMCSyncProvider,
    "adobe_campaign": AdobeSyncProvider,
    "taxi": TaxiSyncProvider,
}


class ConnectorSyncService:
    """Orchestrates ESP connection management and template sync operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = ESPSyncRepository(db)
        self._project_service = ProjectService(db)
        self._template_service = TemplateService(db)

    # ── Helpers ──

    def _get_provider(self, esp_type: str) -> ESPSyncProvider:
        """Instantiate the sync provider for a given ESP type."""
        provider_cls = PROVIDER_REGISTRY.get(esp_type)
        if provider_cls is None:
            raise ESPSyncFailedError(f"Unsupported ESP type: {esp_type}")
        return provider_cls()

    def _encrypt_credentials(self, credentials: dict[str, str]) -> str:
        """Serialize and encrypt credentials for storage."""
        return encrypt_token(json.dumps(credentials))

    def _decrypt_credentials(self, encrypted: str) -> dict[str, str]:
        """Decrypt and deserialize stored credentials."""
        return json.loads(decrypt_token(encrypted))  # type: ignore[no-any-return]

    def _credentials_hint(self, credentials: dict[str, str]) -> str:
        """Extract a safe hint from credentials (last 4 chars of first value)."""
        first_value = next(iter(credentials.values()), "")
        return f"****{first_value[-4:]}" if len(first_value) >= 4 else "****"

    async def _get_accessible_project_ids(self, user: User) -> list[int]:
        """Get IDs of projects the user can access."""
        from app.projects.models import Project, ProjectMember

        if user.role == "admin":
            result = await self.db.execute(select(Project.id))
            return [row[0] for row in result.all()]

        result = await self.db.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        )
        return [row[0] for row in result.all()]

    async def _get_connection_with_bola(
        self, connection_id: int, user: User
    ) -> tuple[ESPConnection, dict[str, str]]:
        """Load a connection, verify BOLA, decrypt credentials."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ESPConnectionNotFoundError(f"ESP connection {connection_id} not found")
        # BOLA: verify the user has access to the connection's project
        await self._project_service.verify_project_access(conn.project_id, user)
        credentials = self._decrypt_credentials(conn.encrypted_credentials)
        return conn, credentials

    # ── Connection CRUD ──

    async def create_connection(
        self, data: ESPConnectionCreate, user: User
    ) -> ESPConnectionResponse:
        """Create a new ESP connection after validating credentials."""
        logger.info(
            "esp_sync.connection_create_started",
            esp_type=data.esp_type,
            project_id=data.project_id,
        )

        # BOLA: verify the user has access to the target project
        await self._project_service.verify_project_access(data.project_id, user)

        # Validate credentials against the ESP
        provider = self._get_provider(data.esp_type)
        is_valid = await provider.validate_credentials(data.credentials)
        if not is_valid:
            raise InvalidESPCredentialsError(f"Invalid credentials for {data.esp_type}")

        encrypted = self._encrypt_credentials(data.credentials)
        hint = self._credentials_hint(data.credentials)

        conn = await self._repo.create_connection(
            esp_type=data.esp_type,
            name=data.name,
            encrypted_credentials=encrypted,
            credentials_hint=hint,
            project_id=data.project_id,
            created_by_id=user.id,
        )

        logger.info(
            "esp_sync.connection_create_completed",
            connection_id=conn.id,
            esp_type=data.esp_type,
        )
        return ESPConnectionResponse.model_validate(conn)

    async def list_connections(self, user: User) -> list[ESPConnectionResponse]:
        """List all ESP connections accessible to the user."""
        accessible_ids = await self._get_accessible_project_ids(user)
        rows = await self._repo.list_connections_for_user(user.id, accessible_ids)
        results: list[ESPConnectionResponse] = []
        for conn, project_name in rows:
            resp = ESPConnectionResponse.model_validate(conn)
            resp.project_name = project_name
            results.append(resp)
        return results

    async def get_connection(self, connection_id: int, user: User) -> ESPConnectionResponse:
        """Get a single ESP connection."""
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ESPConnectionNotFoundError(f"ESP connection {connection_id} not found")
        await self._project_service.verify_project_access(conn.project_id, user)
        return ESPConnectionResponse.model_validate(conn)

    async def delete_connection(self, connection_id: int, user: User) -> None:
        """Delete an ESP connection."""
        logger.info("esp_sync.connection_delete_started", connection_id=connection_id)
        conn = await self._repo.get_connection(connection_id)
        if conn is None:
            raise ESPConnectionNotFoundError(f"ESP connection {connection_id} not found")
        await self._project_service.verify_project_access(conn.project_id, user)
        await self._repo.delete_connection(connection_id)
        logger.info("esp_sync.connection_delete_completed", connection_id=connection_id)

    # ── Remote Template Operations ──

    async def list_remote_templates(self, connection_id: int, user: User) -> ESPTemplateList:
        """List templates from the remote ESP."""
        conn, credentials = await self._get_connection_with_bola(connection_id, user)
        provider = self._get_provider(conn.esp_type)

        try:
            templates = await provider.list_templates(credentials)
        except Exception as exc:
            await self._repo.update_status(conn, "error", str(exc))
            raise ESPSyncFailedError(f"Failed to list templates: {exc}") from exc

        await self._repo.update_status(conn, "connected")
        return ESPTemplateList(templates=templates, count=len(templates))

    async def get_remote_template(
        self, connection_id: int, template_id: str, user: User
    ) -> ESPTemplate:
        """Get a single template from the remote ESP."""
        conn, credentials = await self._get_connection_with_bola(connection_id, user)
        provider = self._get_provider(conn.esp_type)

        try:
            template = await provider.get_template(template_id, credentials)
        except Exception as exc:
            raise ESPSyncFailedError(f"Failed to get template: {exc}") from exc

        return template

    async def import_template(self, connection_id: int, remote_template_id: str, user: User) -> int:
        """Import a remote ESP template into the local Hub as a new template.

        Returns the local template ID.
        """
        logger.info(
            "esp_sync.import_started",
            connection_id=connection_id,
            remote_template_id=remote_template_id,
        )
        conn, credentials = await self._get_connection_with_bola(connection_id, user)
        provider = self._get_provider(conn.esp_type)

        try:
            remote = await provider.get_template(remote_template_id, credentials)
        except Exception as exc:
            raise ESPSyncFailedError(f"Failed to fetch remote template: {exc}") from exc

        # Create local template in the connection's project
        local = await self._template_service.create_template(
            project_id=conn.project_id,
            data=TemplateCreate(
                name=f"[{conn.esp_type}] {remote.name}",
                description=f"Imported from {conn.esp_type} (ID: {remote.id})",
                subject_line=None,
                preheader_text=None,
                html_source=remote.html,
            ),
            user=user,
        )

        logger.info(
            "esp_sync.import_completed",
            connection_id=connection_id,
            remote_template_id=remote_template_id,
            local_template_id=local.id,
        )
        return local.id

    async def push_template(
        self, connection_id: int, local_template_id: int, user: User
    ) -> ESPTemplate:
        """Push a local Hub template to the remote ESP."""
        logger.info(
            "esp_sync.push_started",
            connection_id=connection_id,
            local_template_id=local_template_id,
        )
        conn, credentials = await self._get_connection_with_bola(connection_id, user)
        provider = self._get_provider(conn.esp_type)

        # Get local template HTML from latest version
        local = await self._template_service.get_template(local_template_id, user)
        html = ""
        if local.latest_version is not None:
            version = await self._template_service.get_version(
                local_template_id, local.latest_version, user
            )
            html = version.html_source

        try:
            remote = await provider.create_template(local.name, html, credentials)
        except Exception as exc:
            await self._repo.update_status(conn, "error", str(exc))
            raise ESPSyncFailedError(f"Failed to push template: {exc}") from exc

        await self._repo.update_status(conn, "connected")
        logger.info(
            "esp_sync.push_completed",
            connection_id=connection_id,
            local_template_id=local_template_id,
            remote_template_id=remote.id,
        )
        return remote
