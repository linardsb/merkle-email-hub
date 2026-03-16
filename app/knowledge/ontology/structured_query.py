"""Structured compatibility queries against the ontology registry."""

from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.ontology.registry import OntologyRegistry, load_ontology
from app.knowledge.ontology.types import (
    CSSProperty,
    EmailClient,
    Fallback,
    SupportLevel,
)


@dataclass(frozen=True)
class ClientSupportResult:
    """Support result for a single property x client pair."""

    client: EmailClient
    level: SupportLevel
    notes: str = ""
    workaround: str = ""


@dataclass(frozen=True)
class CompatibilityAnswer:
    """Structured answer to a compatibility query."""

    property: CSSProperty
    client_results: tuple[ClientSupportResult, ...]
    fallbacks: tuple[Fallback, ...]
    summary: str


class OntologyQueryEngine:
    """Stateless engine for structured ontology queries.

    All methods are pure lookups against the in-memory OntologyRegistry.
    No SQL, no external API calls, no mutable state.
    """

    def __init__(self, registry: OntologyRegistry | None = None) -> None:
        self._registry = registry or load_ontology()

    def query_property_support(
        self,
        property_id: str,
        client_ids: list[str] | None = None,
    ) -> CompatibilityAnswer | None:
        """Look up support for a property across clients.

        Args:
            property_id: Ontology property ID (e.g. "display_flex").
            client_ids: Specific clients to check. None = all clients.

        Returns:
            CompatibilityAnswer or None if property not found.
        """
        prop = self._registry.get_property(property_id)
        if prop is None:
            return None

        targets = client_ids or [c.id for c in self._registry.clients]
        results: list[ClientSupportResult] = []

        for cid in targets:
            client = self._registry.get_client(cid)
            if client is None:
                continue
            entry = self._registry.get_support_entry(property_id, cid)
            results.append(
                ClientSupportResult(
                    client=client,
                    level=entry.level if entry else SupportLevel.FULL,
                    notes=entry.notes if entry else "",
                    workaround=entry.workaround if entry else "",
                )
            )

        fallbacks = tuple(self._registry.fallbacks_for(property_id))
        summary = self._build_summary(prop, results, fallbacks)

        return CompatibilityAnswer(
            property=prop,
            client_results=tuple(results),
            fallbacks=fallbacks,
            summary=summary,
        )

    def get_client(self, client_id: str) -> EmailClient | None:
        """Look up a client by ID."""
        return self._registry.get_client(client_id)

    def query_client_limitations(self, client_id: str) -> list[CSSProperty]:
        """List all CSS properties unsupported by a client."""
        return self._registry.properties_unsupported_by(client_id)

    def find_safe_alternatives(
        self,
        property_id: str,
        target_clients: list[str] | None = None,
    ) -> list[Fallback]:
        """Find fallbacks for a property, optionally filtered by target clients."""
        fallbacks = self._registry.fallbacks_for(property_id)
        if target_clients is None:
            return fallbacks
        target_set = set(target_clients)
        return [fb for fb in fallbacks if not fb.client_ids or target_set & set(fb.client_ids)]

    def format_as_search_results(self, answer: CompatibilityAnswer) -> list[dict[str, object]]:
        """Render a CompatibilityAnswer as SearchResult-compatible dicts.

        Returns list of dicts matching SearchResult fields so the caller
        can construct SearchResult objects directly.
        """
        results: list[dict[str, object]] = []

        # Main support matrix result
        support_lines: list[str] = []
        for cr in answer.client_results:
            line = f"- {cr.client.name}: {cr.level.value}"
            if cr.notes:
                line += f" ({cr.notes})"
            if cr.workaround:
                line += f" — workaround: {cr.workaround}"
            support_lines.append(line)

        content = (
            f"## {answer.property.property_name} compatibility\n\n"
            f"{answer.summary}\n\n" + "\n".join(support_lines)
        )

        results.append(
            {
                "chunk_content": content,
                "document_id": 0,
                "document_filename": "ontology",
                "domain": "css_support",
                "language": "en",
                "chunk_index": 0,
                "score": 1.0,
                "metadata_json": None,
            }
        )

        # Fallback results (one per fallback)
        for i, fb in enumerate(answer.fallbacks):
            fb_content = f"## Fallback: {fb.target_property_id}\n\n"
            if fb.technique:
                fb_content += f"Technique: {fb.technique}\n\n"
            if fb.code_example:
                fb_content += f"```\n{fb.code_example}\n```"

            results.append(
                {
                    "chunk_content": fb_content,
                    "document_id": 0,
                    "document_filename": "ontology",
                    "domain": "css_support",
                    "language": "en",
                    "chunk_index": i + 1,
                    "score": 0.95,
                    "metadata_json": None,
                }
            )

        return results

    def _build_summary(
        self,
        prop: CSSProperty,
        results: list[ClientSupportResult],
        fallbacks: tuple[Fallback, ...],
    ) -> str:
        """Build a human-readable summary line."""
        full = [r for r in results if r.level == SupportLevel.FULL]
        partial = [r for r in results if r.level == SupportLevel.PARTIAL]
        none_ = [r for r in results if r.level == SupportLevel.NONE]

        parts: list[str] = [f"`{prop.property_name}`"]
        if not none_ and not partial:
            parts.append("is fully supported across all queried clients.")
        else:
            if full:
                parts.append(f"is supported in {len(full)} client(s)")
            if partial:
                parts.append(f"partially supported in {len(partial)}")
            if none_:
                names = ", ".join(r.client.name for r in none_[:3])
                suffix = f" (+{len(none_) - 3} more)" if len(none_) > 3 else ""
                parts.append(f"not supported in {names}{suffix}")
            if fallbacks:
                parts.append(f"({len(fallbacks)} fallback(s) available)")

        return " ".join(parts)
