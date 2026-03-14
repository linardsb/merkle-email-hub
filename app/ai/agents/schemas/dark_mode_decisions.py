"""Structured decisions for the Dark Mode agent.

The LLM returns color remapping decisions; deterministic code merges
them into the EmailBuildPlan's DesignTokens.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DarkColorOverride:
    """Single dark-mode color override."""

    token_name: str
    light_value: str
    dark_value: str
    reasoning: str


@dataclass(frozen=True)
class DarkModeDecisions:
    """Dark Mode agent structured output — color remapping decisions only."""

    color_overrides: tuple[DarkColorOverride, ...] = ()
    background_dark: str = "#1a1a2e"
    text_dark: str = "#e0e0e0"
    enable_prefers_color_scheme: bool = True
    confidence: float = 0.0
    reasoning: str = ""
