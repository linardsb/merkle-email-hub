# Plan: 48.11 MCP Response Caching and Schema Compression

## Context

MCP tool calls send full schemas with every invocation (~500-2000 tokens per tool). With ~30 registered tools, that's significant schema overhead per session. Repeated calls to read-only tools like `qa_check` on the same HTML waste additional tokens. This task adds a response cache, schema compression layer, and batch execution to the MCP server.

## Research Summary

### MCP Module Structure (`app/mcp/`)

| File | Role |
|------|------|
| `server.py` | `create_mcp_server()` factory, `get_mcp_server()` singleton, `MCPAuthMiddleware`, `_apply_tool_allowlist()` |
| `config.py` | `is_tool_allowed()` — fnmatch against operator allowlist |
| `auth.py` | `verify_mcp_token()` — bearer token validation |
| `resources.py` | MCP resource registration |
| `formatting.py` | `format_qa_result()`, `format_knowledge_result()`, `_apply_token_budget()` — output normalization |
| `tools/qa.py` | 9 QA tools (`qa_check`, `email_production_readiness`, `chaos_test`, etc.) |
| `tools/agents.py` | 9 agent tools (`scaffolder_generate`, `dark_mode_apply`, etc.) |
| `tools/ai.py` | AI tools (`estimate_cost`, `deliverability_score`, `bimi_check`) |
| `tools/email.py` | Email engine tools (`css_optimize`, `schema_markup_inject`) |
| `tools/knowledge.py` | Knowledge search |
| `tools/rendering.py` | Rendering visualization |
| `tools/templates.py` | Template management |
| `__init__.py` | Exports `MCPContext = Context[Any, Any, Any]` |

### Key Patterns to Follow

| Pattern | Source | Relevance |
|---------|--------|-----------|
| Two-layer cache (memory LRU + Redis) | `app/design_sync/section_cache.py` | Direct template for `MCPResponseCache` |
| `blake2b` content hashing | `app/design_sync/vlm_classifier.py:_screenshot_hash()` | Cache key generation |
| Frozen dataclass entries | `SectionCacheEntry` | Cache entry structure |
| Nested Pydantic config | `MCPConfig` at `app/core/config.py:480` | Extend with cache/compress fields |
| Singleton + clear pattern | `get_section_cache()` / `clear_section_cache()` | Cache lifecycle |
| Graceful Redis fallback | `section_cache.py` Redis error handling | Required for resilience |

### Current Config (`app/core/config.py:480`)

```python
class MCPConfig(BaseModel):
    enabled: bool = False
    max_response_tokens: int = 4000
    tool_timeout_s: int = 120
    audit_log_enabled: bool = True
    tool_allowlist: list[str] = []
```

### SDK Details

- Library: `mcp>=1.12.0`, `from mcp.server.fastmcp import FastMCP`
- Tools registered via `@mcp.tool()` decorator inside `register_*_tools(mcp)` functions
- All tool handlers are `async def ... -> str` returning Markdown
- Tool manager access: `mcp._tool_manager._tools` (dict[str, Tool])

## Test Landscape

### Existing MCP Tests (8 files)

| File | Coverage |
|------|----------|
| `app/mcp/tests/test_mcp_server.py` | Server creation, tool execution |
| `app/mcp/tests/test_agent_tools.py` | Agent tool registration (45 tests) |
| `app/mcp/tests/test_tool_execution.py` | Tool execution patterns |
| `app/mcp/tests/test_formatting.py` | Output formatting, token budget |
| `app/mcp/tests/test_resources.py` | MCP resources |
| `app/mcp/tests/test_auth.py` | Authentication |
| `app/mcp/tests/test_allowlist.py` | Tool allowlist |
| `app/mcp/tests/test_tools.py` | Tool handlers |

### Reusable Cache Test Patterns (from `test_section_cache.py`)

- Deterministic hash: same inputs → same key
- LRU eviction at max_size
- TTL expiry
- Redis graceful fallback on `ConnectionError`
- Singleton get/clear lifecycle
- Cache hit/miss rate tracking

### Mock Patterns

```python
# MCP tool mock
def _mock_response(**overrides): ...  # MagicMock with model_dump

# Redis mock
mock_redis = AsyncMock()
mock_redis.get.side_effect = RedisConnectionError("connection refused")
with patch("app.core.redis.get_redis", return_value=mock_redis): ...
```

## Type Check Baseline

