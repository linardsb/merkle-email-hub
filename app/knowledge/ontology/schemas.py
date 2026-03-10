"""API response schemas for ontology endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class EmailClientResponse(BaseModel):
    """Public email client metadata from ontology."""

    id: str
    name: str
    family: str
    platform: str
    engine: str
    market_share: float


class CapabilityFeasibilityResponse(BaseModel):
    """A single capability's feasibility and competitive status."""

    id: str
    name: str
    category: str
    audience_coverage: float
    blocking_clients: list[str]
    hub_supports: bool
    hub_agent: str
    competitor_names: list[str]


class CompetitiveReportResponse(BaseModel):
    """Full audience-scoped competitive feasibility report."""

    audience_client_ids: list[str]
    total_capabilities: int
    hub_advantages: list[CapabilityFeasibilityResponse]
    gaps: list[CapabilityFeasibilityResponse]
    opportunities: list[CapabilityFeasibilityResponse]
    full_matrix: list[CapabilityFeasibilityResponse]


class CompetitiveReportTextResponse(BaseModel):
    """Formatted text competitive landscape report."""

    report: str
