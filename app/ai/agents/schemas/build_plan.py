"""Structured output schema for the Scaffolder agent.

The LLM returns an EmailBuildPlan (JSON); deterministic code assembles HTML.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    """Visual design decisions."""

    primary_color: str
    secondary_color: str
    background_color: str
    text_color: str
    font_family: str
    heading_font_family: str
    border_radius: str = "4px"
    button_style: Literal["filled", "outlined", "text"] = "filled"


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
    personalisation_platform: str | None = None
    personalisation_slots: tuple[str, ...] = ()
    confidence: float = 0.0
    reasoning: str = ""