- **Pyright:** 0 errors (162 warnings — all `reportUnusedFunction` from decorator-registered tools)
- **Mypy:** 0 errors

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `app/mcp/optimization.py` | `MCPResponseCache`, `compress_schema()`, `SchemaRegistry`, `batch_execute()` |
| `app/mcp/tests/test_optimization.py` | 12 tests for cache, compression, batch |

### Modify

| File | Change |
|------|--------|
| `app/core/config.py:480` | Extend `MCPConfig` with cache/compress fields |
| `app/mcp/server.py:47` | Wire cache + schema registry into `create_mcp_server()` |

## Implementation Steps

### Step 1: Extend `MCPConfig` (`app/core/config.py:480`)

Add 4 fields to existing `MCPConfig`:

```python
class MCPConfig(BaseModel):
    # ... existing fields ...
    cache_enabled: bool = True          # MCP__CACHE_ENABLED
    cache_max_size: int = 100           # MCP__CACHE_MAX_SIZE
    cache_ttl: int = 300                # MCP__CACHE_TTL (seconds)
    compress_schemas: bool = True       # MCP__COMPRESS_SCHEMAS
```

### Step 2: Create `app/mcp/optimization.py`

#### 2a. `MCPResponseCache`

```python
@dataclass(frozen=True)
class CacheEntry:
    response: str
    created_at: float
    tool_name: str

class MCPResponseCache:
    """In-memory LRU response cache for read-only MCP tools."""

    # Tools that mutate state — never cache
    WRITE_TOOLS: frozenset[str] = frozenset({
        "run_agent", "scaffolder_generate", "dark_mode_apply",
        "content_rewrite", "outlook_fix", "accessibility_fix",
        "personalisation_apply", "code_review", "innovation_generate",
        "css_optimize", "schema_markup_inject",
    })

    # Read-only tools — safe to cache
    CACHEABLE_TOOLS: frozenset[str] = frozenset({
        "qa_check", "email_production_readiness", "chaos_test",
        "outlook_analyze", "gmail_predict", "css_support_check",
        "search_knowledge", "search_css_property",
        "rendering_confidence", "rendering_fidelity_report",
        "template_search", "estimate_cost", "deliverability_score",
        "bimi_check",
    })

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300) -> None: ...
    def _make_key(self, tool_name: str, params: dict[str, Any]) -> str: ...
        # blake2b(tool_name + json.dumps(params, sort_keys=True)).hexdigest()[:32]
    def get(self, tool_name: str, params: dict[str, Any]) -> str | None: ...
        # Return None if not cacheable, expired, or missing
    def put(self, tool_name: str, params: dict[str, Any], response: str) -> None: ...
        # Skip if not cacheable. LRU evict if at max_size.
    def invalidate(self, tool_name: str | None = None) -> int: ...
        # Clear all or by tool_name. Return count cleared.
    def stats(self) -> dict[str, int]: ...
        # hits, misses, size, evictions
```

Key design decisions:
- `OrderedDict` for LRU (move-to-end on access, popitem(last=False) on evict)
- `time.monotonic()` for TTL comparison (not wall clock)
- `ctx: MCPContext` param excluded from cache key (session-specific)
- Thread-safe via `threading.Lock` (FastMCP is async but cache is sync dict ops)
- Response includes `\n\n---\n_Cached response_` suffix when served from cache

#### 2b. Schema Compression

```python
def compress_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove verbose fields from tool input schema.

    - Strip `description` from nested properties (keep top-level tool description)
    - Collapse `anyOf: [{type: X}]` single-element unions to `{type: X}`
    - Remove `title` fields from properties
    - Remove `default` fields (Claude infers from description)
    """

class SchemaRegistry:
    """Pre-compressed tool schemas loaded at server startup."""

    def __init__(self) -> None:
        self._original: dict[str, dict[str, Any]] = {}
        self._compressed: dict[str, dict[str, Any]] = {}

    def register(self, tool_name: str, schema: dict[str, Any]) -> None: ...
    def get_compressed(self, tool_name: str) -> dict[str, Any]: ...
    def get_original(self, tool_name: str) -> dict[str, Any]: ...
    def compression_ratio(self, tool_name: str) -> float: ...
        # len(json(compressed)) / len(json(original))
```

#### 2c. Batch Execution

```python
@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    params: dict[str, Any]

@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    result: str
    cached: bool
    error: str | None = None

async def batch_execute(
    calls: list[ToolCall],
    cache: MCPResponseCache,
    tool_handlers: dict[str, Any],
    ctx: MCPContext,
) -> list[ToolResult]:
    """Execute multiple tool calls, returning cached results immediately.

    Non-cached calls run concurrently via asyncio.gather.
    Results ordered to match input call order.
    """
```

