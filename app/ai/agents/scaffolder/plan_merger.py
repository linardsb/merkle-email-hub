"""Merge downstream agent decisions into an EmailBuildPlan.

Each merge function takes an immutable EmailBuildPlan and a decision
schema, returning a new plan with the decisions applied.  Because
EmailBuildPlan is a frozen dataclass, every merge produces a new
instance via dataclasses.replace().
"""

from __future__ import annotations

import re
from dataclasses import replace
from html import escape

from app.ai.agents.schemas.accessibility_decisions import (
    AccessibilityDecisions,
)
from app.ai.agents.schemas.build_plan import (
    EmailBuildPlan,
    SlotFill,
)
from app.ai.agents.schemas.content_decisions import ContentDecisions
from app.ai.agents.schemas.dark_mode_decisions import DarkModeDecisions
from app.ai.agents.schemas.personalisation_decisions import (
    PersonalisationDecisions,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def merge_dark_mode(
    plan: EmailBuildPlan,
    decisions: DarkModeDecisions,
) -> EmailBuildPlan:
    """Apply dark mode color overrides to the plan's design tokens.

    Adds dark_* fields to the plan metadata and sets the
    dark_mode_strategy based on the agent's decisions.
    """
    # Build a mapping of token_name → dark_value from overrides
    override_map: dict[str, str] = {o.token_name: o.dark_value for o in decisions.color_overrides}

    # Apply overrides to design tokens where the token name matches a field
    tokens = plan.design_tokens
    token_updates: dict[str, str] = {}
    for field_name in (
        "primary_color",
        "secondary_color",
        "background_color",
        "text_color",
    ):
        if field_name in override_map:
            token_updates[field_name] = override_map[field_name]

    if token_updates:
        tokens = replace(
            tokens,
            primary_color=token_updates.get("primary_color", tokens.primary_color),
            secondary_color=token_updates.get("secondary_color", tokens.secondary_color),
            background_color=token_updates.get("background_color", tokens.background_color),
            text_color=token_updates.get("text_color", tokens.text_color),
        )

    strategy = "custom" if decisions.color_overrides else plan.dark_mode_strategy

    logger.info(
        "plan_merger.dark_mode_merged",
        overrides=len(decisions.color_overrides),
        strategy=strategy,
    )

    return replace(
        plan,
        design_tokens=tokens,
        dark_mode_strategy=strategy,
    )


def merge_accessibility(
    plan: EmailBuildPlan,
    decisions: AccessibilityDecisions,
) -> EmailBuildPlan:
    """Apply alt text and heading hierarchy decisions to plan slots.

    Updates slot_fills with alt text for image slots and applies
    heading level fixes where the slot_id matches.
    """
    # Build lookup of alt text decisions by slot_id
    alt_map: dict[str, str] = {}
    for alt in decisions.alt_texts:
        if alt.is_decorative:
            alt_map[alt.slot_id] = ""
        else:
            alt_map[alt.slot_id] = alt.alt_text

    # Build lookup of heading fixes by slot_id
    heading_map: dict[str, int] = {h.slot_id: h.recommended_level for h in decisions.heading_fixes}

    if not alt_map and not heading_map:
        return plan

    # Apply to matching slot fills
    updated_fills: list[SlotFill] = []
    for sf in plan.slot_fills:
        if sf.slot_id in alt_map:
            # Inject alt attribute into the content
            alt_value = alt_map[sf.slot_id]
            content = _inject_alt_text(sf.content, alt_value)
            sf = replace(sf, content=content)
        if sf.slot_id in heading_map:
            level = heading_map[sf.slot_id]
            content = _fix_heading_level(sf.content, level)
            sf = replace(sf, content=content)
        updated_fills.append(sf)

    logger.info(
        "plan_merger.accessibility_merged",
        alt_texts=len(alt_map),
        heading_fixes=len(heading_map),
    )

    return replace(plan, slot_fills=tuple(updated_fills))


def merge_personalisation(
    plan: EmailBuildPlan,
    decisions: PersonalisationDecisions,
) -> EmailBuildPlan:
    """Inject personalisation variables into plan slot content.

    Wraps personalisable content with ESP-specific variable syntax.
    """
    if not decisions.variables:
        return plan

    # Build lookup by slot_id
    var_map: dict[str, list[tuple[str, str]]] = {}
    for v in decisions.variables:
        var_map.setdefault(v.slot_id, []).append((v.variable_name, v.syntax))

    updated_fills: list[SlotFill] = []
    for sf in plan.slot_fills:
        if sf.slot_id in var_map:
            content = sf.content
            for _var_name, syntax in var_map[sf.slot_id]:
                # The syntax contains the full rendered variable with fallback
                # e.g. '{{first_name|default:"there"}}'
                # Replace empty slot with variable, or append to existing content
                content = syntax if not content else f"{content} {syntax}"
            sf = replace(sf, content=content, is_personalisable=True)
        updated_fills.append(sf)

    personalisation_slot_ids = tuple(v.slot_id for v in decisions.variables)

    logger.info(
        "plan_merger.personalisation_merged",
        variables=len(decisions.variables),
        platform=decisions.esp_platform,
    )

    return replace(
        plan,
        slot_fills=tuple(updated_fills),
        personalisation_platform=decisions.esp_platform or plan.personalisation_platform,
        personalisation_slots=personalisation_slot_ids,
    )


def merge_content(
    plan: EmailBuildPlan,
    decisions: ContentDecisions,
) -> EmailBuildPlan:
    """Apply content refinements to plan slots, subject, preheader."""
    # Build slot refinement lookup
    refinement_map: dict[str, str] = {
        r.slot_id: r.refined_content for r in decisions.slot_refinements
    }

    updated_fills: list[SlotFill] = list(plan.slot_fills)
    if refinement_map:
        updated_fills = []
        for sf in plan.slot_fills:
            if sf.slot_id in refinement_map:
                sf = replace(sf, content=refinement_map[sf.slot_id])
            updated_fills.append(sf)

    subject = decisions.subject_line or plan.subject_line
    preheader = decisions.preheader or plan.preheader_text

    logger.info(
        "plan_merger.content_merged",
        refinements=len(refinement_map),
        subject_updated=bool(decisions.subject_line),
        preheader_updated=bool(decisions.preheader),
    )

    return replace(
        plan,
        slot_fills=tuple(updated_fills),
        subject_line=subject,
        preheader_text=preheader,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inject_alt_text(content: str, alt_text: str) -> str:
    """Inject or replace alt attribute in img tags within slot content."""

    if "<img" not in content:
        return content

    # Escape to prevent attribute injection (defense-in-depth; sanitize_html_xss runs later)
    safe_alt = escape(alt_text, quote=True)

    # Replace existing alt or add alt attribute
    if 'alt="' in content or "alt='" in content:
        return re.sub(r'alt=["\'][^"\']*["\']', f'alt="{safe_alt}"', content)

    return content.replace("<img", f'<img alt="{safe_alt}"', 1)


def _fix_heading_level(content: str, target_level: int) -> str:
    """Replace heading tags with the target level."""

    pattern = re.compile(r"<(/?)[hH]([1-6])(\b[^>]*>)")
    return pattern.sub(
        lambda m: f"<{m.group(1)}h{target_level}{m.group(3)}",
        content,
    )
