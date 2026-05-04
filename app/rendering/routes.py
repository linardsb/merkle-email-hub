# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for rendering tests."""

from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.rate_limit import limiter
from app.core.scoped_db import get_scoped_db
from app.rendering.calibration.schemas import (
    CalibrationHistoryResponse,
    CalibrationSummaryListResponse,
    CalibrationTriggerRequest,
    CalibrationTriggerResponse,
)
from app.rendering.gate_schemas import (
    GateConfigUpdateRequest,
    GateEvaluateRequest,
    GateResult,
    RenderingGateConfigSchema,
)
from app.rendering.sandbox.schemas import (
    SandboxHealthResponse,
    SandboxTestRequest,
    SandboxTestResponse,
)
from app.rendering.sandbox.service import check_sandbox_health, run_sandbox_test
from app.rendering.schemas import (
    BaselineListResponse,
    BaselineResponse,
    BaselineUpdateRequest,
    ClientConfidenceResponse,
    RenderingComparisonRequest,
    RenderingComparisonResponse,
    RenderingTestRequest,
    RenderingTestResponse,
    ScreenshotRequest,
    ScreenshotResponse,
    VisualDiffRequest,
    VisualDiffResponse,
)
from app.rendering.service import RenderingService
from app.shared.schemas import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/api/v1/rendering", tags=["rendering"])


def get_service(db: AsyncSession = Depends(get_scoped_db)) -> RenderingService:
    return RenderingService(db)


