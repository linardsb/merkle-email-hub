# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""Tolgee TMS API endpoints — sub-router mounted under /api/v1/connectors/tolgee."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.connectors.tolgee.schemas import (
    LocaleBuildRequest,
    LocaleBuildResponse,
    TolgeeConnectionRequest,
    TolgeeConnectionResponse,
    TolgeeLanguage,
    TranslationPullRequest,
    TranslationPullResponse,
    TranslationSyncRequest,
    TranslationSyncResponse,
)
from app.connectors.tolgee.service import TolgeeService
from app.core.rate_limit import limiter
from app.core.scoped_db import get_scoped_db

router = APIRouter(prefix="/api/v1/connectors/tolgee", tags=["tolgee"])


@router.post(
    "/connect",
    response_model=TolgeeConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_connection(
    request: Request,
    body: TolgeeConnectionRequest,
    user: User = Depends(require_role("developer")),
    db: AsyncSession = Depends(get_scoped_db),
) -> TolgeeConnectionResponse:
    """Create a Tolgee TMS connection with encrypted PAT."""
    _ = request
    service = TolgeeService(db)
    return await service.create_connection(body, user)


@router.post(
    "/sync-keys",
    response_model=TranslationSyncResponse,
)
@limiter.limit("5/minute")
async def sync_keys(
    request: Request,
    body: TranslationSyncRequest,
    user: User = Depends(require_role("developer")),
    db: AsyncSession = Depends(get_scoped_db),
) -> TranslationSyncResponse:
    """Extract translatable keys from a template and push to Tolgee."""
    _ = request
    service = TolgeeService(db)
    return await service.sync_keys(body, user)


@router.post(
    "/pull",
    response_model=list[TranslationPullResponse],
)
@limiter.limit("10/minute")
async def pull_translations(
    request: Request,
    body: TranslationPullRequest,
    user: User = Depends(require_role("developer")),
    db: AsyncSession = Depends(get_scoped_db),
) -> list[TranslationPullResponse]:
    """Pull translations from Tolgee for specified locales."""
    _ = request
    service = TolgeeService(db)
    return await service.pull_translations(body, user)


@router.post(
    "/build-locales",
    response_model=LocaleBuildResponse,
)
@limiter.limit("3/minute")
async def build_locales(
    request: Request,
    body: LocaleBuildRequest,
    user: User = Depends(require_role("developer")),
    db: AsyncSession = Depends(get_scoped_db),
) -> LocaleBuildResponse:
    """Build email template in multiple locales (pull + translate + Maizzle build)."""
    _ = request
    service = TolgeeService(db)
    return await service.build_locales(body, user)


@router.get(
    "/connections/{connection_id}",
    response_model=TolgeeConnectionResponse,
)
@limiter.limit("20/minute")
async def get_connection(
    request: Request,
    connection_id: int,
    user: User = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_scoped_db),
) -> TolgeeConnectionResponse:
    """Get a Tolgee connection by ID."""
    _ = request
    service = TolgeeService(db)
    return await service.get_connection(connection_id, user)


@router.get(
    "/connections/{connection_id}/languages",
    response_model=list[TolgeeLanguage],
)
@limiter.limit("20/minute")
async def get_languages(
    request: Request,
    connection_id: int,
    user: User = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_scoped_db),
) -> list[TolgeeLanguage]:
    """List available languages for the connected Tolgee project."""
    _ = request
    service = TolgeeService(db)
    return await service.get_languages(connection_id, user)
