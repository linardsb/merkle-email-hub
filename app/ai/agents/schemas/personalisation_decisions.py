"""Structured decisions for the Personalisation agent.

The LLM returns ESP variable placement decisions;
deterministic code merges them into the EmailBuildPlan's SlotFills.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VariablePlacement:
    """Single personalisation variable injection."""

    slot_id: str
    variable_name: str
    fallback_value: str
    syntax: str


@dataclass(frozen=True)
class PersonalisationDecisions:
    """Personalisation agent structured output."""

    esp_platform: str = ""
    variables: tuple[VariablePlacement, ...] = ()
    conditional_blocks: tuple[str, ...] = ()
    confidence: float = 0.0
    reasoning: str = ""
