"""Export component entities and compatibility to Cognee knowledge graph."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.components.models import Component
from app.core.logging import get_logger
from app.knowledge.ontology.query import unsupported_css_in_html
from app.knowledge.ontology.registry import load_ontology

logger = get_logger(__name__)


async def export_component_documents(db: AsyncSession) -> list[tuple[str, str]]:
    """Generate structured text documents from components for Cognee ingestion.

    Returns list of (dataset_name, document_text) tuples.
    Each component becomes a document with its metadata, compatibility
    profile, and CSS properties used — structured for Cognee ECL to extract
    entity-relationship triplets like:
      Component:CTA_Button [compatible_with] Gmail
      Component:CTA_Button [incompatible_with] Outlook_2016
      Component:CTA_Button [uses_css] background_image
    """
    result = await db.execute(
        select(Component)
        .where(Component.deleted_at.is_(None))
        .options(selectinload(Component.versions))
        .order_by(Component.name)
    )
    components = list(result.scalars().all())

    if not components:
        return []

    onto = load_ontology()
    documents: list[tuple[str, str]] = []

    for comp in components:
        if not comp.versions:
            continue

        latest = comp.versions[0]  # Ordered by version_number DESC
        lines = [
            f"# Email Component: {comp.name}",
            f"- Slug: {comp.slug}",
            f"- Category: {comp.category}",
        ]
        if comp.description:
            lines.append(f"- Description: {comp.description}")
        lines.append(f"- Latest Version: {latest.version_number}")
        lines.append("")

        # Compatibility profile
        compat = latest.compatibility or {}
        if compat:
            lines.append("## Client Compatibility")

            # Single pass: resolve names and bucket by level
            by_level: dict[str, list[str]] = {"full": [], "partial": [], "none": []}
            for cid, level in compat.items():
                client = onto.get_client(cid)
                name = client.name if client else cid
                if level in by_level:
                    by_level[level].append(name)

            if by_level["full"]:
                lines.append(f"- Full support: {', '.join(by_level['full'])}")
            if by_level["partial"]:
                lines.append(f"- Partial support: {', '.join(by_level['partial'])}")
            if by_level["none"]:
                lines.append(f"- Not supported: {', '.join(by_level['none'])}")

            lines.append("")

        # CSS analysis
        issues = unsupported_css_in_html(latest.html_source)
        if issues:
            lines.append("## CSS Compatibility Issues")
            for issue in issues:
                prop_name = issue["property_name"]
                value = issue.get("value", "")
                css_decl = f"{prop_name}: {value}" if value else str(prop_name)
                lines.append(
                    f"- `{css_decl}` — unsupported in {issue['unsupported_count']} clients "
                    f"(severity: {issue['severity']}, "
                    f"fallback: {'yes' if issue['fallback_available'] else 'no'})"
                )
            lines.append("")

        documents.append(("email_components", "\n".join(lines)))

    logger.info(
        "components.graph_export_completed",
        component_count=len(documents),
    )

    return documents
