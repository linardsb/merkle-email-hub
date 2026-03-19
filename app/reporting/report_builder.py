"""Report data assembly — fetches QA/rendering/blueprint data for PDF generation."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.qa_engine.schemas import QAResultResponse
from app.qa_engine.service import QAEngineService
from app.reporting.exceptions import ReportNotFoundError
from app.reporting.schemas import (
    ApprovalPackageRequest,
    QAReportRequest,
    RegressionReportRequest,
)
from app.reporting.typst_renderer import TypstRenderer

logger = get_logger(__name__)


class ReportBuilder:
    """Assemble report data and compile to PDF."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._renderer = TypstRenderer()
        self._qa_service = QAEngineService(db)

    async def build_qa_report(self, request: QAReportRequest) -> tuple[bytes, str]:
        """Build full QA report PDF.

        Returns:
            (pdf_bytes, filename)
        """
        qa_result = await self._qa_service.get_result(request.qa_result_id)

        data = self._qa_result_to_data(qa_result)
        data["include_screenshots"] = request.include_screenshots
        data["include_chaos"] = request.include_chaos
        data["include_deliverability"] = request.include_deliverability
        data["generated_at"] = datetime.datetime.now(datetime.UTC).isoformat()

        if request.include_screenshots:
            data["screenshots"] = await self._fetch_screenshots(qa_result)

        pdf_bytes = await self._renderer.render("qa_report", data)
        filename = f"qa-report-{qa_result.id}-{_date_slug()}.pdf"
        return pdf_bytes, filename

    async def build_approval_package(self, request: ApprovalPackageRequest) -> tuple[bytes, str]:
        """Build client approval package PDF.

        Returns:
            (pdf_bytes, filename)
        """
        qa_result = await self._qa_service.get_result(request.qa_result_id)

        data = self._qa_result_to_data(qa_result)
        data["is_approval"] = True
        data["include_mobile_preview"] = request.include_mobile_preview
        data["generated_at"] = datetime.datetime.now(datetime.UTC).isoformat()

        pdf_bytes = await self._renderer.render("approval_package", data)
        filename = f"approval-{qa_result.id}-{_date_slug()}.pdf"
        return pdf_bytes, filename

    async def build_regression_report(self, request: RegressionReportRequest) -> tuple[bytes, str]:
        """Build visual regression comparison PDF.

        Returns:
            (pdf_bytes, filename)
        """
        from app.rendering.service import RenderingService

        rendering_svc = RenderingService(self._db)

        baselines = await rendering_svc.list_baselines(request.entity_type, request.entity_id)
        if not baselines.baselines:
            raise ReportNotFoundError(
                f"No baselines found for {request.entity_type}/{request.entity_id}"
            )

        data: dict[str, object] = {
            "entity_type": request.entity_type,
            "entity_id": request.entity_id,
            "baselines": [b.model_dump(mode="json") for b in baselines.baselines],
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        if request.baseline_test_id and request.current_test_id:
            from app.rendering.schemas import RenderingComparisonRequest

            comparison = await rendering_svc.compare_tests(
                RenderingComparisonRequest(
                    baseline_test_id=request.baseline_test_id,
                    current_test_id=request.current_test_id,
                ),
                user=None,  # type: ignore[arg-type]  # internal call
            )
            data["comparison"] = comparison.model_dump(mode="json")

        pdf_bytes = await self._renderer.render("regression_report", data)
        filename = f"regression-{request.entity_type}-{request.entity_id}-{_date_slug()}.pdf"
        return pdf_bytes, filename

    def _qa_result_to_data(self, result: QAResultResponse) -> dict[str, object]:
        """Convert QA result to template-friendly dict."""
        checks_data = []
        for check in result.checks:
            checks_data.append(
                {
                    "name": check.check_name,
                    "passed": check.passed,
                    "score": check.score,
                    "details": check.details or "",
                    "severity": check.severity,
                }
            )

        failed_checks = [c for c in checks_data if not c["passed"]]
        severity_order = {"error": 0, "warning": 1, "info": 2}
        top_issues = sorted(
            failed_checks,
            key=lambda c: severity_order.get(str(c["severity"]), 99),
        )[:3]

        return {
            "qa_result_id": result.id,
            "overall_score": result.overall_score,
            "passed": result.passed,
            "checks_passed": result.checks_passed,
            "checks_total": result.checks_total,
            "checks": checks_data,
            "top_issues": top_issues,
            "resilience_score": result.resilience_score,
            "created_at": result.created_at.isoformat() if result.created_at else "",
        }

    async def _fetch_screenshots(self, qa_result: QAResultResponse) -> list[dict[str, str]]:
        """Fetch rendering screenshots as base64 for embedding in PDF.

        Returns empty list if no screenshots available — template handles gracefully.
        """
        try:
            if not qa_result.build_id:
                return []
            # Screenshots would be fetched from rendering test results associated
            # with this build. The Typst template gracefully omits the section
            # when screenshots is empty.
            return []
        except Exception:
            logger.warning("report.screenshots_fetch_failed", qa_result_id=qa_result.id)
            return []


def _date_slug() -> str:
    """Short date slug for filenames."""
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")
