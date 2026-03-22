"""Business logic for ESP connector operations."""

from __future__ import annotations

import datetime
import json
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.connectors.adobe.service import AdobeConnectorService
from app.connectors.approval_gate_schemas import ApprovalGateResult
from app.connectors.braze.service import BrazeConnectorService
from app.connectors.exceptions import ExportFailedError, UnsupportedConnectorError
from app.connectors.models import ExportRecord
from app.connectors.protocol import ConnectorProvider
from app.connectors.qa_gate_schemas import (
    ExportPreCheckRequest,
    ExportPreCheckResponse,
    QAGateResult,
)
from app.connectors.schemas import ExportRequest, ExportResponse
from app.connectors.sfmc.service import SFMCConnectorService
from app.connectors.sync_models import ESPConnection
from app.connectors.taxi.service import TaxiConnectorService
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.design_sync.crypto import decrypt_token
from app.email_engine.models import EmailBuild
from app.projects.service import ProjectService
from app.templates.models import TemplateVersion

logger = get_logger(__name__)

SUPPORTED_CONNECTORS: dict[str, type[ConnectorProvider]] = {
    "braze": BrazeConnectorService,
    "sfmc": SFMCConnectorService,
    "adobe_campaign": AdobeConnectorService,
    "taxi": TaxiConnectorService,
}


