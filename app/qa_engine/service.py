"""Business logic for QA engine — orchestrates all 10 quality checks."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.models import QACheck, QAResult
from app.qa_engine.schemas import QACheckResult, QAResultResponse, QARunRequest

logger = get_logger(__name__)


class QAEngineService:
    """Orchestrates the 10-point QA gate."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_checks(self, data: QARunRequest) -> QAResultResponse:
        """Run all QA checks against compiled HTML."""
        logger.info("qa_engine.run_started", build_id=data.build_id)

        check_results: list[QACheckResult] = []
        for check in ALL_CHECKS:
            result = await check.run(data.html)
            check_results.append(result)

        passed_count = sum(1 for c in check_results if c.passed)
        overall_score = (
            sum(c.score for c in check_results) / len(check_results) if check_results else 0.0
        )
        all_passed = passed_count == len(check_results)

        # Persist results
        qa_result = QAResult(
            build_id=data.build_id,
            overall_score=round(overall_score, 3),
            passed=all_passed,
            checks_passed=passed_count,
            checks_total=len(check_results),
        )
        self.db.add(qa_result)
        await self.db.commit()
        await self.db.refresh(qa_result)

        for cr in check_results:
            qa_check = QACheck(
                qa_result_id=qa_result.id,
                check_name=cr.check_name,
                passed=cr.passed,
                score=cr.score,
                details=cr.details,
                severity=cr.severity,
            )
            self.db.add(qa_check)
        await self.db.commit()

        logger.info(
            "qa_engine.run_completed",
            build_id=data.build_id,
            score=overall_score,
            passed=all_passed,
            checks_passed=passed_count,
        )

        return QAResultResponse(
            id=qa_result.id,
            build_id=qa_result.build_id,
            overall_score=qa_result.overall_score,
            passed=qa_result.passed,
            checks_passed=qa_result.checks_passed,
            checks_total=qa_result.checks_total,
            checks=check_results,
            created_at=qa_result.created_at,
        )
