"""Reporting API endpoints — PDF generation for QA reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.reporting.schemas import (
    ApprovalPackageRequest,
    QAReportRequest,
    RegressionReportRequest,
    ReportDownloadResponse,
    ReportResponse,
)
from app.reporting.service import ReportingService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _get_service(db: AsyncSession = Depends(get_db)) -> ReportingService:
    return ReportingService(db)


@router.post("/qa", response_model=ReportResponse)
@limiter.limit("5/minute")
async def generate_qa_report(
    request: Request,
    data: QAReportRequest,
    service: ReportingService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    """Generate a full QA report PDF with all check results."""
    return await service.generate_qa_report(data, current_user)


@router.post("/approval", response_model=ReportResponse)
@limiter.limit("5/minute")
async def generate_approval_package(
    request: Request,
    data: ApprovalPackageRequest,
    service: ReportingService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    """Generate a client-facing approval package PDF."""
    return await service.generate_approval_package(data, current_user)


@router.post("/regression", response_model=ReportResponse)
@limiter.limit("5/minute")
async def generate_regression_report(
    request: Request,
    data: RegressionReportRequest,
    service: ReportingService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    """Generate a visual regression comparison PDF."""
    return await service.generate_regression_report(data, current_user)


@router.get("/{report_id}", response_model=ReportDownloadResponse)
@limiter.limit("20/minute")
async def get_report(
    request: Request,
    report_id: str,
    service: ReportingService = Depends(_get_service),
    _user: User = Depends(get_current_user),
) -> ReportDownloadResponse:
    """Retrieve a previously generated report by ID (cached in Redis)."""
    return await service.get_report(report_id)
