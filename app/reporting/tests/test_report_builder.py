"""Tests for ReportBuilder — data assembly + renderer orchestration."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock

from app.qa_engine.schemas import QACheckResult, QAResultResponse
from app.reporting.report_builder import ReportBuilder, _date_slug
from app.reporting.schemas import ApprovalPackageRequest, QAReportRequest


def _make_qa_result(**overrides: object) -> QAResultResponse:
    """Factory for QAResultResponse test data."""
    defaults: dict[str, object] = {
        "id": 42,
        "build_id": 100,
        "template_version_id": None,
        "overall_score": 0.85,
        "passed": True,
        "checks_passed": 9,
        "checks_total": 11,
        "checks": [
            QACheckResult(
                check_name="html_validation",
                passed=True,
                score=1.0,
                details=None,
                severity="info",
            ),
            QACheckResult(
                check_name="css_support",
                passed=True,
                score=0.9,
                details=None,
                severity="info",
            ),
            QACheckResult(
                check_name="accessibility",
                passed=False,
                score=0.6,
                details="Missing alt attributes on 2 images",
                severity="error",
            ),
            QACheckResult(
                check_name="dark_mode",
                passed=False,
                score=0.5,
                details="No prefers-color-scheme media query",
                severity="warning",
            ),
        ],
        "override": None,
        "resilience_score": 0.92,
        "created_at": datetime.datetime(2026, 3, 18, tzinfo=datetime.UTC),
    }
    defaults.update(overrides)
    return QAResultResponse(**defaults)


class TestReportBuilder:
    async def test_build_qa_report(self) -> None:
        """QA report builds with correct data and returns PDF + filename."""
        mock_db = AsyncMock()
        builder = ReportBuilder(mock_db)

        qa_result = _make_qa_result()
        fake_pdf = b"%PDF-1.4 test"

        builder._qa_service.get_result = AsyncMock(return_value=qa_result)  # type: ignore[method-assign]
        builder._renderer.render = AsyncMock(return_value=fake_pdf)  # type: ignore[method-assign]

        request = QAReportRequest(qa_result_id=42)
        pdf_bytes, filename = await builder.build_qa_report(request)

        assert pdf_bytes == fake_pdf
        assert "qa-report-42" in filename
        assert filename.endswith(".pdf")

        # Verify render was called with correct template
        builder._renderer.render.assert_called_once()
        call_args = builder._renderer.render.call_args
        assert call_args[0][0] == "qa_report"

    async def test_qa_result_to_data_maps_fields(self) -> None:
        """_qa_result_to_data correctly maps all QA result fields."""
        mock_db = AsyncMock()
        builder = ReportBuilder(mock_db)
        qa_result = _make_qa_result()

        data = builder._qa_result_to_data(qa_result)

        assert data["qa_result_id"] == 42
        assert data["overall_score"] == 0.85
        assert data["passed"] is True
        assert data["checks_passed"] == 9
        assert data["checks_total"] == 11
        assert len(data["checks"]) == 4  # type: ignore[arg-type]
        assert data["resilience_score"] == 0.92

    async def test_top_issues_sorted_by_severity(self) -> None:
        """Top issues sorted: error > warning > info."""
        mock_db = AsyncMock()
        builder = ReportBuilder(mock_db)
        qa_result = _make_qa_result()

        data = builder._qa_result_to_data(qa_result)
        top_issues: list[dict[str, object]] = data["top_issues"]  # type: ignore[assignment]

        assert len(top_issues) == 2  # Only 2 failed checks
        assert top_issues[0]["severity"] == "error"
        assert top_issues[1]["severity"] == "warning"

    async def test_empty_screenshots_handled(self) -> None:
        """Screenshots return empty list when no build_id."""
        mock_db = AsyncMock()
        builder = ReportBuilder(mock_db)
        qa_result = _make_qa_result(build_id=None)

        screenshots = await builder._fetch_screenshots(qa_result)
        assert screenshots == []

    async def test_build_approval_package_uses_correct_template(self) -> None:
        """Approval package calls renderer with approval_package template."""
        mock_db = AsyncMock()
        builder = ReportBuilder(mock_db)

        qa_result = _make_qa_result()
        fake_pdf = b"%PDF-1.4 approval"

        builder._qa_service.get_result = AsyncMock(return_value=qa_result)  # type: ignore[method-assign]
        builder._renderer.render = AsyncMock(return_value=fake_pdf)  # type: ignore[method-assign]

        request = ApprovalPackageRequest(qa_result_id=42)
        pdf_bytes, filename = await builder.build_approval_package(request)

        assert pdf_bytes == fake_pdf
        assert "approval-42" in filename
        builder._renderer.render.assert_called_once()
        assert builder._renderer.render.call_args[0][0] == "approval_package"

    async def test_date_slug_format(self) -> None:
        """_date_slug returns YYYYMMDD format."""
        slug = _date_slug()
        assert len(slug) == 8
        # Should be parseable as a date
        datetime.datetime.strptime(slug, "%Y%m%d").replace(tzinfo=datetime.UTC)
