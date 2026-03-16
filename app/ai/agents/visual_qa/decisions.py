"""Structured decisions for the Visual QA agent.

The VLM returns defect analysis decisions; no HTML mutation — advisory only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedDefect:
    """Single rendering defect from VLM analysis."""

    region: str
    description: str
    severity: str  # critical | warning | info
    affected_clients: tuple[str, ...]
    suggested_fix: str
    css_property: str  # empty string if not CSS-related


@dataclass(frozen=True)
class VisualQADecisions:
    """Visual QA agent structured output — rendering defect analysis."""

    defects: tuple[DetectedDefect, ...] = ()
    overall_rendering_score: float = 1.0  # 1.0 = perfect, 0.0 = broken
    critical_clients: tuple[str, ...] = ()  # clients with critical issues
    summary: str = ""
    confidence: float = 0.0
    auto_fixable: bool = False
