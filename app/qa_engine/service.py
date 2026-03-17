"""Business logic for QA engine — orchestrates all 10 quality checks."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.logging import get_logger
from app.projects.models import Project
from app.projects.service import ProjectService
from app.qa_engine.check_config import load_defaults, merge_profile
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.exceptions import QAOverrideNotAllowedError, QAResultNotFoundError
from app.qa_engine.models import QAOverride, QAResult
from app.qa_engine.repository import QARepository
from app.qa_engine.schemas import (
    ChaosTestRequest,
    ChaosTestResponse,
    PropertyFailureSchema,
    PropertyTestRequest,
    PropertyTestResponse,
    QACheckResult,
    QAOverrideRequest,
    QAOverrideResponse,
    QAResultResponse,
    QARunRequest,
)
from app.shared.schemas import PaginatedResponse, PaginationParams

logger = get_logger(__name__)


class QAEngineService:
    """Orchestrates the QA gate (11 core checks + optional resilience check)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = QARepository(db)

    async def run_checks(self, data: QARunRequest) -> QAResultResponse:
        """Run all QA checks against compiled HTML."""
        logger.info(
            "qa_engine.run_started",
            build_id=data.build_id,
            template_version_id=data.template_version_id,
            project_id=data.project_id,
        )

        # Load QA config: defaults + per-project overrides
        profile = load_defaults()
        if data.project_id:
            db_result = await self.db.execute(
                select(Project.qa_profile).where(Project.id == data.project_id)
            )
            project_qa_profile = db_result.scalar_one_or_none()
            profile = merge_profile(profile, project_qa_profile)

        check_results: list[QACheckResult] = []
        for check in ALL_CHECKS:
            check_config = profile.get_check_config(check.name)
            if check_config and not check_config.enabled:
                check_results.append(
                    QACheckResult(
                        check_name=check.name,
                        passed=True,
                        score=1.0,
                        details="Check disabled by project configuration",
                        severity="info",
                    )
                )
                continue
            result = await check.run(data.html, check_config)
            check_results.append(result)

        # Optionally run resilience check (separate from ALL_CHECKS to avoid recursion)
        settings = get_settings()
        if settings.qa_chaos.enabled and settings.qa_chaos.resilience_check_enabled:
            from app.qa_engine.checks.rendering_resilience import RenderingResilienceCheck

            resilience_check = RenderingResilienceCheck(
                threshold=settings.qa_chaos.resilience_threshold,
            )
            res_config = profile.get_check_config(resilience_check.name)
            if not res_config or res_config.enabled:
                resilience_result = await resilience_check.run(data.html, res_config)
                check_results.append(resilience_result)

        passed_count = sum(1 for c in check_results if c.passed)
        overall_score = (
            sum(c.score for c in check_results) / len(check_results) if check_results else 0.0
        )
        all_passed = passed_count == len(check_results)

        qa_result = await self.repository.create_result(
            build_id=data.build_id,
            template_version_id=data.template_version_id,
            overall_score=round(overall_score, 3),
            passed=all_passed,
            checks_passed=passed_count,
            checks_total=len(check_results),
        )

        await self.repository.create_checks(
            qa_result_id=qa_result.id,
            checks=[cr.model_dump() for cr in check_results],
        )

        logger.info(
            "qa_engine.run_completed",
            build_id=data.build_id,
            result_id=qa_result.id,
            score=round(overall_score, 3),
            passed=all_passed,
            checks_passed=passed_count,
        )

        return QAResultResponse(
            id=qa_result.id,
            build_id=qa_result.build_id,
            template_version_id=qa_result.template_version_id,
            overall_score=qa_result.overall_score,
            passed=qa_result.passed,
            checks_passed=qa_result.checks_passed,
            checks_total=qa_result.checks_total,
            checks=check_results,
            created_at=qa_result.created_at,  # pyright: ignore[reportArgumentType]
        )

    async def run_chaos_test(
        self, data: ChaosTestRequest, user: User | None = None
    ) -> ChaosTestResponse:
        """Run chaos testing on HTML with controlled degradations."""
        settings = get_settings()
        if not settings.qa_chaos.enabled:
            raise ForbiddenError("Chaos testing is not enabled")

        from app.qa_engine.chaos.engine import ChaosEngine

        engine = ChaosEngine()
        result = await engine.run_chaos_test(
            html=data.html,
            profiles=data.profiles,
            default_profiles=settings.qa_chaos.default_profiles,
        )

        # Auto-document failures to knowledge base (requires project_id + user for BOLA)
        if (
            settings.qa_chaos.auto_document
            and result.critical_failures
            and data.project_id is not None
            and user is not None
        ):
            try:
                from app.qa_engine.chaos.knowledge_writer import ChaosKnowledgeWriter

                project_service = ProjectService(self.db)
                await project_service.verify_project_access(data.project_id, user)

                writer = ChaosKnowledgeWriter(self.db)
                doc_ids = await writer.write_failure_documents(
                    failures=result.critical_failures,
                    project_id=data.project_id,
                )
                if doc_ids:
                    logger.info(
                        "chaos.auto_document.created",
                        document_count=len(doc_ids),
                        document_ids=doc_ids,
                    )
            except Exception:
                logger.warning("chaos.auto_document.failed", exc_info=True)

        logger.info(
            "qa_engine.chaos_test_completed",
            resilience_score=result.resilience_score,
            profiles_tested=result.profiles_tested,
        )
        return result

    async def run_property_test(self, data: PropertyTestRequest) -> PropertyTestResponse:
        """Run property-based testing on randomly generated emails."""
        settings = get_settings()
        if not settings.qa_property_testing.enabled:
            raise ForbiddenError("Property testing is not enabled")

        from dataclasses import asdict

        from app.qa_engine.property_testing.invariants import ALL_INVARIANTS
        from app.qa_engine.property_testing.runner import PropertyTestRunner

        runner = PropertyTestRunner()
        seed = data.seed if data.seed is not None else settings.qa_property_testing.seed
        num_cases = (
            data.num_cases
            if data.num_cases is not None
            else settings.qa_property_testing.default_cases
        )
        result = await runner.run(
            invariant_names=data.invariants,
            num_cases=num_cases,
            seed=seed,
        )

        logger.info(
            "qa_engine.property_test_completed",
            total_cases=result.total_cases,
            passed=result.passed,
            failed=result.failed,
            seed=result.seed,
        )

        failures = [
            PropertyFailureSchema(
                invariant_name=f.invariant_name,
                violations=list(f.violations),
                config=asdict(f.config),
            )
            for f in result.failures
        ]

        return PropertyTestResponse(
            total_cases=result.total_cases,
            passed=result.passed,
            failed=result.failed,
            failures=failures,
            seed=result.seed,
            invariants_tested=data.invariants or list(ALL_INVARIANTS.keys()),
        )

    async def get_result(self, result_id: int) -> QAResultResponse:
        """Get a single QA result by ID, including checks and override."""
        result = await self.repository.get_result_with_checks(result_id)
        if not result:
            raise QAResultNotFoundError(f"QA result {result_id} not found")
        return self._to_response(result)

    async def list_results(
        self,
        pagination: PaginationParams,
        *,
        build_id: int | None = None,
        template_version_id: int | None = None,
        passed: bool | None = None,
    ) -> PaginatedResponse[QAResultResponse]:
        """List QA results with optional filters."""
        logger.info(
            "qa_engine.list_started",
            page=pagination.page,
            build_id=build_id,
            template_version_id=template_version_id,
        )
        items = await self.repository.list_results(
            build_id=build_id,
            template_version_id=template_version_id,
            passed=passed,
            offset=pagination.offset,
            limit=pagination.page_size,
        )
        total = await self.repository.count_results(
            build_id=build_id,
            template_version_id=template_version_id,
            passed=passed,
        )
        return PaginatedResponse[QAResultResponse](
            items=[self._to_response(r) for r in items],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_latest_result(
        self,
        *,
        build_id: int | None = None,
        template_version_id: int | None = None,
    ) -> QAResultResponse:
        """Get the most recent QA result for a build or template version."""
        result = await self.repository.get_latest_result(
            build_id=build_id,
            template_version_id=template_version_id,
        )
        if not result:
            raise QAResultNotFoundError("No QA results found for the given filters")
        return self._to_response(result)

    async def _resolve_project_id(self, result: QAResult) -> int | None:
        """Resolve the project_id from a QA result via build or template chain."""
        if result.build_id:
            from app.email_engine.models import EmailBuild

            db_result = await self.db.execute(
                select(EmailBuild.project_id).where(EmailBuild.id == result.build_id)
            )
            project_id = db_result.scalar_one_or_none()
            if project_id:
                return int(project_id)
        if result.template_version_id:
            from app.templates.models import Template, TemplateVersion

            db_result = await self.db.execute(
                select(Template.project_id)
                .join(TemplateVersion, TemplateVersion.template_id == Template.id)
                .where(TemplateVersion.id == result.template_version_id)
            )
            project_id = db_result.scalar_one_or_none()
            if project_id:
                return int(project_id)
        return None

    async def override_result(
        self,
        result_id: int,
        data: QAOverrideRequest,
        user: User,
    ) -> QAOverrideResponse:
        """Override failing checks with justification. Requires developer+ role."""
        result = await self.repository.get_result_with_checks(result_id)
        if not result:
            raise QAResultNotFoundError(f"QA result {result_id} not found")

        # BOLA: verify user has access to the result's project
        project_id = await self._resolve_project_id(result)
        if project_id:
            project_service = ProjectService(self.db)
            await project_service.verify_project_access(project_id, user)

        if result.passed:
            raise QAOverrideNotAllowedError("Cannot override a passing QA result")

        # Validate all override check names are real failed checks
        failed_check_names = {c.check_name for c in result.checks if not c.passed}
        invalid_names = set(data.checks_overridden) - failed_check_names
        if invalid_names:
            raise QAOverrideNotAllowedError(
                f"Cannot override checks that passed or don't exist: {', '.join(sorted(invalid_names))}"
            )

        # Check if an override already exists — replace it
        existing = await self.repository.get_override_by_result_id(result_id)
        if existing:
            await self.db.delete(existing)
            await self.db.commit()

        override = await self.repository.create_override(
            qa_result_id=result_id,
            overridden_by_id=user.id,
            justification=data.justification,
            checks_overridden=data.checks_overridden,
        )

        logger.info(
            "qa_engine.override_created",
            result_id=result_id,
            user_id=user.id,
            checks_overridden=data.checks_overridden,
        )

        return QAOverrideResponse.model_validate(override)

    def _to_response(
        self, result: QAResult, override: QAOverride | None = None
    ) -> QAResultResponse:
        """Transform a QAResult model to response schema."""
        resolved_override = override or result.override
        return QAResultResponse(
            id=result.id,
            build_id=result.build_id,
            template_version_id=result.template_version_id,
            overall_score=result.overall_score,
            passed=result.passed,
            checks_passed=result.checks_passed,
            checks_total=result.checks_total,
            checks=[
                QACheckResult(
                    check_name=c.check_name,
                    passed=c.passed,
                    score=c.score,
                    details=c.details,
                    severity=c.severity,
                )
                for c in result.checks
            ],
            override=(
                QAOverrideResponse.model_validate(resolved_override) if resolved_override else None
            ),
            created_at=result.created_at,  # pyright: ignore[reportArgumentType]
        )
