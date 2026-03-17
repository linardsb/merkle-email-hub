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
    resilience_score: float | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ChaosTestRequest(BaseModel):
    """Request to run chaos testing on HTML."""

    html: str = Field(..., min_length=1, max_length=500_000)
    profiles: list[str] | None = Field(
        None,
        description="Profile names to test. None = use defaults from config.",
    )


class ChaosFailure(BaseModel):
    """A specific QA check failure introduced by a chaos profile."""

    profile: str
    check_name: str
    severity: str
    description: str


class ChaosProfileResult(BaseModel):
    """QA results for a single chaos profile."""

    profile: str
    description: str
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    checks_passed: int
    checks_total: int
    failures: list[ChaosFailure] = []


class ChaosTestResponse(BaseModel):
    """Complete chaos test results."""

    original_score: float = Field(ge=0.0, le=1.0)
    resilience_score: float = Field(ge=0.0, le=1.0)
    profiles_tested: int
    profile_results: list[ChaosProfileResult] = []
    critical_failures: list[ChaosFailure] = []
