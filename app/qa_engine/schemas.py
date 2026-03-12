"""Pydantic schemas for QA engine."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class QARunRequest(BaseModel):
    """Request to run QA checks on compiled HTML."""

    build_id: int | None = Field(None, description="Email build ID to validate")
    template_version_id: int | None = Field(
        None, description="Template version ID for audit linkage"
    )
    project_id: int | None = Field(
        None, description="Project ID for per-project QA config (optional)"
    )
    html: str = Field(
        ..., min_length=1, max_length=500_000, description="Compiled HTML to validate"
    )


class QACheckResult(BaseModel):
    """Result of a single QA check."""

    check_name: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    details: str | None = None
    severity: str = "warning"


class QAOverrideRequest(BaseModel):
    """Request to override failing QA checks."""

    justification: str = Field(
        ..., min_length=10, max_length=2000, description="Reason for overriding failing checks"
    )
    checks_overridden: list[str] = Field(..., min_length=1, description="Check names to override")


class QAOverrideResponse(BaseModel):
    """Response for a QA override."""

    id: int
    qa_result_id: int
    overridden_by_id: int
    justification: str
    checks_overridden: list[str]
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class QAResultResponse(BaseModel):
    """Full QA result with individual checks."""

    id: int
    build_id: int | None = None
    template_version_id: int | None = None
    overall_score: float
    passed: bool
    checks_passed: int
    checks_total: int
    checks: list[QACheckResult] = []
    override: QAOverrideResponse | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
