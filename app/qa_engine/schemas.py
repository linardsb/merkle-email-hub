"""Pydantic schemas for QA engine."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class QARunRequest(BaseModel):
    """Request to run QA checks on compiled HTML."""

    build_id: int = Field(..., description="Email build ID to validate")
    html: str = Field(..., min_length=1, description="Compiled HTML to validate")


class QACheckResult(BaseModel):
    """Result of a single QA check."""

    check_name: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    details: str | None = None
    severity: str = "warning"


class QAResultResponse(BaseModel):
    """Full QA result with individual checks."""

    id: int
    build_id: int
    overall_score: float
    passed: bool
    checks_passed: int
    checks_total: int
    checks: list[QACheckResult] = []
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
