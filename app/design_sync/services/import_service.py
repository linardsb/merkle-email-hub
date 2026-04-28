"""Design import lifecycle: create/get/update/start_conversion/extract_components."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal

from app.core.logging import get_logger
from app.core.progress import OperationStatus, ProgressTracker
from app.design_sync.crypto import decrypt_token
from app.design_sync.exceptions import (
    ConnectionNotFoundError,
    ImportNotFoundError,
    ImportStateError,
)
from app.design_sync.schemas import (
    ExtractComponentsResponse,
    ImportResponse,
    StartImportRequest,
)

if TYPE_CHECKING:
    from app.auth.models import User
    from app.design_sync.services._context import DesignSyncContext


logger = get_logger(__name__)


class ImportRequestService:
    """Create, fetch, update, and convert design import records."""

    def __init__(self, ctx: DesignSyncContext) -> None:
        self._ctx = ctx

    async def create_design_import(self, data: StartImportRequest, user: User) -> ImportResponse:
        """Create a new import record with brief. Status = pending."""
        from app.core.exceptions import DomainValidationError

        conn = await self._ctx.repo.get_connection(data.connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {data.connection_id} not found")
        if conn.project_id is None:
            raise DomainValidationError("Connection must be linked to a project")
        await self._ctx.verify_access(conn.project_id, user)

        design_import = await self._ctx.repo.create_import(
            connection_id=data.connection_id,
            project_id=conn.project_id,
            selected_node_ids=data.selected_node_ids,
            created_by_id=user.id,
        )
        await self._ctx.repo.update_import_status(
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
        loaded = await self._ctx.repo.get_import(design_import.id)
        return self._import_to_response(loaded)

    async def get_design_import(self, import_id: int, user: User) -> ImportResponse:
        """Get import status with BOLA check."""
        design_import = await self._ctx.repo.get_import_with_assets(import_id)
        if design_import is None:
            raise ImportNotFoundError(f"Import {import_id} not found")
        await self._ctx.verify_access(design_import.project_id, user)
        return self._import_to_response(design_import)

    async def update_import_brief(self, import_id: int, brief: str, user: User) -> ImportResponse:
        """Update the brief on a pending import."""
        design_import = await self._ctx.repo.get_import(import_id)
        if design_import is None:
            raise ImportNotFoundError(f"Import {import_id} not found")
        await self._ctx.verify_access(design_import.project_id, user)
        if design_import.status != "pending":
            raise ImportStateError(
                f"Cannot edit brief: import is '{design_import.status}', expected 'pending'"
            )
        await self._ctx.repo.update_import_status(design_import, "pending", generated_brief=brief)
        logger.info("design_sync.import_brief_updated", import_id=import_id)
        loaded = await self._ctx.repo.get_import(import_id)
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
        from app.design_sync.import_service import DesignImportService

        # Lazy import to avoid circular dependency at module load.
        from app.design_sync.service import DesignSyncService

        design_import = await self._ctx.repo.get_import(import_id)
        if design_import is None:
            raise ImportNotFoundError(f"Import {import_id} not found")
        await self._ctx.verify_access(design_import.project_id, user)
        if design_import.status not in ("pending", "failed"):
            raise ImportStateError(
                f"Cannot convert: import is '{design_import.status}', expected 'pending' or 'failed'"
            )
        if not design_import.generated_brief:
            raise DomainValidationError("Import has no brief — set one before converting")

        await self._ctx.repo.update_import_status(design_import, "converting")
        operation_id = f"design-sync-{import_id}"
        ProgressTracker.start(operation_id, "design_sync")
        ProgressTracker.update(
            operation_id,
            status=OperationStatus.PROCESSING,
            progress=10,
            message="Starting conversion...",
        )
        logger.info("design_sync.conversion_started", import_id=import_id)

        import_service = DesignImportService(
            design_service_factory=DesignSyncService,
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

        loaded = await self._ctx.repo.get_import(import_id)
        return self._import_to_response(loaded)

    async def get_import_by_template(
        self, template_id: int, project_id: int, user: User
    ) -> ImportResponse | None:
        """Get the completed design import for a template, if any."""
        await self._ctx.verify_access(project_id, user)
        design_import = await self._ctx.repo.get_import_by_template_id(template_id, project_id)
        if design_import is None:
            return None
        return self._import_to_response(design_import)

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

        conn = await self._ctx.repo.get_connection(connection_id)
        if conn is None:
            raise ConnectionNotFoundError(f"Connection {connection_id} not found")
        if conn.project_id is not None:
            await self._ctx.verify_access(conn.project_id, user)

        provider = self._ctx.get_provider(conn.provider)
        access_token = decrypt_token(conn.encrypted_token)
        components = await provider.list_components(conn.file_ref, access_token)
        if component_ids:
            components = [c for c in components if c.component_id in component_ids]

        if not components:
            raise NotFoundError("No components found in design file")

        if conn.project_id is None:
            raise DomainValidationError("Connection must be linked to a project for extraction")
        design_import = await self._ctx.repo.create_import(
            connection_id=connection_id,
            project_id=conn.project_id,
            selected_node_ids=[c.component_id for c in components],
            created_by_id=user.id,
        )

        extractor = ComponentExtractor(
            provider=provider,
            design_repo=self._ctx.repo,
            component_repo=ComponentRepository(self._ctx.db),
            db=self._ctx.db,
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

    @staticmethod
    def _import_to_response(design_import: object) -> ImportResponse:
        """Convert DesignImport model to response schema."""
        return ImportResponse.model_validate(design_import, from_attributes=True)
