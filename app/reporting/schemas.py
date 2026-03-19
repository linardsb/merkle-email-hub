"""Reporting request/response schemas."""

from __future__ import annotations

import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ReportType(StrEnum):
    qa = "qa"
    approval = "approval"
    regression = "regression"


class QAReportRequest(BaseModel):
    """Request to generate a QA report PDF."""

    qa_result_id: int = Field(description="QA result to report on")
    include_screenshots: bool = Field(default=True, description="Embed rendering screenshots")
    include_chaos: bool = Field(default=True, description="Include chaos test results if available")
    include_deliverability: bool = Field(default=True, description="Include deliverability score")


class ApprovalPackageRequest(BaseModel):
    """Request to generate a client approval package."""

    qa_result_id: int = Field(description="QA result for the approval")
    template_version_id: int | None = Field(
        default=None, description="Template version for preview renders"
    )
    include_mobile_preview: bool = Field(default=True)


class RegressionReportRequest(BaseModel):
    """Request to generate a visual regression report."""

    entity_type: str = Field(description="Entity type: component_version or golden_template")
    entity_id: int = Field(description="Entity ID to compare baselines for")
    baseline_test_id: int | None = Field(
        default=None, description="Specific baseline test to compare against"
    )
    current_test_id: int | None = Field(default=None, description="Current test to compare")


class ReportResponse(BaseModel):
    """Generated report metadata."""

    report_id: str = Field(description="Cache key for retrieval")
    filename: str
    size_bytes: int
    generated_at: datetime.datetime
    report_type: ReportType


class ReportDownloadResponse(BaseModel):
    """Cached report for download."""

    pdf_base64: str = Field(description="Base64-encoded PDF bytes")
    filename: str
    size_bytes: int
    generated_at: datetime.datetime
