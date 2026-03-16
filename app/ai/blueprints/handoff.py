"""Typed handoff payloads for structured inter-agent communication."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScaffolderHandoff:
    """Structured output metadata from the Scaffolder agent."""

    template_name: str = ""
    slots_filled: tuple[str, ...] = ()
    design_token_source: str = ""  # "default" | "design_system" | "brief"
    colors_applied: dict[str, str] = field(default_factory=lambda: dict[str, str]())  # role -> hex
    locked_roles: tuple[str, ...] = ()
    dark_mode_strategy: str = ""


@dataclass(frozen=True)
class DarkModeHandoff:
    """Structured output metadata from the Dark Mode agent."""

    overrides_count: int = 0
    strategy: str = ""  # "auto" | "custom"
    background_dark: str = ""
    text_dark: str = ""
    prefers_color_scheme: bool = False


@dataclass(frozen=True)
class AccessibilityHandoff:
    """Structured output metadata from the Accessibility agent."""

    issues_fixed: int = 0
    skills_loaded: tuple[str, ...] = ()
    alt_text_warnings: tuple[str, ...] = ()
    contrast_issues: int = 0
    aria_additions: int = 0


@dataclass(frozen=True)
class PersonalisationHandoff:
    """Structured output metadata from the Personalisation agent."""

    platform: str = ""  # ESP platform name
    merge_tags_added: int = 0
    conditional_blocks: int = 0
    fallback_values: dict[str, str] = field(default_factory=lambda: dict[str, str]())


@dataclass(frozen=True)
class OutlookFixerHandoff:
    """Structured output metadata from the Outlook Fixer agent."""

    issues_found: int = 0
    mso_conditionals_added: int = 0
    severity_counts: dict[str, int] = field(
        default_factory=lambda: dict[str, int]()
    )  # severity -> count


@dataclass(frozen=True)
class CodeReviewHandoff:
    """Structured output metadata from the Code Reviewer agent."""

    quality_score: float = 0.0
    issues_found: int = 0
    categories: tuple[str, ...] = ()  # e.g. ("html_validity", "css_compat")


@dataclass(frozen=True)
class KnowledgeHandoff:
    """Structured output metadata from the Knowledge agent."""

    sources_consulted: int = 0
    facts_injected: int = 0
    relevance_score: float = 0.0


@dataclass(frozen=True)
class InnovationHandoff:
    """Structured output metadata from the Innovation agent."""

    technique: str = ""
    feasibility_score: float = 0.0
    client_compat: tuple[str, ...] = ()  # compatible client IDs


# Union type for typed dispatch
HandoffPayload = (
    ScaffolderHandoff
    | DarkModeHandoff
    | AccessibilityHandoff
    | PersonalisationHandoff
    | OutlookFixerHandoff
    | CodeReviewHandoff
    | KnowledgeHandoff
    | InnovationHandoff
)

# Registry for runtime type lookup by agent name
HANDOFF_PAYLOAD_TYPES: dict[str, type[HandoffPayload]] = {
    "scaffolder": ScaffolderHandoff,
    "dark_mode": DarkModeHandoff,
    "accessibility": AccessibilityHandoff,
    "personalisation": PersonalisationHandoff,
    "outlook_fixer": OutlookFixerHandoff,
    "code_reviewer": CodeReviewHandoff,
    "knowledge": KnowledgeHandoff,
    "innovation": InnovationHandoff,
}


def format_upstream_constraints(handoff: object) -> str:
    """Format typed handoff payload as concise context string for downstream agent prompts.

    Returns empty string if handoff has no typed_payload.
    """
    from app.ai.blueprints.protocols import AgentHandoff

    if not isinstance(handoff, AgentHandoff) or handoff.typed_payload is None:
        return ""

    payload = handoff.typed_payload
    lines: list[str] = [f"## Upstream context from {handoff.agent_name}"]

    if isinstance(payload, ScaffolderHandoff):
        lines.append(f"- Template: {payload.template_name}")
        if payload.slots_filled:
            lines.append(f"- Slots filled: {', '.join(payload.slots_filled)}")
        if payload.colors_applied:
            color_list = ", ".join(f"{k}={v}" for k, v in payload.colors_applied.items())
            lines.append(f"- Colors: {color_list}")
        if payload.locked_roles:
            lines.append(f"- Locked roles (do not change): {', '.join(payload.locked_roles)}")
        if payload.dark_mode_strategy:
            lines.append(f"- Dark mode strategy: {payload.dark_mode_strategy}")
    elif isinstance(payload, DarkModeHandoff):
        lines.append(f"- Strategy: {payload.strategy}")
        lines.append(f"- Overrides: {payload.overrides_count}")
        if payload.prefers_color_scheme:
            lines.append("- Uses prefers-color-scheme media query")
    elif isinstance(payload, AccessibilityHandoff):
        lines.append(f"- Issues fixed: {payload.issues_fixed}")
        if payload.alt_text_warnings:
            lines.append(f"- Alt text warnings: {', '.join(payload.alt_text_warnings[:3])}")
    elif isinstance(payload, PersonalisationHandoff):
        lines.append(f"- Platform: {payload.platform}")
        lines.append(f"- Merge tags: {payload.merge_tags_added}")
    elif isinstance(payload, OutlookFixerHandoff):
        lines.append(f"- Issues found: {payload.issues_found}")
        lines.append(f"- MSO conditionals added: {payload.mso_conditionals_added}")
    elif isinstance(payload, CodeReviewHandoff):
        lines.append(f"- Quality score: {payload.quality_score:.2f}")
        lines.append(f"- Issues: {payload.issues_found}")
    elif isinstance(payload, KnowledgeHandoff):
        lines.append(f"- Sources: {payload.sources_consulted}")
        lines.append(f"- Facts injected: {payload.facts_injected}")
    elif isinstance(payload, InnovationHandoff):
        lines.append(f"- Technique: {payload.technique}")
        lines.append(f"- Feasibility: {payload.feasibility_score:.2f}")

    # Add uncertainties from parent handoff
    if handoff.uncertainties:
        lines.append(f"- Uncertainties: {', '.join(handoff.uncertainties)}")

    return "\n".join(lines)
