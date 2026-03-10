# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Cognee implementation of GraphKnowledgeProvider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.knowledge.graph.exceptions import (
    GraphIngestionError,
    GraphNotEnabledError,
    GraphSearchError,
)
from app.knowledge.graph.protocols import GraphSearchResult

if TYPE_CHECKING:
    from app.core.config import Settings

logger = get_logger(__name__)

# Lazy-loaded flag to avoid importing cognee at module level.
# Not thread-safe but idempotent — worst case config is applied twice.
_config_applied = False


class CogneeGraphProvider:
    """Cognee-backed graph knowledge provider.

    Implements GraphKnowledgeProvider protocol.
    Lazily imports cognee and applies config on first use.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if not settings.cognee.enabled:
            raise GraphNotEnabledError("Cognee integration is disabled (COGNEE__ENABLED=false)")

    def _ensure_configured(self) -> None:
        """Apply Cognee config once, lazily."""
        global _config_applied
        if not _config_applied:
            from app.knowledge.graph.config import apply_cognee_config

            apply_cognee_config(self._settings)
            _config_applied = True

    async def add_documents(
        self,
        texts: list[str],
        *,
        dataset_name: str = "default",
    ) -> None:
        """Ingest documents into Cognee's pipeline."""
        self._ensure_configured()
        import cognee

        try:
            await cognee.add(texts, dataset_name=dataset_name)
            logger.info(
                "knowledge.graph.documents_added",
                count=len(texts),
                dataset=dataset_name,
            )
        except Exception as exc:
            logger.error("knowledge.graph.ingestion_failed", error=str(exc))
            raise GraphIngestionError(f"Failed to add documents: {exc}") from exc

    async def build_graph(
        self,
        *,
        dataset_name: str | None = None,
        background: bool = True,
    ) -> None:
        """Run Cognee's ECL pipeline."""
        self._ensure_configured()
        import cognee

        try:
            kwargs: dict[str, object] = {}
            if dataset_name:
                kwargs["datasets"] = [dataset_name]
            if background:
                kwargs["run_in_background"] = True

            await cognee.cognify(**kwargs)
            logger.info(
                "knowledge.graph.build_started",
                dataset=dataset_name or "all",
                background=background,
            )
        except Exception as exc:
            logger.error("knowledge.graph.build_failed", error=str(exc))
            raise GraphIngestionError(f"Graph build failed: {exc}") from exc

    async def search(
        self,
        query: str,
        *,
        dataset_name: str | None = None,
        top_k: int = 10,
    ) -> list[GraphSearchResult]:
        """Search the knowledge graph for entity-relationship results."""
        self._ensure_configured()
        import cognee
        from cognee.api.v1.search import SearchType

        try:
            kwargs: dict[str, object] = {
                "query_text": query,
                "query_type": SearchType.CHUNKS,
            }
            if dataset_name:
                kwargs["datasets"] = [dataset_name]

            raw_results = await cognee.search(**kwargs)

            results: list[GraphSearchResult] = []
            for item in raw_results[:top_k]:
                content = str(item) if not isinstance(item, str) else item
                results.append(GraphSearchResult(content=content))

            logger.info(
                "knowledge.graph.search_completed",
                query_length=len(query),
                result_count=len(results),
            )
            return results

        except Exception as exc:
            logger.error("knowledge.graph.search_failed", error=str(exc))
            raise GraphSearchError(f"Graph search failed: {exc}") from exc

    async def search_completion(
        self,
        query: str,
        *,
        dataset_name: str | None = None,
        system_prompt: str = "",
    ) -> str:
        """Graph-grounded conversational answer."""
        self._ensure_configured()
        import cognee
        from cognee.api.v1.search import SearchType

        try:
            kwargs: dict[str, object] = {
                "query_text": query,
                "query_type": SearchType.GRAPH_COMPLETION,
            }
            if dataset_name:
                kwargs["datasets"] = [dataset_name]
            if system_prompt:
                kwargs["system_prompt"] = system_prompt

            results = await cognee.search(**kwargs)
            answer = str(results[0]) if results else ""

            logger.info(
                "knowledge.graph.completion_done",
                query_length=len(query),
                answer_length=len(answer),
            )
            return answer

        except Exception as exc:
            logger.error("knowledge.graph.completion_failed", error=str(exc))
            raise GraphSearchError(f"Graph completion failed: {exc}") from exc

    async def reset(self, *, dataset_name: str | None = None) -> None:  # noqa: ARG002
        """Clear Cognee graph data.

        Note: Cognee's prune_data() clears ALL data regardless of dataset_name.
        The parameter is accepted for protocol compatibility but not scoped.
        """
        self._ensure_configured()
        import cognee

        try:
            await cognee.prune.prune_data()
            logger.info("knowledge.graph.reset_completed")
        except Exception as exc:
            logger.error("knowledge.graph.reset_failed", error=str(exc))
            raise GraphIngestionError(f"Graph reset failed: {exc}") from exc