@router.post("/tests", response_model=RenderingTestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def submit_rendering_test(
    request: Request,
    data: RenderingTestRequest,
    service: RenderingService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> RenderingTestResponse:
    """Submit a new cross-client rendering test."""
    _ = request
    return await service.submit_test(data, user_id=current_user.id)


@router.get("/tests", response_model=PaginatedResponse[RenderingTestResponse])
@limiter.limit("30/minute")
async def list_rendering_tests(
    request: Request,
    pagination: PaginationParams = Depends(),
    build_id: int | None = Query(None),
    template_version_id: int | None = Query(None),
    test_status: str | None = Query(None, alias="status"),
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> PaginatedResponse[RenderingTestResponse]:
    """List rendering tests with optional filters."""
    _ = request
    return await service.list_tests(
        pagination,
        build_id=build_id,
        template_version_id=template_version_id,
        status=test_status,
    )


@router.get("/tests/{test_id}", response_model=RenderingTestResponse)
@limiter.limit("30/minute")
async def get_rendering_test(
    request: Request,
    test_id: int,
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> RenderingTestResponse:
    """Get a rendering test by ID with all screenshots."""
    _ = request
    return await service.get_test(test_id)


@router.post("/compare", response_model=RenderingComparisonResponse)
@limiter.limit("10/minute")
async def compare_rendering_tests(
    request: Request,
    data: RenderingComparisonRequest,
    service: RenderingService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> RenderingComparisonResponse:
    """Compare two rendering tests for visual regression detection."""
    _ = request
    return await service.compare_tests(data, current_user)


@router.post("/screenshots", response_model=ScreenshotResponse)
@limiter.limit("5/minute")
async def render_screenshots(
    request: Request,
    data: ScreenshotRequest,
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(require_role("developer")),
) -> ScreenshotResponse:
    """Render email HTML across simulated email client viewports."""
    _ = request
    return await service.render_screenshots(data)


@router.get("/confidence/{client_id}", response_model=ClientConfidenceResponse)
@limiter.limit("30/minute")
async def get_client_confidence(
    request: Request,
    client_id: str = Path(..., pattern=r"^[a-z][a-z0-9_]{1,50}$"),
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> ClientConfidenceResponse:
    """Get current confidence calibration data for an email client."""
    _ = request
    return await service.get_client_confidence(client_id)


@router.post("/visual-diff", response_model=VisualDiffResponse)
@limiter.limit("10/minute")
async def visual_diff(
    request: Request,
    data: VisualDiffRequest,
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(require_role("developer")),
) -> VisualDiffResponse:
    """Compare two images for visual differences using ODiff."""
    _ = request
    return await service.visual_diff(data)


@router.get("/baselines/{entity_type}/{entity_id}", response_model=BaselineListResponse)
@limiter.limit("30/minute")
async def list_baselines(
    request: Request,
    entity_type: str,
    entity_id: int,
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> BaselineListResponse:
    """List all stored baselines for a given entity."""
    _ = request
    return await service.list_baselines(entity_type, entity_id)


@router.put("/baselines/{entity_type}/{entity_id}", response_model=BaselineResponse)
@limiter.limit("10/minute")
async def update_baseline(
    request: Request,
    entity_type: str,
    entity_id: int,
    data: BaselineUpdateRequest,
    service: RenderingService = Depends(get_service),
    current_user: User = Depends(require_role("developer")),
) -> BaselineResponse:
    """Create or update a baseline screenshot for an entity + client combination."""
    _ = request
    return await service.update_baseline(entity_type, entity_id, data, current_user.id)


@router.post("/sandbox/test", response_model=SandboxTestResponse)
@limiter.limit("5/minute")
async def sandbox_test(
    request: Request,
    data: SandboxTestRequest,
    _current_user: User = Depends(require_role("admin")),
) -> SandboxTestResponse:
    """Send email to sandbox, capture rendered DOM and screenshots."""
    _ = request
    return await run_sandbox_test(data)


@router.get("/sandbox/health", response_model=SandboxHealthResponse)
@limiter.limit("30/minute")
async def sandbox_health(
    request: Request,
    _current_user: User = Depends(require_role("admin")),
) -> SandboxHealthResponse:
    """Check sandbox infrastructure availability."""
    _ = request
    return await check_sandbox_health()


# ── Calibration endpoints ──


@router.get("/calibration/summary", response_model=CalibrationSummaryListResponse)
@limiter.limit("30/minute")
async def calibration_summary(
    request: Request,
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> CalibrationSummaryListResponse:
    """Get calibration state for all email clients."""
    _ = request
    return await service.get_calibration_summary()


@router.post("/calibration/trigger", response_model=CalibrationTriggerResponse)
@limiter.limit("3/minute")
async def calibration_trigger(
    request: Request,
    data: CalibrationTriggerRequest,
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(require_role("admin")),
) -> CalibrationTriggerResponse:
    """Trigger a calibration run for specified clients."""
    _ = request
    return await service.trigger_calibration(data)


@router.get("/calibration/history/{client_id}", response_model=CalibrationHistoryResponse)
@limiter.limit("30/minute")
async def calibration_history(
    request: Request,
    client_id: str = Path(..., pattern=r"^[a-z][a-z0-9_]{1,50}$"),
    limit: int = Query(20, ge=1, le=100),
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> CalibrationHistoryResponse:
    """Get calibration history for a specific client."""
    _ = request
    return await service.get_calibration_history(client_id, limit=limit)


# ── Gate endpoints (Phase 27.3) ──


@router.post("/gate/evaluate", response_model=GateResult)
@limiter.limit("10/minute")
async def evaluate_gate(
    request: Request,
    data: GateEvaluateRequest,
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(require_role("developer")),
) -> GateResult:
    """Evaluate rendering gate for given HTML."""
    _ = request
    return await service.evaluate_gate(data)


@router.get("/gate/config/{project_id}", response_model=RenderingGateConfigSchema)
@limiter.limit("30/minute")
async def get_gate_config(
    request: Request,
    project_id: int,
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> RenderingGateConfigSchema:
    """Get project-level gate configuration."""
    _ = request
    return await service.get_gate_config(project_id)


@router.put("/gate/config/{project_id}", response_model=RenderingGateConfigSchema)
@limiter.limit("10/minute")
async def update_gate_config(
    request: Request,
    project_id: int,
    data: GateConfigUpdateRequest,
    service: RenderingService = Depends(get_service),
    _current_user: User = Depends(require_role("admin")),
) -> RenderingGateConfigSchema:
    """Update project-level gate configuration (admin only)."""
    _ = request
    return await service.update_gate_config(project_id, data)
