"""Business logic for QA engine — orchestrates all 10 quality checks."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.logging import get_logger
from app.projects.service import ProjectService
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.exceptions import QAOverrideNotAllowedError, QAResultNotFoundError
from app.qa_engine.models import QAOverride, QAResult
from app.qa_engine.repository import QARepository
from app.qa_engine.schemas import (
    QACheckResult,
    QAOverrideRequest,
    QAOverrideResponse,
    QAResultResponse,
    QARunRequest,
)
from app.shared.schemas import PaginatedResponse, PaginationParams

logger = get_logger(__name__)


class QAEngineService:
    """Orchestrates the 10-point QA gate."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = QARepository(db)

    async def run_checks(self, data: QARunRequest) -> QAResultResponse:
        """Run all QA checks against compiled HTML."""
        logger.info(
            "qa_engine.run_started",
            build_id=data.build_id,
            template_version_id=data.template_version_id,
        )

        check_results: list[QACheckResult] = []
        for check in ALL_CHECKS:
            result = await check.run(data.html)
            check_results.append(result)

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
