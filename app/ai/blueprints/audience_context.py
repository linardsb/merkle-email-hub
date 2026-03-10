"""Audience context: persona → ontology → agent-readable constraints."""

from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.types import (
    EmailClient,
    SupportLevel,
)
from app.personas.schemas import PersonaResponse

# Persona email_client slug → ontology client IDs
# Maps persona slugs to all ontology clients in that family/platform
CLIENT_MAPPING: dict[str, list[str]] = {
    "gmail": ["gmail_web", "gmail_ios", "gmail_android"],
    "outlook-365": ["outlook_365_win"],
    "outlook-2019": ["outlook_2019_win"],
    "apple-mail": ["apple_mail_macos", "apple_mail_ios"],
    "samsung-mail": ["samsung_mail"],
    "yahoo": ["yahoo_web", "yahoo_ios", "yahoo_android"],
    "thunderbird": ["thunderbird"],
    "outlook-mac": ["outlook_mac"],
    "outlook-web": ["outlook_web"],
    "aol": ["aol_web"],
    "protonmail": ["protonmail_web"],
}


@dataclass(frozen=True)
class AudienceConstraint:
    """A CSS property that is unsupported/partial for the target audience."""

    property_id: str
    property_name: str
    category: str
    level: SupportLevel
    client_name: str
    client_id: str
    fallback_ids: tuple[str, ...]
    workaround: str


@dataclass(frozen=True)
class AudienceProfile:
    """Aggregated audience constraints from one or more personas."""

    persona_names: tuple[str, ...]
    client_ids: tuple[str, ...]
    clients: tuple[EmailClient, ...]
    constraints: tuple[AudienceConstraint, ...]
    dark_mode_required: bool
    mobile_viewports: tuple[int, ...]


def resolve_audience_clients(personas: list[PersonaResponse]) -> list[str]:
    """Resolve persona email_client slugs to ontology client IDs."""
    seen: set[str] = set()
    result: list[str] = []
    for persona in personas:
        mapped = CLIENT_MAPPING.get(persona.email_client, [])
        for cid in mapped:
            if cid not in seen:
                seen.add(cid)
                result.append(cid)
    return result


def build_audience_profile(personas: list[PersonaResponse]) -> AudienceProfile | None:
    """Build an audience profile from personas using the ontology registry."""
    if not personas:
        return None

    ontology = load_ontology()
    client_ids = resolve_audience_clients(personas)
    if not client_ids:
        return None

    clients: list[EmailClient] = []
    for cid in client_ids:
        client = ontology.get_client(cid)
        if client:
            clients.append(client)

    # Collect all unsupported/partial CSS properties across target clients
    constraints: list[AudienceConstraint] = []
    for client in clients:
        unsupported = ontology.properties_unsupported_by(client.id)
        for prop in unsupported:
            entry = ontology.get_support_entry(prop.id, client.id)
            level = entry.level if entry else SupportLevel.NONE
            fallback_ids = entry.fallback_ids if entry else ()
            workaround = entry.workaround if entry else ""
            constraints.append(
                AudienceConstraint(
                    property_id=prop.id,
                    property_name=prop.property_name,
                    category=prop.category.value
                    if hasattr(prop.category, "value")
                    else str(prop.category),
                    level=level,
                    client_name=client.name,
                    client_id=client.id,
                    fallback_ids=fallback_ids,
                    workaround=workaround,
                )
            )

    dark_mode_required = any(p.dark_mode for p in personas)
    mobile_viewports = tuple(p.viewport_width for p in personas if p.viewport_width <= 480)

    return AudienceProfile(
        persona_names=tuple(p.name for p in personas),
        client_ids=tuple(client_ids),
        clients=tuple(clients),
        constraints=tuple(constraints),
        dark_mode_required=dark_mode_required,
        mobile_viewports=mobile_viewports,
    )


def format_audience_context(profile: AudienceProfile) -> str:
    """Format audience profile as agent-readable context string."""
    parts: list[str] = []
    parts.append("--- TARGET AUDIENCE CONSTRAINTS ---")
    parts.append(f"Personas: {', '.join(profile.persona_names)}")
    parts.append(f"Email Clients: {', '.join(c.name for c in profile.clients)}")

    if profile.dark_mode_required:
        parts.append(
            "REQUIREMENT: Dark mode support is required "
            "(include color-scheme meta + prefers-color-scheme)"
        )

    if profile.mobile_viewports:
        viewport_str = ", ".join(str(v) + "px" for v in profile.mobile_viewports)
        parts.append(f"REQUIREMENT: Mobile-responsive design needed (viewports: {viewport_str})")

    # Group constraints by category for readability
    by_category: dict[str, list[AudienceConstraint]] = {}
    for c in profile.constraints:
        by_category.setdefault(c.category, []).append(c)

    if by_category:
        parts.append("\nCSS PROPERTIES TO AVOID (unsupported by target clients):")
        for category, items in sorted(by_category.items()):
            # Deduplicate by property_name, show which clients don't support
            prop_clients: dict[str, list[str]] = {}
            prop_workarounds: dict[str, str] = {}
            for item in items:
                prop_clients.setdefault(item.property_name, []).append(item.client_name)
                if item.workaround and item.property_name not in prop_workarounds:
                    prop_workarounds[item.property_name] = item.workaround

            parts.append(f"\n  [{category.upper()}]")
            for prop_name, client_list in sorted(prop_clients.items()):
                line = f"  - {prop_name}: unsupported in {', '.join(sorted(set(client_list)))}"
                if prop_name in prop_workarounds:
                    line += f" → use: {prop_workarounds[prop_name]}"
                parts.append(line)
    else:
        parts.append("\nNo CSS restrictions — all properties supported by target clients.")

    parts.append("--- END AUDIENCE CONSTRAINTS ---")
    return "\n".join(parts)
