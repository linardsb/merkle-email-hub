"""Structured decisions for the Content agent.

The LLM returns slot text refinements;
deterministic code merges them into the EmailBuildPlan's SlotFills.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlotContentRefinement:
    """Content refinement for a single slot."""

    slot_id: str
    refined_content: str
    reasoning: str


@dataclass(frozen=True)
class ContentDecisions:
    """Content agent structured output — slot text refinements."""

    subject_line: str = ""
    preheader: str = ""
    slot_refinements: tuple[SlotContentRefinement, ...] = ()
    cta_text: str = ""
    confidence: float = 0.0
    reasoning: str = ""
