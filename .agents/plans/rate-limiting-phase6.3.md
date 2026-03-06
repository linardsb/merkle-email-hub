# Plan: Phase 6.3 Rate Limiting & Resource Controls

## Context

Phase 6 OWASP API Security Hardening. Tasks 6.1 (BOLA) and 6.2 (response hardening) are complete. Phase 6.3 addresses 4 MEDIUM-severity resource control gaps:

1. **6.3.1** AI quota is per-IP in-memory — loses state on restart, wrong key for multi-user
2. **6.3.2** WebSocket has global connection limit but no per-user limit — one user can exhaust all 100 slots
3. **6.3.3** LLM streaming has no timeout — a hung provider keeps the connection open forever
4. **6.3.4** Blueprint engine tracks tokens but has no cost cap — runaway pipelines can burn budget

### Current Infrastructure
- **SlowAPI limiter** (`app/core/rate_limit.py`): Redis-backed, keyed by `X-Real-IP` or client addr
- **Redis client** (`app/core/redis.py`): async singleton via `get_redis()`, `redis_available()`
- **AI quota** (`app/ai/routes.py`): `_QuotaTracker` class, in-memory dict, per-IP, 24h window
- **WebSocket** (`app/streaming/manager.py`): `ConnectionManager` with global `max_connections=100`
- **WS route** (`app/streaming/routes.py`): JWT auth, user resolved, BOLA checks, heartbeat task
- **AI streaming** (`app/ai/service.py`): `stream_chat()` yields SSE chunks with no timeout
- **Blueprint engine** (`app/ai/blueprints/engine.py`): `BlueprintRun.model_usage` accumulates tokens, `MAX_TOTAL_STEPS=20` but no token cap
- **Circuit breaker** (`app/core/resilience.py`): protects `provider.complete()`, not streaming

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `app/core/quota.py` | **Create** | Redis-backed per-user daily quota tracker |
| `app/core/config.py` | Modify | Add `BlueprintConfig` with `daily_token_cap` |
| `app/ai/routes.py` | Modify | Replace `_QuotaTracker` with Redis-backed `UserQuotaTracker` |
| `app/ai/service.py` | Modify | Add `asyncio.timeout` to `stream_chat()` |
| `app/ai/blueprints/engine.py` | Modify | Add token cap check after each node |
| `app/streaming/manager.py` | Modify | Add per-user connection tracking |
| `app/streaming/routes.py` | Modify | Pass `user_id` to manager, enforce per-user limit |
| `app/tests/test_quota.py` | **Create** | Unit tests for Redis quota tracker |
| `app/tests/test_ws_per_user_limit.py` | **Create** | Unit tests for per-user WS limit |
| `app/tests/test_stream_timeout.py` | **Create** | Unit tests for streaming timeout |
| `app/tests/test_blueprint_cost_cap.py` | **Create** | Unit tests for blueprint token cap |

## Implementation Steps

---

### Task 6.3.1 — AI quota per-IP (in-memory) to per-user (Redis)

#### Step 1: Create `app/core/quota.py`

```python
"""Redis-backed per-user daily quota tracker.

Tracks AI request counts per user with automatic 24-hour TTL expiry.
Falls back to in-memory tracking when Redis is unavailable.
"""

import time
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)

_SECONDS_PER_DAY: int = 86_400


@dataclass
class _InMemoryEntry:
    count: int = 0
    reset_at: float = field(default_factory=lambda: time.monotonic() + _SECONDS_PER_DAY)


class UserQuotaTracker:
    """Per-user daily quota tracker backed by Redis.

    Redis key: ``ai:quota:{user_id}`` with 24h TTL.
    Falls back to in-memory dict if Redis is unavailable.

    Args:
        daily_limit: Maximum requests per user per day.
    """

    def __init__(self, daily_limit: int) -> None:
        self._daily_limit = daily_limit
        self._fallback: dict[int, _InMemoryEntry] = {}

    async def check_and_increment(self, user_id: int) -> bool:
        """Check quota and increment if allowed. Returns True if allowed."""
        try:
            return await self._check_redis(user_id)
        except Exception:
            logger.debug("quota.redis_fallback", user_id=user_id)
            return self._check_memory(user_id)

    async def get_remaining(self, user_id: int) -> int:
        """Get remaining quota for a user."""
        try:
            return await self._remaining_redis(user_id)
        except Exception:
            return self._remaining_memory(user_id)

    # -- Redis path --

    async def _check_redis(self, user_id: int) -> bool:
        from app.core.redis import get_redis

        r = await get_redis()
        key = f"ai:quota:{user_id}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, _SECONDS_PER_DAY)
        if count > self._daily_limit:
            logger.warning(
                "ai.quota_exceeded",
                user_id=user_id,
                daily_limit=self._daily_limit,
                current_count=count,
            )
            return False
        return True

    async def _remaining_redis(self, user_id: int) -> int:
        from app.core.redis import get_redis

        r = await get_redis()
        key = f"ai:quota:{user_id}"
        raw = await r.get(key)
        if raw is None:
            return self._daily_limit
        return max(0, self._daily_limit - int(raw))

    # -- In-memory fallback --

    def _check_memory(self, user_id: int) -> bool:
        now = time.monotonic()
        entry = self._fallback.get(user_id)
        if entry is None or now >= entry.reset_at:
            self._fallback[user_id] = _InMemoryEntry(count=1, reset_at=now + _SECONDS_PER_DAY)
            return True
        if entry.count >= self._daily_limit:
            return False
        entry.count += 1
        return True

    def _remaining_memory(self, user_id: int) -> int:
        now = time.monotonic()
        entry = self._fallback.get(user_id)
        if entry is None or now >= entry.reset_at:
            return self._daily_limit
        return max(0, self._daily_limit - entry.count)
```

