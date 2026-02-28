"""Business logic for email component library."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.components.exceptions import ComponentAlreadyExistsError, ComponentNotFoundError
from app.components.repository import ComponentRepository
from app.components.schemas import (
    ComponentCreate,
    ComponentResponse,
    ComponentUpdate,
    VersionCreate,
    VersionResponse,
)
from app.core.logging import get_logger
from app.shared.schemas import PaginatedResponse, PaginationParams

logger = get_logger(__name__)


class ComponentService:
    """Business logic for email component management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ComponentRepository(db)

    async def get_component(self, component_id: int) -> ComponentResponse:
        logger.info("components.fetch_started", component_id=component_id)
        component = await self.repository.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component {component_id} not found")
        latest = await self.repository.get_latest_version_number(component_id)
        resp = ComponentResponse.model_validate(component)
        resp.latest_version = latest if latest > 0 else None
        return resp

    async def list_components(
        self,
        pagination: PaginationParams,
        *,
        category: str | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[ComponentResponse]:
        items = await self.repository.list(
            offset=pagination.offset, limit=pagination.page_size, category=category, search=search
        )
        total = await self.repository.count(category=category, search=search)
        return PaginatedResponse[ComponentResponse](
            items=[ComponentResponse.model_validate(c) for c in items],
            total=total, page=pagination.page, page_size=pagination.page_size,
        )

    async def create_component(self, data: ComponentCreate, user_id: int) -> ComponentResponse:
        logger.info("components.create_started", name=data.name)
        existing = await self.repository.get_by_slug(data.slug)
        if existing:
            raise ComponentAlreadyExistsError(f"Component with slug '{data.slug}' already exists")
        component = await self.repository.create(data, user_id)
        resp = ComponentResponse.model_validate(component)
        resp.latest_version = 1
        return resp

    async def update_component(self, component_id: int, data: ComponentUpdate) -> ComponentResponse:
        component = await self.repository.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component {component_id} not found")
        component = await self.repository.update(component, data)
        return ComponentResponse.model_validate(component)

    async def delete_component(self, component_id: int) -> None:
        component = await self.repository.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component {component_id} not found")
        await self.repository.delete(component)

    async def create_version(self, component_id: int, data: VersionCreate, user_id: int) -> VersionResponse:
        component = await self.repository.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component {component_id} not found")
        version = await self.repository.create_version(component_id, data, user_id)
        return VersionResponse.model_validate(version)

    async def list_versions(self, component_id: int) -> list[VersionResponse]:
        component = await self.repository.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component {component_id} not found")
        versions = await self.repository.get_versions(component_id)
        return [VersionResponse.model_validate(v) for v in versions]
