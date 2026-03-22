"""Pydantic schemas for the export QA gate."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.rendering.gate_schemas import GateResult


class QAGateMode(StrEnum):
    enforce = "enforce"
    warn = "warn"
    skip = "skip"


class QAGateVerdict(StrEnum):
    PASS = "pass"  # noqa: S105
    WARN = "warn"
    BLOCK = "block"


class QACheckSummary(BaseModel):
    """Summary of a single QA check result for the export gate."""

    check_name: str
    passed: bool
    score: float  # 0.0-1.0
    severity: str  # "blocking" | "warning"
    details: str | None = None


class QAGateResult(BaseModel):
    """Result of the export QA gate evaluation."""

    passed: bool
    verdict: QAGateVerdict
    mode: QAGateMode
    blocking_failures: list[QACheckSummary] = []
    warnings: list[QACheckSummary] = []
    checks_run: int = 0
    evaluated_at: str  # ISO datetime


class ExportQAConfig(BaseModel):
    """Per-project export QA gate configuration."""

    mode: QAGateMode = QAGateMode.warn
    blocking_checks: list[str] = Field(
        default_factory=lambda: [
            "html_validation",
            "link_validation",
            "spam_score",
            "personalisation_syntax",
            "liquid_syntax",
        ]
    )
    warning_checks: list[str] = Field(
        default_factory=lambda: [
            "accessibility",
            "dark_mode",
            "image_optimization",
            "file_size",
        ]
    )
    ignored_checks: list[str] = Field(default_factory=list)


class ExportPreCheckRequest(BaseModel):
    """Request for a dry-run export pre-check."""

    html: str = Field(..., min_length=1, max_length=500_000)
    project_id: int | None = None
    target_clients: list[str] | None = None


class ExportPreCheckResponse(BaseModel):
    """Combined QA + rendering gate pre-check result."""

    qa: QAGateResult
    rendering: GateResult | None = None
    can_export: bool