#### Step 2: Modify `app/ai/routes.py`

1. Remove `_QuotaEntry`, `_QuotaTracker`, `_quota_tracker`, `_get_quota_tracker` (lines 31-108)
2. Remove `from app.core.rate_limit import _get_client_ip` import (no longer needed for quota)
3. Add import: `from app.core.quota import UserQuotaTracker`
4. Add module-level singleton:
   ```python
   _user_quota: UserQuotaTracker | None = None

   def _get_user_quota() -> UserQuotaTracker:
       global _user_quota
       if _user_quota is None:
           settings = get_settings()
           _user_quota = UserQuotaTracker(daily_limit=settings.ai.daily_quota)
       return _user_quota
   ```
5. In `chat_completions()`, replace the quota check block (lines 137-146):
   ```python
   # Check daily quota (per-user, Redis-backed)
   tracker = _get_user_quota()
   if not await tracker.check_and_increment(current_user.id):
       remaining = await tracker.get_remaining(current_user.id)
       raise HTTPException(
           status_code=429,
           detail=f"Daily query quota exceeded. Remaining: {remaining}. Resets in 24 hours.",
       )
   ```
6. Remove `_get_client_ip` from the function body (no longer used for quota)

#### Step 3: Create `app/tests/test_quota.py`

Tests:
- `test_allows_within_limit` — user makes N requests < limit, all return True
- `test_blocks_over_limit` — user exceeds limit, returns False
- `test_separate_users` — user A at limit, user B still allowed
- `test_remaining_decrements` — remaining count decreases with each call
- `test_fallback_when_redis_unavailable` — mock Redis to raise, verify in-memory fallback works

Use `AsyncMock` to mock `get_redis()`. Test both Redis path and in-memory fallback path by patching.

---

### Task 6.3.2 — Per-user WebSocket connection limit

#### Step 4: Add config for per-user WS limit in `app/core/config.py`

Add to `WebSocketConfig`:
```python
max_connections_per_user: int = 5  # Per-user concurrent WS limit
```

#### Step 5: Modify `app/streaming/manager.py`

1. Add `_user_connections: dict[str, set[int]]` to `ConnectionManager.__init__`:
   ```python
   self._user_connections: dict[str, set[int]] = {}
   self._max_per_user = max_per_user
   ```
2. Update `__init__` signature to accept `max_per_user: int`
3. Update `connect()` to accept `user_id: str | None = None` and enforce per-user limit:
   ```python
   async def connect(
       self,
       websocket: WebSocket,
       filters: dict[str, str | None] | None = None,
       user_id: str | None = None,
   ) -> bool:
       # Global limit check (existing)
       if len(self._clients) >= self._max_connections:
           ...
           return False

       # Per-user limit check
       if user_id is not None:
           user_conns = self._user_connections.get(user_id, set())
           if len(user_conns) >= self._max_per_user:
               logger.warning(
                   "streaming.ws.per_user_limit_reached",
                   user_id=user_id,
                   max_per_user=self._max_per_user,
                   active_count=len(user_conns),
               )
               return False

       ws_id = id(websocket)
       self._clients[ws_id] = _ClientSubscription(
           websocket=websocket,
           filters=filters or {},
       )
       if user_id is not None:
           self._user_connections.setdefault(user_id, set()).add(ws_id)
       return True
   ```
