"""Structured output schema for the Content agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContentAlternative:
    """A single content alternative."""

    text: str
    tone: str
    char_count: int
    word_count: int
    reasoning: str


@dataclass(frozen=True)
class ContentPlan:
    """Structured content generation results."""

    operation: str
    alternatives: tuple[ContentAlternative, ...]
    selected_index: int = 0
