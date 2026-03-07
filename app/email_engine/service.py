"""Business logic for email build pipeline.

Orchestrates Maizzle builds by calling the maizzle-builder Node.js sidecar
service via HTTP.
"""

from __future__ import annotations

import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import get_settings
from app.core.logging import get_logger
from app.email_engine.exceptions import BuildFailedError, BuildServiceUnavailableError
from app.email_engine.models import EmailBuild
from app.email_engine.schemas import BuildRequest, BuildResponse, PreviewRequest, PreviewResponse

logger = get_logger(__name__)
settings = get_settings()

MAIZZLE_BUILDER_URL = settings.maizzle_builder_url


class EmailEngineService:
    """Orchestrates email template builds via the Maizzle sidecar."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build(self, data: BuildRequest, user_id: int) -> BuildResponse:
        """Execute a full email build and persist the result."""
        logger.info(
            "email_engine.build_started", template=data.template_name, project_id=data.project_id
        )

        build = EmailBuild(
            project_id=data.project_id,
            template_name=data.template_name,
            source_html=data.source_html,
            build_config=str(data.config_overrides) if data.config_overrides else None,
            triggered_by_id=user_id,
            is_production=data.is_production,
            status="building",
        )
        self.db.add(build)
        await self.db.commit()
        await self.db.refresh(build)

        try:
            compiled = await self._call_builder(
                data.source_html, data.config_overrides, data.is_production
            )
            build.compiled_html = compiled
            build.status = "success"
        except BuildServiceUnavailableError:
            build.status = "failed"
            build.error_message = "Maizzle builder service unavailable"
            raise
        except Exception as exc:
            build.status = "failed"
            build.error_message = "Build failed"
            logger.error(
                "email_engine.build_error",
                build_id=build.id,
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            raise BuildFailedError("Email build failed") from exc
        finally:
            await self.db.commit()
            await self.db.refresh(build)

        logger.info("email_engine.build_completed", build_id=build.id, status=build.status)
        return BuildResponse.model_validate(build)

    async def get_build(self, build_id: int, user: User) -> BuildResponse:
        """Get a build by ID. Verifies user has access to the build's project."""
        result = await self.db.execute(select(EmailBuild).where(EmailBuild.id == build_id))
        build = result.scalar_one_or_none()
        if not build:
            raise BuildFailedError(f"Build {build_id} not found")

        from app.projects.service import ProjectService

        project_service = ProjectService(self.db)
        await project_service.verify_project_access(build.project_id, user)

        return BuildResponse.model_validate(build)

    async def preview(self, data: PreviewRequest) -> PreviewResponse:
        """Execute a preview build without persisting."""
        logger.info("email_engine.preview_started")
        start = time.monotonic()
        compiled = await self._call_builder(
            data.source_html, data.config_overrides, is_production=False
        )
        elapsed = (time.monotonic() - start) * 1000
        logger.info("email_engine.preview_completed", build_time_ms=elapsed)
        return PreviewResponse(compiled_html=compiled, build_time_ms=round(elapsed, 2))

    async def _call_builder(
        self, source_html: str, config_overrides: dict[str, object] | None, is_production: bool
    ) -> str:
        """Call the Maizzle builder sidecar service."""
        payload = {
            "source": source_html,
            "config": config_overrides or {},
            "production": is_production,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{MAIZZLE_BUILDER_URL}/build", json=payload)
                response.raise_for_status()
                result = response.json()
                return str(result["html"])
        except httpx.ConnectError as exc:
            raise BuildServiceUnavailableError("Cannot connect to maizzle-builder service") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "email_engine.builder_http_error",
                status_code=exc.response.status_code,
            )
            raise BuildFailedError("Email build failed") from exc
