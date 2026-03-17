"""Rendering resilience check — runs chaos engine and measures degradation tolerance.

NOT registered in ALL_CHECKS to avoid recursion (chaos engine runs ALL_CHECKS internally).
Instead, QAEngineService runs this separately after the 11 core checks.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)


class RenderingResilienceCheck:
    """QA check that runs chaos profiles and fails if resilience is below threshold."""

    name = "rendering_resilience"

    def __init__(self, threshold: float = 0.7) -> None:
        self._threshold = threshold

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:  # noqa: ARG002
        """Run chaos engine with default profiles, return pass/fail based on resilience score."""
        from app.core.config import get_settings
        from app.qa_engine.chaos.engine import ChaosEngine

        settings = get_settings()
        engine = ChaosEngine()
        chaos_result = await engine.run_chaos_test(
            html=html,
            profiles=None,
            default_profiles=settings.qa_chaos.default_profiles,
        )

        resilience = chaos_result.resilience_score
        passed = resilience >= self._threshold
        critical_count = len(chaos_result.critical_failures)

        severity: str
        if resilience < 0.4:
            severity = "error"
        elif not passed:
            severity = "warning"
        else:
            severity = "info"

        profile_summaries = [
            f"{pr.profile}: {pr.score:.2f} ({pr.checks_passed}/{pr.checks_total})"
            for pr in chaos_result.profile_results
        ]
        details = (
            f"Resilience: {resilience:.2f} (threshold: {self._threshold:.2f}). "
            f"Profiles: {', '.join(profile_summaries)}"
        )
        if critical_count > 0:
            details += f". {critical_count} critical failure(s)"

        logger.info(
            "qa.resilience_check_completed",
            resilience_score=resilience,
            threshold=self._threshold,
            passed=passed,
            critical_failures=critical_count,
        )

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=round(resilience, 4),
            details=details,
            severity=severity,
        )
