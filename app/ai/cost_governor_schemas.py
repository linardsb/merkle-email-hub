"""Pydantic schemas for cost governor API responses."""

from pydantic import BaseModel, Field


class CostDimension(BaseModel):
    """Cost breakdown by a single dimension."""

    name: str
    cost_gbp: float


class CostReportResponse(BaseModel):
    """Monthly cost report."""

    month: str = Field(description="YYYY-MM")
    total_gbp: float
    budget_gbp: float
    utilization_pct: float
    status: str = Field(description="ok | warning | exceeded")
    by_model: list[CostDimension] = []
    by_agent: list[CostDimension] = []
    by_project: list[CostDimension] = []
