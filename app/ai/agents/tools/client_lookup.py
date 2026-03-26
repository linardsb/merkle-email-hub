"""Agent tools for querying the email client rendering matrix.

Provides ``ClientLookupTool`` and ``MultiClientLookupTool`` — lightweight,
deterministic alternatives to the Knowledge agent's RAG pipeline.  Agents
call these during LLM execution to query specific CSS support, dark mode
behavior, known bugs, size limits, or font support for any email client
in the centralized matrix (Phase 32.1).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Literal

from pydantic import BaseModel

from app.core.logging import get_logger
from app.knowledge.client_matrix import (
    ClientMatrix,
    CSSSupport,
    load_client_matrix,
)

logger = get_logger(__name__)

QueryType = Literal["css_support", "dark_mode", "known_bugs", "size_limits", "font_support"]
_VALID_QUERY_TYPES: frozenset[str] = frozenset(
    {"css_support", "dark_mode", "known_bugs", "size_limits", "font_support"}
)


# ── Parameter / result models ────────────────────────────────────────


class ClientLookupParams(BaseModel):
    """Parameters for a single client lookup query."""

    query_type: QueryType
    client_id: str
    property: str | None = None


class ClientLookupResult(BaseModel):
    """Structured result from a client lookup query."""

    client: str
    query_type: str
    result: dict[str, Any]
    workaround: str | None = None
    confidence: float = 1.0


# ── Internal helpers ─────────────────────────────────────────────────


def _css_support_to_dict(css: CSSSupport) -> dict[str, Any]:
    return {
        "support": css.support.value,
        "workaround": css.workaround,
        "notes": css.notes,
    }


def _execute_single_lookup(
    matrix: ClientMatrix,
    query_type: QueryType,
    client_id: str,
    prop: str | None,
) -> ClientLookupResult:
    """Core lookup logic shared by single and batch tools."""
    profile = matrix.get_client(client_id)
    if profile is None:
        available = [c.id for c in matrix.clients]
        return ClientLookupResult(
            client=client_id,
            query_type=query_type,
            result={"error": "Unknown client", "available_clients": available},
        )

    result: dict[str, Any]
    workaround: str | None = None

    if query_type == "css_support":
        if not prop:
            return ClientLookupResult(
                client=client_id,
                query_type=query_type,
                result={
                    "error": "property is required for css_support queries",
                },
            )
        css = matrix.get_css_support(client_id, prop)
        if css is None:
            result = {"support": "unknown", "notes": f"No data for property '{prop}'"}
        else:
            result = _css_support_to_dict(css)
            workaround = css.workaround or None

    elif query_type == "dark_mode":
        dm = matrix.get_dark_mode(client_id)
        if dm is None:
            result = {"error": "No dark mode data"}
        else:
            result = {
                "type": dm.type,
                "developer_control": dm.developer_control,
                "selectors": list(dm.selectors),
                "notes": dm.notes,
            }

    elif query_type == "known_bugs":
        bugs = matrix.get_known_bugs(client_id)
        result = {
            "bugs": [asdict(b) for b in bugs],
            "count": len(bugs),
        }

    elif query_type == "size_limits":
        sl = profile.size_limits
        result = {
            "clip_threshold_kb": sl.clip_threshold_kb,
            "style_block": sl.style_block,
        }

    elif query_type == "font_support":
        fonts = profile.supported_fonts
        if isinstance(fonts, str):
            result = {"fonts": fonts, "notes": "All fonts supported"}
        else:
            result = {"fonts": list(fonts), "count": len(fonts)}

    else:  # pragma: no cover — exhaustive Literal
        result = {"error": f"Unknown query_type: {query_type}"}

    return ClientLookupResult(
        client=client_id,
        query_type=query_type,
        result=result,
        workaround=workaround,
    )


# ── Tool classes (ToolProvider protocol) ─────────────────────────────


class ClientLookupTool:
    """Single-client lookup tool implementing the ToolProvider protocol."""

    name: str = "lookup_client_support"
    description: str = (
        "Look up email client rendering support for a CSS property, dark mode "
        "behavior, known bugs, or size limits. Returns structured data from the "
        "authoritative client rendering matrix."
    )

    async def execute(self, **params: object) -> str:
        """Execute a single client lookup query."""
        query_type = str(params.get("query_type", ""))
        client_id = str(params.get("client_id", ""))
        prop = params.get("property")
        prop_str = str(prop) if prop is not None else None

        # Validate query_type
        if query_type not in _VALID_QUERY_TYPES:
            error = {
                "error": f"Invalid query_type: {query_type}",
                "valid_types": sorted(_VALID_QUERY_TYPES),
            }
            return json.dumps(error)

        matrix = load_client_matrix()
        result = _execute_single_lookup(
            matrix,
            query_type,  # type: ignore[arg-type]
            client_id,
            prop_str,
        )

        logger.info(
            "agents.client_lookup.query",
            query_type=query_type,
            client_id=client_id,
            property=prop_str,
        )

        return result.model_dump_json()


class MultiClientLookupTool:
    """Batch client lookup tool implementing the ToolProvider protocol."""

    name: str = "lookup_client_support_batch"
    description: str = (
        "Batch lookup of email client rendering support across multiple clients "
        "and/or properties. Returns a matrix of results — useful for comparing "
        "support across target clients."
    )

    async def execute(self, **params: object) -> str:
        """Execute a batch client lookup query."""
        raw_client_ids: object = params.get("client_ids", [])
        raw_properties: object = params.get("properties", [])
        query_type = str(params.get("query_type", "css_support"))

        client_ids: list[str] = (
            [str(item) for item in raw_client_ids]  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType]
            if isinstance(raw_client_ids, list)
            else []
        )
        properties: list[str] = (
            [str(item) for item in raw_properties]  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType]
            if isinstance(raw_properties, list)
            else []
        )

        if query_type not in _VALID_QUERY_TYPES:
            error = {
                "error": f"Invalid query_type: {query_type}",
                "valid_types": sorted(_VALID_QUERY_TYPES),
            }
            return json.dumps(error)

        matrix = load_client_matrix()
        results: list[dict[str, Any]] = []

        # If properties are given, iterate client x property
        # Otherwise, iterate clients only (for non-css queries)
        if properties:
            for cid in client_ids:
                for prop in properties:
                    r = _execute_single_lookup(
                        matrix,
                        query_type,  # type: ignore[arg-type]
                        cid,
                        prop,
                    )
                    entry = r.model_dump()
                    entry["property"] = prop
                    results.append(entry)
        else:
            for cid in client_ids:
                r = _execute_single_lookup(
                    matrix,
                    query_type,  # type: ignore[arg-type]
                    cid,
                    None,
                )
                results.append(r.model_dump())

        logger.info(
            "agents.client_lookup.batch_query",
            query_type=query_type,
            client_count=len(client_ids),
            property_count=len(properties),
        )

        return json.dumps({"results": results})


# ── Module-level singletons (stateless — safe to reuse) ──────────────

_CLIENT_LOOKUP_TOOL = ClientLookupTool()
_MULTI_CLIENT_LOOKUP_TOOL = MultiClientLookupTool()


# ── Tool definitions for LLM function calling ───────────────────────


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return JSON Schema tool definitions for both lookup tools."""
    return [
        {
            "name": ClientLookupTool.name,
            "description": ClientLookupTool.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": [
                            "css_support",
                            "dark_mode",
                            "known_bugs",
                            "size_limits",
                            "font_support",
                        ],
                        "description": "Type of client rendering query.",
                    },
                    "client_id": {
                        "type": "string",
                        "description": "Email client identifier (e.g. 'outlook_365_win', 'gmail_web').",
                    },
                    "property": {
                        "type": "string",
                        "description": "CSS property name — required for css_support queries.",
                    },
                },
                "required": ["query_type", "client_id"],
            },
        },
        {
            "name": MultiClientLookupTool.name,
            "description": MultiClientLookupTool.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": [
                            "css_support",
                            "dark_mode",
                            "known_bugs",
                            "size_limits",
                            "font_support",
                        ],
                        "description": "Type of client rendering query.",
                    },
                    "client_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of email client identifiers.",
                    },
                    "properties": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of CSS property names (for css_support queries).",
                    },
                },
                "required": ["query_type", "client_ids"],
            },
        },
    ]
