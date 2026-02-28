# pyright: reportUnknownMemberType=false, reportUntypedFunctionDecorator=false
"""REST API routes for item management."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.example.schemas import (
    ItemCreate,
    ItemResponse,
    ItemUpdate,
)
from app.example.service import ItemService
from app.shared.schemas import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/api/v1/items", tags=["items"])


def get_service(db: AsyncSession = Depends(get_db)) -> ItemService:  # noqa: B008
    """Dependency to create ItemService with request-scoped session."""
    return ItemService(db)


@router.get("/", response_model=PaginatedResponse[ItemResponse])
@limiter.limit("30/minute")
async def list_items(
    request: Request,
    pagination: PaginationParams = Depends(),  # noqa: B008
    search: str | None = Query(None, max_length=200),
    active_only: bool = Query(default=True),
    status: str | None = Query(None, max_length=20),
    service: ItemService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> PaginatedResponse[ItemResponse]:
    """List items with pagination and optional filters."""
    _ = request
    return await service.list_items(
        pagination, search=search, active_only=active_only, status=status
    )


@router.get("/{item_id}", response_model=ItemResponse)
@limiter.limit("30/minute")
async def get_item(
    request: Request,
    item_id: int,
    service: ItemService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(get_current_user),  # noqa: B008
) -> ItemResponse:
    """Get an item by database ID."""
    _ = request
    return await service.get_item(item_id)


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_item(
    request: Request,
    data: ItemCreate,
    service: ItemService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> ItemResponse:
    """Create a new item."""
    _ = request
    return await service.create_item(data)


@router.patch("/{item_id}", response_model=ItemResponse)
@limiter.limit("10/minute")
async def update_item(
    request: Request,
    item_id: int,
    data: ItemUpdate,
    service: ItemService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> ItemResponse:
    """Update an existing item."""
    _ = request
    return await service.update_item(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_item(
    request: Request,
    item_id: int,
    service: ItemService = Depends(get_service),  # noqa: B008
    _current_user: User = Depends(require_role("admin")),  # noqa: B008
) -> None:
    """Delete an item by database ID."""
    _ = request
    await service.delete_item(item_id)
