# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""caniemail.com support data loader.

Loads the local ``data/caniemail-support.json`` file (synced by
``scripts/sync-caniemail.py``) and provides lookup functions for
CSS/HTML feature support across email clients.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "caniemail-support.json"


@dataclass(frozen=True)
class CanieMailSupport:
    """Support level for a single feature+client pair."""

    support: str  # "yes" | "no" | "partial" | "unknown"
    notes: str = ""


@dataclass(frozen=True)
class CanieMailData:
    """Loaded caniemail.com support matrix."""

    features: dict[str, dict[str, CanieMailSupport]] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_caniemail_data() -> CanieMailData:
    """Load and cache caniemail-support.json.

    Returns empty data if the file does not exist (sync hasn't been run).
    """
    if not _DATA_PATH.exists():
        logger.info("design_sync.caniemail_data_missing", path=str(_DATA_PATH))
        return CanieMailData()

    try:
        raw = json.loads(_DATA_PATH.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("design_sync.caniemail_load_failed", error=str(exc))
        return CanieMailData()

    metadata = raw.get("metadata", {})
    raw_features = raw.get("features", {})

    features: dict[str, dict[str, CanieMailSupport]] = {}
    for feature_slug, clients in raw_features.items():
        if not isinstance(clients, dict):
            continue
        client_map: dict[str, CanieMailSupport] = {}
        for client_id, support_data in clients.items():
            if not isinstance(support_data, dict):
                continue
            client_map[client_id] = CanieMailSupport(
                support=str(support_data.get("support", "unknown")),
                notes=str(support_data.get("notes", "")),
            )
        features[feature_slug] = client_map

    logger.info(
        "design_sync.caniemail_data_loaded",
        features=len(features),
        last_synced=metadata.get("last_synced", "unknown"),
    )

    return CanieMailData(features=features, metadata=metadata)


def get_caniemail_support(feature: str, client_id: str) -> CanieMailSupport | None:
    """Look up support for a feature+client pair.

    Returns ``None`` if no data exists for the combination.
    """
    data = load_caniemail_data()
    client_map = data.features.get(feature)
    if client_map is None:
        return None
    return client_map.get(client_id)


def clear_caniemail_cache() -> None:
    """Clear the LRU cache (for testing)."""
    load_caniemail_data.cache_clear()
