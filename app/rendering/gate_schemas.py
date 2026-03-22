"""Pydantic schemas for the pre-send rendering gate."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GateMode(StrEnum):
    enforce = "enforce"
    warn = "warn"
    skip = "skip"


class GateVerdict(StrEnum):
    PASS = "pass"  # noqa: S105
    WARN = "warn"
    BLOCK = "block"


class GateEvaluateRequest(BaseModel):
    html: str = Field(..., min_length=1, max_length=500_000)
    target_clients: list[str] | None = None
    project_id: int | None = None


class ClientGateResult(BaseModel):
    client_name: str
    confidence_score: float  # 0-100
    threshold: float  # 0-100
    passed: bool
    tier: str  # "tier_1" | "tier_2" | "tier_3"
    blocking_reasons: list[str] = []
    remediation: list[str] = []


class GateResult(BaseModel):
    passed: bool
    verdict: GateVerdict
    mode: GateMode
    client_results: list[ClientGateResult] = []
    blocking_clients: list[str] = []
    recommendations: list[str] = []
    evaluated_at: str  # ISO datetime string


class RenderingGateConfigSchema(BaseModel):
    """Project-level gate configuration."""

    mode: GateMode = GateMode.warn
    tier_thresholds: dict[str, float] = Field(
        default_factory=lambda: {"tier_1": 85.0, "tier_2": 70.0, "tier_3": 60.0}
    )
    target_clients: list[str] = Field(default_factory=list)
    require_external_validation: list[str] = Field(default_factory=list)


class GateConfigUpdateRequest(BaseModel):
    """Partial update for gate config."""

    mode: GateMode | None = None
    tier_thresholds: dict[str, float] | None = None
    target_clients: list[str] | None = None
    require_external_validation: list[str] | None = None