class ConnectorService:
    """Orchestrates exports to ESP connectors."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._providers: dict[str, ConnectorProvider] = {}

    def _get_provider(self, connector_type: str) -> ConnectorProvider:
        """Get or create a connector provider instance."""
        if connector_type not in self._providers:
            provider_cls = SUPPORTED_CONNECTORS.get(connector_type)
            if provider_cls is None:
                raise UnsupportedConnectorError(
                    f"Connector '{connector_type}' is not supported. "
                    f"Supported: {', '.join(sorted(SUPPORTED_CONNECTORS))}"
                )
            self._providers[connector_type] = provider_cls()
        return self._providers[connector_type]

    async def _resolve_html(self, data: ExportRequest, user: User) -> str:
        """Resolve export HTML from either template_version_id or build_id."""
        if data.template_version_id is not None:
            result = await self.db.execute(
                select(TemplateVersion).where(TemplateVersion.id == data.template_version_id)
            )
            version = result.scalar_one_or_none()
            if not version:
                raise NotFoundError(f"Template version {data.template_version_id} not found")
            return version.html_source

        # Legacy path: fetch from EmailBuild
        if data.build_id is None:
            raise ExportFailedError("No build_id or template_version_id provided")
        build_result = await self.db.execute(
            select(EmailBuild).where(EmailBuild.id == data.build_id)
        )
        build = build_result.scalar_one_or_none()
        if not build:
            raise NotFoundError(f"Build {data.build_id} not found")

        # BOLA: verify user has access to the build's project
        project_service = ProjectService(self.db)
        await project_service.verify_project_access(build.project_id, user)

        if not build.compiled_html:
            raise ExportFailedError("Build has no compiled HTML yet")
        return build.compiled_html

    async def _resolve_credentials(self, connection_id: int, user: User) -> dict[str, str]:
        """Load an ESPConnection, verify BOLA, and decrypt credentials."""
        logger.info("connectors.resolve_credentials_started", connection_id=connection_id)
        result = await self.db.execute(
            select(ESPConnection).where(ESPConnection.id == connection_id)
        )
        conn = result.scalar_one_or_none()
        if conn is None:
            raise NotFoundError(f"ESP connection {connection_id} not found")
        project_service = ProjectService(self.db)
        await project_service.verify_project_access(conn.project_id, user)
        try:
            credentials: dict[str, str] = json.loads(decrypt_token(conn.encrypted_credentials))
        except Exception as exc:
            logger.error(
                "connectors.credential_decryption_failed",
                connection_id=connection_id,
                error_type=type(exc).__name__,
            )
            raise ExportFailedError("Failed to decrypt ESP credentials") from exc
        logger.info("connectors.resolve_credentials_completed", connection_id=connection_id)
        return credentials

    async def _resolve_project_id(self, data: ExportRequest, user: User) -> int | None:  # noqa: ARG002
        """Extract project_id from build or connection for gate evaluation."""
        if data.build_id:
            result = await self.db.execute(
                select(EmailBuild.project_id).where(EmailBuild.id == data.build_id)
            )
            row = result.scalar_one_or_none()
            return row if row else None
        if data.connection_id:
            result = await self.db.execute(
                select(ESPConnection.project_id).where(ESPConnection.id == data.connection_id)
            )
            return result.scalar_one_or_none()
        return None

    async def export(self, data: ExportRequest, user: User) -> ExportResponse:
        """Export an email build or template version to the specified ESP."""
        # Admin-only overrides
        if data.skip_qa_gate and user.role != "admin":
            raise ForbiddenError("Only admins can skip QA gate")
        if data.skip_approval and user.role != "admin":
            raise ForbiddenError("Only admins can skip approval gate")

        html = await self._resolve_html(data, user)
        provider = self._get_provider(data.connector_type)

        # Shared project_id for all gate evaluations
        gate_project_id = await self._resolve_project_id(data, user)

        # ── QA gate check (Phase 28.1) ──
        settings = get_settings()
        qa_gate_result: QAGateResult | None = None
        if settings.export.qa_gate_mode != "skip" and not data.skip_qa_gate:
            from app.connectors.exceptions import ExportQAGateBlockedError
            from app.connectors.qa_gate import ExportQAGate
            from app.connectors.qa_gate_schemas import QAGateVerdict as QAVerdict

            qa_gate = ExportQAGate(self.db)
            qa_gate_result = await qa_gate.evaluate(html, gate_project_id)

            if qa_gate_result.verdict == QAVerdict.BLOCK:
                logger.warning(
                    "connectors.export_qa_gate_blocked",
                    blocking_checks=[f.check_name for f in qa_gate_result.blocking_failures],
                    build_id=data.build_id,
                )
                raise ExportQAGateBlockedError(
                    f"QA gate blocked export: "
                    f"{', '.join(f.check_name for f in qa_gate_result.blocking_failures)} failed"
                )

            if qa_gate_result.verdict == QAVerdict.WARN:
                logger.info(
                    "connectors.export_qa_gate_warning",
                    blocking_checks=[f.check_name for f in qa_gate_result.blocking_failures],
                    build_id=data.build_id,
                )
        elif data.skip_qa_gate:
            logger.warning(
                "connectors.export_qa_gate_skipped",
                user_id=user.id,
                build_id=data.build_id,
            )

        # ── Rendering gate check (Phase 27.3) ──
        if settings.rendering.gate_mode != "skip":
            from app.rendering.exceptions import RenderingGateBlockedError
            from app.rendering.gate import RenderingSendGate
            from app.rendering.gate_schemas import GateEvaluateRequest, GateVerdict

            gate = RenderingSendGate(self.db)
            gate_result = await gate.evaluate(
                GateEvaluateRequest(html=html, project_id=gate_project_id)
            )

            if gate_result.verdict == GateVerdict.BLOCK:
                logger.warning(
                    "connectors.export_gate_blocked",
                    blocking_clients=gate_result.blocking_clients,
                    build_id=data.build_id,
                )
                raise RenderingGateBlockedError(
                    f"Rendering gate blocked export: "
                    f"{', '.join(gate_result.blocking_clients)} below confidence threshold"
                )

            if gate_result.verdict == GateVerdict.WARN:
                logger.info(
                    "connectors.export_gate_warning",
                    blocking_clients=gate_result.blocking_clients,
                    build_id=data.build_id,
                )

        # ── Approval gate check (Phase 28.2) ──
        approval_result: ApprovalGateResult | None = None
        if not data.skip_approval:
            from app.connectors.approval_gate import ExportApprovalGate
            from app.connectors.exceptions import ApprovalRequiredError

            approval_gate = ExportApprovalGate(self.db)
            approval_result = await approval_gate.evaluate(data.build_id, gate_project_id)

            if not approval_result.passed and approval_result.required:
                logger.warning(
                    "connectors.export_approval_gate_blocked",
                    reason=approval_result.reason,
                    build_id=data.build_id,
                )
                raise ApprovalRequiredError(f"Approval required: {approval_result.reason}")
        elif data.skip_approval:
            logger.warning(
                "connectors.export_approval_skipped",
                user_id=user.id,
                build_id=data.build_id,
            )

        # Resolve credentials if a connection_id was provided
        credentials: dict[str, str] | None = None
        if data.connection_id is not None:
            credentials = await self._resolve_credentials(data.connection_id, user)

        logger.info(
            "connectors.export_started",
            connector=data.connector_type,
            build_id=data.build_id,
            template_version_id=data.template_version_id,
            has_credentials=credentials is not None,
        )

        # Template version path: no ExportRecord (no build_id FK to satisfy)
        if data.template_version_id is not None and data.build_id is None:
            try:
                external_id = await provider.export(html, data.content_block_name, credentials)
            except Exception as exc:
                logger.error(
                    "connectors.export_error",
                    connector=data.connector_type,
                    template_version_id=data.template_version_id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                    exc_info=True,
                )
                raise ExportFailedError("Export operation failed") from exc

            logger.info(
                "connectors.export_completed",
                connector=data.connector_type,
                template_version_id=data.template_version_id,
                status="success",
            )
            return ExportResponse(
                template_version_id=data.template_version_id,
                connector_type=data.connector_type,
                status="success",
                external_id=external_id,
                qa_gate_result=qa_gate_result,
                approval_result=approval_result,
                created_at=datetime.datetime.now(datetime.UTC),
            )

        # Legacy build path: create ExportRecord for audit trail
        # build_id is guaranteed non-None here by the template_version branch above
        record = ExportRecord(
            build_id=data.build_id,
            connector_type=data.connector_type,
            exported_by_id=user.id,
            status="exporting",
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        try:
            external_id = await provider.export(html, data.content_block_name)
            record.status = "success"
            record.external_id = external_id
        except Exception as exc:
            record.status = "failed"
            record.error_message = "Export failed"
            logger.error(
                "connectors.export_error",
                record_id=record.id,
                connector=data.connector_type,
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            raise ExportFailedError("Export operation failed") from exc
        finally:
            await self.db.commit()
            await self.db.refresh(record)

        logger.info(
            "connectors.export_completed",
            record_id=record.id,
            connector=data.connector_type,
            status=record.status,
        )
        return ExportResponse(
            id=record.id,
            build_id=record.build_id,
            connector_type=record.connector_type,
            status=record.status,
            external_id=record.external_id,
            error_message=record.error_message,
            qa_gate_result=qa_gate_result,
            approval_result=approval_result,
            created_at=record.created_at,  # pyright: ignore[reportArgumentType]
        )

    async def pre_check(
        self,
        data: ExportPreCheckRequest,
    ) -> ExportPreCheckResponse:
        """Dry-run QA + rendering gates without exporting."""
        from app.connectors.qa_gate import ExportQAGate

        qa_gate = ExportQAGate(self.db)
        qa_result = await qa_gate.evaluate(data.html, data.project_id)

        render_result = None
        settings = get_settings()
        if settings.rendering.gate_mode != "skip":
            from app.rendering.gate import RenderingSendGate
            from app.rendering.gate_schemas import GateEvaluateRequest

            gate = RenderingSendGate(self.db)
            render_result = await gate.evaluate(
                GateEvaluateRequest(
                    html=data.html,
                    project_id=data.project_id,
                    target_clients=data.target_clients,
                )
            )

        approval_result = None
        if data.build_id is not None:
            from app.connectors.approval_gate import ExportApprovalGate

            approval_gate = ExportApprovalGate(self.db)
            approval_result = await approval_gate.evaluate(data.build_id, data.project_id)

        can_export = (
            qa_result.passed
            and (render_result is None or render_result.passed)
            and (approval_result is None or approval_result.passed)
        )
        return ExportPreCheckResponse(
            qa=qa_result,
            rendering=render_result,
            approval=approval_result,
            can_export=can_export,
        )

    async def import_and_annotate(
        self,
        connector_type: str,
        template_id: str,
        user: User,  # noqa: ARG002
    ) -> dict[str, object]:
        """Pull template HTML from an ESP connector and annotate for the builder."""
        provider = self._get_provider(connector_type)

        if not hasattr(provider, "get_template_html"):
            raise UnsupportedConnectorError(
                f"Connector '{connector_type}' does not support template import"
            )

        html = cast(str, await provider.get_template_html(template_id))  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]

        logger.info(
            "connectors.import_annotate_started",
            connector=connector_type,
            template_id=template_id,
        )

        from app.ai.agents.import_annotator.service import get_import_annotator_service

        annotator = get_import_annotator_service()
        return await annotator.annotate(html=html, esp_platform=connector_type)
