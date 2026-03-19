# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Template upload REST API."""

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.exceptions import DomainValidationError
from app.core.rate_limit import limiter
from app.templates.upload.schemas import (
    AnalysisPreview,
    ConfirmRequest,
    TemplateUploadResponse,
)
from app.templates.upload.service import TemplateUploadService

router = APIRouter(prefix="/api/v1/templates/upload", tags=["template-upload"])


def _get_service(db: AsyncSession = Depends(get_db)) -> TemplateUploadService:  # noqa: B008
    return TemplateUploadService(db)


@router.post("", response_model=AnalysisPreview, status_code=201)
@limiter.limit("5/hour")
async def upload_template(
    request: Request,  # noqa: ARG001
    file: UploadFile = File(...),  # noqa: B008
    project_id: int | None = None,
    current_user: User = Depends(require_role("developer")),  # noqa: B008
    service: TemplateUploadService = Depends(_get_service),  # noqa: B008
) -> AnalysisPreview:
    """Upload HTML template for analysis. Max 2MB. Returns analysis preview."""
    if file.content_type and file.content_type not in (
        "text/html",
        "text/plain",
        "application/octet-stream",
    ):
        raise DomainValidationError(f"Unsupported content type: {file.content_type}")
    content = await file.read()
    try:
        html_content = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DomainValidationError("File must be valid UTF-8 encoded HTML") from exc
    return await service.upload_and_analyze(html_content, current_user.id, project_id)


@router.get("/{upload_id}/preview", response_model=AnalysisPreview)
@limiter.limit("30/minute")
async def get_upload_preview(
    request: Request,  # noqa: ARG001
    upload_id: int,
    current_user: User = Depends(require_role("developer")),  # noqa: B008
    service: TemplateUploadService = Depends(_get_service),  # noqa: B008
) -> AnalysisPreview:
    """Preview extracted metadata before confirmation."""
    return await service.get_preview(upload_id, current_user.id)


@router.post("/{upload_id}/confirm", response_model=TemplateUploadResponse)
@limiter.limit("10/minute")
async def confirm_upload(
    request: Request,  # noqa: ARG001
    upload_id: int,
    body: ConfirmRequest,
    current_user: User = Depends(require_role("developer")),  # noqa: B008
    service: TemplateUploadService = Depends(_get_service),  # noqa: B008
) -> TemplateUploadResponse:
    """Confirm and register template after review."""
    return await service.confirm(upload_id, current_user.id, body)


@router.delete("/{upload_id}", status_code=204)
@limiter.limit("10/minute")
async def reject_upload(
    request: Request,  # noqa: ARG001
    upload_id: int,
    current_user: User = Depends(require_role("developer")),  # noqa: B008
    service: TemplateUploadService = Depends(_get_service),  # noqa: B008
) -> None:
    """Reject and discard upload."""
    await service.reject(upload_id, current_user.id)
