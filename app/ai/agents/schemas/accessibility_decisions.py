"""Structured decisions for the Accessibility agent.

The LLM returns alt text and heading hierarchy decisions;
deterministic code merges them into the EmailBuildPlan's SlotFills.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AltTextDecision:
    """Alt text for a single image slot."""

    slot_id: str
    alt_text: str
    is_decorative: bool = False


@dataclass(frozen=True)
class HeadingDecision:
    """Heading hierarchy validation result."""

    slot_id: str
    current_level: int
    recommended_level: int
    reason: str


@dataclass(frozen=True)
class AccessibilityDecisions:
    """Accessibility agent structured output."""

    alt_texts: tuple[AltTextDecision, ...] = ()
    heading_fixes: tuple[HeadingDecision, ...] = ()
    lang_attribute: str = "en"
    confidence: float = 0.0
    reasoning: str = ""
