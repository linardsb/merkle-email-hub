"""Audience-aware competitive feasibility analysis.

Cross-references competitor capabilities with ontology CSS support
to answer: "Is this technique feasible for the client's audience
AND do competitors support it?"
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.knowledge.ontology.competitors import (
    CompetitorCapability,
    HubCapability,
    load_competitors,
)
from app.knowledge.ontology.registry import OntologyRegistry, load_ontology
from app.knowledge.ontology.types import SupportLevel

logger = get_logger(__name__)


@dataclass(frozen=True)
class CapabilityFeasibility:
    """Feasibility of a single capability for a target audience."""

    capability_id: str
    capability_name: str
    category: str
    # Audience feasibility (from ontology CSS support)
    audience_coverage: float  # 0.0-1.0 proportion of target clients that can render
    blocking_clients: tuple[str, ...]  # Client names that can't render this technique
    # Competitive landscape
    hub_supports: bool
    hub_agent: str  # Agent that provides this capability (empty if none)
    competitor_names: tuple[str, ...]  # Competitors offering this capability
    is_hub_exclusive: bool  # True if no competitor supports it
    is_competitor_exclusive: bool  # True if Hub doesn't support it


@dataclass(frozen=True)
class CompetitiveReport:
    """Full competitive feasibility report scoped to an audience."""

    audience_client_ids: tuple[str, ...]
    feasibilities: tuple[CapabilityFeasibility, ...]
    hub_advantages: tuple[CapabilityFeasibility, ...]  # Hub-only + >=30% coverage
    gaps: tuple[CapabilityFeasibility, ...]  # Competitor-only capabilities
    opportunities: tuple[CapabilityFeasibility, ...]  # Hub-supported + >=50% coverage


# Capability ID → list of ontology CSS property IDs required.
# Verified against css_properties.yaml exact IDs.
_CAPABILITY_CSS_DEPS: dict[str, list[str]] = {
    "css_checkbox_interactivity": [],  # No combinator/checked entries in ontology — assume full
    "css_animations": ["animation", "keyframes", "transition"],
    "dark_mode_preview": ["media_prefers_color_scheme", "color_scheme"],
    "responsive_email": ["media_min_width"],
    "progressive_enhancement": ["display_flex", "display_grid"],
}

# AMP is not CSS-based — has a known fixed set of supporting clients
_AMP_SUPPORTING_CLIENTS = frozenset(
    {
        "gmail_web",
        "gmail_android",
        "gmail_ios",
        "yahoo_web",
        "yahoo_android",
        "yahoo_ios",
    }
)


def compute_audience_coverage(
    capability_id: str,
    client_ids: tuple[str, ...],
    onto: OntologyRegistry,
) -> tuple[float, tuple[str, ...]]:
    """Compute what proportion of target clients can render a capability.

    Returns (coverage_ratio, blocking_client_names).
    Coverage = (clients supporting ALL required CSS) / (total target clients).
    """
    if not client_ids:
        return 0.0, ()

    # AMP: known client list, not CSS-based
    if capability_id == "amp_email":
        supported = sum(1 for cid in client_ids if cid in _AMP_SUPPORTING_CLIENTS)
        blocking = tuple(
            client.name
            for cid in client_ids
            if cid not in _AMP_SUPPORTING_CLIENTS
            for client in [onto.get_client(cid)]
            if client is not None
        )
        return supported / len(client_ids), blocking

    css_deps = _CAPABILITY_CSS_DEPS.get(capability_id)
    if css_deps is None or not css_deps:
        # No CSS dependency mapping — assume full coverage (conservative)
        return 1.0, ()

    blocking_names: list[str] = []
    supported_count = 0
    resolved_count = 0
    for cid in client_ids:
        client = onto.get_client(cid)
        if not client:
            continue
        resolved_count += 1
        all_supported = all(
            onto.get_support(prop_id, cid) != SupportLevel.NONE for prop_id in css_deps
        )
        if all_supported:
            supported_count += 1
        else:
            blocking_names.append(client.name)

    if resolved_count == 0:
        return 0.0, ()
    return supported_count / len(client_ids), tuple(blocking_names)


def build_competitive_report(
    client_ids: tuple[str, ...],
    competitor_id: str | None = None,
) -> CompetitiveReport:
    """Build full audience-scoped competitive feasibility report.

    Args:
        client_ids: Target audience email client IDs.
        competitor_id: Optional — focus on a single competitor.
    """
    registry = load_competitors()
    onto = load_ontology()

    hub_cap_ids = {h.id for h in registry.hub_capabilities}
    hub_cap_map: dict[str, HubCapability] = {h.id: h for h in registry.hub_capabilities}

    # Union of all capability IDs from both sides
    all_cap_ids = sorted(
        {c.id for c in registry.capabilities} | {h.id for h in registry.hub_capabilities}
    )

    feasibilities: list[CapabilityFeasibility] = []
    for cap_id in all_cap_ids:
        cap: CompetitorCapability | None = registry.get_capability(cap_id)
        hub_cap = hub_cap_map.get(cap_id)

        name = cap.name if cap else (hub_cap.name if hub_cap else cap_id)
        category = cap.category if cap else (hub_cap.category if hub_cap else "")

        coverage, blocking = compute_audience_coverage(cap_id, client_ids, onto)

        supporters = registry.competitors_supporting(cap_id)
        if competitor_id:
            supporters = [s for s in supporters if s.id == competitor_id]

        all_supporters = registry.competitors_supporting(cap_id)

        feasibilities.append(
            CapabilityFeasibility(
                capability_id=cap_id,
                capability_name=name,
                category=category,
                audience_coverage=coverage,
                blocking_clients=blocking,
                hub_supports=cap_id in hub_cap_ids,
                hub_agent=hub_cap.agent if hub_cap else "",
                competitor_names=tuple(s.name for s in supporters),
                is_hub_exclusive=cap_id in hub_cap_ids and len(all_supporters) == 0,
                is_competitor_exclusive=cap_id not in hub_cap_ids and len(all_supporters) > 0,
            )
        )

    result = tuple(feasibilities)
    report = CompetitiveReport(
        audience_client_ids=client_ids,
        feasibilities=result,
        hub_advantages=tuple(
            f for f in result if f.is_hub_exclusive and f.audience_coverage >= 0.3
        ),
        gaps=tuple(f for f in result if f.is_competitor_exclusive),
        opportunities=tuple(
            f
            for f in result
            if f.hub_supports and f.audience_coverage >= 0.5 and not f.is_competitor_exclusive
        ),
    )

    logger.info(
        "competitive_feasibility.report_built",
        client_count=len(client_ids),
        capabilities=len(result),
        hub_advantages=len(report.hub_advantages),
        gaps=len(report.gaps),
    )
    return report


def format_feasibility_context(
    client_ids: tuple[str, ...],
    technique: str,
) -> str:
    """Format audience-aware competitive context for agent prompt injection.

    Combines competitive landscape with audience feasibility.
    Used by LAYER 10 in the blueprint engine.
    """
    registry = load_competitors()
    onto = load_ontology()

    from app.ai.blueprints.competitor_context import _match_capabilities

    relevant_caps = _match_capabilities(technique.lower(), registry)

    if not relevant_caps and not client_ids:
        return ""

    lines = ["--- COMPETITIVE LANDSCAPE (audience-aware) ---"]

    if relevant_caps:
        lines.append("\nTechnique competitive analysis:")
        for cap in relevant_caps:
            supporters = registry.competitors_supporting(cap.id)
            coverage, blocking = compute_audience_coverage(cap.id, client_ids, onto)

            supporter_str = (
                ", ".join(s.name for s in supporters) if supporters else "no tracked competitor"
            )
            lines.append(f"\n**{cap.name}**")
            lines.append(f"  Competitors offering this: {supporter_str}")
            if client_ids:
                lines.append(f"  Audience coverage: {coverage:.0%} of target clients")
                if blocking:
                    lines.append(f"  Blocked by: {', '.join(blocking)}")

    # Hub exclusive advantages relevant to technique
    hub_unique = registry.hub_unique_capabilities()
    technique_lower = technique.lower()
    relevant_unique = [
        h
        for h in hub_unique
        if any(
            kw in h.name.lower() or kw in h.description.lower()
            for kw in technique_lower.split()[:5]
        )
    ]
    if relevant_unique:
        lines.append("\nHub-exclusive capabilities (no competitor offers):")
        for h in relevant_unique:
            if client_ids:
                cov, _ = compute_audience_coverage(h.id, client_ids, onto)
                lines.append(f"  - {h.name} (audience coverage: {cov:.0%})")
            else:
                lines.append(f"  - {h.name}")

    if len(lines) == 1:
        return ""

    lines.append("")
    return "\n".join(lines)
