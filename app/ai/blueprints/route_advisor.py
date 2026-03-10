"""Route advisor — audience-aware node relevance for blueprint execution."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.blueprints.audience_context import AudienceProfile

from app.core.logging import get_logger
from app.knowledge.ontology.types import ClientEngine

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class RoutingAction(StrEnum):
    """What the route advisor recommends for a node."""

    SKIP = "skip"
    PRIORITISE = "prioritise"


@dataclass(frozen=True)
class RoutingDecision:
    """A single routing recommendation for one node."""

    node_name: str
    action: RoutingAction
    reason: str


@dataclass(frozen=True)
class RoutingPlan:
    """Pre-execution routing plan for a blueprint run."""

    decisions: tuple[RoutingDecision, ...]
    skip_nodes: frozenset[str]
    prioritise_nodes: frozenset[str]
    force_full: bool = False


# ---------------------------------------------------------------------------
# Content detection helpers (pure, no I/O)
# ---------------------------------------------------------------------------

_PERSONALISATION_PATTERNS = re.compile(
    r"\{\{|{%|%%\[|AMPscript|ContentBlockByName|Lookup\(", re.IGNORECASE
)

_ACCESSIBILITY_KEYWORDS = re.compile(
    r"wcag|accessibility|a11y|screen.?reader|alt.?text|contrast", re.IGNORECASE
)


def _has_personalisation_syntax(html: str, brief: str) -> bool:
    """Check if template contains Liquid/AMPscript/dynamic content markers."""
    return bool(_PERSONALISATION_PATTERNS.search(html) or _PERSONALISATION_PATTERNS.search(brief))


def _mentions_accessibility(brief: str) -> bool:
    """Check if brief explicitly requests accessibility work."""
    return bool(_ACCESSIBILITY_KEYWORDS.search(brief))


# ---------------------------------------------------------------------------
# Routing plan builder
# ---------------------------------------------------------------------------

# Deterministic nodes are never skipped or reordered.
_DETERMINISTIC_NODES = frozenset({"qa_gate", "recovery_router", "maizzle_build", "export"})


def build_routing_plan(
    node_names: list[str],
    audience_profile: AudienceProfile | None,
    html: str,
    brief: str,
    force_full: bool = False,
) -> RoutingPlan:
    """Build a pre-execution routing plan based on audience + content analysis.

    Rules (applied in order):
    1. Audience-based: nodes without matching audience are SKIP
    2. Content-based: nodes whose domain isn't present in HTML/brief are SKIP
    3. Priority: nodes whose domain IS heavily present get PRIORITISE
    4. Deterministic nodes (qa_gate, recovery_router, etc.) are never skipped
    """
    decisions: list[RoutingDecision] = []

    has_personalisation = _has_personalisation_syntax(html, brief)
    mentions_a11y = _mentions_accessibility(brief)

    for name in node_names:
        if name in _DETERMINISTIC_NODES:
            continue

        # Rule 1: Audience-based skip
        if not is_node_relevant(name, audience_profile):
            decisions.append(
                RoutingDecision(
                    node_name=name,
                    action=RoutingAction.SKIP,
                    reason=_audience_skip_reason(name),
                )
            )
            continue

        # Rule 2+3: Content-based skip/prioritise
        decision = _content_based_decision(
            name,
            audience_profile,
            html,
            has_personalisation=has_personalisation,
            mentions_a11y=mentions_a11y,
        )
        if decision is not None:
            decisions.append(decision)

    skip_nodes = frozenset(d.node_name for d in decisions if d.action == RoutingAction.SKIP)
    prioritise_nodes = frozenset(
        d.node_name for d in decisions if d.action == RoutingAction.PRIORITISE
    )

    logger.info(
        "route_advisor.plan_built",
        total_nodes=len(node_names),
        skip=len(skip_nodes),
        prioritise=len(prioritise_nodes),
        force_full=force_full,
    )

    return RoutingPlan(
        decisions=tuple(decisions),
        skip_nodes=skip_nodes,
        prioritise_nodes=prioritise_nodes,
        force_full=force_full,
    )


def _audience_skip_reason(name: str) -> str:
    """Generate human-readable reason for audience-based skip."""
    if name == "outlook_fixer":
        return "No Microsoft Word-engine clients in target audience"
    if name == "dark_mode":
        return "No personas require dark mode support"
    return f"Node '{name}' not relevant for target audience"


def _content_based_decision(
    name: str,
    audience_profile: AudienceProfile | None,
    html: str,
    *,
    has_personalisation: bool,
    mentions_a11y: bool,
) -> RoutingDecision | None:
    """Content-based routing decision for a node. Returns None if no decision."""
    if name == "personalisation" and not has_personalisation:
        return RoutingDecision(
            node_name=name,
            action=RoutingAction.SKIP,
            reason="No Liquid/AMPscript/dynamic content in template or brief",
        )

    if name == "accessibility" and mentions_a11y:
        return RoutingDecision(
            node_name=name,
            action=RoutingAction.PRIORITISE,
            reason="Brief explicitly requests accessibility work",
        )

    if name == "code_reviewer" and len(html.encode("utf-8")) > 50_000:
        return RoutingDecision(
            node_name=name,
            action=RoutingAction.PRIORITISE,
            reason="HTML exceeds 50KB — code review can optimize before Gmail clip threshold",
        )

    if name == "dark_mode" and audience_profile is not None:
        engines = {c.engine for c in audience_profile.clients}
        if len(engines) > 1 and ClientEngine.WORD in engines:
            return RoutingDecision(
                node_name=name,
                action=RoutingAction.PRIORITISE,
                reason="Mixed rendering engines including Word — dark mode requires careful handling",
            )

    return None


def is_node_relevant(
    node_name: str,
    audience_profile: AudienceProfile | None,
) -> bool:
    """Determine whether a blueprint node is relevant for the target audience.

    Returns True (relevant) when:
    - No audience profile is set (backward compatible — skip nothing)
    - The node has no audience-dependent relevance rule
    - The audience matches the node's relevance criteria

    Returns False (skip) when the audience data proves the node unnecessary.
    """
    if audience_profile is None:
        return True

    rule = _RELEVANCE_RULES.get(node_name)
    if rule is None:
        return True  # No rule → always relevant

    return rule(audience_profile)


def _has_word_engine_client(profile: AudienceProfile) -> bool:
    """True if any target client uses the Word rendering engine (Outlook desktop)."""
    return any(c.engine == ClientEngine.WORD for c in profile.clients)


def _needs_dark_mode(profile: AudienceProfile) -> bool:
    """True if any persona requires dark mode support."""
    return profile.dark_mode_required


# Maps node names to relevance check functions.
# Nodes NOT listed here are always relevant.
_RELEVANCE_RULES: dict[str, Callable[[AudienceProfile], bool]] = {
    "outlook_fixer": _has_word_engine_client,
    "dark_mode": _needs_dark_mode,
}
