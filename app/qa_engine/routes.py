# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for QA engine."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.rate_limit import limiter
from app.core.scoped_db import get_scoped_db
from app.qa_engine.meta_eval_routes import router as meta_eval_router
from app.qa_engine.schemas import (
    BIMICheckRequest,
    BIMICheckResponse,
    ChaosTestRequest,
    ChaosTestResponse,
    DeliverabilityScoreRequest,
    DeliverabilityScoreResponse,
    GmailOptimizeRequest,
    GmailOptimizeResponse,
    GmailPredictRequest,
    GmailPredictResponse,
    MigrationPlanRequest,
    MigrationPlanResponse,
    OutlookAnalysisRequest,
    OutlookAnalysisResponse,
    OutlookModernizeRequest,
    OutlookModernizeResponse,
    PropertyTestRequest,
    PropertyTestResponse,
    QAOverrideRequest,
    QAOverrideResponse,
    QAResultResponse,
    QARunRequest,
)
from app.qa_engine.service import QAEngineService
from app.shared.schemas import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/api/v1/qa", tags=["qa-engine"])
router.include_router(meta_eval_router)


def get_service(db: AsyncSession = Depends(get_scoped_db)) -> QAEngineService:
    return QAEngineService(db)


@router.post(
    "/property-test",
    response_model=PropertyTestResponse,
    status_code=200,
    summary="Run property-based email testing",
)
@limiter.limit("1/minute")
async def run_property_test(
    request: Request,
    data: PropertyTestRequest,
    service: QAEngineService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> PropertyTestResponse:
    """Generate random email configurations and verify invariants hold."""
    _ = request
    return await service.run_property_test(data)


@router.post(
    "/chaos-test",
    response_model=ChaosTestResponse,
    status_code=200,
    summary="Run chaos resilience test",
)
@limiter.limit("3/minute")
async def run_chaos_test(
    request: Request,
    data: ChaosTestRequest,
    service: QAEngineService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> ChaosTestResponse:
    """Apply controlled email client degradations and measure QA resilience."""
    _ = request
    return await service.run_chaos_test(data, user=current_user)


@router.post(
    "/outlook-analysis",
    response_model=OutlookAnalysisResponse,
    status_code=200,
    summary="Analyze HTML for Outlook Word-engine dependencies",
)
@limiter.limit("10/minute")
async def run_outlook_analysis(
    request: Request,
    data: OutlookAnalysisRequest,
    service: QAEngineService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> OutlookAnalysisResponse:
    """Scan email HTML for VML shapes, ghost tables, MSO conditionals, and other Word-engine dependencies."""
    _ = request
    return await service.run_outlook_analysis(data)


@router.post(
    "/outlook-modernize",
    response_model=OutlookModernizeResponse,
    status_code=200,
    summary="Modernize HTML by removing Word-engine dependencies",
)
@limiter.limit("5/minute")
async def run_outlook_modernize(
    request: Request,
    data: OutlookModernizeRequest,
    service: QAEngineService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> OutlookModernizeResponse:
    """Apply safe modernizations to remove Outlook Word-engine hacks based on target mode."""
    _ = request
    return await service.run_outlook_modernize(data)


@router.post(
    "/outlook-migration-plan",
    response_model=MigrationPlanResponse,
    status_code=200,
    summary="Generate audience-aware migration plan",
    description=(
        "Combine Outlook dependency analysis with audience data to produce "
        "a phased migration plan. Omit audience data for industry-average estimates."
    ),
)
@limiter.limit("5/minute")
async def outlook_migration_plan(
    request: Request,
    data: MigrationPlanRequest,
    service: QAEngineService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> MigrationPlanResponse:
    """Generate audience-aware Outlook migration plan."""
    _ = request
    return await service.run_migration_plan(data)


@router.post(
    "/deliverability-score",
    response_model=DeliverabilityScoreResponse,
    status_code=200,
    summary="Pre-send deliverability prediction scoring",
)
@limiter.limit("10/minute")
async def run_deliverability_score(
    request: Request,
    data: DeliverabilityScoreRequest,
    service: QAEngineService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> DeliverabilityScoreResponse:
    """Score email deliverability across 4 dimensions (content, hygiene, auth, engagement)."""
    _ = request
    return await service.run_deliverability_score(data)


@router.post(
    "/gmail-predict",
    response_model=GmailPredictResponse,
    status_code=200,
    summary="Predict Gmail AI summary",
)
@limiter.limit("5/minute")
async def gmail_predict(
    request: Request,
    data: GmailPredictRequest,
    service: QAEngineService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> GmailPredictResponse:
    """Predict how Gmail's AI will summarize this email."""
    _ = request
    return await service.predict_gmail_summary(data)


@router.post(
    "/gmail-optimize",
    response_model=GmailOptimizeResponse,
    status_code=200,
    summary="Optimize email for Gmail AI summary",
)
@limiter.limit("5/minute")
async def gmail_optimize(
    request: Request,
    data: GmailOptimizeRequest,
    service: QAEngineService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> GmailOptimizeResponse:
    """Suggest subject/preview text optimizations for better AI summaries."""
    _ = request
    return await service.optimize_gmail_preview(data)


@router.post(
    "/bimi-check",
    response_model=BIMICheckResponse,
    status_code=200,
    summary="Check BIMI readiness for a sending domain",
)
@limiter.limit("5/minute")
async def run_bimi_check(
    request: Request,
    data: BIMICheckRequest,
    service: QAEngineService = Depends(get_service),
    _user: User = Depends(get_current_user),
) -> BIMICheckResponse:
    """Check DMARC policy, BIMI DNS record, SVG logo format, and CMC status."""
    _ = request
    return await service.run_bimi_check(data)


@router.post("/run", response_model=QAResultResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def run_qa_checks(
    request: Request,
    data: QARunRequest,
    service: QAEngineService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> QAResultResponse:
    """Run all 10 QA checks against compiled email HTML."""
    _ = request
    return await service.run_checks(data)


# IMPORTANT: /results/latest must precede /results/{result_id} to avoid
# FastAPI parsing "latest" as an integer path parameter.
@router.get("/results/latest", response_model=QAResultResponse)
@limiter.limit("30/minute")
async def get_latest_qa_result(
    request: Request,
    build_id: int | None = Query(None),
    template_version_id: int | None = Query(None),
    service: QAEngineService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> QAResultResponse:
    """Get the latest QA result for a build or template version."""
    _ = request
    return await service.get_latest_result(
        build_id=build_id, template_version_id=template_version_id
    )


@router.get("/results/{result_id}", response_model=QAResultResponse)
@limiter.limit("30/minute")
async def get_qa_result(
    request: Request,
    result_id: int,
    service: QAEngineService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> QAResultResponse:
    """Get a QA result by ID with all checks and override info."""
    _ = request
    return await service.get_result(result_id)


@router.get("/results", response_model=PaginatedResponse[QAResultResponse])
@limiter.limit("30/minute")
async def list_qa_results(
    request: Request,
    pagination: PaginationParams = Depends(),
    build_id: int | None = Query(None),
    template_version_id: int | None = Query(None),
    passed: bool | None = Query(None),
    service: QAEngineService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> PaginatedResponse[QAResultResponse]:
    """List QA results with optional filters."""
    _ = request
    return await service.list_results(
        pagination, build_id=build_id, template_version_id=template_version_id, passed=passed
    )


@router.post(
    "/results/{result_id}/override",
    response_model=QAOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def override_qa_result(
    request: Request,
    result_id: int,
    data: QAOverrideRequest,
    service: QAEngineService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> QAOverrideResponse:
    """Override failing QA checks with justification. Requires developer+ role."""
    _ = request
    return await service.override_result(result_id, data, current_user)
