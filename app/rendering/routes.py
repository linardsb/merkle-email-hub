# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for rendering tests."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.rendering.schemas import (
    RenderingComparisonRequest,
    RenderingComparisonResponse,
    RenderingTestRequest,
    RenderingTestResponse,
)
from app.rendering.service import RenderingService
from app.shared.schemas import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/api/v1/rendering", tags=["rendering"])


def get_service(db: AsyncSession = Depends(get_db)) -> RenderingService:  # noqa: B008
    return RenderingService(db)


@router.post("/tests", response_model=RenderingTestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def submit_rendering_test(
    request: Request,
    data: RenderingTestRequest,
    service: RenderingService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> RenderingTestResponse:
    """Submit a new cross-client rendering test."""
    _ = request
    return await service.submit_test(data, user_id=current_user.id)


@router.get("/tests", response_model=PaginatedResponse[RenderingTestResponse])
@limiter.limit("30/minute")
async def list_rendering_tests(
    request: Request,
    pagination: PaginationParams = Depends(),  # noqa: B008
    build_id: int | None = Query(None),
    template_version_id: int | None = Query(None),
    test_status: str | None = Query(None, alias="status"),
    service: RenderingService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
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
    service: RenderingService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> RenderingTestResponse:
    """Get a rendering test by ID with all screenshots."""
    _ = request
    return await service.get_test(test_id)


@router.post("/compare", response_model=RenderingComparisonResponse)
@limiter.limit("10/minute")
async def compare_rendering_tests(
    request: Request,
    data: RenderingComparisonRequest,
    service: RenderingService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> RenderingComparisonResponse:
    """Compare two rendering tests for visual regression detection."""
    _ = request
    return await service.compare_tests(data, current_user)
