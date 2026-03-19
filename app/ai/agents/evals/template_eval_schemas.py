"""Schemas for template-sourced eval case management."""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class EvalCaseType(enum.StrEnum):
    SELECTION_POSITIVE = "selection_positive"
    SELECTION_NEGATIVE = "selection_negative"
    SLOT_FILL = "slot_fill"
    ASSEMBLY_GOLDEN = "assembly_golden"
    QA_PASSTHROUGH = "qa_passthrough"


class TemplateEvalCase(BaseModel):
    """A single eval case generated from an uploaded template."""

    id: str
    case_type: EvalCaseType
    template_name: str
    source: str  # "uploaded:{template_name}"
    dimensions: dict[str, str] = Field(default_factory=dict)
    brief: str = ""
    expected_template: str = ""
    expected_checks: dict[str, bool] = Field(default_factory=dict)
    slot_fills: dict[str, str] = Field(default_factory=dict)
    created_at: str = ""


class TemplateEvalTemplateSummary(BaseModel):
    """Per-template case count summary."""

    template_name: str
    case_count: int
    case_types: list[str]
    generated_at: str


class TemplateEvalCaseSet(BaseModel):
    """All eval cases for one uploaded template."""

    template_name: str
    cases: list[TemplateEvalCase]
    generated_at: str


class TemplateEvalSummary(BaseModel):
    """Summary of all template-sourced eval cases."""

    total_templates: int
    total_cases: int
    templates: list[TemplateEvalTemplateSummary]