4. Update `disconnect()` to accept `user_id: str | None = None` and clean up tracking:
   ```python
   def disconnect(self, websocket: WebSocket, user_id: str | None = None) -> None:
       ws_id = id(websocket)
       if ws_id in self._clients:
           del self._clients[ws_id]
       if user_id is not None and user_id in self._user_connections:
           self._user_connections[user_id].discard(ws_id)
           if not self._user_connections[user_id]:
               del self._user_connections[user_id]
   ```
5. Also update the broadcast cleanup to remove from `_user_connections` (iterate `_user_connections` values to discard disconnected ws_ids). Add helper:
   ```python
   def _cleanup_user_tracking(self, ws_id: int) -> None:
       for uid, conns in list(self._user_connections.items()):
           conns.discard(ws_id)
           if not conns:
               del self._user_connections[uid]
   ```
   Call `self._cleanup_user_tracking(ws_id)` in the broadcast disconnected cleanup loop.

#### Step 6: Modify `app/streaming/routes.py`

1. Update `get_ws_manager()` to pass `max_per_user`:
   ```python
   _ws_manager = ConnectionManager(
       max_connections=settings.ws.max_connections,
       max_per_user=settings.ws.max_connections_per_user,
   )
   ```
2. Pass `user_id` to `manager.connect()`:
   ```python
   if not await manager.connect(websocket, user_id=user_id):
   ```
3. Pass `user_id` to `manager.disconnect()` in the `finally` block:
   ```python
   manager.disconnect(websocket, user_id=user_id)
   ```

#### Step 7: Create `app/tests/test_ws_per_user_limit.py`

Tests:
- `test_allows_connections_within_per_user_limit` — user opens N < limit connections, all succeed
- `test_blocks_user_over_per_user_limit` — user at limit, next connect returns False
- `test_other_user_not_affected` — user A at limit, user B can still connect
- `test_disconnect_frees_slot` — disconnect then reconnect succeeds
- `test_global_limit_still_enforced` — many users can hit global limit
- `test_broadcast_cleanup_updates_user_tracking` — disconnected client removed from user tracking

Use mock `WebSocket` objects with unique `id()` values.

---

### Task 6.3.3 — Timeout on LLM streaming responses

#### Step 8: Add config for streaming timeout in `app/core/config.py`

Add to `AIConfig`:
```python
stream_timeout_seconds: int = 120  # Max duration for a streaming response
```

#### Step 9: Modify `app/ai/service.py` — `stream_chat()`

Wrap the streaming loop with `asyncio.timeout`:

```python
import asyncio

async def stream_chat(self, request: ChatCompletionRequest) -> AsyncIterator[str]:
    # ... existing setup (provider resolution, message sanitization, logging) ...

    settings = get_settings()
    timeout_seconds = settings.ai.stream_timeout_seconds

    try:
        async with asyncio.timeout(timeout_seconds):
            async for chunk in provider.stream(messages, model_override=model):
                sse_data = { ... }  # existing SSE formatting
                yield f"data: {json.dumps(sse_data)}\n\n"

    except TimeoutError:
        logger.error(
            "ai.stream_timeout",
            response_id=response_id,
            provider=provider_name,
            timeout_seconds=timeout_seconds,
        )
        # Send error event before closing
        error_data = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_id,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "timeout"}],
        }
        yield f"data: {json.dumps(error_data)}\n\n"
    except Exception as e:
        # ... existing error handling ...
        pass

    yield "data: [DONE]\n\n"
    # ... existing completion logging ...
```

**Important**: The `yield "data: [DONE]\n\n"` and completion logging should be outside the try/except blocks so they always execute (move to after the try/except).

#### Step 10: Create `app/tests/test_stream_timeout.py`

Tests:
- `test_stream_completes_within_timeout` — normal streaming finishes, yields [DONE]
- `test_stream_times_out` — mock provider.stream to sleep > timeout, verify timeout error chunk emitted with `finish_reason: "timeout"`, then [DONE]
- `test_timeout_configurable` — verify `settings.ai.stream_timeout_seconds` is respected

Mock the provider registry and `provider.stream()` with an async generator that either yields immediately or hangs.

---

### Task 6.3.4 — Blueprint daily cost cap

#### Step 11: Add `BlueprintConfig` to `app/core/config.py`

