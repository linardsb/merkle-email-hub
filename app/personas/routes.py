# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for test personas."""

from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.rate_limit import limiter
from app.core.scoped_db import get_scoped_db
from app.personas.schemas import PersonaCreate, PersonaResponse
from app.personas.service import PersonaService

router = APIRouter(prefix="/api/v1/personas", tags=["personas"])


def get_service(db: AsyncSession = Depends(get_scoped_db)) -> PersonaService:
    return PersonaService(db)


@router.get("/", response_model=list[PersonaResponse])
@limiter.limit("30/minute")
async def list_personas(
    request: Request,
    service: PersonaService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> list[PersonaResponse]:
    """List all test personas."""
    _ = request
    return await service.list_personas()


@router.get("/{persona_id}", response_model=PersonaResponse)
@limiter.limit("30/minute")
async def get_persona(
    request: Request,
    persona_id: int,
    service: PersonaService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
) -> PersonaResponse:
    """Get a persona by ID."""
    _ = request
    return await service.get_persona(persona_id)


@router.post("/", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_persona(
    request: Request,
    data: PersonaCreate,
    service: PersonaService = Depends(get_service),
    _current_user: User = Depends(require_role("developer")),
) -> PersonaResponse:
    """Create a custom test persona."""
    _ = request
    return await service.create_persona(data)
