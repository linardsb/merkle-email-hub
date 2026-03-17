"""Audience-aware Outlook migration planner (Phase 19.2).

Combines dependency analysis with audience data to produce phased
migration plans. Pure CPU — no LLM, no database.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.qa_engine.outlook_analyzer.types import (
    DEPENDENCY_RISK,
    AudienceProfile,
    MigrationPhase,
    MigrationPlan,
    OutlookAnalysis,
    OutlookDependency,
)

logger = get_logger(__name__)

# Default audience profile when no ESP data is available (industry average)
DEFAULT_AUDIENCE = AudienceProfile(
    client_distribution={
        "gmail_web": 0.28,
        "apple_mail": 0.22,
        "outlook_2016": 0.08,
        "outlook_2019": 0.07,
        "outlook_2021": 0.04,
        "new_outlook": 0.06,
        "outlook_web": 0.05,
        "yahoo_mail": 0.05,
        "gmail_android": 0.08,
        "apple_mail_ios": 0.07,
    }
)

# Thresholds for safe_when classification
SAFE_NOW_THRESHOLD = 0.02  # < 2% on Word engine → safe to remove now
MODERATE_THRESHOLD = 0.10  # < 10% → moderate, can plan removal
CONSERVATIVE_THRESHOLD = 0.25  # < 25% → conservative, phase carefully


class MigrationPlanner:
    """Produces phased migration plans based on audience composition."""

    def plan(
        self,
        analysis: OutlookAnalysis,
        audience: AudienceProfile | None = None,
    ) -> MigrationPlan:
        """Generate a phased migration plan.

        Args:
            analysis: Output from OutlookDependencyDetector.analyze()
            audience: Client distribution. Uses industry averages if None.

        Returns:
            MigrationPlan with ordered phases from safest to riskiest.
        """
        profile = audience or DEFAULT_AUDIENCE
        word_share = profile.word_engine_share

        if not analysis.dependencies:
            return MigrationPlan(
                phases=[],
                total_dependencies=0,
                total_removable=0,
                total_savings_bytes=0,
                word_engine_audience=word_share,
                risk_assessment="No Outlook Word-engine dependencies detected.",
                recommendation="aggressive",
            )

        # Group dependencies by type
        by_type: dict[str, list[OutlookDependency]] = {}
        for dep in analysis.dependencies:
            by_type.setdefault(dep.type, []).append(dep)

        # Build phases ordered by risk (low → medium → high)
        phases = self._build_phases(by_type, word_share)

        # Determine overall recommendation
        recommendation = self._determine_recommendation(word_share)
        risk_assessment = self._build_risk_assessment(word_share, analysis, recommendation)

        total_savings = sum(p.estimated_byte_savings for p in phases)

        plan = MigrationPlan(
            phases=phases,
            total_dependencies=analysis.total_count,
            total_removable=analysis.removable_count,
            total_savings_bytes=total_savings,
            word_engine_audience=word_share,
            risk_assessment=risk_assessment,
            recommendation=recommendation,
        )

        logger.info(
            "qa_engine.migration_plan_created",
            phases=len(phases),
            total_dependencies=analysis.total_count,
            word_engine_share=round(word_share, 4),
            recommendation=recommendation,
        )

        return plan

    def _build_phases(
        self,
        by_type: dict[str, list[OutlookDependency]],
        word_share: float,
    ) -> list[MigrationPhase]:
        """Build migration phases ordered by risk level (safest first)."""
        raw_phases: list[MigrationPhase] = []

        for dep_type, deps in by_type.items():
            risk = DEPENDENCY_RISK.get(dep_type, "medium")
            safe_when = self._classify_safe_when(risk, word_share)
            byte_savings = sum(len(d.code_snippet.encode()) for d in deps)

            phase = MigrationPhase(
                name=self._phase_name(dep_type),
                description=self._phase_description(dep_type, len(deps)),
                dependencies_to_remove=deps,
                dependency_types=[dep_type],
                audience_impact=word_share,
                safe_when=safe_when,
                risk_level=risk,
                estimated_byte_savings=byte_savings,
            )
            raw_phases.append(phase)

        # Sort: low risk first, then medium, then high
        risk_order = {"low": 0, "medium": 1, "high": 2}
        raw_phases.sort(key=lambda p: risk_order.get(p.risk_level, 1))

        return raw_phases

    def _classify_safe_when(self, risk: str, word_share: float) -> str:
        """Determine when it's safe to remove dependencies of this risk level."""
        if risk == "low":
            if word_share < MODERATE_THRESHOLD:
                return "now"
            return "when word_engine < 10%"

        if risk == "medium":
            if word_share < SAFE_NOW_THRESHOLD:
                return "now"
            if word_share < MODERATE_THRESHOLD:
                return "when word_engine < 5%"
            return "when word_engine < 10%"

        # high risk
        if word_share < SAFE_NOW_THRESHOLD:
            return "now"
        if word_share < MODERATE_THRESHOLD:
            return "when word_engine < 5%"
        if word_share < CONSERVATIVE_THRESHOLD:
            return "when word_engine < 10%"
        return "after word_engine sunset"

    def _determine_recommendation(self, word_share: float) -> str:
        """Determine overall migration aggressiveness."""
        if word_share < SAFE_NOW_THRESHOLD:
            return "aggressive"
        if word_share < MODERATE_THRESHOLD:
            return "moderate"
        return "conservative"

    def _phase_name(self, dep_type: str) -> str:
        """Human-readable phase name for a dependency type."""
        names = {
            "vml_shape": "Remove VML Shapes",
            "ghost_table": "Remove Ghost Tables",
            "mso_conditional": "Remove MSO Conditionals",
            "mso_css": "Remove MSO CSS Properties",
            "dpi_image": "Normalize DPI Images",
            "external_class": "Remove ExternalClass Rules",
            "word_wrap_hack": "Modernize Word-Wrap Hacks",
        }
        return names.get(dep_type, f"Remove {dep_type}")

    def _phase_description(self, dep_type: str, count: int) -> str:
        """Human-readable description for a migration phase."""
        descriptions = {
            "vml_shape": f"Remove {count} VML shape element(s) used for Outlook buttons and graphics. Replace with CSS-based alternatives.",
            "ghost_table": f"Remove {count} ghost table wrapper(s) used for Outlook layout. Modern Outlook supports CSS layout natively.",
            "mso_conditional": f"Remove {count} MSO conditional comment block(s). These conditionals target Word-engine rendering.",
            "mso_css": f"Remove {count} mso-* CSS property declaration(s). These are Word-engine-specific styling hints.",
            "dpi_image": f"Normalize {count} image(s) with mismatched HTML/CSS dimensions used for Outlook DPI workarounds.",
            "external_class": f"Remove {count} .ExternalClass CSS rule(s) targeting Outlook.com rendering quirks.",
            "word_wrap_hack": f"Modernize {count} word-wrap/word-break hack(s) with standard overflow-wrap.",
        }
        return descriptions.get(dep_type, f"Address {count} {dep_type} instance(s).")

    def _build_risk_assessment(
        self,
        word_share: float,
        analysis: OutlookAnalysis,
        recommendation: str,
    ) -> str:
        """Build human-readable risk assessment summary."""
        pct = round(word_share * 100, 1)

        if recommendation == "aggressive":
            return (
                f"Only {pct}% of your audience uses Word-engine Outlook. "
                f"All {analysis.total_count} dependencies can be safely removed now "
                f"with minimal risk, saving ~{analysis.byte_savings} bytes."
            )

        if recommendation == "moderate":
            return (
                f"{pct}% of your audience uses Word-engine Outlook. "
                f"Low-risk dependencies (DPI images, ExternalClass, word-wrap) can be removed now. "
                f"High-risk dependencies (VML, ghost tables, MSO conditionals) should wait "
                f"until Word-engine share drops below 5%."
            )

        return (
            f"{pct}% of your audience uses Word-engine Outlook — a significant share. "
            f"Only the lowest-risk dependencies should be removed now. "
            f"VML shapes, ghost tables, and MSO conditionals must be preserved "
            f"to avoid layout breakage for {pct}% of recipients."
        )
