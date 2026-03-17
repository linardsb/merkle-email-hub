"""Background poller that syncs Can I Email data into the ontology."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.poller import DataPoller
from app.knowledge.ontology.sync.schemas import SyncReport
from app.knowledge.ontology.sync.service import CanIEmailSyncService

logger = get_logger(__name__)


class CanIEmailSyncPoller(DataPoller):
    """Periodically syncs Can I Email data into the local ontology."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            name="caniemail-sync",
            interval_seconds=settings.ontology_sync.interval_hours * 3600,
            leader_lock_ttl=300,
        )
        self._service = CanIEmailSyncService()
        self._dry_run = settings.ontology_sync.dry_run

    async def fetch(self) -> object:
        """Run sync via service."""
        report = await self._service.sync(dry_run=self._dry_run)
        return report

    async def enrich(self, raw: object) -> object:
        """No enrichment needed — service returns complete report."""
        return raw

    async def store(self, data: object) -> None:
        """Log results and optionally refresh graph."""
        if data is None:
            return

        report: SyncReport = data  # type: ignore[assignment]

        if report.errors:
            logger.warning(
                "ontology.sync.errors",
                errors=report.errors,
            )

        logger.info(
            "ontology.sync.cycle_completed",
            new_properties=report.new_properties,
            updated_levels=report.updated_levels,
            new_clients=report.new_clients,
            changelog_entries=len(report.changelog),
            dry_run=report.dry_run,
        )

        # Refresh knowledge graph if real changes were applied
        if not report.dry_run and (report.new_properties or report.updated_levels):
            await self._refresh_graph()

    async def _refresh_graph(self) -> None:
        """Re-export ontology to Cognee knowledge graph."""
        settings = get_settings()
        if not settings.cognee.enabled:
            return

        try:
            from app.knowledge.graph.cognee_provider import CogneeGraphProvider
            from app.knowledge.ontology.graph_export import export_ontology_documents

            provider = CogneeGraphProvider(settings)
            documents = export_ontology_documents()

            by_dataset: dict[str, list[str]] = {}
            for dataset_name, text in documents:
                by_dataset.setdefault(dataset_name, []).append(text)

            for dataset, texts in by_dataset.items():
                await provider.add_documents(texts, dataset_name=dataset)
                await provider.build_graph(dataset_name=dataset, background=True)

            logger.info(
                "ontology.sync.graph_refreshed",
                datasets=len(by_dataset),
            )
        except Exception:
            logger.warning("ontology.sync.graph_refresh_failed", exc_info=True)
