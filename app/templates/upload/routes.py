# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Template upload REST API."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.requests import Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import DomainValidationError, NotFoundError
from app.core.rate_limit import limiter
from app.templates.upload.schemas import (
    AnalysisPreview,
    ConfirmRequest,
    TemplateUploadResponse,
)
from app.templates.upload.service import TemplateUploadService

router = APIRouter(prefix="/api/v1/templates/upload", tags=["template-upload"])


def _get_service(db: AsyncSession = Depends(get_db)) -> TemplateUploadService:
    return TemplateUploadService(db)


@router.post("", response_model=AnalysisPreview, status_code=201)
@limiter.limit("5/hour")
async def upload_template(
    request: Request,
    file: UploadFile = File(...),
    project_id: int | None = None,
    current_user: User = Depends(require_role("developer")),
    service: TemplateUploadService = Depends(_get_service),
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
    request: Request,
    upload_id: int,
    current_user: User = Depends(require_role("developer")),
    service: TemplateUploadService = Depends(_get_service),
) -> AnalysisPreview:
    """Preview extracted metadata before confirmation."""
    return await service.get_preview(upload_id, current_user.id)


@router.post("/{upload_id}/confirm", response_model=TemplateUploadResponse)
@limiter.limit("10/minute")
async def confirm_upload(
    request: Request,
    upload_id: int,
    body: ConfirmRequest,
    current_user: User = Depends(require_role("developer")),
    service: TemplateUploadService = Depends(_get_service),
) -> TemplateUploadResponse:
    """Confirm and register template after review."""
    return await service.confirm(upload_id, current_user.id, body)


@router.delete("/{upload_id}", status_code=204)
@limiter.limit("10/minute")
async def reject_upload(
    request: Request,
    upload_id: int,
    current_user: User = Depends(require_role("developer")),
    service: TemplateUploadService = Depends(_get_service),
) -> None:
    """Reject and discard upload."""
    await service.reject(upload_id, current_user.id)


_SAFE_ASSET_RE = re.compile(r"^[a-f0-9]{12}\.(png|jpg|gif|webp|svg)$")


@router.get("/assets/{upload_id}/{filename}")
@limiter.limit("120/minute")
async def serve_upload_asset(
    upload_id: int,
    filename: str,
    request: Request,
    _current_user: User = Depends(require_role("viewer")),
) -> FileResponse:
    """Serve a stored image from a template upload."""
    if not _SAFE_ASSET_RE.match(filename):
        raise NotFoundError("Asset not found")

    settings = get_settings().templates
    asset_path = Path(settings.image_storage_path) / str(upload_id) / filename
    if not asset_path.is_file():
        raise NotFoundError("Asset not found")

    # Prevent path traversal via resolved path check
    base = Path(settings.image_storage_path).resolve()
    if not asset_path.resolve().is_relative_to(base):
        raise NotFoundError("Asset not found")

    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    media_type = media_types.get(asset_path.suffix, "application/octet-stream")
    return FileResponse(
        asset_path,
        media_type=media_type,
        headers={"Content-Security-Policy": "default-src 'none'"},
    )
