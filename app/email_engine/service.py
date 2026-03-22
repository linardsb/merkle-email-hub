"""Business logic for email build pipeline.

Orchestrates Maizzle builds by calling the maizzle-builder Node.js sidecar
service via HTTP.
"""

from __future__ import annotations

import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.shared import sanitize_html_xss
from app.auth.models import User
from app.core.config import get_settings
from app.core.logging import get_logger
from app.email_engine.exceptions import BuildFailedError, BuildServiceUnavailableError
from app.email_engine.models import EmailBuild
from app.email_engine.schemas import (
    BuildRequest,
    BuildResponse,
    CSSCompileResponse,
    CSSConversionSchema,
    DetectedIntentSchema,
    ExtractedEntitySchema,
    PreviewRequest,
    PreviewResponse,
    SchemaInjectResponse,
)

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
            # Optimize CSS before Maizzle inlining
            optimized_html = self._optimize_css_for_build(data.source_html)
            compiled = await self._call_builder(
                optimized_html, data.config_overrides, data.is_production
            )
            compiled = sanitize_html_xss(compiled)
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
        optimized_html = self._optimize_css_for_build(data.source_html)
        compiled = await self._call_builder(
            optimized_html, data.config_overrides, is_production=False
        )
        compiled = sanitize_html_xss(compiled)
        elapsed = (time.monotonic() - start) * 1000
        logger.info("email_engine.preview_completed", build_time_ms=elapsed)
        return PreviewResponse(compiled_html=compiled, build_time_ms=round(elapsed, 2))

    def compile_css(
        self,
        html: str,
        target_clients: list[str] | None = None,
        css_variables: dict[str, str] | None = None,
    ) -> CSSCompileResponse:
        """Compile and optimize CSS for email clients.

        Synchronous — no DB access, pure CPU transformation.
        """
        from app.email_engine.css_compiler.compiler import CompilationResult, EmailCSSCompiler

        compiler = EmailCSSCompiler(
            target_clients=target_clients,
            css_variables=css_variables,
        )
        result: CompilationResult = compiler.compile(html)

        reduction_pct = (
            round((1 - result.compiled_size / result.original_size) * 100, 1)
            if result.original_size > 0
            else 0.0
        )

        return CSSCompileResponse(
            html=result.html,
            original_size=result.original_size,
            compiled_size=result.compiled_size,
            reduction_pct=reduction_pct,
            removed_properties=result.removed_properties,
            conversions=[
                CSSConversionSchema(
                    original_property=c.original_property,
                    original_value=c.original_value,
                    replacement_property=c.replacement_property,
                    replacement_value=c.replacement_value,
                    reason=c.reason,
                    affected_clients=list(c.affected_clients),
                )
                for c in result.conversions
            ],
            warnings=result.warnings,
            compile_time_ms=result.compile_time_ms,
        )

    def inject_schema(
        self,
        html: str,
        subject: str = "",
    ) -> SchemaInjectResponse:
        """Inject schema.org JSON-LD markup into email HTML.

        Synchronous — no DB access, pure CPU transformation.
        """
        from app.email_engine.schema_markup.classifier import EmailIntentClassifier
        from app.email_engine.schema_markup.injector import SchemaMarkupInjector

        classifier = EmailIntentClassifier()
        intent = classifier.classify(html, subject)

        injector = SchemaMarkupInjector()
        result = injector.inject(html, intent)

        return SchemaInjectResponse(
            html=result.html,
            injected=result.injected,
            intent=DetectedIntentSchema(
                intent_type=result.intent_type,
                confidence=result.confidence,
                entity_count=len(intent.extracted_entities),
            ),
            entities=[
                ExtractedEntitySchema(entity_type=e.entity_type, value=e.value)
                for e in intent.extracted_entities
            ],
            schema_types=result.schema_types,
            validation_errors=list(result.validation_errors),
            inject_time_ms=result.inject_time_ms,
        )

    def _optimize_css_for_build(self, source_html: str) -> str:
        """Run CSS optimization stages 1-5 before Maizzle inlining.

        Best-effort — returns unmodified HTML on failure.
        """
        try:
            from app.email_engine.css_compiler.compiler import EmailCSSCompiler

            compiler = EmailCSSCompiler()
            optimized = compiler.optimize_css(source_html)
            logger.info(
                "email_engine.css_optimized",
                removed_count=len(optimized.removed_properties),
                conversion_count=len(optimized.conversions),
                optimize_time_ms=optimized.optimize_time_ms,
            )
            return optimized.html
        except Exception as exc:
            logger.warning("email_engine.css_optimize_failed", error=str(exc))
            return source_html

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