```python
class BlueprintConfig(BaseModel):
    """Blueprint execution settings."""

    daily_token_cap: int = 500_000  # Max tokens per user per day across all blueprint runs
```

Add to `Settings`:
```python
blueprint: BlueprintConfig = BlueprintConfig()
```

#### Step 12: Create `app/core/cost_tracker.py` (or add to `quota.py`)

Actually — keep it in `app/core/quota.py` as a second class for consistency:

Add `BlueprintCostTracker` to `app/core/quota.py`:

```python
class BlueprintCostTracker:
    """Tracks daily blueprint token usage per user via Redis.

    Redis key: ``blueprint:tokens:{user_id}`` with 24h TTL.
    Falls back to in-memory dict if Redis is unavailable.

    Args:
        daily_cap: Maximum total tokens per user per day.
    """

    def __init__(self, daily_cap: int) -> None:
        self._daily_cap = daily_cap
        self._fallback: dict[int, _InMemoryEntry] = {}

    async def check_budget(self, user_id: int) -> int:
        """Return remaining token budget. 0 means cap exhausted."""
        try:
            return await self._remaining_redis(user_id)
        except Exception:
            return self._remaining_memory(user_id)

    async def record_usage(self, user_id: int, tokens: int) -> None:
        """Record token usage for a blueprint run."""
        try:
            await self._record_redis(user_id, tokens)
        except Exception:
            self._record_memory(user_id, tokens)

    async def _remaining_redis(self, user_id: int) -> int:
        from app.core.redis import get_redis
        r = await get_redis()
        key = f"blueprint:tokens:{user_id}"
        raw = await r.get(key)
        if raw is None:
            return self._daily_cap
        return max(0, self._daily_cap - int(raw))

    async def _record_redis(self, user_id: int, tokens: int) -> None:
        from app.core.redis import get_redis
        r = await get_redis()
        key = f"blueprint:tokens:{user_id}"
        new_total = await r.incrby(key, tokens)
        if new_total == tokens:
            await r.expire(key, _SECONDS_PER_DAY)
        if new_total > self._daily_cap:
            logger.warning(
                "blueprint.cost_cap_exceeded",
                user_id=user_id,
                total_tokens=new_total,
                daily_cap=self._daily_cap,
            )

    def _record_memory(self, user_id: int, tokens: int) -> None:
        now = time.monotonic()
        entry = self._fallback.get(user_id)
        if entry is None or now >= entry.reset_at:
            self._fallback[user_id] = _InMemoryEntry(count=tokens, reset_at=now + _SECONDS_PER_DAY)
        else:
            entry.count += tokens

    def _remaining_memory(self, user_id: int) -> int:
        now = time.monotonic()
        entry = self._fallback.get(user_id)
        if entry is None or now >= entry.reset_at:
            return self._daily_cap
        return max(0, self._daily_cap - entry.count)
```

#### Step 13: Modify `app/ai/blueprints/engine.py`

Add a token cap exception in `app/ai/blueprints/exceptions.py`:
```python
class BlueprintCostCapError(BlueprintNodeError):
    """Raised when a blueprint run exceeds the daily token cost cap."""

    def __init__(self, total_tokens: int, cap: int) -> None:
        super().__init__("cost_cap", f"Token usage {total_tokens} exceeds daily cap {cap}")
        self.total_tokens = total_tokens
        self.cap = cap
```

Modify `BlueprintEngine.run()` to accept an optional `user_id` and check cost:

1. Update `run()` signature:
   ```python
   async def run(self, brief: str, initial_html: str = "", user_id: int | None = None) -> BlueprintRun:
   ```

