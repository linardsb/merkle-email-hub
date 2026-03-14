"""Structured diagnostics for the Outlook Fixer agent.

In the template-first architecture golden templates handle MSO
compatibility.  The Outlook Fixer becomes diagnostic-only — it
reports issues but does NOT modify HTML.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MSOIssue:
    """Single MSO rendering issue detected."""

    issue_type: str
    severity: Literal["critical", "warning", "info"]
    location: str
    recommendation: str


@dataclass(frozen=True)
class OutlookDiagnostic:
    """Outlook Fixer agent diagnostic output — reports issues, does NOT fix HTML."""

    issues: tuple[MSOIssue, ...] = ()
    template_bug: bool = False
    composition_bug: bool = False
    overall_mso_safe: bool = True
    confidence: float = 0.0
    reasoning: str = ""
