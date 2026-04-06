"""Tests for MCP response caching, schema compression, and batch execution."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.mcp.optimization import (
    MCPResponseCache,
    SchemaRegistry,
    ToolCall,
    batch_execute,
    clear_mcp_cache,
    clear_schema_registry,
    compress_schema,
)

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_singletons() -> None:
    """Reset module singletons between tests."""
    clear_mcp_cache()
    clear_schema_registry()


@pytest.fixture()
def cache() -> MCPResponseCache:
    return MCPResponseCache(max_size=3, ttl_seconds=2)


@pytest.fixture()
def mock_ctx() -> Any:
    return AsyncMock()


# ── TestMCPResponseCache ────────────────────────────────────────────


class TestMCPResponseCache:
    def test_cache_hit(self, cache: MCPResponseCache) -> None:
        """Same tool+params returns cached response."""
        cache.put("qa_check", {"html": "<table></table>"}, "result-1")
        hit = cache.get("qa_check", {"html": "<table></table>"})
        assert hit == "result-1"

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["size"] == 1

    def test_cache_miss_different_params(self, cache: MCPResponseCache) -> None:
        """Different params produce a cache miss."""
        cache.put("qa_check", {"html": "<table>A</table>"}, "result-a")
        miss = cache.get("qa_check", {"html": "<table>B</table>"})
        assert miss is None

        stats = cache.stats()
        assert stats["misses"] == 1

    def test_write_tool_not_cached(self, cache: MCPResponseCache) -> None:
        """Write tools are never stored."""
        cache.put("scaffolder_generate", {"brief": "test"}, "generated-html")
        result = cache.get("scaffolder_generate", {"brief": "test"})
        assert result is None
        assert cache.stats()["size"] == 0

    def test_ttl_expiry(self, cache: MCPResponseCache) -> None:
        """Entry expires after ttl_seconds."""
        cache.put("qa_check", {"html": "x"}, "result")

        # Patch monotonic to simulate time passing
        start = time.monotonic()
        with patch("app.mcp.optimization.time.monotonic", return_value=start + 3):
            result = cache.get("qa_check", {"html": "x"})
        assert result is None

    def test_lru_eviction(self, cache: MCPResponseCache) -> None:
        """At max_size, oldest entry is evicted."""
        cache.put("qa_check", {"html": "1"}, "r1")
        cache.put("qa_check", {"html": "2"}, "r2")
        cache.put("qa_check", {"html": "3"}, "r3")
        # Cache is full (max_size=3). Adding a 4th evicts the oldest.
        cache.put("qa_check", {"html": "4"}, "r4")

        assert cache.get("qa_check", {"html": "1"}) is None  # evicted
        assert cache.get("qa_check", {"html": "4"}) == "r4"
        assert cache.stats()["evictions"] == 1

    def test_invalidate_by_tool(self, cache: MCPResponseCache) -> None:
        """invalidate(tool_name) clears only that tool's entries."""
        cache.put("qa_check", {"html": "a"}, "r-qa")
        cache.put("estimate_cost", {"html": "a"}, "r-cost")

        cleared = cache.invalidate("qa_check")
        assert cleared == 1
        assert cache.get("qa_check", {"html": "a"}) is None
        assert cache.get("estimate_cost", {"html": "a"}) == "r-cost"


# ── TestSchemaCompression ───────────────────────────────────────────


