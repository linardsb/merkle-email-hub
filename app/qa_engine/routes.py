# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for QA engine."""

from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.qa_engine.schemas import QAResultResponse, QARunRequest
from app.qa_engine.service import QAEngineService

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
