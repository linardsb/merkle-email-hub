"""Detect component references in HTML and format metadata for agent context."""

import re

from app.ai.blueprints.protocols import ComponentMeta

_COMPONENT_RE = re.compile(
    r'<component\s+src="components/([^"]+?)(?:\.html)?"',
    re.IGNORECASE,
)


def detect_component_refs(html: str) -> list[str]:
    """Extract deduplicated component slugs from Maizzle ``<component>`` tags."""
    return list(dict.fromkeys(_COMPONENT_RE.findall(html)))


def format_component_context(components: list[ComponentMeta]) -> str:
    """Format component metadata as agent-readable context block."""
    if not components:
        return ""
    parts = ["--- COMPONENT CONTEXT ---"]
    for c in components:
        parts.append(f"\n## {c.name} ({c.slug}) [{c.category}]")
        if c.description:
            parts.append(c.description)
        if c.compatibility:
            parts.append(
                "Compatibility: " + ", ".join(f"{k}: {v}" for k, v in c.compatibility.items())
            )
        if c.html_snippet:
            parts.append(f"HTML preview: {c.html_snippet[:300]}")
    return "\n".join(parts)