2. After the token accumulation block (after line 122), add cap check:
   ```python
   # Check token cost cap per node completion
   if user_id is not None:
       from app.core.config import get_settings
       from app.core.quota import BlueprintCostTracker

       settings = get_settings()
       tracker = BlueprintCostTracker(daily_cap=settings.blueprint.daily_token_cap)
       remaining = await tracker.check_budget(user_id)
       node_tokens = result.usage.get("total_tokens", 0) if result.usage else 0
       if node_tokens > 0:
           if remaining <= 0:
               run.status = "cost_cap_exceeded"
               logger.warning(
                   "blueprint.cost_cap_reached",
                   run_id=run.run_id,
                   user_id=user_id,
                   total_tokens=run.model_usage["total_tokens"],
               )
               break
           await tracker.record_usage(user_id, node_tokens)
   ```

   **Note**: Instantiating the tracker per-node is fine (it's stateless, Redis holds the state). But for efficiency, move tracker creation before the while loop and pass `settings` once.

   Refined approach — before the `while` loop:
   ```python
   cost_tracker: BlueprintCostTracker | None = None
   if user_id is not None:
       from app.core.config import get_settings as _get_settings
       from app.core.quota import BlueprintCostTracker
       _settings = _get_settings()
       cost_tracker = BlueprintCostTracker(daily_cap=_settings.blueprint.daily_token_cap)
   ```

   Then after token accumulation:
   ```python
   if cost_tracker is not None and user_id is not None:
       node_tokens = result.usage.get("total_tokens", 0) if result.usage else 0
       if node_tokens > 0:
           remaining = await cost_tracker.check_budget(user_id)
           if remaining <= 0:
               run.status = "cost_cap_exceeded"
               logger.warning(
                   "blueprint.cost_cap_reached",
                   run_id=run.run_id,
                   user_id=user_id,
                   total_tokens=run.model_usage["total_tokens"],
               )
               break
           await cost_tracker.record_usage(user_id, node_tokens)
   ```

#### Step 14: Thread `user_id` through blueprint service to engine

In `app/ai/blueprints/service.py`, the `run()` method constructs and calls `engine.run()`. It must pass `user_id` from the authenticated user:

1. Update `BlueprintRunRequest` schema (in `app/ai/blueprints/schemas.py`) — **NO**, don't put user_id in request body. Instead pass it from the route via service.

2. In `app/ai/blueprints/routes.py`, add `current_user` dependency:
   ```python
   from app.auth.dependencies import get_current_user
   from app.auth.models import User

   async def run_blueprint(
       request: Request,
       body: BlueprintRunRequest,
       current_user: User = Depends(get_current_user),
   ) -> BlueprintRunResponse:
       service = get_blueprint_service()
       return await service.run(body, user_id=current_user.id)
   ```

3. In `app/ai/blueprints/service.py`, update the `run()` method to accept and forward `user_id`:
   ```python
   async def run(self, request: BlueprintRunRequest, user_id: int | None = None) -> BlueprintRunResponse:
       # ... existing code ...
       result = await engine.run(request.brief, initial_html=request.initial_html or "", user_id=user_id)
   ```

#### Step 15: Create `app/tests/test_blueprint_cost_cap.py`

Tests:
- `test_blueprint_runs_within_cap` — tokens < cap, run completes normally
- `test_blueprint_stops_at_cap` — mock Redis counter to return 0 remaining, run breaks with `cost_cap_exceeded`
- `test_token_usage_recorded` — verify `record_usage` called after each agentic node
- `test_no_tracking_without_user_id` — `user_id=None` skips all cost tracking
- `test_cost_tracker_fallback` — Redis unavailable, in-memory tracking works

---

## Edge Cases & Design Decisions

1. **Quota fallback**: Both `UserQuotaTracker` and `BlueprintCostTracker` fall back to in-memory when Redis is down. This is acceptable because: (a) Redis being down is transient, (b) in-memory still enforces limits per-worker, (c) no silent bypass — the limit is still enforced, just not shared across workers.

2. **Per-user WS tracking cleanup**: The broadcast loop already cleans up disconnected clients. We add `_cleanup_user_tracking()` to keep `_user_connections` in sync. The `disconnect()` method also cleans up for normal disconnects.

3. **Stream timeout**: We use `asyncio.timeout` (Python 3.11+, project requires 3.12+) which is cleaner than `asyncio.wait_for`. The timeout wraps only the provider stream iteration, not the SSE yield. On timeout, we send a final chunk with `finish_reason: "timeout"` so the client knows what happened.

4. **Blueprint cost cap check timing**: We check remaining budget BEFORE recording, so if remaining is 0 we stop immediately. Tokens from the current node that pushed us over are still recorded (the node already ran). This is by design — we stop AFTER the node that exhausts the budget, not before.

5. **BlueprintCostTracker vs adding to engine directly**: Keeping the tracker as a separate module in `app/core/quota.py` follows the VSA principle — core infrastructure, reusable by other features if needed.

## Verification

- [ ] `make lint` passes (ruff format + lint)
- [ ] `make types` passes (mypy + pyright)
- [ ] `make test` passes (all existing + new tests)
- [ ] New tests cover: Redis path, in-memory fallback, edge cases (limit boundary, multi-user isolation)
- [ ] No `Any` types without justification
- [ ] All functions have complete type annotations
- [ ] Structured logging follows `domain.action_state` pattern
