from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class PatternCategory(StrEnum):
    OUTLOOK_FIX = "outlook_fix"
    DARK_MODE = "dark_mode"
    RESPONSIVE = "responsive"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"
    ESP_SYNTAX = "esp_syntax"
    PROGRESSIVE_ENHANCEMENT = "progressive_enhancement"


class AmendmentStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    REVERTED = "reverted"


# Agent name → list of target skill files (relative to app/ai/agents/{agent}/)
AGENT_SKILL_TARGETS: dict[str, list[str]] = {
    "outlook_fixer": [
        "skills/vml_reference.md",
        "skills/mso_conditionals.md",
        "skills/mso_bug_fixes.md",
    ],
    "scaffolder": [
        "skills/client_compatibility.md",
        "skills/table_layouts.md",
        "skills/mso_vml_quick_ref.md",
    ],
    "dark_mode": [
        "skills/color_remapping.md",
        "skills/client_behavior.md",
        "skills/outlook_dark_mode.md",
    ],
    "accessibility": [
        "skills/wcag_email_mapping.md",
        "skills/alt_text_guidelines.md",
    ],
    "personalisation": [
        "skills/braze_liquid.md",
        "skills/sfmc_ampscript.md",
        "skills/fallback_patterns.md",
    ],
    "code_reviewer": [
        "skills/css_client_support.md",
        "skills/file_size_optimization.md",
        "skills/anti_patterns.md",
    ],
    "content": ["skills/spam_triggers.md"],
    "innovation": ["skills/css_checkbox_hacks.md", "skills/css_animations.md"],
}


class SkillPattern(BaseModel):
    """A detected HTML pattern that maps to agent skill knowledge."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    pattern_name: str  # e.g., "vml_bulletproof_button"
    category: PatternCategory
    description: str  # Human-readable explanation
    html_example: str  # Minimal HTML snippet demonstrating the pattern
    confidence: float = Field(ge=0.0, le=1.0)
    source_template_id: str | None = None
    applicable_agents: list[str]  # ["outlook_fixer", "scaffolder"]


class SkillAmendment(BaseModel):
    """A proposed addition to an agent skill file."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_name: str
    skill_file: str  # Relative path: "skills/vml_reference.md"
    section: str  # Section heading to append under
    content: str  # Markdown content to append
    confidence: float = Field(ge=0.0, le=1.0)
    source_pattern_id: str
    source_template_id: str | None = None
    status: AmendmentStatus = AmendmentStatus.PENDING


class AmendmentReport(BaseModel):
    """Result of applying or dry-running amendments."""

    total: int
    applied: int
    skipped_duplicate: int
    skipped_conflict: int
    skipped_low_confidence: int
    diffs: list[dict[str, Any]]  # [{file, before_lines, after_lines, diff_preview}]


# --- API Request/Response Schemas ---


class AmendmentListResponse(BaseModel):
    amendments: list[SkillAmendment]
    total: int


class AmendmentActionRequest(BaseModel):
    reason: str = ""


class BatchAmendmentAction(BaseModel):
    id: str
    action: Literal["approve", "reject"]
    reason: str = ""


class BatchAmendmentRequest(BaseModel):
    actions: list[BatchAmendmentAction]


class BatchAmendmentResponse(BaseModel):
    processed: int
    errors: list[dict[str, str]]


class StatusResponse(BaseModel):
    status: str


class ExtractionResponse(BaseModel):
    patterns_found: int
    amendments_generated: int
    amendments: list[SkillAmendment]
