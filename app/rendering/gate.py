"""Pre-send rendering gate — evaluates rendering confidence against thresholds."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.gate_schemas import (
    ClientGateResult,
    GateEvaluateRequest,
    GateMode,
    GateResult,
    GateVerdict,
    RenderingGateConfigSchema,
)
from app.rendering.local.confidence import RenderingConfidence, RenderingConfidenceScorer
from app.rendering.local.profiles import CLIENT_PROFILES

logger = get_logger(__name__)

CLIENT_TIERS: dict[str, str] = {
    "gmail_web": "tier_1",
    "outlook_desktop": "tier_1",
    "apple_mail": "tier_1",
    "outlook_2019": "tier_1",
    "yahoo_web": "tier_2",
    "yahoo_mobile": "tier_2",
    "samsung_mail": "tier_2",
    "thunderbird": "tier_2",
    "android_gmail": "tier_3",
    "outlook_web": "tier_3",
    "outlook_dark": "tier_3",
    "samsung_mail_dark": "tier_3",
    "android_gmail_dark": "tier_3",
    "mobile_ios": "tier_3",
}

DEFAULT_GATE_CLIENTS: list[str] = [
    "gmail_web",
    "outlook_desktop",
    "apple_mail",
    "yahoo_web",
    "samsung_mail",
    "thunderbird",
    "android_gmail",
    "outlook_web",
]


class RenderingSendGate:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._scorer = RenderingConfidenceScorer()

    async def evaluate(self, request: GateEvaluateRequest) -> GateResult:
        """Evaluate rendering confidence against gate thresholds."""
        config = await self.resolve_config(request.project_id)

        if config.mode == GateMode.skip:
            return GateResult(
                passed=True,
                verdict=GateVerdict.PASS,
                mode=config.mode,
                evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
            )

        # Determine target clients (request override > project config > defaults)
        clients = request.target_clients or config.target_clients or DEFAULT_GATE_CLIENTS
        thresholds = config.tier_thresholds

        client_results: list[ClientGateResult] = []
        blocking: list[str] = []
        all_recommendations: list[str] = []

        for client_id in clients:
            profile = CLIENT_PROFILES.get(client_id)
            if not profile:
                continue

            # Score using existing confidence system
            confidence = self._scorer.score(request.html, profile)
            tier = CLIENT_TIERS.get(client_id, "tier_3")
            threshold = thresholds.get(tier, 60.0)
            passed = confidence.score >= threshold

            # Build blocking reasons from confidence breakdown
            reasons = self._blocking_reasons(confidence, client_id, threshold)
            remediation = self._remediation(confidence, client_id)

            if not passed:
                blocking.append(client_id)

            all_recommendations.extend(confidence.recommendations)

            client_results.append(
                ClientGateResult(
                    client_name=client_id,
                    confidence_score=confidence.score,
                    threshold=threshold,
                    passed=passed,
                    tier=tier,
                    blocking_reasons=reasons if not passed else [],
                    remediation=remediation if not passed else [],
                )
            )

        # Determine verdict
        has_blocking = len(blocking) > 0
        if not has_blocking:
            verdict = GateVerdict.PASS
        elif config.mode == GateMode.warn:
            verdict = GateVerdict.WARN
        else:
            verdict = GateVerdict.BLOCK

        gate_passed = verdict != GateVerdict.BLOCK

        # Deduplicate recommendations
        seen: set[str] = set()
        unique_recs: list[str] = []
        for r in all_recommendations:
            if r not in seen:
                seen.add(r)
                unique_recs.append(r)

        return GateResult(
            passed=gate_passed,
            verdict=verdict,
            mode=config.mode,
            client_results=client_results,
            blocking_clients=blocking,
            recommendations=unique_recs[:10],
            evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )

    async def resolve_config(self, project_id: int | None) -> RenderingGateConfigSchema:
        settings = get_settings()
        defaults = RenderingGateConfigSchema(
            mode=GateMode(settings.rendering.gate_mode),
            tier_thresholds={
                "tier_1": settings.rendering.gate_tier1_threshold,
                "tier_2": settings.rendering.gate_tier2_threshold,
                "tier_3": settings.rendering.gate_tier3_threshold,
            },
        )
        if project_id is None:
            return defaults

        from app.projects.models import Project

        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project or not project.rendering_gate_config:
            return defaults

        try:
            return RenderingGateConfigSchema.model_validate(project.rendering_gate_config)
        except Exception:
            logger.warning("gate.invalid_project_config", project_id=project_id)
            return defaults

    def _blocking_reasons(
        self,
        confidence: RenderingConfidence,
        client_id: str,
        threshold: float,
    ) -> list[str]:
        """Generate human-readable blocking reasons from confidence breakdown."""
        reasons: list[str] = []
        breakdown = confidence.breakdown

        if breakdown.css_compatibility < 0.7:
            reasons.append(f"Some CSS properties unsupported by {client_id}")

        if breakdown.emulator_coverage < 0.5:
            reasons.append(f"Limited emulator coverage for {client_id}")

        if breakdown.calibration_accuracy < 0.6:
            reasons.append("Low calibration accuracy — external validation recommended")

        if breakdown.layout_complexity > 0.5:
            reasons.append("Complex layout reduces emulator accuracy")

        if breakdown.known_blind_spots:
            spots = ", ".join(breakdown.known_blind_spots[:3])
            reasons.append(f"Known blind spots: {spots}")

        if not reasons:
            reasons.append(f"Confidence {confidence.score:.0f}% below threshold {threshold:.0f}%")

        return reasons

    def _remediation(self, confidence: RenderingConfidence, client_id: str) -> list[str]:
        """Generate actionable remediation suggestions."""
        suggestions: list[str] = []
        breakdown = confidence.breakdown

        if breakdown.css_compatibility < 0.7 and "outlook" in client_id:
            suggestions.append("Add MSO conditional with table-based fallback")

        if breakdown.layout_complexity > 0.3 and "outlook" in client_id:
            suggestions.append("Replace flexbox with table layout for Outlook clients")

        if confidence.score < 70:
            suggestions.append(f"Validate with Litmus or Email on Acid for {client_id}")

        return suggestions
