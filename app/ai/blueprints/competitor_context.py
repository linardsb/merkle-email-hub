"""Competitive intelligence context for blueprint agents."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.knowledge.ontology.competitors import CompetitorCapability, CompetitorRegistry

from app.core.logging import get_logger

logger = get_logger(__name__)

# Trigger patterns — fetch competitive context when technique/competitor mentioned
_TRIGGER_PATTERNS = (
    re.compile(r"\b(?:compet\w*|stripo|parcel|chamaileon|dyspatch|knak)\b", re.IGNORECASE),
    re.compile(r"\b(?:unique|differentiat\w*|advantage|gap|versus|vs\.?)\b", re.IGNORECASE),
    re.compile(r"\b(?:alternative|rival|market|landscape|comparison)\b", re.IGNORECASE),
)


def should_fetch_competitive_context(brief: str) -> bool:
    """Check whether the brief warrants competitive context injection."""
    return any(p.search(brief) for p in _TRIGGER_PATTERNS)


def build_competitive_context(technique: str) -> str:
    """Build competitive context text for an Innovation Agent prompt.

    Queries the competitor registry for relevant competitive intelligence
    based on the technique being evaluated.

    Args:
        technique: The technique request text.

    Returns:
        Formatted competitive context block, or empty string if no data.
    """
    try:
        from app.knowledge.ontology.competitors import load_competitors
    except ImportError:
        return ""

    try:
        registry = load_competitors()
    except FileNotFoundError:
        return ""

    if not registry.competitors:
        return ""

    lines = ["--- COMPETITIVE LANDSCAPE ---"]

    # Find capabilities matching the technique keywords
    technique_lower = technique.lower()
    relevant_caps = _match_capabilities(technique_lower, registry)

    if relevant_caps:
        lines.append("\nRelevant competitor capabilities:")
        for cap in relevant_caps:
            supporters = registry.competitors_supporting(cap.id)
            if supporters:
                names = ", ".join(s.name for s in supporters)
                lines.append(f"- {cap.name}: supported by {names}")
            else:
                lines.append(f"- {cap.name}: NOT supported by any tracked competitor")

    # Hub unique advantages
    hub_unique = registry.hub_unique_capabilities()
    if hub_unique:
        # Filter to relevant ones
        relevant_unique = [
            h
            for h in hub_unique
            if any(
                kw in h.name.lower() or kw in h.description.lower()
                for kw in technique_lower.split()[:5]
            )
        ]
        if relevant_unique:
            lines.append("\nHub-exclusive capabilities (no competitor offers these):")
            for h in relevant_unique:
                lines.append(f"- {h.name}: {h.description}")

    # If we only have the header, no useful data found
    if len(lines) == 1:
        return ""

    lines.append("")
    return "\n".join(lines)


def format_full_competitive_report() -> str:
    """Generate a full competitive landscape report.

    Used for standalone capability reports, not for agent prompt injection.
    """
    try:
        from app.knowledge.ontology.competitors import load_competitors
    except ImportError:
        return "Competitive intelligence data not available."

    try:
        registry = load_competitors()
    except FileNotFoundError:
        return "Competitive intelligence data not available."

    lines = ["# Competitive Intelligence Report\n"]

    for comp in registry.competitors:
        lines.append(f"## {comp.name}")
        lines.append(
            f"Category: {comp.category} | Market: {comp.target_market} | Pricing: {comp.pricing_tier}\n"
        )

        hub_only, shared, comp_only = registry.hub_vs_competitor(comp.id)
        lines.append(f"- Shared capabilities: {len(shared)}")
        lines.append(f"- Hub advantages: {len(hub_only)}")
        lines.append(f"- {comp.name} advantages: {len(comp_only)}")

        if hub_only:
            lines.append(f"\n**Hub advantages over {comp.name}:**")
            for cap_id in hub_only:
                hub_cap = registry.get_hub_capability(cap_id)
                lines.append(f"  - {hub_cap.name if hub_cap else cap_id}")

        if comp_only:
            lines.append(f"\n**{comp.name} has (Hub does not):**")
            for cap_id in comp_only:
                cap = registry.get_capability(cap_id)
                lines.append(f"  - {cap.name if cap else cap_id}")

        lines.append("")

    return "\n".join(lines)


def build_audience_competitive_context(
    technique: str,
    client_ids: tuple[str, ...],
) -> str:
    """Build competitive context enhanced with audience feasibility.

    Delegates to competitive_feasibility module when audience data available.
    Falls back to standard competitive context otherwise.
    """
    if client_ids:
        from app.knowledge.ontology.competitive_feasibility import (
            format_feasibility_context,
        )

        return format_feasibility_context(client_ids=client_ids, technique=technique)
    return build_competitive_context(technique)


def _match_capabilities(
    technique_lower: str,
    registry: CompetitorRegistry,
) -> list[CompetitorCapability]:
    """Match technique text to relevant capabilities via keyword overlap."""
    from app.knowledge.ontology.competitors import CompetitorCapability as _Cap
    from app.knowledge.ontology.competitors import CompetitorRegistry as _Reg

    if not isinstance(registry, _Reg):
        return []

    # Keyword → capability ID mapping
    keyword_map: dict[str, list[str]] = {
        "amp": ["amp_email"],
        "checkbox": ["css_checkbox_interactivity"],
        "tab": ["css_checkbox_interactivity"],
        "accordion": ["css_checkbox_interactivity"],
        "carousel": ["css_checkbox_interactivity", "amp_email"],
        "animation": ["css_animations"],
        "transition": ["css_animations"],
        "keyframe": ["css_animations"],
        "dark mode": ["dark_mode_preview"],
        "dark_mode": ["dark_mode_preview"],
        "accessibility": ["accessibility_checking"],
        "wcag": ["accessibility_checking"],
        "rendering": ["cross_client_rendering"],
        "outlook": ["outlook_specific_fixes"],
        "mso": ["outlook_specific_fixes"],
        "vml": ["outlook_specific_fixes"],
        "braze": ["esp_integration_braze"],
        "sfmc": ["esp_integration_sfmc"],
        "personalisation": ["personalisation_syntax"],
        "personalization": ["personalisation_syntax"],
        "liquid": ["personalisation_syntax"],
        "responsive": ["responsive_email"],
        "ai": ["ai_code_generation", "ai_content_generation"],
        "figma": ["figma_integration"],
        "collaboration": ["collaboration_realtime"],
        "approval": ["approval_workflow"],
    }

    matched_ids: set[str] = set()
    for keyword, cap_ids in keyword_map.items():
        # Use word boundary for short keywords to avoid false matches (e.g. "ai" in "email")
        if len(keyword) <= 3:
            if re.search(rf"\b{re.escape(keyword)}\b", technique_lower):
                matched_ids.update(cap_ids)
        elif keyword in technique_lower:
            matched_ids.update(cap_ids)

    result: list[_Cap] = []
    for cap_id in sorted(matched_ids):
        cap = registry.get_capability(cap_id)
        if cap:
            result.append(cap)

    return result
