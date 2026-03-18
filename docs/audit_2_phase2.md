# Audit 2 — Phase 2: High Severity

**Depends on:** Phase 1 complete, `make check` passing
**Gate:** `make check` must pass before proceeding to Phase 3

---

## 2.1 Voice Routes Blocked by Body Size Middleware

**Problem:** `UPLOAD_PATHS` only allows `/api/v1/knowledge` for large bodies. Voice routes at `/api/v1/ai/voice/*` reject any audio >100KB.

**File:** `app/core/middleware.py`

### Diagnosis

```bash
grep -n 'UPLOAD_PATHS' app/core/middleware.py
grep -n 'MAX_BODY_SIZE' app/core/middleware.py
grep -rn 'voice' app/core/middleware.py  # Should return nothing — that's the bug
```

### Fix

1. Open `app/core/middleware.py`
2. Find the `UPLOAD_PATHS` tuple
3. Add `"/api/v1/ai/voice"` and `"/mcp"` to the tuple:
   ```python
   UPLOAD_PATHS = ("/api/v1/knowledge", "/api/v1/ai/voice", "/mcp")
   ```

### Verification

```bash
make test
# Confirm the tuple now includes voice:
grep -A2 'UPLOAD_PATHS' app/core/middleware.py
```

---

## 2.2 MCP Server Authentication

**Problem:** MCP server at `/mcp` has zero auth. `verify_mcp_token()` exists but is never called.

**Files:**
- `app/mcp/auth.py` — has the verification function
- `app/mcp/server.py` — tool registration
- `app/main.py` — mount point

### Diagnosis

```bash
# See the existing auth function
cat app/mcp/auth.py

# Confirm it's never used
grep -rn 'verify_mcp_token' app/ --include='*.py'

# See how MCP is mounted
grep -n 'mcp' app/main.py
```

### Fix (Middleware approach)

1. Read `app/mcp/auth.py` to understand `verify_mcp_token()` signature and return type
2. In `app/mcp/server.py`, add an ASGI middleware class that:
   - Extracts `Authorization: Bearer <token>` from request headers
   - Calls `verify_mcp_token(token)`
   - Returns 401 JSON response if invalid
   - Passes through to the MCP app if valid
3. Wrap the MCP Starlette app with this middleware before it's mounted in `main.py`
4. If `MCP__ENABLED=false` (default), the entire `/mcp` mount should be skipped in `main.py`

```python
# Example middleware skeleton for app/mcp/server.py:
class MCPAuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if not auth.startswith("Bearer "):
                response = JSONResponse({"detail": "Missing auth"}, status_code=401)
                await response(scope, receive, send)
                return
            token = auth.removeprefix("Bearer ")
            if not await verify_mcp_token(token):
                response = JSONResponse({"detail": "Invalid token"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
```

### Verification

```bash
make test
# Manual check (if server is running):
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8891/mcp
# Should return 401
```

---

## 2.3 Docker PostgreSQL Volume Path

**Problem:** Volume mounts to `/var/lib/postgresql` instead of `/var/lib/postgresql/data`. Data loss on container rebuild.

**File:** `docker-compose.yml`

### Fix

```bash
# Find the line
grep -n 'postgres_data' docker-compose.yml
```

Change:
```yaml
- postgres_data:/var/lib/postgresql
```
To:
```yaml
- postgres_data:/var/lib/postgresql/data
```

### Verification

```bash
grep 'postgresql/data' docker-compose.yml  # Should match
```

---

## 2.4 E2E Test Infrastructure

**Problem:** `make e2e` calls npm scripts that don't exist.

**Files:**
- `cms/apps/web/package.json`
- `cms/turbo.json`
- `Makefile`

### Diagnosis

```bash
# Confirm scripts are missing
grep '"e2e"' cms/apps/web/package.json  # Should return nothing
grep 'e2e' Makefile                      # Shows the make targets exist
```

### Fix

1. Add scripts to `cms/apps/web/package.json` in the `"scripts"` block:
   ```json
   "e2e": "playwright test",
   "e2e:ui": "playwright test --ui"
   ```

2. Add `e2e` task to `cms/turbo.json` in the `"tasks"` object:
   ```json
   "e2e": {
     "dependsOn": ["build"],
     "cache": false
   }
   ```

3. In `Makefile`:
   - Remove the `e2e-all` target (it's identical to `e2e`)
   - Add missing `.PHONY` declarations. Find the `.PHONY` line and append:
     ```
     docker-logs test-properties e2e-ui sdk-local db-migrate db-revision eval-refresh help
     ```

### Verification

```bash
# Script should resolve (will fail due to no server, but that's fine)
cd cms && pnpm --filter web e2e --help 2>&1 | head -5
```

---

## 2.5 Broken `/dashboard` Route Links

**Problem:** Three pages link to `href="/dashboard"` which doesn't exist. Dashboard is at `/`.

### Fix

```bash
# Find all instances
grep -rn 'href="/dashboard"' cms/apps/web/src/ --include='*.tsx'
```

In each of these files, change `href="/dashboard"` to `href="/"`:
- `cms/apps/web/src/app/not-found.tsx`
- `cms/apps/web/src/app/(dashboard)/unauthorized/page.tsx`
- `cms/apps/web/src/app/(dashboard)/error.tsx`

### Verification

```bash
# Should return empty
grep -rn 'href="/dashboard"' cms/apps/web/src/ --include='*.tsx'

make check-fe
```

---

## 2.6 Agent Signature Mismatches (mypy override errors)

**Problem:** 6 agent services don't accept the `context_blocks` parameter from `BaseAgentService`. Multimodal context silently dropped.

### Diagnosis

```bash
# See the base class signature
grep -A5 'def process\|def stream_process' app/ai/agents/base.py | head -20

# See the type used for context_blocks
grep 'context_blocks' app/ai/agents/base.py
```

### Fix

For each agent below, add the `context_blocks` parameter to match the base class signature. Read the base class first to get the exact type:

```python
# Expected signature pattern (from base.py):
async def process(self, request: Any, context_blocks: list[...] | None = None) -> Any:
async def stream_process(self, request: Any, context_blocks: list[...] | None = None) -> AsyncIterator[str]:
```

**Files to edit:**

| File | Methods to fix |
|------|----------------|
| `app/ai/agents/personalisation/service.py` | `stream_process` |
| `app/ai/agents/dark_mode/service.py` | `stream_process` |
| `app/ai/agents/content/service.py` | `process` |
| `app/ai/agents/outlook_fixer/service.py` | `process` + `stream_process` |
| `app/ai/agents/code_reviewer/service.py` | `process` + `stream_process` |
| `app/ai/agents/accessibility/service.py` | `stream_process` |

For each:
1. Read the file, find the method
2. Add `context_blocks: list[TextBlock | ImageBlock | AudioBlock | StructuredOutputBlock | ToolResultBlock] | None = None` parameter
3. Import the block types if not already imported (check existing imports)
4. The method body doesn't need to use the parameter yet — just accept it

### Verification

```bash
make types  # The 6 [override] errors should disappear
# 37 errors → 31 errors (remaining are test type issues, fixed in Phase 4)
```

---

## Phase 2 Gate

```bash
make check   # lint + types + tests + security
make check-fe  # frontend type-check + tests
```

If both pass (or types has only the known Phase 4 test errors), proceed to Phase 3.
