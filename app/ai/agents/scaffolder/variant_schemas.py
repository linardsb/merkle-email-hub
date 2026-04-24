"""Multi-variant campaign assembly schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.ai.agents.schemas.build_plan import EmailBuildPlan, SlotFill
from app.qa_engine.schemas import QACheckResult

# The 6 built-in content strategies
StrategyName = Literal[
    "urgency_driven",
    "benefit_focused",
    "social_proof",
    "curiosity_gap",
    "personalization_heavy",
    "minimal",
]

STRATEGY_DESCRIPTIONS: dict[StrategyName, str] = {
    "urgency_driven": "Time-limited language, scarcity cues, action-oriented CTAs with countdown urgency",
    "benefit_focused": "Outcome-oriented copy, feature-to-benefit transformation, longer explanatory content",
    "social_proof": "Testimonials, user counts, trust badges, case study references",
    "curiosity_gap": "Question-based subject lines, partial reveals, 'find out' CTAs",
    "personalization_heavy": "Maximum use of personalisation slots, dynamic content blocks, conditional sections",
    "minimal": "Short copy, single CTA, clean layout, mobile-optimized for quick scanning",
}


@dataclass(frozen=True)
class VariantPlan:
    """A single variant's content strategy and slot overrides."""

    variant_id: str  # "A", "B", "C", ...
    strategy_name: StrategyName
    hypothesis: str
    slot_fills: tuple[SlotFill, ...]
    subject_line: str
    preheader: str
    predicted_differentiator: str


@dataclass(frozen=True)
class VariantResult:
    """Assembled + QA'd variant."""

    variant_id: str
    strategy_name: StrategyName
    hypothesis: str
    predicted_differentiator: str
    subject_line: str
    preheader: str
    html: str
    build_plan: EmailBuildPlan
    qa_results: list[QACheckResult] = field(default_factory=list[QACheckResult])
    qa_passed: bool = False


@dataclass(frozen=True)
class SlotDifference:
    """A single slot that differs between variants."""

    slot_id: str
    variants: dict[str, str]  # variant_id -> content snippet (first 80 chars)


@dataclass(frozen=True)
class ComparisonMatrix:
    """Side-by-side differences across all variants."""

    subject_lines: dict[str, str]  # variant_id -> subject line
    preheaders: dict[str, str]
    slot_differences: tuple[SlotDifference, ...]
    strategy_summary: dict[str, str]  # variant_id -> strategy description


@dataclass(frozen=True)
class CampaignVariantSet:
    """Complete variant set: base plan + N assembled variants + comparison."""

    brief: str
    base_template: str
    base_design_tokens: dict[str, object]
    variants: tuple[VariantResult, ...]
    comparison: ComparisonMatrix
