"""Structured output schema for the Code Reviewer agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CodeReviewFinding:
    """A single code review finding."""

    rule_name: str
    severity: Literal["error", "warning", "info"]
    responsible_agent: str
    current_value: str
    fix_value: str
    selector: str
    is_actionable: bool


@dataclass(frozen=True)
class CodeReviewPlan:
    """Structured code review results."""

    findings: tuple[CodeReviewFinding, ...]
    summary: str
    overall_quality: Literal["excellent", "good", "needs_work", "poor"]
