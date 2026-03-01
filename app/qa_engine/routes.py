# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for QA engine."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.qa_engine.schemas import (
    QAOverrideRequest,
    QAOverrideResponse,
    QAResultResponse,
    QARunRequest,
)
from app.qa_engine.service import QAEngineService
from app.shared.schemas import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/api/v1/qa", tags=["qa-engine"])


def get_service(db: AsyncSession = Depends(get_db)) -> QAEngineService:  # noqa: B008
    return QAEngineService(db)


@router.post("/run", response_model=QAResultResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def run_qa_checks(
    request: Request,
    data: QARunRequest,
    service: QAEngineService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
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
    service: QAEngineService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
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
    service: QAEngineService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> QAResultResponse:
    """Get a QA result by ID with all checks and override info."""
    _ = request
    return await service.get_result(result_id)


@router.get("/results", response_model=PaginatedResponse[QAResultResponse])
@limiter.limit("30/minute")
async def list_qa_results(
    request: Request,
    pagination: PaginationParams = Depends(),  # noqa: B008
    build_id: int | None = Query(None),
    template_version_id: int | None = Query(None),
    passed: bool | None = Query(None),
    service: QAEngineService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
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
    service: QAEngineService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> QAOverrideResponse:
    """Override failing QA checks with justification. Requires developer+ role."""
    _ = request
    return await service.override_result(result_id, data, current_user)
