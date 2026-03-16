"""Component search service for template-intent queries."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.components.models import Component, ComponentVersion
from app.components.repository import ComponentRepository
from app.core.logging import get_logger
from app.knowledge.schemas import SearchResult

logger = get_logger(__name__)


class ComponentSearchService:
    """Search reusable email components with optional compatibility filtering."""

    def __init__(self, db: AsyncSession) -> None:
        self.repo = ComponentRepository(db)

    async def search_components(
        self,
        query: str,
        *,
        category: str | None = None,
        compatible_with: list[str] | None = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """Search components by text + optional compatibility filter.

        Returns backward-compatible SearchResult objects.
        """
        results = await self.repo.search_with_compatibility(
            search=query,
            category=category,
            compatible_with=compatible_with,
            limit=limit,
        )

        logger.info(
            "component_search.completed",
            query=query,
            category=category,
            compatible_with=compatible_with,
            result_count=len(results),
        )

        return self._format_as_search_results(results)

    @staticmethod
    def _format_as_search_results(
        components: list[tuple[Component, ComponentVersion]],
    ) -> list[SearchResult]:
        """Convert component + latest version to SearchResult objects."""
        results: list[SearchResult] = []
        for component, version in components:
            content_parts = [f"## Component: {component.name}"]
            if component.description:
                content_parts.append(component.description)
            content_parts.append(f"\n**Category:** {component.category}")
            if version.compatibility:
                compat_items = [
                    f"{client}: {level}" for client, level in version.compatibility.items()
                ]
                content_parts.append(f"**Compatibility:** {', '.join(compat_items)}")
            content_parts.append(f"\n```html\n{version.html_source}\n```")

            results.append(
                SearchResult(
                    chunk_content="\n".join(content_parts),
                    document_id=0,
                    document_filename=f"component:{component.slug}",
                    domain="components",
                    language="en",
                    chunk_index=0,
                    score=1.0,
                    metadata_json=None,
                )
            )
        return results
