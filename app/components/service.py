"""Business logic for email component library."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.components.exceptions import (
    ComponentAlreadyExistsError,
    ComponentNotFoundError,
    ComponentQADataNotFoundError,
)
from app.components.models import Component
from app.components.repository import ComponentRepository
from app.components.sanitize import sanitize_component_html
from app.components.schemas import (
    ClientCompatibility,
    ComponentCompatibilityResponse,
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
        compat = await self.repository.get_latest_compatibility(component_id)
        resp.compatibility_badge = self._compute_badge(compat)
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
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def create_component(self, data: ComponentCreate, user_id: int) -> ComponentResponse:
        logger.info("components.create_started", name=data.name)
        existing = await self.repository.get_by_slug(data.slug)
        if existing:
            raise ComponentAlreadyExistsError(f"Component with slug '{data.slug}' already exists")
        data.html_source = sanitize_component_html(data.html_source)
        if data.css_source:
            data.css_source = sanitize_component_html(data.css_source)
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

    async def create_version(
        self, component_id: int, data: VersionCreate, user_id: int
    ) -> VersionResponse:
        component = await self.repository.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component {component_id} not found")
        data.html_source = sanitize_component_html(data.html_source)
        if data.css_source:
            data.css_source = sanitize_component_html(data.css_source)
        version = await self.repository.create_version(component_id, data, user_id)
        return VersionResponse.model_validate(version)

    async def list_versions(self, component_id: int) -> list[VersionResponse]:
        component = await self.repository.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component {component_id} not found")
        versions = await self.repository.get_versions(component_id)
        return [VersionResponse.model_validate(v) for v in versions]

    async def run_qa_for_version(
        self, component_id: int, version_number: int
    ) -> ComponentCompatibilityResponse:
        """Run QA checks on a specific component version and store compatibility."""
        from app.components.qa_bridge import run_component_qa

        await self._get_or_404(component_id)
        version = await self.repository.get_version(component_id, version_number)
        if not version:
            raise ComponentNotFoundError(
                f"Version {version_number} not found for component {component_id}"
            )

        await run_component_qa(self.db, version)
        return await self.get_compatibility(component_id)

    async def get_compatibility(self, component_id: int) -> ComponentCompatibilityResponse:
        """Get aggregated compatibility data for a component's latest QA'd version."""
        from app.knowledge.ontology.registry import load_ontology

        component = await self._get_or_404(component_id)
        compat = await self.repository.get_latest_compatibility(component_id)

        if not compat:
            raise ComponentQADataNotFoundError(
                f"No QA compatibility data for component {component_id}"
            )

        onto = load_ontology()
        clients: list[ClientCompatibility] = []
        for client_id, level in compat.items():
            client = onto.get_client(client_id)
            if client:
                clients.append(
                    ClientCompatibility(
                        client_id=client_id,
                        client_name=client.name,
                        level=level,
                        platform=client.platform,
                    )
                )

        full = sum(1 for c in clients if c.level == "full")
        partial = sum(1 for c in clients if c.level == "partial")
        none_count = sum(1 for c in clients if c.level == "none")

        return ComponentCompatibilityResponse(
            component_id=component_id,
            component_name=component.name,
            version_number=component.versions[0].version_number if component.versions else 0,
            full_count=full,
            partial_count=partial,
            none_count=none_count,
            clients=clients,
        )

    async def _get_or_404(self, component_id: int) -> Component:
        """Get component or raise 404."""

        component = await self.repository.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component {component_id} not found")
        return component

    @staticmethod
    def _compute_badge(compatibility: dict[str, str] | None) -> str | None:
        """Derive a badge label from compatibility data."""
        if not compatibility:
            return None
        none_count = sum(1 for v in compatibility.values() if v == "none")
        partial_count = sum(1 for v in compatibility.values() if v == "partial")
        if none_count > 0:
            return "issues"
        if partial_count > 0:
            return "partial"
        return "full"
