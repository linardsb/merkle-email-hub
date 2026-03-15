"""Extract Figma components into Hub Component + ComponentVersion records."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from app.ai.shared import sanitize_html_xss
from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.components.models import Component
    from app.components.repository import ComponentRepository
    from app.design_sync.protocol import DesignComponent, DesignSyncProvider
    from app.design_sync.repository import DesignSyncRepository

logger = get_logger(__name__)

# Category detection: Figma component name pattern → Hub category
CATEGORY_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"button|btn|cta", re.IGNORECASE), "cta"),
    (re.compile(r"header|nav|navigation", re.IGNORECASE), "header"),
    (re.compile(r"footer", re.IGNORECASE), "footer"),
    (re.compile(r"hero|banner", re.IGNORECASE), "hero"),
    (re.compile(r"card|tile|feature", re.IGNORECASE), "content"),
]
DEFAULT_CATEGORY = "general"


def detect_category(component_name: str) -> str:
    """Detect Hub component category from Figma component name."""
    for pattern, category in CATEGORY_MAP:
        if pattern.search(component_name):
            return category
    return DEFAULT_CATEGORY


def slugify(name: str) -> str:
    """Convert component name to kebab-case slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower().strip())
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")[:100]


def build_component_brief(component: DesignComponent, category: str) -> str:
    """Build a mini-brief for the Scaffolder to generate component HTML."""
    desc = f" Description: {component.description}." if component.description else ""
    return (
        f"Generate a single reusable email component: '{component.name}' "
        f"(category: {category}).{desc} "
        f"Output ONLY the HTML for this one component section — no full email, "
        f"no <html>/<body> wrapper. Use inline styles for email compatibility. "
        f"Keep it simple, clean, and responsive with max-width 600px."
    )


