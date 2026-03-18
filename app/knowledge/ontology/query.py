"""Convenience query functions over the ontology registry."""

from __future__ import annotations

import re

from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.types import (
    ClientEngine,
    EmailClient,
    SupportLevel,
)

_STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
_INLINE_STYLE_RE = re.compile(r'style\s*=\s*"([^"]*)"', re.IGNORECASE)


def lookup_support(property_name: str, value: str | None, client_id: str) -> SupportLevel:
    """Look up support by CSS property name + value (not ID).

    Convenience for QA checks that parse raw CSS.
    Constructs property_id from name + value (e.g. "display" + "flex" -> "display_flex").
    """
    onto = load_ontology()
    prop_id = _property_id_from_css(property_name, value)
    return onto.get_support(prop_id, client_id)


def _extract_css_content(html: str) -> str:
    """Extract CSS content from <style> blocks and inline style attributes."""
    parts: list[str] = []
    for match in _STYLE_BLOCK_RE.finditer(html):
        parts.append(match.group(1))
    for match in _INLINE_STYLE_RE.finditer(html):
        parts.append(match.group(1))
    return "\n".join(parts).lower()


def unsupported_css_in_html(html: str) -> list[dict[str, object]]:
    """Scan HTML for CSS properties with known poor support.

    Returns list of dicts with property info and affected clients.
    Used by the QA css_support check. Only scans CSS contexts
    (<style> blocks and style= attributes), not HTML attributes.
    """
    onto = load_ontology()
    css_content = _extract_css_content(html)
    if not css_content:
        return []
    issues: list[dict[str, object]] = []

    for prop in onto.properties:
        # Build regex pattern that avoids matching as substring of longer property
        # e.g. "color-scheme:" should not match inside "prefers-color-scheme:"
        prop_escaped = re.escape(prop.property_name)
        if prop.value:
            val_escaped = re.escape(prop.value)
            pattern = rf"(?<![a-z\-]){prop_escaped}\s*:\s*{val_escaped}"
        else:
            pattern = rf"(?<![a-z\-]){prop_escaped}\s*:"

        if not re.search(pattern, css_content):
            continue

        # Check which clients don't support it
        unsupported_clients = onto.clients_not_supporting(prop.id)
        if not unsupported_clients:
            continue

        # Get fallbacks
        fallbacks = onto.fallbacks_for(prop.id)

        issues.append(
            {
                "property_id": prop.id,
                "property_name": prop.property_name,
                "value": prop.value,
                "category": prop.category.value,
                "unsupported_clients": [c.name for c in unsupported_clients],
                "unsupported_count": len(unsupported_clients),
                "fallback_available": len(fallbacks) > 0,
                "severity": _compute_severity(unsupported_clients),
            }
        )

    return issues


def unsupported_engines_in_html(html: str) -> list[dict[str, object]]:
    """Scan HTML for CSS properties with engine-level poor support.

    Returns list of dicts grouping issues by rendering engine.
    Complements unsupported_css_in_html() with engine-level aggregation.
    """
    onto = load_ontology()
    css_content = _extract_css_content(html)
    if not css_content:
        return []
    issues: list[dict[str, object]] = []

    for prop in onto.properties:
        prop_escaped = re.escape(prop.property_name)
        if prop.value:
            val_escaped = re.escape(prop.value)
            pattern = rf"(?<![a-z\-]){prop_escaped}\s*:\s*{val_escaped}"
        else:
            pattern = rf"(?<![a-z\-]){prop_escaped}\s*:"

        if not re.search(pattern, css_content):
            continue

        unsupported_engines = onto.engines_not_supporting(prop.id)
        if not unsupported_engines:
            continue

        engine_details: list[dict[str, object]] = []
        for engine in unsupported_engines:
            share = onto.engine_market_share(engine)
            engine_details.append({
                "engine": engine.value,
                "market_share": round(share, 1),
                "clients": [c.name for c in onto.clients_by_engine(engine)
                            if onto.get_support(prop.id, c.id) == SupportLevel.NONE],
            })

        total_engine_share = sum(d["market_share"] for d in engine_details)  # type: ignore[arg-type]
        issues.append({
            "property_id": prop.id,
            "property_name": prop.property_name,
            "value": prop.value,
            "unsupported_engines": engine_details,
            "total_engine_share": round(total_engine_share, 1),
            "severity": "error" if total_engine_share > 20.0 else "warning" if total_engine_share > 5.0 else "info",
        })

    return issues


def _property_id_from_css(property_name: str, value: str | None) -> str:
    """Convert CSS property name + value to ontology property ID."""
    name = property_name.strip().lower().replace("-", "_")
    if value:
        val = value.strip().lower().replace("-", "_")
        return f"{name}_{val}"
    return name


def _compute_severity(unsupported: list[EmailClient]) -> str:
    """Compute severity based on market share of unsupported clients."""
    total_share = sum(c.market_share for c in unsupported)
    if total_share > 20.0:
        return "error"
    if total_share > 5.0:
        return "warning"
    return "info"
