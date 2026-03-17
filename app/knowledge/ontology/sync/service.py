"""Orchestrates Can I Email sync: fetch → diff → optional merge → report."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.sync.caniemail_client import CanIEmailClient
from app.knowledge.ontology.sync.differ import compute_diff
from app.knowledge.ontology.sync.schemas import (
    ChangelogEntry,
    SyncReport,
    SyncState,
    SyncStatus,
)
from app.knowledge.ontology.sync.writer import apply_sync

logger = get_logger(__name__)

_REDIS_STATE_KEY = "ontology:sync:state"
_REDIS_REPORT_KEY = "ontology:sync:last_report"
_REDIS_STATE_TTL = 60 * 60 * 24 * 30  # 30 days


class CanIEmailSyncService:
    """High-level sync orchestrator used by both poller and manual trigger."""

    def __init__(self) -> None:
        self._client = CanIEmailClient()

    async def sync(self, dry_run: bool = False) -> SyncReport:
        """Run the full fetch → diff → merge pipeline.

        Args:
            dry_run: If True, compute diff and report but do NOT write changes.
        """
        report = SyncReport(dry_run=dry_run)

        try:
            latest_sha = await self._client.get_latest_commit_sha()
            report.commit_sha = latest_sha
        except Exception as exc:
            report.errors.append(f"Failed to fetch commit SHA: {exc}")
            return report

        try:
            features = await self._client.fetch_all_features()
        except Exception as exc:
            report.errors.append(f"Failed to fetch features: {exc}")
            return report

        registry = load_ontology()
        diff = compute_diff(registry, features)

        # Build changelog from diff
        report.new_properties = len(diff.new_properties)
        report.new_clients = len(diff.new_clients)

        for prop_id, client_id, old_level, new_level in diff.updated_support:
            report.updated_levels += 1
            report.changelog.append(
                ChangelogEntry(
                    property_id=prop_id,
                    client_id=client_id,
                    old_level=old_level,
                    new_level=new_level,
                    source="caniemail",
                )
            )

        for prop_id, client_id, level in diff.new_support:
            report.changelog.append(
                ChangelogEntry(
                    property_id=prop_id,
                    client_id=client_id,
                    old_level=None,
                    new_level=level,
                    source="caniemail",
                )
            )

        if not dry_run and diff.has_changes:
            try:
                apply_sync(features, diff)
                logger.info(
                    "ontology.sync.applied",
                    changes=report.new_properties + report.updated_levels + len(diff.new_support),
                    sha=latest_sha[:8],
                )
            except Exception as exc:
                report.errors.append(f"Failed to apply sync: {exc}")
                return report

        if not dry_run:
            state = SyncState(
                last_sync_at=datetime.now(UTC),
                last_commit_sha=latest_sha,
                features_synced=len(features),
            )
            await self._save_state(state)

        # Always save the report for dashboard display
        await self._save_report(report)

        return report

    async def get_status(self) -> SyncStatus:
        """Return last sync state + report from Redis."""
        state = await self._load_state()
        report_data = await self._load_report()
        return SyncStatus(
            last_sync_at=state.last_sync_at.isoformat() if state.last_sync_at else None,
            last_commit_sha=state.last_commit_sha or None,
            features_synced=state.features_synced,
            error_count=state.error_count,
            last_report=report_data,
        )

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
                "last_sync_at": state.last_sync_at.isoformat() if state.last_sync_at else None,
                "last_commit_sha": state.last_commit_sha,
                "features_synced": state.features_synced,
                "error_count": state.error_count,
            }
            await redis.setex(_REDIS_STATE_KEY, _REDIS_STATE_TTL, json.dumps(d))
        except Exception:
            logger.warning("ontology.sync.state_save_failed", exc_info=True)

    async def _save_report(self, report: SyncReport) -> None:
        """Persist last sync report to Redis for dashboard display."""
        try:
            redis = await get_redis()
            d = {
                "new_properties": report.new_properties,
                "updated_levels": report.updated_levels,
                "new_clients": report.new_clients,
                "dry_run": report.dry_run,
                "commit_sha": report.commit_sha,
                "errors": report.errors,
                "changelog_count": len(report.changelog),
                "changelog": [
                    {
                        "property_id": c.property_id,
                        "client_id": c.client_id,
                        "old_level": c.old_level,
                        "new_level": c.new_level,
                        "source": c.source,
                    }
                    for c in report.changelog[:100]  # Cap at 100 entries in Redis
                ],
            }
            await redis.setex(_REDIS_REPORT_KEY, _REDIS_STATE_TTL, json.dumps(d))
        except Exception:
            logger.warning("ontology.sync.report_save_failed", exc_info=True)

    async def _load_report(self) -> dict[str, object] | None:
        """Load last sync report from Redis."""
        try:
            redis = await get_redis()
            raw = await redis.get(_REDIS_REPORT_KEY)
            if raw:
                return json.loads(raw)  # type: ignore[no-any-return]
        except Exception:
            logger.debug("ontology.sync.report_load_failed", exc_info=True)
        return None
