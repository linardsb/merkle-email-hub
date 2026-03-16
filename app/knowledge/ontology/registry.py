"""Ontology registry — loads YAML data and builds lookup indexes."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, cast

import yaml

from app.core.logging import get_logger
from app.knowledge.ontology.types import (
    ClientEngine,
    CSSCategory,
    CSSProperty,
    EmailClient,
    Fallback,
    SupportEntry,
    SupportLevel,
)

logger = get_logger(__name__)

_DATA_DIR = Path(__file__).parent / "data"


class OntologyRegistry:
    """Immutable, indexed view of the email development ontology."""

    __slots__ = (
        "_client_by_id",
        "_fallback_by_source",
        "_property_by_id",
        "_support_by_client",
        "_support_by_prop",
        "_support_lookup",
        "clients",
        "fallbacks",
        "properties",
        "support_entries",
    )

    def __init__(
        self,
        *,
        clients: tuple[EmailClient, ...],
        properties: tuple[CSSProperty, ...],
        support_entries: tuple[SupportEntry, ...],
        fallbacks: tuple[Fallback, ...],
        client_by_id: dict[str, EmailClient],
        property_by_id: dict[str, CSSProperty],
        support_by_prop: dict[str, list[SupportEntry]],
        support_by_client: dict[str, list[SupportEntry]],
        support_lookup: dict[tuple[str, str], SupportEntry],
        fallback_by_source: dict[str, list[Fallback]],
    ) -> None:
        self.clients = clients
        self.properties = properties
        self.support_entries = support_entries
        self.fallbacks = fallbacks
        self._client_by_id = client_by_id
        self._property_by_id = property_by_id
        self._support_by_prop = support_by_prop
        self._support_by_client = support_by_client
        self._support_lookup = support_lookup
        self._fallback_by_source = fallback_by_source

    def get_client(self, client_id: str) -> EmailClient | None:
        return self._client_by_id.get(client_id)

    def get_property(self, property_id: str) -> CSSProperty | None:
        return self._property_by_id.get(property_id)

    def get_support(self, property_id: str, client_id: str) -> SupportLevel:
        """Get support level. Returns FULL if no entry (default assumption)."""
        entry = self._support_lookup.get((property_id, client_id))
        return entry.level if entry else SupportLevel.FULL

    def get_support_entry(self, property_id: str, client_id: str) -> SupportEntry | None:
        return self._support_lookup.get((property_id, client_id))

    def properties_unsupported_by(self, client_id: str) -> list[CSSProperty]:
        """All properties with NONE support for a given client."""
        entries = self._support_by_client.get(client_id, [])
        return [
            self._property_by_id[e.property_id]
            for e in entries
            if e.level == SupportLevel.NONE and e.property_id in self._property_by_id
        ]

    def clients_not_supporting(self, property_id: str) -> list[EmailClient]:
        """All clients that do NOT support a given property."""
        entries = self._support_by_prop.get(property_id, [])
        return [
            self._client_by_id[e.client_id]
            for e in entries
            if e.level == SupportLevel.NONE and e.client_id in self._client_by_id
        ]

    def fallbacks_for(self, property_id: str) -> list[Fallback]:
        return self._fallback_by_source.get(property_id, [])

    def client_ids(self) -> list[str]:
        return [c.id for c in self.clients]

    def property_ids(self) -> list[str]:
        return [p.id for p in self.properties]

    def properties_by_category(self, category: CSSCategory) -> list[CSSProperty]:
        return [p for p in self.properties if p.category == category]

    def find_property_by_name(self, css_name: str, value: str | None = None) -> CSSProperty | None:
        """Fuzzy property lookup: exact ID → case-insensitive name → prefix match."""
        from app.knowledge.ontology.query import _property_id_from_css

        # Try exact ID first
        prop_id = _property_id_from_css(css_name, value)
        exact = self._property_by_id.get(prop_id)
        if exact is not None:
            return exact

        # Case-insensitive property_name match
        name_lower = css_name.strip().lower()
        for prop in self.properties:
            if prop.property_name.lower() == name_lower:
                return prop

        # Prefix match (e.g. "flex" matches "flex-direction", "flex-wrap", etc.)
        # Return first match only — caller should use exact names for precision
        for prop in self.properties:
            if prop.property_name.lower().startswith(name_lower):
                return prop

        return None

    def find_client_by_name(self, name: str) -> EmailClient | None:
        """Fuzzy client lookup: exact name → family → substring. Highest market share on ambiguity."""
        name_lower = name.strip().lower()

        # Exact name match
        for client in self.clients:
            if client.name.lower() == name_lower:
                return client

        # Family match (e.g. "outlook" matches Outlook 2019, Outlook 365, etc.)
        family_matches: list[EmailClient] = []
        for client in self.clients:
            if client.family.lower() == name_lower:
                family_matches.append(client)
        if family_matches:
            return max(family_matches, key=lambda c: c.market_share)

        # Substring match
        substring_matches: list[EmailClient] = []
        for client in self.clients:
            if name_lower in client.name.lower() or name_lower in client.family.lower():
                substring_matches.append(client)
        if substring_matches:
            return max(substring_matches, key=lambda c: c.market_share)

        return None


def _parse_clients(data: dict[str, Any]) -> tuple[EmailClient, ...]:
    """Parse clients.yaml into EmailClient tuples."""
    raw = cast(list[dict[str, Any]], data.get("clients", []))
    clients: list[EmailClient] = []
    for item in raw:
        clients.append(
            EmailClient(
                id=str(item["id"]),
                name=str(item["name"]),
                family=str(item["family"]),
                platform=str(item["platform"]),
                engine=ClientEngine(str(item["engine"])),
                market_share=float(item.get("market_share", 0)),
                notes=str(item.get("notes", "")),
                tags=tuple(str(t) for t in item.get("tags", [])),
            )
        )
    return tuple(clients)


def _parse_properties(data: dict[str, Any]) -> tuple[CSSProperty, ...]:
    """Parse css_properties.yaml into CSSProperty tuples."""
    raw = cast(list[dict[str, Any]], data.get("properties", []))
    props: list[CSSProperty] = []
    for item in raw:
        value = item.get("value")
        props.append(
            CSSProperty(
                id=str(item["id"]),
                property_name=str(item["property_name"]),
                value=str(value) if value is not None else None,
                category=CSSCategory(str(item.get("category", "other"))),
                description=str(item.get("description", "")),
                mdn_url=str(item.get("mdn_url", "")),
                tags=tuple(str(t) for t in item.get("tags", [])),
            )
        )
    return tuple(props)


def _parse_support(data: dict[str, Any]) -> tuple[SupportEntry, ...]:
    """Parse support_matrix.yaml into SupportEntry tuples."""
    raw = cast(list[dict[str, Any]], data.get("support", []))
    entries: list[SupportEntry] = []
    for item in raw:
        entries.append(
            SupportEntry(
                property_id=str(item["property_id"]),
                client_id=str(item["client_id"]),
                level=SupportLevel(str(item["level"])),
                notes=str(item.get("notes", "")),
                fallback_ids=tuple(str(f) for f in item.get("fallback_ids", [])),
                workaround=str(item.get("workaround", "")),
            )
        )
    return tuple(entries)


def _parse_fallbacks(data: dict[str, Any]) -> tuple[Fallback, ...]:
    """Parse fallbacks.yaml into Fallback tuples."""
    raw = cast(list[dict[str, Any]], data.get("fallbacks", []))
    fbs: list[Fallback] = []
    for item in raw:
        fbs.append(
            Fallback(
                id=str(item["id"]),
                source_property_id=str(item["source_property_id"]),
                target_property_id=str(item["target_property_id"]),
                client_ids=tuple(str(c) for c in item.get("client_ids", [])),
                technique=str(item.get("technique", "")),
                code_example=str(item.get("code_example", "")),
            )
        )
    return tuple(fbs)


def _build_registry(
    clients: tuple[EmailClient, ...],
    properties: tuple[CSSProperty, ...],
    support_entries: tuple[SupportEntry, ...],
    fallbacks: tuple[Fallback, ...],
) -> OntologyRegistry:
    """Build indexed registry from parsed data."""
    client_by_id = {c.id: c for c in clients}
    property_by_id = {p.id: p for p in properties}

    support_by_prop: dict[str, list[SupportEntry]] = {}
    support_by_client: dict[str, list[SupportEntry]] = {}
    support_lookup: dict[tuple[str, str], SupportEntry] = {}

    for entry in support_entries:
        support_by_prop.setdefault(entry.property_id, []).append(entry)
        support_by_client.setdefault(entry.client_id, []).append(entry)
        support_lookup[(entry.property_id, entry.client_id)] = entry

    fallback_by_source: dict[str, list[Fallback]] = {}
    for fb in fallbacks:
        fallback_by_source.setdefault(fb.source_property_id, []).append(fb)

    return OntologyRegistry(
        clients=clients,
        properties=properties,
        support_entries=support_entries,
        fallbacks=fallbacks,
        client_by_id=client_by_id,
        property_by_id=property_by_id,
        support_by_prop=support_by_prop,
        support_by_client=support_by_client,
        support_lookup=support_lookup,
        fallback_by_source=fallback_by_source,
    )


@functools.lru_cache(maxsize=1)
def load_ontology() -> OntologyRegistry:
    """Load and cache the email development ontology from YAML files.

    Cached at module level — YAML is read once per process.
    """
    clients_path = _DATA_DIR / "clients.yaml"
    props_path = _DATA_DIR / "css_properties.yaml"
    support_path = _DATA_DIR / "support_matrix.yaml"
    fallbacks_path = _DATA_DIR / "fallbacks.yaml"

    with clients_path.open(encoding="utf-8") as f:
        clients_data = yaml.safe_load(f)
    with props_path.open(encoding="utf-8") as f:
        props_data = yaml.safe_load(f)
    with support_path.open(encoding="utf-8") as f:
        support_data = yaml.safe_load(f)
    with fallbacks_path.open(encoding="utf-8") as f:
        fallbacks_data = yaml.safe_load(f)

    clients = _parse_clients(clients_data)
    properties = _parse_properties(props_data)
    support_entries = _parse_support(support_data)
    fallbacks = _parse_fallbacks(fallbacks_data)

    registry = _build_registry(clients, properties, support_entries, fallbacks)

    logger.info(
        "ontology.loaded",
        clients=len(clients),
        properties=len(properties),
        support_entries=len(support_entries),
        fallbacks=len(fallbacks),
    )
    return registry


def reload_ontology() -> OntologyRegistry:
    """Clear cache and reload ontology from YAML files.

    Used after sync updates YAML data on disk.
    """
    load_ontology.cache_clear()
    return load_ontology()
