"""MCP response caching, schema compression, and batch execution."""

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Protocol, cast, runtime_checkable

from app.core.config import get_settings
from app.core.logging import get_logger
from app.mcp import MCPContext

logger = get_logger(__name__)


# ── Response Cache ──────────────────────────────────────────────────


@dataclass(frozen=True)
class CacheEntry:
    """Single cached MCP tool response."""

    response: str
    created_at: float
    tool_name: str


class MCPResponseCache:
    """In-memory LRU response cache for read-only MCP tools.

    Uses ``OrderedDict`` for O(1) LRU eviction.  Thread-safe via a
    ``threading.Lock`` (FastMCP is async but cache dict ops are sync).
    """

    WRITE_TOOLS: frozenset[str] = frozenset(
        {
            "run_agent",
            "scaffolder_generate",
            "dark_mode_apply",
            "content_rewrite",
            "outlook_fix",
            "accessibility_fix",
            "personalisation_apply",
            "code_review",
            "innovation_generate",
            "css_optimize",
            "schema_markup_inject",
        }
    )

    CACHEABLE_TOOLS: frozenset[str] = frozenset(
        {
            "qa_check",
            "email_production_readiness",
            "chaos_test",
            "outlook_analyze",
            "gmail_predict",
            "css_support_check",
            "search_knowledge",
            "search_css_property",
            "rendering_confidence",
            "rendering_fidelity_report",
            "template_search",
            "estimate_cost",
            "deliverability_score",
            "bimi_check",
        }
    )

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300) -> None:
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    @staticmethod
    def _make_key(tool_name: str, params: dict[str, Any]) -> str:
        raw = f"{tool_name}:{json.dumps(params, sort_keys=True, separators=(',', ':'))}"
        return hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

    def get(self, tool_name: str, params: dict[str, Any]) -> str | None:
        """Return cached response or ``None`` on miss / expiry / non-cacheable."""
        if tool_name not in self.CACHEABLE_TOOLS:
            return None

        key = self._make_key(tool_name, params)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None

            if (time.monotonic() - entry.created_at) > self._ttl_seconds:
                del self._entries[key]
                self._misses += 1
                return None

            # Move to end for LRU freshness
            self._entries.move_to_end(key)
            self._hits += 1
            return entry.response

    def put(self, tool_name: str, params: dict[str, Any], response: str) -> None:
        """Store a response.  Skips non-cacheable tools.  LRU-evicts at capacity."""
        if tool_name not in self.CACHEABLE_TOOLS:
            return

        key = self._make_key(tool_name, params)
        entry = CacheEntry(
            response=response,
            created_at=time.monotonic(),
            tool_name=tool_name,
        )
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                self._entries[key] = entry
                return

            if len(self._entries) >= self._max_size:
                self._entries.popitem(last=False)
                self._evictions += 1

            self._entries[key] = entry

    def invalidate(self, tool_name: str | None = None) -> int:
        """Clear all entries, or only entries for *tool_name*.  Returns count removed."""
        with self._lock:
            if tool_name is None:
                count = len(self._entries)
                self._entries.clear()
                return count

            keys = [k for k, v in self._entries.items() if v.tool_name == tool_name]
            for k in keys:
                del self._entries[k]
            return len(keys)

    def stats(self) -> dict[str, int]:
        """Return cache hit/miss/size/eviction counters."""
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._entries),
                "evictions": self._evictions,
            }


# ── Singleton lifecycle ─────────────────────────────────────────────

_mcp_cache: MCPResponseCache | None = None


def get_mcp_cache() -> MCPResponseCache:
    """Return the module-level MCP cache singleton, lazily created."""
    global _mcp_cache
    if _mcp_cache is None:
        settings = get_settings()
        _mcp_cache = MCPResponseCache(
            max_size=settings.mcp.cache_max_size,
            ttl_seconds=settings.mcp.cache_ttl,
        )
    return _mcp_cache


def clear_mcp_cache() -> None:
    """Reset the singleton (for tests)."""
    global _mcp_cache
    _mcp_cache = None


# ── Schema Compression ──────────────────────────────────────────────


