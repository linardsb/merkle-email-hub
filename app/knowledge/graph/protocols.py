"""Graph knowledge provider protocol and data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class GraphEntity:
    """An entity node from the knowledge graph."""

    id: str
    name: str
    entity_type: str  # e.g. "email_client", "css_property", "technique"
    description: str = ""
    properties: dict[str, object] = field(default_factory=dict[str, object])


@dataclass(frozen=True)
class GraphRelationship:
    """A typed edge between two entities."""

    source_id: str
    target_id: str
    relationship_type: str  # e.g. "supports", "breaks_in", "workaround_for"
    properties: dict[str, object] = field(default_factory=dict[str, object])


@dataclass(frozen=True)
class GraphSearchResult:
    """A single result from a graph knowledge query."""

    content: str  # LLM-generated summary or raw text
    entities: tuple[GraphEntity, ...] = ()
    relationships: tuple[GraphRelationship, ...] = ()
    score: float = 0.0


@runtime_checkable
class GraphKnowledgeProvider(Protocol):
    """Protocol for graph-backed knowledge retrieval."""

    async def add_documents(
        self,
        texts: list[str],
        *,
        dataset_name: str = "default",
    ) -> None:
        """Ingest documents into the graph pipeline."""
        ...

    async def build_graph(
        self,
        *,
        dataset_name: str | None = None,
        background: bool = True,
    ) -> None:
        """Run the ECL pipeline to build/update the knowledge graph."""
        ...

    async def search(
        self,
        query: str,
        *,
        dataset_name: str | None = None,
        top_k: int = 10,
    ) -> list[GraphSearchResult]:
        """Query the knowledge graph."""
        ...

    async def search_completion(
        self,
        query: str,
        *,
        dataset_name: str | None = None,
        system_prompt: str = "",
    ) -> str:
        """Graph-backed completion (conversational answer grounded in graph)."""
        ...

    async def reset(self, *, dataset_name: str | None = None) -> None:
        """Clear graph data. Use with caution."""
        ...
