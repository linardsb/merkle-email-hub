"""Generate structured compatibility brief data for frontend display."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.types import CSSProperty, EmailClient

logger = get_logger(__name__)


@dataclass(frozen=True)
class UnsupportedProperty:
    """A CSS property unsupported by a specific email client."""

    css: str
    fallback: str | None
    technique: str | None


@dataclass(frozen=True)
class ClientProfile:
    """Compatibility profile for a single email client."""

    id: str
    name: str
    platform: str
    engine: str
    market_share: float
    notes: str | None
    unsupported_count: int
    unsupported_properties: list[UnsupportedProperty] = field(default_factory=list)


@dataclass(frozen=True)
class RiskMatrixEntry:
    """A CSS property unsupported by multiple target clients."""

    css: str
    unsupported_in: list[str]
    fallback: str | None


@dataclass(frozen=True)
class CompatibilityBrief:
    """Structured compatibility brief for a project's target clients."""

    client_count: int
    total_risky_properties: int
    dark_mode_warning: bool
    clients: list[ClientProfile] = field(default_factory=list)
    risk_matrix: list[RiskMatrixEntry] = field(default_factory=list)


def generate_compatibility_brief(client_ids: list[str]) -> CompatibilityBrief | None:
    """Build structured brief from ontology. Returns None if no valid clients."""
    onto = load_ontology()

    # Resolve clients — skip unknown IDs gracefully
    clients: list[EmailClient] = []
    for cid in client_ids:
        client = onto.get_client(cid)
        if client:
            clients.append(client)
        else:
            logger.warning("compatibility_brief.unknown_client_id", client_id=cid)

    if not clients:
        return None

    # Build per-client profiles (cache unsupported lookups for reuse in risk matrix)
    total_risky: set[str] = set()
    client_profiles: list[ClientProfile] = []
    unsupported_by_client: dict[str, list[CSSProperty]] = {}

    for client in clients:
        unsupported = onto.properties_unsupported_by(client.id)
        unsupported_by_client[client.id] = unsupported
        total_risky.update(p.id for p in unsupported)

        props: list[UnsupportedProperty] = []
        for prop in unsupported:
            css_decl = f"{prop.property_name}: {prop.value}" if prop.value else prop.property_name
            fallbacks = onto.fallbacks_for(prop.id)
            relevant = [fb for fb in fallbacks if client.id in fb.client_ids]

            if relevant:
                fb = relevant[0]
                target = onto.get_property(fb.target_property_id)
                fallback_text = (
                    f"{target.property_name}: {target.value}" if target and target.value
                    else target.property_name if target
                    else fb.target_property_id
                )
                props.append(UnsupportedProperty(
                    css=css_decl, fallback=fallback_text, technique=fb.technique,
                ))
            else:
                props.append(UnsupportedProperty(css=css_decl, fallback=None, technique=None))

        client_profiles.append(ClientProfile(
            id=client.id,
            name=client.name,
            platform=client.platform,
            engine=client.engine.value,
            market_share=client.market_share,
            notes=client.notes or None,
            unsupported_count=len(unsupported),
            unsupported_properties=props,
        ))

    # Build risk matrix: properties unsupported by 2+ clients (reuse cached lookups)
    prop_fail_count: dict[str, list[str]] = {}
    for client in clients:
        for prop in unsupported_by_client[client.id]:
            prop_fail_count.setdefault(prop.id, []).append(client.name)

    risk_matrix: list[RiskMatrixEntry] = []
    for pid in sorted(prop_fail_count, key=lambda p: len(prop_fail_count[p]), reverse=True):
        names = prop_fail_count[pid]
        if len(names) < 2:
            continue
        risk_prop = onto.get_property(pid)
        if not risk_prop:
            continue
        css_decl = (
            f"{risk_prop.property_name}: {risk_prop.value}"
            if risk_prop.value
            else risk_prop.property_name
        )
        fallbacks = onto.fallbacks_for(pid)
        fb_text = fallbacks[0].technique if fallbacks else None
        risk_matrix.append(RiskMatrixEntry(css=css_decl, unsupported_in=names, fallback=fb_text))

    # Dark mode warning: Word engine has worst dark mode support
    dark_mode_warning = any(c.engine.value.lower() == "word" for c in clients)

    logger.info(
        "compatibility_brief.generated",
        client_count=len(clients),
        risky_properties=len(total_risky),
    )

    return CompatibilityBrief(
        client_count=len(clients),
        total_risky_properties=len(total_risky),
        dark_mode_warning=dark_mode_warning,
        clients=client_profiles,
        risk_matrix=risk_matrix,
    )
