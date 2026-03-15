# pyright: reportUnknownVariableType=false
"""Orchestrator for the Figma → Scaffolder → Template conversion pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from app.auth.models import User
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.design_sync.exceptions import SyncFailedError
from app.design_sync.models import DesignConnection
from app.design_sync.repository import DesignSyncRepository
from app.design_sync.schemas import (
    DesignTokensResponse,
    DownloadAssetsResponse,
    LayoutAnalysisResponse,
)

if TYPE_CHECKING:
    from app.ai.agents.scaffolder.schemas import ScaffolderResponse
    from app.design_sync.service import DesignSyncService

logger = get_logger(__name__)


class DesignImportService:
    """Orchestrates the Figma → Scaffolder → Template conversion pipeline.

    Runs as a background task with its own DB session (via get_db_context).
    Updates DesignImport status as it progresses:
    pending → converting → completed/failed
    """

    def __init__(
        self,
        design_service_factory: type[DesignSyncService],
        user: User,
    ) -> None:
        self._service_factory = design_service_factory
        self._user = user

    async def run_conversion(
        self,
        import_id: int,
        *,
        run_qa: bool = True,
        output_mode: Literal["html", "structured"] = "structured",
    ) -> None:
        """Background pipeline: layout analysis → asset download → Scaffolder → Template creation.

        Creates its own DB session to avoid sharing the request-scoped session.
        """
        async with get_db_context() as db:
            repo = DesignSyncRepository(db)
            design_service = self._service_factory(db)

            design_import = await repo.get_import_with_assets(import_id)
            if design_import is None:
                logger.error("design_sync.import_not_found", import_id=import_id)
                return

            try:
                await repo.update_import_status(design_import, "converting")

                # 1. Get connection details
                conn = await repo.get_connection(design_import.connection_id)
                if conn is None:
                    logger.error(
                        "design_sync.connection_not_found",
                        import_id=import_id,
                        connection_id=design_import.connection_id,
                    )
                    await repo.update_import_status(
                        design_import,
                        "failed",
                        error_message="Connection not found",
                    )
                    return

                # 2. Analyze layout
                layout_response = await design_service.analyze_layout(
                    design_import.connection_id,
                    self._user,
                    selected_node_ids=design_import.selected_node_ids or None,
                )

                # 3. Download assets for image nodes
                image_node_ids = self._collect_image_node_ids(layout_response)
                asset_response = None
                if image_node_ids:
                    asset_response = await design_service.download_assets(
                        design_import.connection_id,
                        self._user,
                        image_node_ids,
                    )

                # 4. Get design tokens (best-effort — skip on provider errors)
                tokens = None
                try:
                    tokens = await design_service.get_tokens(
                        design_import.connection_id, self._user
                    )
                except (SyncFailedError, ConnectionError):
                    logger.warning(
                        "design_sync.tokens_skipped",
                        import_id=import_id,
                        exc_info=True,
                    )

                # 5. Build design context
                design_context = self._build_design_context(
                    layout_response, asset_response, tokens, conn
                )

                # 6. Call Scaffolder
                scaffolder_response = await self._call_scaffolder(
                    brief=design_import.generated_brief or "",
                    design_context=design_context,
                    run_qa=run_qa,
                    output_mode=output_mode,
                )

                # 7. Create Template + TemplateVersion (single transaction)
                raw_name = (
                    design_import.structure_json.get("template_name")
                    if design_import.structure_json
                    else None
                )
                template_name = str(raw_name) if isinstance(raw_name, str) else None
                template_id = await self._create_template(
                    db=db,
                    project_id=design_import.project_id,
                    brief=design_import.generated_brief or "",
                    html=scaffolder_response.html,
                    user_id=design_import.created_by_id,
                    template_name=template_name,
                )

                # 8. Mark complete
                await repo.update_import_status(
                    design_import,
                    "completed",
                    result_template_id=template_id,
                    structure_json={
                        **(design_import.structure_json or {}),
                        "scaffolder_model": scaffolder_response.model,
                        "qa_passed": scaffolder_response.qa_passed,
                        "confidence": scaffolder_response.confidence,
                    },
                )

                logger.info(
                    "design_sync.conversion_completed",
                    import_id=import_id,
                    template_id=template_id,
                )

            except Exception:
                logger.exception("design_sync.conversion_failed", import_id=import_id)
                try:
                    design_import = await repo.get_import(import_id)
                    if design_import is not None:
                        await repo.update_import_status(
                            design_import,
                            "failed",
                            error_message="Conversion pipeline failed",
                        )
                except Exception:
                    logger.exception(
                        "design_sync.failure_status_update_failed",
                        import_id=import_id,
                    )

    def _collect_image_node_ids(self, layout: LayoutAnalysisResponse) -> list[str]:
        """Extract image node IDs from layout analysis sections."""
        node_ids: list[str] = []
        for section in layout.sections:
            for img in section.images:
                node_ids.append(img.node_id)
        return node_ids

    def _build_design_context(
        self,
        layout: LayoutAnalysisResponse,
        asset_response: DownloadAssetsResponse | None,
        tokens: DesignTokensResponse | None,
        conn: DesignConnection,
    ) -> dict[str, object]:
        """Build the design context dict for the Scaffolder."""
        image_urls: dict[str, str] = {}
        if asset_response is not None:
            for asset in asset_response.assets:
                image_urls[asset.node_id] = f"/api/v1/design-sync/assets/{conn.id}/{asset.filename}"

        layout_summary = ", ".join(s.section_type for s in layout.sections)

        design_tokens: dict[str, object] | None = None
        if tokens is not None:
            design_tokens = {
                "colors": [
                    {"name": c.name, "hex": c.hex, "opacity": c.opacity} for c in tokens.colors
                ],
                "typography": [
                    {
                        "name": t.name,
                        "family": t.family,
                        "weight": t.weight,
                        "size": t.size,
                    }
                    for t in tokens.typography
                ],
            }

        return {
            "image_urls": image_urls,
            "layout_summary": layout_summary or None,
            "design_tokens": design_tokens,
            "source_file": layout.file_name,
        }

    async def _call_scaffolder(
        self,
        brief: str,
        design_context: dict[str, object],
        run_qa: bool,
        output_mode: Literal["html", "structured"],
    ) -> ScaffolderResponse:
        """Invoke the Scaffolder agent with the brief and design context."""
        from app.ai.agents.scaffolder.schemas import ScaffolderRequest
        from app.ai.agents.scaffolder.service import get_scaffolder_service

        request = ScaffolderRequest(
            brief=brief,
            run_qa=run_qa,
            output_mode=output_mode,
            design_context=design_context,
        )
        service = get_scaffolder_service()
        return await service.generate(request)

    @staticmethod
    async def _create_template(
        db: object,
        project_id: int,
        brief: str,
        html: str,
        user_id: int,
        template_name: str | None = None,
    ) -> int:
        """Create Template + TemplateVersion atomically in a single commit."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.templates.models import Template, TemplateVersion

        session: AsyncSession = db  # type: ignore[assignment]
        name = template_name or DesignImportService._derive_template_name(brief)

        template = Template(
            project_id=project_id,
            name=name,
            description="Imported from Figma design",
            status="draft",
            created_by_id=user_id,
        )
        session.add(template)
        await session.flush()  # assign template.id without committing

        version = TemplateVersion(
            template_id=template.id,
            version_number=1,
            html_source=html,
            created_by_id=user_id,
        )
        session.add(version)
        await session.commit()  # single atomic commit

        return template.id

    @staticmethod
    def _derive_template_name(brief: str) -> str:
        """Derive a template name from the first meaningful line of the brief."""
        for line in brief.strip().splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:200]
        return "Imported from Figma"
