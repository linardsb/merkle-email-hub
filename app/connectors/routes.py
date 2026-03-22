# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for ESP connectors."""

from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.connectors.qa_gate_schemas import ExportPreCheckRequest, ExportPreCheckResponse
from app.connectors.schemas import ExportRequest, ExportResponse
from app.connectors.service import ConnectorService
from app.core.database import get_db
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


def get_service(db: AsyncSession = Depends(get_db)) -> ConnectorService:  # noqa: B008
    return ConnectorService(db)


@router.post("/export", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def export_email(
    request: Request,
    data: ExportRequest,
    service: ConnectorService = Depends(get_service),  # noqa: B008
    current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ExportResponse:
    """Export a built email template to an ESP."""
    _ = request
    return await service.export(data, user=current_user)


@router.post("/export/pre-check", response_model=ExportPreCheckResponse)
@limiter.limit("10/minute")
async def export_pre_check(
    request: Request,
    data: ExportPreCheckRequest,
    service: ConnectorService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("developer")),  # noqa: B008
) -> ExportPreCheckResponse:
    """Dry-run QA + rendering gates without exporting."""
    _ = request
    return await service.pre_check(data)
