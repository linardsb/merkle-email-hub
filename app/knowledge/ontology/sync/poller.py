"""Background poller that syncs Can I Email data into the ontology."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.poller import DataPoller
from app.core.redis import get_redis
from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.sync.caniemail_client import CanIEmailClient
from app.knowledge.ontology.sync.differ import compute_diff
from app.knowledge.ontology.sync.schemas import CanIEmailFeature, SyncDiff, SyncState
from app.knowledge.ontology.sync.writer import apply_sync

logger = get_logger(__name__)

_REDIS_STATE_KEY = "ontology:sync:state"
_REDIS_STATE_TTL = 60 * 60 * 24 * 30  # 30 days


class CanIEmailSyncPoller(DataPoller):
    """Periodically syncs Can I Email data into the local ontology."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            name="caniemail-sync",
            interval_seconds=settings.ontology_sync.interval_hours * 3600,
            leader_lock_ttl=300,
        )
        self._client = CanIEmailClient()

    async def fetch(self) -> object:
        """Fetch latest data from Can I Email GitHub repo.

        Returns None if the commit SHA hasn't changed since last sync.
        """
        latest_sha = await self._client.get_latest_commit_sha()
        state = await self._load_state()

        if state.last_commit_sha == latest_sha:
            logger.debug("ontology.sync.skip_unchanged", sha=latest_sha[:8])
            return None

        logger.info(
            "ontology.sync.fetch_started",
            sha=latest_sha[:8],
            previous_sha=(state.last_commit_sha[:8] if state.last_commit_sha else "none"),
        )

        features = await self._client.fetch_all_features()
        logger.info("ontology.sync.fetch_completed", features=len(features))
        return {"sha": latest_sha, "features": features}

    async def enrich(self, raw: object) -> object:
        """Compute diff against current ontology."""
        if raw is None:
            return None

        data: dict[str, object] = raw  # type: ignore[assignment]
        features: list[CanIEmailFeature] = data["features"]  # type: ignore[assignment]
        registry = load_ontology()
        diff = compute_diff(registry, features)

        return {"sha": data["sha"], "features": features, "diff": diff}

    async def store(self, data: object) -> None:
        """Apply changes to YAML and optionally re-export to graph."""
        if data is None:
            return

        payload: dict[str, object] = data  # type: ignore[assignment]
        diff: SyncDiff = payload["diff"]  # type: ignore[assignment]
        features: list[CanIEmailFeature] = payload["features"]  # type: ignore[assignment]
        sha: str = payload["sha"]  # type: ignore[assignment]

        if diff.has_changes:
            changes = apply_sync(features, diff)
            logger.info("ontology.sync.applied", changes=changes, sha=sha[:8])
            await self._refresh_graph()
        else:
            logger.info("ontology.sync.no_changes", sha=sha[:8])

        state = SyncState(
            last_sync_at=datetime.now(UTC),
            last_commit_sha=sha,
            features_synced=len(features),
        )
        await self._save_state(state)

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

            # Also refresh component compatibility in graph
            await self._refresh_component_graph(provider)
        except Exception:
            logger.warning("ontology.sync.graph_refresh_failed", exc_info=True)

    @staticmethod
    async def _refresh_component_graph(provider: object) -> None:
        """Re-export component documents to Cognee after ontology changes."""
        try:
            from app.components.graph_export import export_component_documents
            from app.core.database import get_db_context

            async with get_db_context() as db:
                comp_docs = await export_component_documents(db)
                if comp_docs:
                    texts = [text for _, text in comp_docs]
                    await provider.add_documents(texts, dataset_name="email_components")  # type: ignore[union-attr]
                    await provider.build_graph(dataset_name="email_components", background=True)  # type: ignore[union-attr]
                    logger.info(
                        "ontology.sync.component_graph_refreshed",
                        component_count=len(comp_docs),
                    )
        except Exception:
            logger.warning("ontology.sync.component_graph_refresh_failed", exc_info=True)

    async def _load_state(self) -> SyncState:
        """Load sync state from Redis."""
        try:
            redis = await get_redis()
            raw = await redis.get(_REDIS_STATE_KEY)
            if raw:
                d = json.loads(raw)
                return SyncState(
                    last_sync_at=(
                        datetime.fromisoformat(d["last_sync_at"]) if d.get("last_sync_at") else None
                    ),
                    last_commit_sha=d.get("last_commit_sha", ""),
                    features_synced=d.get("features_synced", 0),
                    error_count=d.get("error_count", 0),
                )
        except Exception:
            logger.debug("ontology.sync.state_load_failed", exc_info=True)
        return SyncState()

    async def _save_state(self, state: SyncState) -> None:
        """Persist sync state to Redis."""
        try:
            redis = await get_redis()
            d = {
                "last_sync_at": (state.last_sync_at.isoformat() if state.last_sync_at else None),
                "last_commit_sha": state.last_commit_sha,
                "features_synced": state.features_synced,
                "error_count": state.error_count,
            }
            await redis.setex(_REDIS_STATE_KEY, _REDIS_STATE_TTL, json.dumps(d))
        except Exception:
            logger.debug("ontology.sync.state_save_failed", exc_info=True)