### Step 3: Wire into `app/mcp/server.py`

Modify `create_mcp_server()` at line 47:

```python
def create_mcp_server() -> FastMCP:
    mcp = FastMCP(...)

    # Register tool groups (unchanged)
    register_qa_tools(mcp)
    ...

    _apply_tool_allowlist(mcp)
    register_resources(mcp)

    # NEW: Initialize cache and schema registry
    settings = get_settings()
    if settings.mcp.cache_enabled:
        cache = get_mcp_cache()  # singleton
        _wrap_cacheable_tools(mcp, cache)

    if settings.mcp.compress_schemas:
        registry = get_schema_registry()
        _register_schemas(mcp, registry)

    # NEW: Register batch_execute as a tool
    _register_batch_tool(mcp)

    tool_count = len(mcp._tool_manager._tools)
    logger.info("mcp.server_created", tool_count=tool_count)
    return mcp
```

`_wrap_cacheable_tools()` iterates `mcp._tool_manager._tools`, wraps each cacheable tool's handler with a cache-check decorator that:
1. Computes cache key from tool name + params (excluding `ctx`)
2. Returns cached response on hit (with `_cached: true` metadata)
3. Calls original handler on miss, stores result, returns it

### Step 4: Tests (`app/mcp/tests/test_optimization.py`)

12 tests across 3 test classes:

#### `TestMCPResponseCache` (6 tests)

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_cache_hit` | Same tool+params → cached response returned |
| 2 | `test_cache_miss_different_params` | Different params → cache miss |
| 3 | `test_write_tool_not_cached` | `scaffolder_generate` call → never stored |
| 4 | `test_ttl_expiry` | Entry expires after `ttl_seconds` → returns None |
| 5 | `test_lru_eviction` | At `max_size`, oldest entry evicted |
| 6 | `test_invalidate_by_tool` | `invalidate("qa_check")` clears only qa_check entries |

#### `TestSchemaCompression` (3 tests)

| # | Test | Assertion |
|---|------|-----------|
| 7 | `test_compress_removes_nested_descriptions` | Nested `description` fields stripped |
| 8 | `test_compress_collapses_single_anyof` | `anyOf: [{type: "string"}]` → `{type: "string"}` |
| 9 | `test_compression_ratio` | Compressed schema ≤ 60% of original size |

#### `TestBatchExecute` (3 tests)

| # | Test | Assertion |
|---|------|-----------|
| 10 | `test_batch_returns_cached_immediately` | Cached calls skip handler execution |
| 11 | `test_batch_concurrent_execution` | Non-cached calls run via `asyncio.gather` |
| 12 | `test_batch_error_isolation` | One failing tool doesn't block others |

## Preflight Warnings

- `mcp._tool_manager._tools` is a private API — if the `mcp` SDK changes, this accessor breaks. Currently used in `server.py:81,89` so it's an accepted pattern.
- Tool handler wrapping must preserve the original function signature for FastMCP's parameter introspection. Use `functools.wraps`.
- `ctx: MCPContext` must be excluded from cache keys — it's session-specific and not serializable.
- Schema compression must not remove the top-level `description` (FastMCP uses it for tool discovery).

## Security Checklist

| Concern | Mitigation |
|---------|------------|
| Cache poisoning | Cache is per-process in-memory, not shared. No external input to cache keys beyond tool params. |
| Sensitive data in cache | MCP requires auth (bearer token). Cache lives in same process. No persistence to disk. |
| Batch execution DoS | `batch_execute` limited by existing `tool_timeout_s` per call + bounded by `asyncio.Semaphore(5)` |
| Schema stripping | Only removes documentation fields, not validation constraints. Original schemas available as fallback. |

## Verification

- [ ] `make check` passes
- [ ] `qa_check` called twice with same HTML → second returns cached with `_cached` suffix
- [ ] Different HTML → cache miss
- [ ] TTL expiry → cache miss after 300s
- [ ] Write tools (`scaffolder_generate`) never cached
- [ ] `compress_schema` reduces `qa_check` schema to ≤60% original size
- [ ] `batch_execute` with 3 calls → 3 results, cached ones skip handlers
- [ ] Cache eviction at `max_size`
- [ ] Pyright errors ≤ baseline (0 errors before)
- [ ] 12 new tests pass