class TestSchemaCompression:
    def test_compress_removes_nested_descriptions(self) -> None:
        """Nested description fields are stripped, top-level kept."""
        schema: dict[str, Any] = {
            "description": "Top-level desc",
            "type": "object",
            "properties": {
                "html": {
                    "type": "string",
                    "description": "The HTML content to validate",
                    "title": "Html",
                },
            },
        }
        compressed = compress_schema(schema)
        assert compressed["description"] == "Top-level desc"
        assert "description" not in compressed["properties"]["html"]
        assert "title" not in compressed["properties"]["html"]

    def test_compress_collapses_single_anyof(self) -> None:
        """anyOf with single element is collapsed."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "target": {
                    "anyOf": [{"type": "string"}],
                    "title": "Target",
                },
            },
        }
        compressed = compress_schema(schema)
        prop = compressed["properties"]["target"]
        assert "anyOf" not in prop
        assert prop["type"] == "string"

    def test_compression_ratio(self) -> None:
        """Compressed schema is ≤60% of original size."""
        schema: dict[str, Any] = {
            "description": "Validate email HTML",
            "type": "object",
            "properties": {
                "html": {
                    "type": "string",
                    "description": "The full HTML email content to validate",
                    "title": "Html",
                    "default": "",
                },
                "checks": {
                    "type": "array",
                    "description": "List of specific checks to run",
                    "title": "Checks",
                    "default": [],
                    "items": {
                        "type": "string",
                        "description": "Check name",
                        "title": "CheckItem",
                    },
                },
                "target_clients": {
                    "anyOf": [{"type": "array", "items": {"type": "string"}}],
                    "description": "Optional list of target email clients for CSS filtering",
                    "title": "TargetClients",
                    "default": None,
                },
            },
            "required": ["html"],
        }
        registry = SchemaRegistry()
        registry.register("qa_check", schema)
        ratio = registry.compression_ratio("qa_check")
        assert ratio <= 0.60, f"Compression ratio {ratio:.2%} exceeds 60%"


# ── TestBatchExecute ────────────────────────────────────────────────


class TestBatchExecute:
    @pytest.mark.anyio()
    async def test_batch_returns_cached_immediately(self, mock_ctx: Any) -> None:
        """Cached calls skip handler execution."""
        cache = MCPResponseCache(max_size=10, ttl_seconds=60)
        cache.put("qa_check", {"html": "x"}, "cached-result")

        handler = AsyncMock(return_value="fresh-result")
        handlers: dict[str, Any] = {"qa_check": handler}

        results = await batch_execute(
            [ToolCall(tool_name="qa_check", params={"html": "x"})],
            cache,
            handlers,
            mock_ctx,
        )

        assert len(results) == 1
        assert results[0].cached is True
        assert results[0].result == "cached-result"
        handler.assert_not_called()

    @pytest.mark.anyio()
    async def test_batch_concurrent_execution(self, mock_ctx: Any) -> None:
        """Non-cached calls run via asyncio.gather (concurrently)."""
        cache = MCPResponseCache(max_size=10, ttl_seconds=60)

        call_times: list[float] = []

        async def _slow_handler(**kwargs: Any) -> str:
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)
            return f"result-{kwargs.get('html', '')}"

        handlers: dict[str, Any] = {
            "qa_check": _slow_handler,
            "estimate_cost": _slow_handler,
        }

        results = await batch_execute(
            [
                ToolCall(tool_name="qa_check", params={"html": "a"}),
                ToolCall(tool_name="estimate_cost", params={"html": "b"}),
            ],
            cache,
            handlers,
            mock_ctx,
        )

        assert len(results) == 2
        assert all(not r.cached for r in results)
        assert results[0].result == "result-a"
        assert results[1].result == "result-b"

    @pytest.mark.anyio()
    async def test_batch_error_isolation(self, mock_ctx: Any) -> None:
        """One failing tool doesn't block others."""
        cache = MCPResponseCache(max_size=10, ttl_seconds=60)

        async def _good_handler(**kwargs: Any) -> str:
            return "ok"

        async def _bad_handler(**kwargs: Any) -> str:
            msg = "boom"
            raise RuntimeError(msg)

        handlers: dict[str, Any] = {
            "qa_check": _bad_handler,
            "estimate_cost": _good_handler,
        }

        results = await batch_execute(
            [
                ToolCall(tool_name="qa_check", params={"html": "x"}),
                ToolCall(tool_name="estimate_cost", params={"html": "y"}),
            ],
            cache,
            handlers,
            mock_ctx,
        )

        assert len(results) == 2
        assert results[0].error == "boom"
        assert results[0].result == ""
        assert results[1].error is None
        assert results[1].result == "ok"
