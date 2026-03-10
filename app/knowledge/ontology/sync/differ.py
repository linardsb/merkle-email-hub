"""Compute diff between current ontology and incoming Can I Email data."""

from __future__ import annotations

from app.core.logging import get_logger
from app.knowledge.ontology.registry import OntologyRegistry
from app.knowledge.ontology.sync.mapper import (
    feature_to_css_property,
    feature_to_support_entries,
)
from app.knowledge.ontology.sync.schemas import CanIEmailFeature, SyncDiff
from app.knowledge.ontology.types import SupportLevel

logger = get_logger(__name__)


def compute_diff(
    registry: OntologyRegistry,
    features: list[CanIEmailFeature],
) -> SyncDiff:
    """Compare incoming Can I Email features against current ontology.

    Only reports changes — does NOT modify the registry.
    """
    diff = SyncDiff()

    existing_prop_ids = set(registry.property_ids())
    existing_client_ids = set(registry.client_ids())

    for feature in features:
        prop = feature_to_css_property(feature)

        if prop.id not in existing_prop_ids:
            diff.new_properties.append(prop.id)

        support_tuples = feature_to_support_entries(feature)
        for prop_id, client_id, level, _note in support_tuples:
            if client_id not in existing_client_ids:
                if client_id not in diff.new_clients:
                    diff.new_clients.append(client_id)
                continue

            existing_entry = registry.get_support_entry(prop_id, client_id)

            if prop_id not in existing_prop_ids:
                # New property — all its support entries are new
                diff.new_support.append((prop_id, client_id, level.value))
            elif existing_entry is None:
                # Property exists but no explicit support entry for this client
                # Only record if incoming level differs from the default (FULL)
                if level != SupportLevel.FULL:
                    diff.new_support.append((prop_id, client_id, level.value))
                else:
                    diff.unchanged_count += 1
            elif existing_entry.level != level and existing_entry.level != SupportLevel.UNKNOWN:
                # Explicit entry exists and level changed
                diff.updated_support.append(
                    (prop_id, client_id, existing_entry.level.value, level.value)
                )
            elif existing_entry.level == SupportLevel.UNKNOWN:
                # Was unknown, now we know
                diff.new_support.append((prop_id, client_id, level.value))
            else:
                diff.unchanged_count += 1

    logger.info(
        "ontology.sync.diff_computed",
        new_properties=len(diff.new_properties),
        new_clients=len(diff.new_clients),
        updated_support=len(diff.updated_support),
        new_support=len(diff.new_support),
        unchanged=diff.unchanged_count,
    )

    return diff
