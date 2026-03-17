"""Cost governor admin dashboard routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.ai.cost_governor import get_cost_governor
from app.ai.cost_governor_schemas import CostDimension, CostReportResponse
from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.logging import get_logger
from app.core.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/ai/cost", tags=["ai-cost"])


@router.get("/report", response_model=CostReportResponse)
@limiter.limit("30/minute")
async def get_cost_report(
    request: Request,  # noqa: ARG001
    _current_user: Annotated[User, Depends(require_role("admin"))],
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM"),
) -> CostReportResponse:
    """Get monthly cost report. Admin only."""
    settings = get_settings()
    if not settings.ai.cost_governor_enabled:
        raise ForbiddenError("Cost governor is disabled")

    governor = get_cost_governor()
    report = await governor.get_report(month)

    return CostReportResponse(
        month=report.month,
        total_gbp=report.total_gbp,
        budget_gbp=report.budget_gbp,
        utilization_pct=report.utilization_pct,
        status=report.status.value,
        by_model=[CostDimension(name=k, cost_gbp=v) for k, v in report.by_model.items()],
        by_agent=[CostDimension(name=k, cost_gbp=v) for k, v in report.by_agent.items()],
        by_project=[CostDimension(name=k, cost_gbp=v) for k, v in report.by_project.items()],
    )


@router.get("/status")
@limiter.limit("60/minute")
async def get_budget_status(
    request: Request,  # noqa: ARG001
    _current_user: Annotated[User, Depends(require_role("admin", "developer"))],
) -> dict[str, str]:
    """Quick budget status check. Admin + developer."""
    settings = get_settings()
    if not settings.ai.cost_governor_enabled:
        raise ForbiddenError("Cost governor is disabled")

    governor = get_cost_governor()
    status = await governor.check_budget()
    return {"status": status.value}
