# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for email build pipeline."""

from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.email_engine.schemas import BuildRequest, BuildResponse, PreviewRequest, PreviewResponse
from app.email_engine.service import EmailEngineService

router = APIRouter(prefix="/api/v1/email", tags=["email-engine"])


def get_service(db: AsyncSession = Depends(get_db)) -> EmailEngineService:  # noqa: B008
    return EmailEngineService(db)


@router.post("/build", response_model=BuildResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def build_email(
    request: Request,
    data: BuildRequest,
    service: EmailEngineService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> BuildResponse:
    """Build an email template using Maizzle."""
    _ = request
    return await service.build(data, user_id=current_user.id)


@router.get("/builds/{build_id}", response_model=BuildResponse)
@limiter.limit("30/minute")
async def get_build(
    request: Request,
    build_id: int,
    service: EmailEngineService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> BuildResponse:
    """Get a build by ID."""
    _ = request
    return await service.get_build(build_id)


@router.post("/preview", response_model=PreviewResponse)
@limiter.limit("60/minute")
async def preview_email(
    request: Request,
    data: PreviewRequest,
    service: EmailEngineService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> PreviewResponse:
    """Preview-build an email template (not persisted)."""
    _ = request
    return await service.preview(data)
