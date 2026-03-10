"""Detect graph context triggers and format knowledge graph results for agent context."""

import re

from app.knowledge.graph.protocols import GraphEntity, GraphSearchResult

# Keywords that indicate the agent would benefit from structured compatibility data.
# These cover the highest-impact domains: email client support, CSS quirks, and techniques.
_TRIGGER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:outlook|gmail|apple\s*mail|yahoo|aol|thunderbird)\b", re.IGNORECASE),
    re.compile(r"\b(?:dark\s*mode|prefers-color-scheme|color-scheme)\b", re.IGNORECASE),
    re.compile(r"\b(?:mso|vml|conditional|fallback)\b", re.IGNORECASE),
    re.compile(r"\b(?:css\s+support|compatibility|client\s+support)\b", re.IGNORECASE),
    re.compile(r"\b(?:responsive|media\s+query|viewport)\b", re.IGNORECASE),
    re.compile(r"\b(?:accessibility|wcag|alt\s+text|aria)\b", re.IGNORECASE),
    re.compile(r"\b(?:liquid|ampscript|personalisation|personalization)\b", re.IGNORECASE),
)


def should_fetch_graph_context(
    brief: str,
    html: str = "",
    qa_failures: list[str] | None = None,
    iteration: int = 0,
) -> bool:
    """Determine whether this node execution would benefit from graph context.

    Progressive disclosure: graph queries have latency cost, so only fetch when
    the task involves email client compatibility, CSS support, or known-tricky areas.

    Always fetch on retries (iteration > 0) since the agent is struggling and
    needs maximum context to self-correct.
    """
    if iteration > 0:
        return True

    combined = f"{brief} {html}"
    if qa_failures:
        combined += " " + " ".join(qa_failures)

    return any(pattern.search(combined) for pattern in _TRIGGER_PATTERNS)


def format_graph_context(results: list[GraphSearchResult]) -> str:
    """Format graph search results as an agent-readable context block.

    Outputs structured triplets when entity/relationship data is available,
    falls back to content summaries otherwise.
    """
    if not results:
        return ""

    parts = ["--- GRAPH KNOWLEDGE CONTEXT ---"]
    parts.append(
        "The following relationships are from the email development knowledge graph."
        " Use them to inform your decisions about compatibility and techniques."
    )

    for i, result in enumerate(results, 1):
        if result.relationships:
            for rel in result.relationships:
                source_name = _find_entity_name(rel.source_id, result.entities)
                target_name = _find_entity_name(rel.target_id, result.entities)
                rel_type = rel.relationship_type.replace("_", " ")
                parts.append(f"- {source_name} [{rel_type}] {target_name}")
                if rel.properties:
                    props = ", ".join(f"{k}: {v}" for k, v in rel.properties.items())
                    parts.append(f"  ({props})")
        elif result.content:
            parts.append(f"\n{i}. {result.content}")

    return "\n".join(parts)


def _find_entity_name(entity_id: str, entities: tuple[GraphEntity, ...]) -> str:
    """Look up entity name by ID, falling back to the ID itself."""
    for entity in entities:
        if entity.id == entity_id:
            return entity.name
    return entity_id
