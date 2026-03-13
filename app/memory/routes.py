"""REST API routes for agent memory."""

from fastapi import APIRouter, Depends
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.knowledge.embedding import get_embedding_provider
from app.memory.schemas import (
    MemoryCreate,
    MemoryPromote,
    MemoryResponse,
    MemorySearch,
)
from app.memory.service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])
settings = get_settings()


def _get_service(db: AsyncSession = Depends(get_db)) -> MemoryService:  # noqa: B008
    """Build MemoryService with embedding provider from settings."""
    provider = get_embedding_provider(settings)
    return MemoryService(db, provider)


@router.post("/", response_model=MemoryResponse, status_code=201)
@limiter.limit("10/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def store_memory(
    request: Request,  # noqa: ARG001
    data: MemoryCreate,
    _current_user: User = Depends(require_role("admin", "developer")),  # noqa: B008
    service: MemoryService = Depends(_get_service),  # noqa: B008
) -> MemoryResponse:
    """Store a new agent memory entry."""
    entry = await service.store(data)
    return MemoryResponse.model_validate(entry)


@router.post("/search", response_model=list[MemoryResponse])
@limiter.limit("30/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def search_memories(
    request: Request,  # noqa: ARG001
    data: MemorySearch,
    _current_user: User = Depends(require_role("admin", "developer")),  # noqa: B008
    service: MemoryService = Depends(_get_service),  # noqa: B008
) -> list[MemoryResponse]:
    """Search memories by similarity."""
    results = await service.recall(
        data.query,
        project_id=data.project_id,
        agent_type=data.agent_type,
        memory_type=data.memory_type,
        limit=data.limit,
    )
    responses: list[MemoryResponse] = []
    for entry, score in results:
        resp = MemoryResponse.model_validate(entry)
        resp.similarity = score
        responses.append(resp)
    return responses


@router.get("/{memory_id}", response_model=MemoryResponse)
@limiter.limit("30/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def get_memory(
    request: Request,  # noqa: ARG001
    memory_id: int,
    _current_user: User = Depends(require_role("admin", "developer")),  # noqa: B008
    service: MemoryService = Depends(_get_service),  # noqa: B008
) -> MemoryResponse:
    """Get a specific memory entry."""
    entry = await service.get_by_id(memory_id)
    return MemoryResponse.model_validate(entry)


@router.delete("/{memory_id}", status_code=204)
@limiter.limit("10/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def delete_memory(
    request: Request,  # noqa: ARG001
    memory_id: int,
    _current_user: User = Depends(require_role("admin", "developer")),  # noqa: B008
    service: MemoryService = Depends(_get_service),  # noqa: B008
) -> None:
    """Delete a memory entry."""
    await service.delete(memory_id)


@router.post("/promote", response_model=MemoryResponse, status_code=201)
@limiter.limit("10/minute")  # pyright: ignore[reportUntypedFunctionDecorator,reportUnknownMemberType]
async def promote_dcg_note(
    request: Request,  # noqa: ARG001
    data: MemoryPromote,
    _current_user: User = Depends(require_role("admin", "developer")),  # noqa: B008
    service: MemoryService = Depends(_get_service),  # noqa: B008
) -> MemoryResponse:
    """Promote a DCG note into Hub memory (4.9.7 bridge)."""
    entry = await service.promote_from_dcg(data)
    return MemoryResponse.model_validate(entry)
