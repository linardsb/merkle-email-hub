"""Structured output schema for the Scaffolder agent.

The LLM returns an EmailBuildPlan (JSON); deterministic code assembles HTML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class TemplateSelection:
    """LLM's template choice + reasoning."""

    template_name: str
    reasoning: str
    section_order: tuple[str, ...] = ()
    fallback_template: str | None = None


@dataclass(frozen=True)
class SlotFill:
    """Content for a single template slot."""

    slot_id: str
    content: str
    is_personalisable: bool = False


@dataclass(frozen=True)
class DesignTokens:
    """Visual design tokens — dynamic role-based map.

    When source is "design_system", all values come from the client's
    design system and locked_roles lists which roles the assembler
    must enforce (overriding any LLM deviation).

    When source is "llm_generated", the LLM produced these values
    and nothing is locked.
    """

    colors: dict[str, str] = field(default_factory=dict[str, str])
    fonts: dict[str, str] = field(default_factory=dict[str, str])
    font_sizes: dict[str, str] = field(default_factory=dict[str, str])
    spacing: dict[str, str] = field(default_factory=dict[str, str])
    button_style: Literal["filled", "outlined", "text"] = "filled"
    source: Literal["design_system", "llm_generated", "brief_extracted"] = "llm_generated"
    locked_roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class SectionDecision:
    """Per-section design decisions."""

    section_name: str
    background_color: str | None = None
    padding: str | None = None
    hidden: bool = False


@dataclass(frozen=True)
class EmailBuildPlan:
    """Complete structured plan for email assembly."""

    template: TemplateSelection
    slot_fills: tuple[SlotFill, ...]
    design_tokens: DesignTokens
    sections: tuple[SectionDecision, ...] = ()
    preheader_text: str = ""
    subject_line: str = ""
    dark_mode_strategy: Literal["auto", "custom", "none"] = "auto"
    tier_strategy: Literal["universal", "progressive"] = "universal"
    personalisation_platform: str | None = None
    personalisation_slots: tuple[str, ...] = ()
    confidence: float = 0.0
    reasoning: str = ""
