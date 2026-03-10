"""Export ontology to text documents for Cognee graph ingestion."""

from __future__ import annotations

from app.knowledge.ontology.registry import OntologyRegistry, load_ontology
from app.knowledge.ontology.types import CSSCategory, EmailClient


def export_ontology_documents() -> list[tuple[str, str]]:
    """Generate structured text documents from the ontology for Cognee ingestion.

    Returns list of (dataset_name, document_text) tuples.
    Documents are structured so Cognee's ECL pipeline can extract
    entity-relationship triplets.
    """
    onto = load_ontology()
    documents: list[tuple[str, str]] = []

    documents.extend(_export_client_profiles(onto))
    documents.extend(_export_category_matrices(onto))
    documents.extend(_export_fallbacks(onto))

    return documents


def _export_client_profiles(onto: OntologyRegistry) -> list[tuple[str, str]]:
    """One document per client family describing capabilities."""
    families: dict[str, list[EmailClient]] = {}
    for client in onto.clients:
        families.setdefault(client.family, []).append(client)

    docs: list[tuple[str, str]] = []
    for family, clients in families.items():
        lines = [f"# Email Client Family: {family.title()}\n"]
        for c in clients:
            lines.append(f"## {c.name}")
            lines.append(f"- Platform: {c.platform}")
            lines.append(f"- Rendering Engine: {c.engine.value}")
            lines.append(f"- Market Share: {c.market_share}%")
            if c.notes:
                lines.append(f"- Notes: {c.notes}")

            unsupported = onto.properties_unsupported_by(c.id)
            if unsupported:
                lines.append(f"\n### Unsupported CSS Properties ({len(unsupported)} total)")
                for prop in unsupported[:50]:
                    entry = onto.get_support_entry(prop.id, c.id)
                    note = f" — {entry.notes}" if entry and entry.notes else ""
                    lines.append(f"- `{prop.property_name}: {prop.value or '*'}`{note}")
            lines.append("")

        docs.append(("email_ontology", "\n".join(lines)))
    return docs


def _export_category_matrices(onto: OntologyRegistry) -> list[tuple[str, str]]:
    """One document per CSS category with full support matrix."""
    docs: list[tuple[str, str]] = []

    for category in CSSCategory:
        props = onto.properties_by_category(category)
        if not props:
            continue

        lines = [
            f"# CSS {category.value.replace('_', ' ').title()} — Email Client Support Matrix\n"
        ]

        for prop in props:
            css_decl = f"{prop.property_name}: {prop.value}" if prop.value else prop.property_name
            lines.append(f"## `{css_decl}`")
            if prop.description:
                lines.append(f"{prop.description}\n")

            lines.append("| Client | Support | Notes |")
            lines.append("|--------|---------|-------|")

            for client in onto.clients:
                entry = onto.get_support_entry(prop.id, client.id)
                if entry:
                    level_str = entry.level.value
                    notes = entry.notes or ""
                else:
                    level_str = "full"
                    notes = ""
                lines.append(f"| {client.name} | {level_str} | {notes} |")

            fallbacks = onto.fallbacks_for(prop.id)
            if fallbacks:
                lines.append(f"\n### Fallbacks for `{css_decl}`")
                for fb in fallbacks:
                    target = onto.get_property(fb.target_property_id)
                    target_name = (
                        f"`{target.property_name}: {target.value}`"
                        if target
                        else fb.target_property_id
                    )
                    lines.append(f"- Use {target_name} via {fb.technique}")
                    if fb.code_example:
                        lines.append(f"  ```html\n  {fb.code_example.strip()}\n  ```")

            lines.append("")

        docs.append(("email_ontology", "\n".join(lines)))
    return docs


def _export_fallbacks(onto: OntologyRegistry) -> list[tuple[str, str]]:
    """Single document listing all fallback relationships."""
    lines = ["# Email CSS Fallback Relationships\n"]
    lines.append("This document describes fallback patterns when CSS properties are unsupported.\n")

    for fb in onto.fallbacks:
        source = onto.get_property(fb.source_property_id)
        target = onto.get_property(fb.target_property_id)
        source_name = f"{source.property_name}: {source.value}" if source else fb.source_property_id
        target_name = f"{target.property_name}: {target.value}" if target else fb.target_property_id

        clients = [onto.get_client(cid) for cid in fb.client_ids]
        client_names = [c.name for c in clients if c]

        lines.append(f"## `{source_name}` -> `{target_name}`")
        lines.append(f"- Technique: {fb.technique}")
        lines.append(f"- Needed for: {', '.join(client_names)}")
        if fb.code_example:
            lines.append(f"```html\n{fb.code_example.strip()}\n```")
        lines.append("")

    return [("email_ontology", "\n".join(lines))]