class ComponentExtractor:
    """Extract Figma components into Hub Component + ComponentVersion records.

    Runs as a background task. Updates DesignImport status as it progresses.
    """

    def __init__(
        self,
        provider: DesignSyncProvider,
        design_repo: DesignSyncRepository,
        component_repo: ComponentRepository,
        db: AsyncSession,
    ) -> None:
        self._provider = provider
        self._design_repo = design_repo
        self._component_repo = component_repo
        self._db = db

    async def extract(
        self,
        import_id: int,
        file_ref: str,
        access_token: str,
        user_id: int,
        component_ids: list[str] | None = None,
        generate_html: bool = True,
    ) -> None:
        """Run the full extraction pipeline. Updates DesignImport status."""
        try:
            # 1. Update status to extracting
            design_import = await self._design_repo.get_import(import_id)
            if design_import is None:
                logger.error("design_sync.import_not_found", import_id=import_id)
                return
            await self._design_repo.update_import_status(design_import, "extracting")

            # 2. List components from Figma
            all_components = await self._provider.list_components(file_ref, access_token)
            if component_ids:
                all_components = [c for c in all_components if c.component_id in component_ids]

            if not all_components:
                await self._design_repo.update_import_status(
                    design_import,
                    "completed",
                    structure_json={"components_extracted": 0},
                )
                return

            logger.info(
                "design_sync.extract_components_started",
                import_id=import_id,
                total=len(all_components),
            )

            # 3. Export PNG previews for all components
            preview_images = await self._provider.export_images(
                file_ref,
                access_token,
                node_ids=[c.component_id for c in all_components],
                format="png",
                scale=2.0,
            )
            preview_map = {img.node_id: img.url for img in preview_images}

            # 4. Update status to converting (Scaffolder phase)
            await self._design_repo.update_import_status(design_import, "converting")

            # 5. Process each component
            results: list[dict[str, object]] = []
            for component in all_components:
                try:
                    result = await self._process_single_component(
                        component=component,
                        file_ref=file_ref,
                        preview_url=preview_map.get(component.component_id),
                        user_id=user_id,
                        import_id=import_id,
                        generate_html=generate_html,
                    )
                    results.append(result)
                except Exception:
                    logger.exception(
                        "design_sync.component_extraction_failed",
                        component_id=component.component_id,
                        component_name=component.name,
                        import_id=import_id,
                    )
                    results.append(
                        {
                            "figma_component_id": component.component_id,
                            "name": component.name,
                            "error": "extraction_failed",
                        }
                    )

            # 6. Mark complete
            await self._design_repo.update_import_status(
                design_import,
                "completed",
                structure_json={
                    "components_extracted": len([r for r in results if "error" not in r]),
                    "components_failed": len([r for r in results if "error" in r]),
                    "results": results,
                },
            )

            logger.info(
                "design_sync.extract_components_completed",
                import_id=import_id,
                extracted=len([r for r in results if "error" not in r]),
                failed=len([r for r in results if "error" in r]),
            )

        except Exception:
            logger.exception(
                "design_sync.extract_components_error",
                import_id=import_id,
            )
            design_import = await self._design_repo.get_import(import_id)
            if design_import is not None:
                await self._design_repo.update_import_status(
                    design_import,
                    "failed",
                    error_message="Component extraction failed unexpectedly",
                )

    async def _process_single_component(
        self,
        component: DesignComponent,
        file_ref: str,
        preview_url: str | None,
        user_id: int,
        import_id: int,
        generate_html: bool,
    ) -> dict[str, object]:
        """Process one Figma component → Hub Component + ComponentVersion."""
        category = detect_category(component.name)
        figma_origin: dict[str, Any] = {
            "figma": {
                "file_key": file_ref,
                "component_id": component.component_id,
            }
        }

        # Generate HTML via Scaffolder (if enabled)
        html_source = ""
        if generate_html:
            html_source = await self._generate_html(component, category)

        # Check for existing component with same Figma origin
        existing = await self._find_existing_component(file_ref, component.component_id)

        if existing:
            # Create new version of existing component
            from app.components.schemas import VersionCreate

            version_data = VersionCreate(
                html_source=html_source or "<!-- pending -->",
                changelog=f"Re-extracted from Figma component {component.name}",
            )
            version = await self._component_repo.create_version(existing.id, version_data, user_id)
            # Set Figma origin directly on model (nested dict not supported by Pydantic schema)
            version.compatibility = figma_origin
            await self._db.flush()

            if preview_url:
                await self._store_preview_asset(import_id, component, preview_url, category)

            return {
                "figma_component_id": component.component_id,
                "name": component.name,
                "category": category,
                "component_id": existing.id,
                "version_number": version.version_number,
                "is_new": False,
            }
        else:
            # Create new component + v1
            from app.components.schemas import ComponentCreate

            slug = slugify(component.name)
            slug = await self._ensure_unique_slug(slug)

            create_data = ComponentCreate(
                name=component.name,
                slug=slug,
                description=component.description or f"Extracted from Figma: {component.name}",
                category=category,
                html_source=html_source or "<!-- pending -->",
            )
            new_component = await self._component_repo.create(create_data, user_id)

            # Update v1's compatibility with Figma origin
            if new_component.versions:
                v1 = new_component.versions[0]
                v1.compatibility = figma_origin
                await self._db.flush()

            if preview_url:
                await self._store_preview_asset(import_id, component, preview_url, category)

            return {
                "figma_component_id": component.component_id,
                "name": component.name,
                "category": category,
                "component_id": new_component.id,
                "version_number": 1,
                "is_new": True,
            }

    async def _generate_html(self, component: DesignComponent, category: str) -> str:
        """Generate component HTML via the Scaffolder agent."""
        from app.ai.agents.scaffolder.schemas import ScaffolderRequest
        from app.ai.agents.scaffolder.service import ScaffolderService

        brief = build_component_brief(component, category)
        scaffolder = ScaffolderService()
        request = ScaffolderRequest(brief=brief, output_mode="html")

        try:
            response = await scaffolder.generate(request)
            html = response.html if response.html else ""
            return sanitize_html_xss(html)
        except Exception:
            logger.exception(
                "design_sync.scaffolder_generation_failed",
                component_name=component.name,
            )
            return ""

    async def _find_existing_component(
        self, file_ref: str, figma_component_id: str
    ) -> Component | None:
        """Find an existing Hub component previously extracted from this Figma component.

        Searches ComponentVersion.compatibility JSON for matching figma origin.
        """
        from sqlalchemy import select

        from app.components.models import Component, ComponentVersion

        stmt = (
            select(Component)
            .join(ComponentVersion)
            .where(
                ComponentVersion.compatibility["figma"]["file_key"].as_string() == file_ref,
                ComponentVersion.compatibility["figma"]["component_id"].as_string()
                == figma_component_id,
                Component.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def _ensure_unique_slug(self, base_slug: str, *, max_attempts: int = 100) -> str:
        """Ensure slug is unique by appending -N suffix if needed."""
        slug = base_slug
        for counter in range(2, max_attempts + 2):
            existing = await self._component_repo.get_by_slug(slug)
            if existing is None:
                return slug
            slug = f"{base_slug}-{counter}"[:100]
        return f"{base_slug}-{counter}"[:100]

    async def _store_preview_asset(
        self,
        import_id: int,
        component: DesignComponent,
        preview_url: str,
        category: str,
    ) -> None:
        """Store component preview as a DesignImportAsset."""
        await self._design_repo.create_import_asset(
            import_id=import_id,
            node_id=component.component_id,
            node_name=component.name,
            file_path=preview_url,
            format="png",
            usage=category if category != "general" else None,
        )
