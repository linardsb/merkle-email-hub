"""Write updated ontology data back to YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.logging import get_logger
from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.sync.mapper import (
    feature_to_css_property,
    feature_to_property_id,
)
from app.knowledge.ontology.sync.schemas import CanIEmailFeature, SyncDiff

logger = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def apply_sync(
    features: list[CanIEmailFeature],
    diff: SyncDiff,
) -> int:
    """Apply diff to YAML files. Returns count of changes written.

    Only touches files that have actual changes. Invalidates the
    ontology LRU cache so next load_ontology() picks up new data.
    """
    if not diff.has_changes:
        return 0

    changes = 0

    # Load overrides — skip any entries that have manual overrides
    overrides_path = _DATA_DIR / "overrides.yaml"
    override_keys: set[tuple[str, str]] = set()
    if overrides_path.exists():
        with overrides_path.open(encoding="utf-8") as f:
            overrides_data = yaml.safe_load(f)
        for o in (overrides_data or {}).get("overrides", []):
            override_keys.add((str(o["property_id"]), str(o["client_id"])))

    if override_keys:
        diff = SyncDiff(
            new_clients=diff.new_clients,
            new_properties=diff.new_properties,
            updated_support=[
                u for u in diff.updated_support
                if (u[0], u[1]) not in override_keys
            ],
            new_support=[
                s for s in diff.new_support
                if (s[0], s[1]) not in override_keys
            ],
        )
        if not diff.has_changes:
            return 0

    if diff.new_properties:
        changes += _append_properties(features, diff.new_properties)

    if diff.updated_support or diff.new_support:
        changes += _update_support_matrix(diff)

    # Invalidate LRU cache so next load picks up changes
    load_ontology.cache_clear()

    logger.info("ontology.sync.yaml_written", changes=changes)
    return changes


def _append_properties(
    features: list[CanIEmailFeature],
    new_prop_ids: list[str],
) -> int:
    """Append new CSS properties to css_properties.yaml."""
    props_path = _DATA_DIR / "css_properties.yaml"
    with props_path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {"properties": []}

    feature_by_prop_id: dict[str, CanIEmailFeature] = {}
    for feat in features:
        feature_by_prop_id[feature_to_property_id(feat.slug)] = feat

    added = 0
    for prop_id in new_prop_ids:
        matched_feat = feature_by_prop_id.get(prop_id)
        if not matched_feat:
            continue
        prop = feature_to_css_property(matched_feat)
        data["properties"].append(
            {
                "id": prop.id,
                "property_name": prop.property_name,
                "value": prop.value,
                "category": prop.category.value,
                "description": prop.description,
                "tags": list(prop.tags),
            }
        )
        added += 1

    with props_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    return added


def _update_support_matrix(diff: SyncDiff) -> int:
    """Update support_matrix.yaml with new and changed entries."""
    support_path = _DATA_DIR / "support_matrix.yaml"
    with support_path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {"support": []}

    entries: list[dict[str, Any]] = data.get("support", [])

    # Index existing entries for fast lookup
    entry_index: dict[tuple[str, str], int] = {}
    for i, entry in enumerate(entries):
        key = (entry["property_id"], entry["client_id"])
        entry_index[key] = i

    changes = 0

    for prop_id, client_id, _old_level, new_level in diff.updated_support:
        key = (prop_id, client_id)
        if key in entry_index:
            entries[entry_index[key]]["level"] = new_level
            changes += 1

    for prop_id, client_id, level in diff.new_support:
        entries.append(
            {
                "property_id": prop_id,
                "client_id": client_id,
                "level": level,
                "notes": "",
                "fallback_ids": [],
                "workaround": "",
            }
        )
        changes += 1

    data["support"] = entries
    with support_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    return changes
