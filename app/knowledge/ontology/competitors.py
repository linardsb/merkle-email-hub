"""Competitive intelligence types and registry."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from app.core.logging import get_logger

logger = get_logger(__name__)

_DATA_DIR = Path(__file__).parent / "data"


@dataclass(frozen=True)
class CompetitorCapability:
    """A single capability/feature offered by a competitor."""

    id: str  # e.g. "amp_email", "dark_mode_preview"
    name: str  # Human-readable: "AMP for Email"
    category: str  # "interactive", "visual", "export", "testing", "builder"
    description: str = ""


@dataclass(frozen=True)
class Competitor:
    """An email development platform that competes with the Hub."""

    id: str  # e.g. "stripo", "parcel"
    name: str  # "Stripo"
    homepage_url: str = ""  # Public URL
    category: str = ""  # "visual_builder", "code_editor", "platform"
    pricing_tier: str = ""  # "freemium", "paid", "enterprise"
    target_market: str = ""  # "ecommerce", "enterprise", "agencies"
    capabilities: tuple[str, ...] = ()  # Capability IDs this competitor supports
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class HubCapability:
    """A technique/feature the Hub offers (for gap analysis vs competitors)."""

    id: str  # Matches CompetitorCapability.id where overlapping
    name: str
    category: str
    agent: str = ""  # Which Hub agent provides this (e.g. "innovation", "dark_mode")
    description: str = ""


class CompetitorRegistry:
    """Immutable, indexed view of competitive intelligence data."""

    __slots__ = (
        "_capability_by_id",
        "_competitor_by_id",
        "_competitors_by_capability",
        "_hub_capability_by_id",
        "capabilities",
        "competitors",
        "hub_capabilities",
    )

    def __init__(
        self,
        *,
        competitors: tuple[Competitor, ...],
        capabilities: tuple[CompetitorCapability, ...],
        hub_capabilities: tuple[HubCapability, ...],
    ) -> None:
        self.competitors = competitors
        self.capabilities = capabilities
        self.hub_capabilities = hub_capabilities

        self._competitor_by_id: dict[str, Competitor] = {c.id: c for c in competitors}
        self._capability_by_id: dict[str, CompetitorCapability] = {c.id: c for c in capabilities}
        self._hub_capability_by_id: dict[str, HubCapability] = {h.id: h for h in hub_capabilities}

        # Reverse index: capability_id → list of competitors supporting it
        self._competitors_by_capability: dict[str, list[Competitor]] = {}
        for comp in competitors:
            for cap_id in comp.capabilities:
                self._competitors_by_capability.setdefault(cap_id, []).append(comp)

    def get_competitor(self, competitor_id: str) -> Competitor | None:
        return self._competitor_by_id.get(competitor_id)

    def get_capability(self, capability_id: str) -> CompetitorCapability | None:
        return self._capability_by_id.get(capability_id)

    def competitors_supporting(self, capability_id: str) -> list[Competitor]:
        """All competitors that support a given capability."""
        return self._competitors_by_capability.get(capability_id, [])

    def capabilities_of(self, competitor_id: str) -> list[CompetitorCapability]:
        """All capabilities of a given competitor."""
        comp = self._competitor_by_id.get(competitor_id)
        if not comp:
            return []
        return [
            self._capability_by_id[cid]
            for cid in comp.capabilities
            if cid in self._capability_by_id
        ]

    def hub_unique_capabilities(self) -> list[HubCapability]:
        """Capabilities the Hub has that NO competitor supports."""
        competitor_cap_ids = {cid for comp in self.competitors for cid in comp.capabilities}
        return [h for h in self.hub_capabilities if h.id not in competitor_cap_ids]

    def competitor_unique_capabilities(self, competitor_id: str) -> list[CompetitorCapability]:
        """Capabilities a competitor has that the Hub does NOT."""
        comp = self._competitor_by_id.get(competitor_id)
        if not comp:
            return []
        hub_ids = {h.id for h in self.hub_capabilities}
        return [
            self._capability_by_id[cid]
            for cid in comp.capabilities
            if cid not in hub_ids and cid in self._capability_by_id
        ]

    def get_hub_capability(self, capability_id: str) -> HubCapability | None:
        """Look up a Hub capability by ID."""
        return self._hub_capability_by_id.get(capability_id)

    def hub_vs_competitor(self, competitor_id: str) -> tuple[list[str], list[str], list[str]]:
        """Compare Hub vs competitor. Returns (hub_only, shared, competitor_only) capability IDs."""
        comp = self._competitor_by_id.get(competitor_id)
        if not comp:
            return [h.id for h in self.hub_capabilities], [], []

        hub_ids = {h.id for h in self.hub_capabilities}
        comp_ids = set(comp.capabilities)

        hub_only = sorted(hub_ids - comp_ids)
        shared = sorted(hub_ids & comp_ids)
        competitor_only = sorted(comp_ids - hub_ids)
        return hub_only, shared, competitor_only


def _parse_capabilities(data: dict[str, Any]) -> tuple[CompetitorCapability, ...]:
    raw = cast(list[dict[str, Any]], data.get("capabilities", []))
    return tuple(
        CompetitorCapability(
            id=str(item["id"]),
            name=str(item["name"]),
            category=str(item.get("category", "")),
            description=str(item.get("description", "")),
        )
        for item in raw
    )


def _parse_competitors(data: dict[str, Any]) -> tuple[Competitor, ...]:
    raw = cast(list[dict[str, Any]], data.get("competitors", []))
    return tuple(
        Competitor(
            id=str(item["id"]),
            name=str(item["name"]),
            homepage_url=str(item.get("homepage_url", "")),
            category=str(item.get("category", "")),
            pricing_tier=str(item.get("pricing_tier", "")),
            target_market=str(item.get("target_market", "")),
            capabilities=tuple(str(c) for c in item.get("capabilities", [])),
            strengths=tuple(str(s) for s in item.get("strengths", [])),
            weaknesses=tuple(str(w) for w in item.get("weaknesses", [])),
            notes=str(item.get("notes", "")),
        )
        for item in raw
    )


def _parse_hub_capabilities(data: dict[str, Any]) -> tuple[HubCapability, ...]:
    raw = cast(list[dict[str, Any]], data.get("hub_capabilities", []))
    return tuple(
        HubCapability(
            id=str(item["id"]),
            name=str(item["name"]),
            category=str(item.get("category", "")),
            agent=str(item.get("agent", "")),
            description=str(item.get("description", "")),
        )
        for item in raw
    )


@functools.lru_cache(maxsize=1)
def load_competitors() -> CompetitorRegistry:
    """Load and cache competitive intelligence from YAML files.

    Cached at module level — YAML is read once per process.
    """
    competitors_path = _DATA_DIR / "competitors.yaml"
    hub_path = _DATA_DIR / "hub_capabilities.yaml"

    with competitors_path.open(encoding="utf-8") as f:
        comp_data = yaml.safe_load(f)

    with hub_path.open(encoding="utf-8") as f:
        hub_data = yaml.safe_load(f)

    capabilities = _parse_capabilities(comp_data)
    competitors = _parse_competitors(comp_data)
    hub_capabilities = _parse_hub_capabilities(hub_data)

    registry = CompetitorRegistry(
        competitors=competitors,
        capabilities=capabilities,
        hub_capabilities=hub_capabilities,
    )

    logger.info(
        "competitors.loaded",
        competitors=len(competitors),
        capabilities=len(capabilities),
        hub_capabilities=len(hub_capabilities),
    )
    return registry


def reload_competitors() -> CompetitorRegistry:
    """Clear cache and reload from YAML files."""
    load_competitors.cache_clear()
    return load_competitors()
