# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Admin-only routes for QA check meta-evaluation."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from pydantic import BaseModel

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.rate_limit import limiter

router = APIRouter(prefix="/meta-eval", tags=["qa-meta-eval"])

_require_admin = require_role("admin")


class CheckEvalResultResponse(BaseModel):
    """Per-check confusion matrix and metrics."""

    check_name: str
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f1: float
    specificity: float
    current_threshold: Any = None
    recommended_threshold: Any | None = None


class ThresholdRecommendationResponse(BaseModel):
    """Threshold adjustment suggestion."""

    check_name: str
    current: Any
    recommended: Any
    improvement_f1: float
    reasoning: str


class MetaEvalReportResponse(BaseModel):
    """Full meta-evaluation report."""

    checks: dict[str, CheckEvalResultResponse]
    overall_f1: float
    timestamp: datetime
    recommendations: list[ThresholdRecommendationResponse]
    golden_count: int
    adversarial_count: int


@router.post("", response_model=MetaEvalReportResponse)
@limiter.limit("1/minute")
async def run_meta_eval(
    request: Request,
    _admin: User = Depends(_require_admin),  # noqa: B008
) -> MetaEvalReportResponse:
    """Run full meta-evaluation of all QA checks against golden + adversarial data."""
    _ = request
    from app.qa_engine.meta_eval import (
        MetaEvaluator,
        load_golden_samples,
        report_to_dict,
        save_report,
    )

    samples = load_golden_samples()
    evaluator = MetaEvaluator()
    report = await evaluator.evaluate_all_checks(samples)
    save_report(report)
    return MetaEvalReportResponse(**report_to_dict(report))


@router.get("/latest", response_model=MetaEvalReportResponse)
@limiter.limit("10/minute")
async def get_latest_report(
    request: Request,
    _admin: User = Depends(_require_admin),  # noqa: B008
) -> MetaEvalReportResponse:
    """Retrieve most recent meta-eval report."""
    _ = request
    from app.qa_engine.meta_eval import load_latest_report

    data = load_latest_report()
    if data is None:
        raise HTTPException(status_code=404, detail="No meta-eval report found")
    return MetaEvalReportResponse(**data)
