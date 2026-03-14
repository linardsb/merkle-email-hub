"""Structured output schema for the Personalisation agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonalisationTag:
    """A single personalisation tag to inject."""

    slot_id: str
    tag_syntax: str
    fallback: str
    is_conditional: bool


@dataclass(frozen=True)
class ConditionalBlock:
    """A conditional content block."""

    condition: str
    true_content: str
    false_content: str
    platform_syntax: str


@dataclass(frozen=True)
class PersonalisationPlan:
    """Structured plan for personalisation injection."""

    platform: str
    tags: tuple[PersonalisationTag, ...]
    conditional_blocks: tuple[ConditionalBlock, ...] = ()
    reasoning: str = ""
