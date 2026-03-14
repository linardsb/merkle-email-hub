"""Structured decisions for the Code Reviewer agent.

The LLM reviews the EmailBuildPlan for quality issues
instead of reviewing raw HTML.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PlanQualityIssue:
    """Single quality issue found in the EmailBuildPlan."""

    field: str
    severity: Literal["critical", "warning", "suggestion"]
    issue: str
    recommendation: str


@dataclass(frozen=True)
class CodeReviewDecisions:
    """Code Reviewer structured output — plan quality assessment."""

    issues: tuple[PlanQualityIssue, ...] = ()
    template_appropriate: bool = True
    slot_quality_score: float = 1.0
    design_token_coherent: bool = True
    personalisation_complete: bool = True
    confidence: float = 0.0
    reasoning: str = ""
