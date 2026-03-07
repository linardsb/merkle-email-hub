"""Database-backed component resolver for blueprint context injection."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.blueprints.protocols import ComponentMeta
from app.components.repository import ComponentRepository


class DbComponentResolver:
    """Resolves component slugs to metadata from the database."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def resolve(self, slugs: list[str]) -> list[ComponentMeta]:
        """Look up components by slug and return lightweight metadata."""
        repo = ComponentRepository(self._db)
        results: list[ComponentMeta] = []
        for slug in slugs:
            comp = await repo.get_by_slug(slug)
            if comp and comp.versions:
                latest = comp.versions[0]
                results.append(
                    ComponentMeta(
                        slug=comp.slug,
                        name=comp.name,
                        category=comp.category,
                        description=comp.description or "",
                        compatibility=latest.compatibility or {},
                        html_snippet=latest.html_source[:500],
                    )
                )
        return results
