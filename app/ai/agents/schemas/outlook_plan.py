"""Structured output schema for the Outlook Fixer agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MSOFix:
    """A single MSO/Outlook fix to apply."""

    issue_type: Literal[
        "missing_conditional",
        "unbalanced_pair",
        "missing_namespace",
        "vml_background",
        "table_width",
        "ghost_table",
        "css_fallback",
    ]
    location_hint: str
    fix_description: str
    fix_html: str | None = None


@dataclass(frozen=True)
class OutlookFixPlan:
    """Structured plan for Outlook compatibility fixes."""

    fixes: tuple[MSOFix, ...]
    add_namespaces: tuple[str, ...]
    add_ghost_tables: bool
    reasoning: str = ""
