"""Export QA gate — evaluates QA checks and classifies as blocking/warning."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.qa_gate_schemas import (
    ExportQAConfig,
    QACheckSummary,
    QAGateMode,
    QAGateResult,
    QAGateVerdict,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.qa_engine.schemas import QARunRequest

logger = get_logger(__name__)


class ExportQAGate:
    """Evaluates QA checks against export gate rules."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def evaluate(self, html: str, project_id: int | None = None) -> QAGateResult:
        """Run QA checks and classify results against gate config."""
        config = await self._resolve_config(project_id)

        now = datetime.datetime.now(datetime.UTC).isoformat()

        if config.mode == QAGateMode.skip:
            return QAGateResult(
                passed=True,
                verdict=QAGateVerdict.PASS,
                mode=config.mode,
                evaluated_at=now,
            )

        from app.qa_engine.service import QAEngineService

        qa_service = QAEngineService(self.db)
        result = await qa_service.run_checks(QARunRequest(html=html, project_id=project_id))  # pyright: ignore[reportCallIssue]

        blocking_failures: list[QACheckSummary] = []
        warnings: list[QACheckSummary] = []

        for check in result.checks:
            if check.check_name in config.ignored_checks:
                continue

            is_blocking = check.check_name in config.blocking_checks
            is_warning = check.check_name in config.warning_checks

            if not is_blocking and not is_warning:
                continue

            summary = QACheckSummary(
                check_name=check.check_name,
                passed=check.passed,
                score=check.score,
                severity="blocking" if is_blocking else "warning",
                details=check.details,
            )

            if not check.passed and is_blocking:
                blocking_failures.append(summary)
            elif not check.passed and is_warning:
                warnings.append(summary)

        has_blocking = len(blocking_failures) > 0
        if not has_blocking:
            verdict = QAGateVerdict.PASS
        elif config.mode == QAGateMode.warn:
            verdict = QAGateVerdict.WARN
        else:
            verdict = QAGateVerdict.BLOCK

        return QAGateResult(
            passed=verdict != QAGateVerdict.BLOCK,
            verdict=verdict,
            mode=config.mode,
            blocking_failures=blocking_failures,
            warnings=warnings,
            checks_run=len(result.checks),
            evaluated_at=now,
        )

    async def _resolve_config(self, project_id: int | None) -> ExportQAConfig:
        """Resolve gate config: settings defaults → project override."""
        settings = get_settings()
        defaults = ExportQAConfig(
            mode=QAGateMode(settings.export.qa_gate_mode),
            blocking_checks=settings.export.qa_blocking_checks,
            warning_checks=settings.export.qa_warning_checks,
        )

        if project_id is None:
            return defaults

        from app.projects.models import Project

        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project or not project.export_qa_config:
            return defaults

        try:
            return ExportQAConfig.model_validate(project.export_qa_config)
        except Exception:
            logger.warning("qa_gate.invalid_project_config", project_id=project_id)
            return defaults
