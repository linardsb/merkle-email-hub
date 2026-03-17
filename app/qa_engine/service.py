"""Business logic for QA engine — orchestrates all 10 quality checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    BIMICheckRequest,
    BIMICheckResponse,
    ChaosTestRequest,
    ChaosTestResponse,
    DeliverabilityDimension,
    DeliverabilityIssue,
    DeliverabilityScoreRequest,
    DeliverabilityScoreResponse,
    GmailOptimizeRequest,
    GmailOptimizeResponse,
    GmailPredictRequest,
    GmailPredictResponse,
    MigrationPhaseSchema,
    MigrationPlanRequest,
    MigrationPlanResponse,
    ModernizationStepSchema,
    OutlookAnalysisRequest,
    OutlookAnalysisResponse,
    OutlookDependencySchema,
    OutlookModernizeRequest,
    OutlookModernizeResponse,
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

if TYPE_CHECKING:
    from app.qa_engine.outlook_analyzer.types import OutlookAnalysis

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

    async def predict_gmail_summary(
        self,
        data: GmailPredictRequest,
    ) -> GmailPredictResponse:
        """Predict Gmail's AI summary for an email."""
        settings = get_settings()
        if not settings.qa_gmail_predictor.enabled:
            raise ForbiddenError("Gmail AI prediction is not enabled")

        logger.info(
            "qa_engine.gmail_predict_started",
            subject_length=len(data.subject),
            html_length=len(data.html),
        )

        from app.qa_engine.gmail_intelligence.predictor import GmailSummaryPredictor

        predictor = GmailSummaryPredictor()
        prediction = await predictor.predict(
            html=data.html,
            subject=data.subject,
            from_name=data.from_name,
        )

        logger.info(
            "qa_engine.gmail_predict_completed",
            predicted_category=prediction.predicted_category,
            confidence=prediction.confidence,
        )

        return GmailPredictResponse(
            summary_text=prediction.summary_text,
            predicted_category=prediction.predicted_category,
            key_actions=list(prediction.key_actions),
            promotion_signals=list(prediction.promotion_signals),
            improvement_suggestions=list(prediction.improvement_suggestions),
            confidence=prediction.confidence,
        )

    async def optimize_gmail_preview(
        self,
        data: GmailOptimizeRequest,
    ) -> GmailOptimizeResponse:
        """Suggest optimized subject/preview text for better AI summaries."""
        settings = get_settings()
        if not settings.qa_gmail_predictor.enabled:
            raise ForbiddenError("Gmail AI prediction is not enabled")

        logger.info(
            "qa_engine.gmail_optimize_started",
            subject_length=len(data.subject),
            html_length=len(data.html),
        )

        from app.qa_engine.gmail_intelligence.optimizer import PreviewTextOptimizer

        optimizer = PreviewTextOptimizer()
        result = await optimizer.optimize(
            html=data.html,
            subject=data.subject,
            from_name=data.from_name,
            target_summary=data.target_summary,
        )

        logger.info("qa_engine.gmail_optimize_completed")

        return GmailOptimizeResponse(
            original_subject=result.original_subject,
            suggested_subjects=list(result.suggested_subjects),
            original_preview=result.original_preview,
            suggested_previews=list(result.suggested_previews),
            reasoning=result.reasoning,
        )

    async def run_outlook_analysis(self, data: OutlookAnalysisRequest) -> OutlookAnalysisResponse:
        """Analyze HTML for Word-engine dependencies."""
        settings = get_settings()
        if not settings.qa_outlook_analyzer.enabled:
            raise ForbiddenError("Outlook dependency analyzer is not enabled")

        from app.qa_engine.outlook_analyzer import OutlookDependencyDetector

        detector = OutlookDependencyDetector()
        analysis = detector.analyze(data.html)

        logger.info(
            "qa_engine.outlook_analysis_completed",
            total=analysis.total_count,
            removable=analysis.removable_count,
            byte_savings=analysis.byte_savings,
        )

        return self._analysis_to_response(analysis)

    async def run_outlook_modernize(
        self, data: OutlookModernizeRequest
    ) -> OutlookModernizeResponse:
        """Analyze and modernize HTML by removing Word-engine dependencies."""
        settings = get_settings()
        if not settings.qa_outlook_analyzer.enabled:
            raise ForbiddenError("Outlook dependency analyzer is not enabled")

        from app.qa_engine.outlook_analyzer import (
            OutlookDependencyDetector,
            OutlookModernizer,
        )

        detector = OutlookDependencyDetector()
        analysis = detector.analyze(data.html)

        target = data.target or settings.qa_outlook_analyzer.default_target

        modernizer = OutlookModernizer()
        result = modernizer.modernize(data.html, analysis, target=target)

        logger.info(
            "qa_engine.outlook_modernize_completed",
            target=target,
            changes=result.changes_applied,
            bytes_saved=result.bytes_before - result.bytes_after,
        )

        return OutlookModernizeResponse(
            html=result.html,
            changes_applied=result.changes_applied,
            bytes_before=result.bytes_before,
            bytes_after=result.bytes_after,
            bytes_saved=result.bytes_before - result.bytes_after,
            target=result.target,
            analysis=self._analysis_to_response(analysis),
        )

    async def run_migration_plan(self, data: MigrationPlanRequest) -> MigrationPlanResponse:
        """Generate audience-aware migration plan."""
        settings = get_settings()
        if not settings.qa_outlook_analyzer.enabled:
            raise ForbiddenError("Outlook dependency analyzer is not enabled")

        from app.qa_engine.outlook_analyzer import (
            AudienceProfile,
            MigrationPlanner,
            OutlookDependencyDetector,
        )

        detector = OutlookDependencyDetector()
        analysis = detector.analyze(data.html)

        audience: AudienceProfile | None = None
        if data.audience is not None:
            audience = AudienceProfile(
                client_distribution=data.audience.client_distribution,
            )

        planner = MigrationPlanner()
        plan = planner.plan(analysis, audience)

        analysis_response = self._analysis_to_response(analysis)

        logger.info(
            "qa_engine.migration_plan_completed",
            phases=len(plan.phases),
            recommendation=plan.recommendation,
            word_engine_share=round(plan.word_engine_audience, 4),
        )

        return MigrationPlanResponse(
            phases=[
                MigrationPhaseSchema(
                    name=p.name,
                    description=p.description,
                    dependency_types=p.dependency_types,
                    dependency_count=len(p.dependencies_to_remove),
                    audience_impact=p.audience_impact,
                    safe_when=p.safe_when,
                    risk_level=p.risk_level,
                    estimated_byte_savings=p.estimated_byte_savings,
                )
                for p in plan.phases
            ],
            total_dependencies=plan.total_dependencies,
            total_removable=plan.total_removable,
            total_savings_bytes=plan.total_savings_bytes,
            word_engine_audience=plan.word_engine_audience,
            risk_assessment=plan.risk_assessment,
            recommendation=plan.recommendation,
            analysis=analysis_response,
        )

    async def run_deliverability_score(
        self, data: DeliverabilityScoreRequest
    ) -> DeliverabilityScoreResponse:
        """Run standalone deliverability prediction scoring."""
        settings = get_settings()
        if not settings.qa_deliverability.enabled:
            raise ForbiddenError("Deliverability scoring is not enabled")

        from app.qa_engine.checks.deliverability import get_detailed_result

        threshold = settings.qa_deliverability.threshold
        total_score, passed, dimensions = get_detailed_result(data.html, threshold)

        response_dimensions: list[DeliverabilityDimension] = []
        all_issues: list[DeliverabilityIssue] = []
        for dim in dimensions:
            dim_issues = [
                DeliverabilityIssue(
                    dimension=issue.dimension,
                    severity=issue.severity,
                    description=issue.description,
                    fix=issue.fix,
                )
                for issue in dim.issues
            ]
            response_dimensions.append(
                DeliverabilityDimension(
                    name=dim.name,
                    score=dim.score,
                )
            )
            all_issues.extend(dim_issues)

        # Summary
        if total_score >= 85:
            summary = "Excellent deliverability. Email is well-optimized for inbox placement."
        elif total_score >= threshold:
            summary = "Good deliverability. Minor improvements possible."
        elif total_score >= 50:
            summary = "Fair deliverability. Several issues should be addressed before sending."
        else:
            summary = (
                "Poor deliverability. Significant issues detected that may cause spam filtering."
            )

        logger.info(
            "qa_engine.deliverability_score_completed",
            score=total_score,
            passed=passed,
            threshold=threshold,
        )

        return DeliverabilityScoreResponse(
            score=total_score,
            passed=passed,
            threshold=threshold,
            dimensions=response_dimensions,
            issues=all_issues,
            summary=summary,
        )

    async def run_bimi_check(self, data: BIMICheckRequest) -> BIMICheckResponse:
        """Check BIMI readiness for a sending domain."""
        settings = get_settings()
        if not settings.qa_bimi.enabled:
            raise ForbiddenError("BIMI readiness check is not enabled")

        from app.qa_engine.bimi import BIMIReadinessChecker

        checker = BIMIReadinessChecker()
        status = await checker.check_domain(data.domain)

        logger.info(
            "qa_engine.bimi_check_completed",
            domain=data.domain,
            ready=status.ready,
            dmarc_ready=status.dmarc_ready,
            bimi_exists=status.bimi_record_exists,
            issue_count=len(status.issues),
        )

        return BIMICheckResponse(
            domain=status.domain,
            ready=status.ready,
            dmarc_ready=status.dmarc_ready,
            dmarc_policy=status.dmarc_policy,
            dmarc_record=status.dmarc_record,
            bimi_record_exists=status.bimi_record_exists,
            bimi_record=status.bimi_record,
            bimi_svg_url=status.bimi_svg_url,
            bimi_authority_url=status.bimi_authority_url,
            svg_valid=status.svg_valid,
            cmc_status=status.cmc_status,
            generated_record=status.generated_record,
            issues=status.issues,
        )

    def _analysis_to_response(self, analysis: OutlookAnalysis) -> OutlookAnalysisResponse:
        """Convert OutlookAnalysis dataclass to response schema."""

        return OutlookAnalysisResponse(
            dependencies=[
                OutlookDependencySchema(
                    type=d.type,
                    location=d.location,
                    line_number=d.line_number,
                    code_snippet=d.code_snippet,
                    severity=d.severity,
                    removable=d.removable,
                    modern_replacement=d.modern_replacement,
                )
                for d in analysis.dependencies
            ],
            total_count=analysis.total_count,
            removable_count=analysis.removable_count,
            byte_savings=analysis.byte_savings,
            modernization_plan=[
                ModernizationStepSchema(
                    description=s.description,
                    dependency_type=s.dependency_type,
                    removals=s.removals,
                    byte_savings=s.byte_savings,
                )
                for s in analysis.modernization_plan
            ],
            vml_count=analysis.vml_count,
            ghost_table_count=analysis.ghost_table_count,
            mso_conditional_count=analysis.mso_conditional_count,
            mso_css_count=analysis.mso_css_count,
            dpi_image_count=analysis.dpi_image_count,
            external_class_count=analysis.external_class_count,
            word_wrap_count=analysis.word_wrap_count,
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
