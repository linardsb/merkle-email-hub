"""Business logic for email component library."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select as sa_select
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
    AssignDesignOriginRequest,
    ClientCompatibility,
    ComponentCompatibilityResponse,
    ComponentCreate,
    ComponentResponse,
    ComponentUpdate,
    DesignOrigin,
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
        # Enrich with design origin from latest version
        if component.versions:
            resp.design_origin = self._parse_design_origin(component.versions[0].compatibility)
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

        component_ids = [c.id for c in items]
        compat_map = await self.repository.get_latest_compatibility_batch(component_ids)
        version_compat_map = await self.repository.get_latest_version_compatibility_batch(
            component_ids
        )

        responses: list[ComponentResponse] = []
        for c in items:
            resp = ComponentResponse.model_validate(c)
            resp.compatibility_badge = self._compute_badge(compat_map.get(c.id))
            resp.design_origin = self._parse_design_origin(version_compat_map.get(c.id))
            responses.append(resp)

        return PaginatedResponse[ComponentResponse](
            items=responses,
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
        resp = VersionResponse.model_validate(version)
        resp.design_origin = self._parse_design_origin(version.compatibility)
        return resp

    async def list_versions(self, component_id: int) -> list[VersionResponse]:
        component = await self.repository.get(component_id)
        if not component:
            raise ComponentNotFoundError(f"Component {component_id} not found")
        versions = await self.repository.get_versions(component_id)
        results: list[VersionResponse] = []
        for v in versions:
            resp = VersionResponse.model_validate(v)
            resp.design_origin = self._parse_design_origin(v.compatibility)
            results.append(resp)
        return results

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

    async def assign_design_origin(
        self, component_id: int, data: AssignDesignOriginRequest
    ) -> ComponentResponse:
        """Assign a design component to a Hub component's latest version."""
        from app.design_sync.models import DesignConnection

        await self._get_or_404(component_id)

        # Validate the connection exists
        result = await self.db.execute(
            sa_select(DesignConnection).where(DesignConnection.id == data.connection_id)
        )
        connection = result.scalar_one_or_none()
        if not connection:
            raise ComponentNotFoundError(f"Design connection {data.connection_id} not found")

        version = await self.repository.get_latest_version(component_id)
        if not version:
            raise ComponentNotFoundError(f"No versions found for component {component_id}")

        # Merge design origin into existing compatibility JSON (don't overwrite QA data)
        existing_compat: dict[str, object] = dict(version.compatibility or {})
        existing_compat[connection.provider] = {
            "file_key": connection.file_ref,
            "component_id": data.design_component_id,
            "component_name": data.design_component_name,
        }

        await self.repository.update_version_compatibility(version, existing_compat)

        logger.info(
            "components.design_origin_assigned",
            component_id=component_id,
            provider=connection.provider,
            connection_id=data.connection_id,
        )

        return await self.get_component(component_id)

    @staticmethod
    def _parse_design_origin(
        compatibility: dict[str, Any] | None,
    ) -> DesignOrigin | None:
        """Extract design origin from version compatibility JSON.

        Looks for known design provider keys (figma, penpot) containing
        file_key and component_id sub-fields.
        """
        if not compatibility:
            return None

        for provider in ("figma", "penpot"):
            origin = compatibility.get(provider)
            if isinstance(origin, dict) and "file_key" in origin and "component_id" in origin:
                name = origin.get("component_name")
                return DesignOrigin(
                    provider=provider,
                    file_key=str(origin["file_key"]),
                    component_id=str(origin["component_id"]),
                    component_name=str(name) if name is not None else None,
                )
        return None

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
