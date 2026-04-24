"""CSS conversion rules driven by ontology fallbacks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.knowledge.ontology.registry import OntologyRegistry, load_ontology
from app.knowledge.ontology.types import SupportLevel


@dataclass(frozen=True)
class CSSConversion:
    """A single CSS conversion applied during compilation."""

    original_property: str
    original_value: str
    replacement_property: str
    replacement_value: str
    reason: str
    affected_clients: tuple[str, ...]


def get_conversions_for_property(
    property_name: str,
    value: str | None,
    target_client_ids: list[str],
    registry: OntologyRegistry | None = None,
) -> list[CSSConversion]:
    """Get applicable conversions for a CSS property given target clients.

    Returns conversions only when:
    1. The property is unsupported by at least one target client
    2. A fallback exists in the ontology for that property
    """
    onto = registry or load_ontology()
    prop = onto.find_property_by_name(property_name, value)
    if prop is None:
        return []

    # Check which target clients don't support this property
    unsupported_ids: list[str] = []
    for cid in target_client_ids:
        level = onto.get_support(prop.id, cid)
        if level == SupportLevel.NONE:
            unsupported_ids.append(cid)

    if not unsupported_ids:
        return []

    # Get ontology fallbacks
    fallbacks = onto.fallbacks_for(prop.id)
    if not fallbacks:
        return []

    conversions: list[CSSConversion] = []
    for fb in fallbacks:
        target_prop = onto.get_property(fb.target_property_id)
        if target_prop is None:
            continue

        # If fallback is client-scoped, only apply if relevant
        if fb.client_ids:
            relevant = [cid for cid in unsupported_ids if cid in fb.client_ids]
            if not relevant:
                continue
            affected = tuple(relevant)
        else:
            affected = tuple(unsupported_ids)

        conversions.append(
            CSSConversion(
                original_property=property_name,
                original_value=value or "",
                replacement_property=target_prop.property_name,
                replacement_value=target_prop.value or "",
                reason=fb.technique or f"Fallback for {property_name}",
                affected_clients=affected,
            )
        )

    return conversions


# --------------------------------------------------------------------------- #
# Built-in conversion functions for common patterns                           #
# These handle structural HTML changes that ontology fallbacks can't express  #
# --------------------------------------------------------------------------- #

# Bounded quantifiers prevent polynomial backtracking (py/polynomial-redos).
_VAR_RE = re.compile(r"var\(\s{0,10}--([a-zA-Z0-9_-]{1,200})\s{0,10}(?:,\s{0,10}([^)]{0,1000}))?\s{0,10}\)")


def resolve_css_variables(css_text: str, variables: dict[str, str]) -> str:
    """Resolve var(--x) references to computed values.

    Falls back to the default value in var(--x, default) if variable not found.
    """

    def _replace(m: re.Match[str]) -> str:
        name = m.group(1)
        default = m.group(2)
        return variables.get(name, default.strip() if default else m.group(0))

    return _VAR_RE.sub(_replace, css_text)


def should_remove_property(
    property_name: str,
    value: str | None,
    target_client_ids: list[str],
    registry: OntologyRegistry | None = None,
) -> bool:
    """Check if a CSS property should be removed (zero support, no fallback)."""
    onto = registry or load_ontology()
    prop = onto.find_property_by_name(property_name, value)
    if prop is None:
        return False  # Unknown property — keep it

    # Must be unsupported by ALL target clients
    for cid in target_client_ids:
        level = onto.get_support(prop.id, cid)
        if level != SupportLevel.NONE:
            return False

    # No fallback available — safe to remove
    fallbacks = onto.fallbacks_for(prop.id)
    return len(fallbacks) == 0