def compress_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove verbose fields from a tool input schema.

    - Strip ``description`` from nested properties (keep top-level)
    - Collapse single-element ``anyOf`` unions
    - Remove ``title`` from properties
    - Remove ``default`` fields
    """
    return _compress_node(schema, is_root=True)


def _compress_node(node: dict[str, Any], *, is_root: bool = False) -> dict[str, Any]:
    """Recursively compress a JSON Schema node."""
    result: dict[str, Any] = {}
    for key, value in node.items():
        # Strip title from all nodes
        if key == "title":
            continue

        # Strip description from non-root nodes
        if key == "description" and not is_root:
            continue

        # Strip default values
        if key == "default":
            continue

        # Collapse single-element anyOf
        if key == "anyOf" and isinstance(value, list):
            anyof_items = cast(list[dict[str, Any]], value)
            if len(anyof_items) != 1:
                result[key] = value
                continue
            merged = _compress_node(anyof_items[0])
            result.update(merged)
            continue

        # Recurse into properties
        if key == "properties" and isinstance(value, dict):
            props_dict = cast(dict[str, dict[str, Any]], value)
            result[key] = {pn: _compress_node(ps) for pn, ps in props_dict.items()}
            continue

        # Recurse into items
        if key == "items" and isinstance(value, dict):
            items_dict = cast(dict[str, Any], value)
            result[key] = _compress_node(items_dict)
            continue

        result[key] = value

    return result


class SchemaRegistry:
    """Pre-compressed tool schemas loaded at server startup."""

    def __init__(self) -> None:
        self._original: dict[str, dict[str, Any]] = {}
        self._compressed: dict[str, dict[str, Any]] = {}

    def register(self, tool_name: str, schema: dict[str, Any]) -> None:
        """Register a tool schema and store its compressed form."""
        self._original[tool_name] = schema
        self._compressed[tool_name] = compress_schema(schema)

    def get_compressed(self, tool_name: str) -> dict[str, Any]:
        """Return the compressed schema for *tool_name*."""
        return self._compressed[tool_name]

    def get_original(self, tool_name: str) -> dict[str, Any]:
        """Return the original uncompressed schema for *tool_name*."""
        return self._original[tool_name]

    def compression_ratio(self, tool_name: str) -> float:
        """Return ``len(compressed) / len(original)`` as a float (lower = better)."""
        orig = json.dumps(self._original[tool_name], separators=(",", ":"))
        comp = json.dumps(self._compressed[tool_name], separators=(",", ":"))
        if not orig:
            return 1.0
        return len(comp) / len(orig)


_schema_registry: SchemaRegistry | None = None


def get_schema_registry() -> SchemaRegistry:
    """Return the module-level schema registry singleton."""
    global _schema_registry
    if _schema_registry is None:
        _schema_registry = SchemaRegistry()
    return _schema_registry


def clear_schema_registry() -> None:
    """Reset the singleton (for tests)."""
    global _schema_registry
    _schema_registry = None


# ── Batch Execution ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolCall:
    """A single tool invocation request."""

    tool_name: str
    params: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))


@dataclass(frozen=True)
class ToolResult:
    """Result of a single tool invocation."""

    tool_name: str
    result: str
    cached: bool
    error: str | None = None


@runtime_checkable
class ToolHandler(Protocol):
    """Protocol for async tool handlers."""

    async def __call__(self, **kwargs: Any) -> str: ...  # noqa: ANN401


async def batch_execute(
    calls: list[ToolCall],
    cache: MCPResponseCache,
    tool_handlers: dict[str, ToolHandler],
    ctx: MCPContext,
) -> list[ToolResult]:
    """Execute multiple tool calls, returning cached results immediately.

    Non-cached calls run concurrently via ``asyncio.gather`` with a
    semaphore bound of 5 to prevent overwhelming the system.
    Results are ordered to match the input *calls* list.
    """
    results: dict[int, ToolResult] = {}
    pending: list[tuple[int, ToolCall]] = []

    # Phase 1: serve from cache
    for idx, call in enumerate(calls):
        cached = cache.get(call.tool_name, call.params)
        if cached is not None:
            results[idx] = ToolResult(
                tool_name=call.tool_name,
                result=cached,
                cached=True,
            )
        else:
            pending.append((idx, call))

    # Phase 2: execute non-cached concurrently
    if pending:
        sem = asyncio.Semaphore(5)

        async def _run(idx: int, call: ToolCall) -> tuple[int, ToolResult]:
            async with sem:
                handler = tool_handlers.get(call.tool_name)
                if handler is None:
                    return idx, ToolResult(
                        tool_name=call.tool_name,
                        result="",
                        cached=False,
                        error=f"Unknown tool: {call.tool_name}",
                    )
                try:
                    response = await handler(ctx=ctx, **call.params)
                    cache.put(call.tool_name, call.params, response)
                    return idx, ToolResult(
                        tool_name=call.tool_name,
                        result=response,
                        cached=False,
                    )
                except Exception as exc:
                    logger.warning(
                        "mcp.batch_tool_error",
                        tool=call.tool_name,
                        error=str(exc),
                    )
                    return idx, ToolResult(
                        tool_name=call.tool_name,
                        result="",
                        cached=False,
                        error=str(exc),
                    )

        completed = await asyncio.gather(*[_run(idx, call) for idx, call in pending])
        results.update(dict(completed))

    return [results[i] for i in range(len(calls))]
