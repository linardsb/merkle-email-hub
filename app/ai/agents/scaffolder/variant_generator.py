"""Multi-variant content strategy selection and generation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.ai.agents.scaffolder.variant_schemas import (
    STRATEGY_DESCRIPTIONS,
    ComparisonMatrix,
    SlotDifference,
    StrategyName,
    VariantPlan,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def select_strategies(
    brief: str,
    count: int,
    call_json: Callable[..., Awaitable[dict[str, Any]]],
) -> list[tuple[StrategyName, str, str]]:
    """Ask LLM to pick the top N strategies for this brief.

    Returns list of (strategy_name, hypothesis, predicted_differentiator).
    """
    strategies_desc = "\n".join(f"- {name}: {desc}" for name, desc in STRATEGY_DESCRIPTIONS.items())
    system = (
        "You are an email marketing strategist. Given a campaign brief, select the "
        f"top {count} content strategies that would create the most meaningful A/B test.\n\n"
        f"Available strategies:\n{strategies_desc}\n\n"
        "Return JSON with:\n"
        "- strategies: array of {strategy_name: string, hypothesis: string, predicted_differentiator: string}\n\n"
        "Rules:\n"
        "- Each hypothesis must be testable (e.g., 'Urgency-driven CTA increases CTR for sale campaigns')\n"
        "- Each predicted_differentiator must describe a measurable difference\n"
        "- Pick strategies that create MEANINGFUL contrast, not minor wording tweaks\n"
        "- Order by expected impact (most impactful first)\n\n"
        "Respond ONLY with valid JSON."
    )
    parsed = await call_json(system, f"Campaign brief:\n{brief}")

    result: list[tuple[StrategyName, str, str]] = []
    for s in parsed.get("strategies", [])[:count]:
        name = s.get("strategy_name", "")
        if name in STRATEGY_DESCRIPTIONS:
            result.append(
                (
                    name,
                    str(s.get("hypothesis", "")),
                    str(s.get("predicted_differentiator", "")),
                )
            )
    return result


def build_strategy_prompt_modifier(strategy: StrategyName) -> str:
    """Return a prompt modifier that steers the content pass toward a strategy."""
    modifiers: dict[StrategyName, str] = {
        "urgency_driven": (
            "CONTENT STRATEGY: Urgency-driven. Use time-limited language, scarcity cues "
            "(e.g., 'Only X left', 'Ends tonight'), and action-oriented CTAs with strong verbs. "
            "Subject line should create time pressure. Keep copy punchy and direct."
        ),
        "benefit_focused": (
            "CONTENT STRATEGY: Benefit-focused. Transform every feature into a clear outcome/benefit. "
            "Use longer explanatory copy that paints the 'after' picture. "
            "Subject line should promise a specific result. CTA should reference the benefit."
        ),
        "social_proof": (
            "CONTENT STRATEGY: Social proof. Reference testimonials, user counts, ratings, "
            "trust badges, or case studies. Include concrete numbers where possible. "
            "Subject line should imply community validation. CTA should leverage FOMO."
        ),
        "curiosity_gap": (
            "CONTENT STRATEGY: Curiosity gap. Use question-based subject lines, partial reveals, "
            "and 'find out' CTAs. Body copy should tease the value without fully revealing it. "
            "Create information asymmetry that drives clicks."
        ),
        "personalization_heavy": (
            "CONTENT STRATEGY: Personalization-heavy. Maximize use of personalisation slots — "
            "use first_name in greeting and CTA, reference past behavior, add conditional content. "
            "Set is_personalisable=true on as many slots as possible. "
            "Subject line must include a personalisation token."
        ),
        "minimal": (
            "CONTENT STRATEGY: Minimal. Extremely concise copy — 1-2 sentences per section max. "
            "Single CTA, no secondary actions. Short subject line (under 40 chars). "
            "Optimized for quick mobile scanning. Remove any non-essential content."
        ),
    }
    return modifiers[strategy]


def build_comparison_matrix(
    variants: list[VariantPlan],
) -> ComparisonMatrix:
    """Build a side-by-side comparison of all variants."""
    subject_lines = {v.variant_id: v.subject_line for v in variants}
    preheaders = {v.variant_id: v.preheader for v in variants}
    strategy_summary = {
        v.variant_id: f"{v.strategy_name}: {v.predicted_differentiator}" for v in variants
    }

    # Find slots that differ across variants
    all_slot_ids: set[str] = set()
    for v in variants:
        all_slot_ids.update(sf.slot_id for sf in v.slot_fills)

    differences: list[SlotDifference] = []
    for slot_id in sorted(all_slot_ids):
        slot_contents: dict[str, str] = {}
        for v in variants:
            fill = next((sf for sf in v.slot_fills if sf.slot_id == slot_id), None)
            if fill:
                slot_contents[v.variant_id] = fill.content[:80]
        # Only include if content actually differs
        unique_values = set(slot_contents.values())
        if len(unique_values) > 1:
            differences.append(SlotDifference(slot_id=slot_id, variants=slot_contents))

    return ComparisonMatrix(
        subject_lines=subject_lines,
        preheaders=preheaders,
        slot_differences=tuple(differences),
        strategy_summary=strategy_summary,
    )
