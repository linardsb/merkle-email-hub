"""Chaos Engine — applies degradation profiles and measures QA resilience."""

from __future__ import annotations

from app.core.logging import get_logger
from app.qa_engine.chaos.profiles import PROFILES, ChaosProfile
from app.qa_engine.check_config import load_defaults
from app.qa_engine.checks import ALL_CHECKS
from app.qa_engine.schemas import (
    ChaosFailure,
    ChaosProfileResult,
    ChaosTestResponse,
    QACheckResult,
)

logger = get_logger(__name__)


class ChaosEngine:
    """Applies chaos profiles to HTML and measures QA score degradation."""

    async def run_chaos_test(
        self,
        html: str,
        profiles: list[str] | None = None,
        default_profiles: list[str] | None = None,
    ) -> ChaosTestResponse:
        """Run chaos test with specified or default profiles.

        Args:
            html: The original HTML to test.
            profiles: Explicit profile names to run. None = use default_profiles.
            default_profiles: Fallback profile names from config.

        Returns:
            ChaosTestResponse with per-profile scores and resilience score.
        """
        profile_names = profiles or default_profiles or list(PROFILES.keys())

        # Validate profile names
        resolved: list[ChaosProfile] = []
        for name in profile_names:
            profile = PROFILES.get(name)
            if profile is None:
                logger.warning("chaos.unknown_profile", profile=name)
                continue
            resolved.append(profile)

        if not resolved:
            return ChaosTestResponse(
                original_score=0.0,
                resilience_score=0.0,
                profiles_tested=0,
                profile_results=[],
                critical_failures=[],
            )

        # Run QA on original HTML
        original_score, _ = await self._run_qa(html)

        # Run each profile
        profile_results: list[ChaosProfileResult] = []
        all_critical: list[ChaosFailure] = []
        total_degraded_score = 0.0

        for profile in resolved:
            degraded_html = profile.apply(html)
            score, check_results = await self._run_qa(degraded_html)

            # Identify failures (checks that went from pass to fail or score dropped)
            failures: list[ChaosFailure] = []
            for cr in check_results:
                if not cr.passed:
                    failure = ChaosFailure(
                        profile=profile.name,
                        check_name=cr.check_name,
                        severity=cr.severity,
                        description=cr.details or f"{cr.check_name} failed after {profile.name}",
                    )
                    failures.append(failure)
                    if cr.severity == "error":
                        all_critical.append(failure)

            checks_passed = sum(1 for cr in check_results if cr.passed)
            profile_results.append(
                ChaosProfileResult(
                    profile=profile.name,
                    description=profile.description,
                    score=score,
                    passed=all(cr.passed for cr in check_results),
                    checks_passed=checks_passed,
                    checks_total=len(check_results),
                    failures=failures,
                )
            )
            total_degraded_score += score

        # Resilience = avg degraded score / original score (capped at 1.0)
        if original_score > 0:
            resilience = min(
                1.0,
                round((total_degraded_score / len(resolved)) / original_score, 4),
            )
        else:
            resilience = 0.0

        logger.info(
            "chaos.test_completed",
            profiles_tested=len(resolved),
            original_score=original_score,
            resilience_score=resilience,
            critical_failures=len(all_critical),
        )

        return ChaosTestResponse(
            original_score=original_score,
            resilience_score=resilience,
            profiles_tested=len(resolved),
            profile_results=profile_results,
            critical_failures=all_critical,
        )

    async def _run_qa(self, html: str) -> tuple[float, list[QACheckResult]]:
        """Run all QA checks on HTML, return (overall_score, check_results)."""
        defaults = load_defaults()
        results: list[QACheckResult] = []

        for check in ALL_CHECKS:
            config = defaults.get_check_config(check.name)
            if config and not config.enabled:
                results.append(
                    QACheckResult(
                        check_name=check.name,
                        passed=True,
                        score=1.0,
                        severity="info",
                        details=None,
                    )
                )
                continue
            result = await check.run(html, config)
            results.append(result)

        overall = round(sum(r.score for r in results) / len(results), 4) if results else 0.0
        return overall, results
