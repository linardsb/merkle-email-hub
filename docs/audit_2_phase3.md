# Audit 2 — Phase 3: Medium Severity

**Depends on:** Phase 2 complete, `make check` passing (except known test type errors)
**Gate:** `make check` + `make check-fe` must pass before proceeding to Phase 4

---

## 3.1 Body Size Middleware — Chunked Encoding Bypass

**Problem:** Middleware only checks `Content-Length` header. `Transfer-Encoding: chunked` bypasses size limit entirely.

**File:** `app/core/middleware.py`

### Diagnosis

```bash
grep -n 'content.length\|Content-Length\|transfer' app/core/middleware.py
```

### Fix

After the existing `Content-Length` check, add a guard for missing Content-Length on non-upload paths:

```python
content_length = request.headers.get("content-length")
if content_length is None and path not in self.UPLOAD_PATHS:
    return JSONResponse(status_code=411, content={"detail": "Content-Length required"})
```

This rejects chunked-encoding requests to non-upload paths. Simpler and safer than trying to count bytes mid-stream.

### Verification

```bash
make test
```

---

## 3.2 Blueprint Cost Tracking — Record Before Check

**Problem:** Usage not recorded if budget exceeded. Concurrent runs can double-spend.

**File:** `app/ai/blueprints/engine.py`

### Diagnosis

```bash
grep -n 'record_usage\|check_budget\|remaining' app/ai/blueprints/engine.py
```

### Fix

Find the block around lines 411-425 where `check_budget` and `record_usage` are called. Reorder so `record_usage` runs unconditionally first:

```python
# BEFORE (buggy):
remaining = check_budget(...)
if remaining <= 0:
    break
record_usage(...)

# AFTER (fixed):
record_usage(...)  # Always record, even if over budget
remaining = check_budget(...)
if remaining <= 0:
    break
```

### Verification

```bash
make test
```

---

## 3.3 Circuit Breaker — State Property Must Mutate `self._state`

**Problem:** `state` property returns `HALF_OPEN` without actually setting `self._state`. `__aexit__` reads `self._state` which is still `OPEN`.

**File:** `app/core/resilience.py`

### Diagnosis

```bash
grep -n '_state\|HALF_OPEN' app/core/resilience.py
```

### Fix

In the `state` property, add the actual state mutation:

```python
@property
def state(self) -> CircuitState:
    if self._state == CircuitState.OPEN:
        if time.monotonic() - self._last_failure_time >= self._timeout:
            self._state = CircuitState.HALF_OPEN  # ADD THIS LINE
            return CircuitState.HALF_OPEN
    return self._state
```

### Verification

```bash
make test
```

---

## 3.4 `authFetch` — Combine Caller Signal With Timeout Signal

**Problem:** When caller provides its own `signal`, the internal timeout is silently lost. Streaming requests can hang forever.

**File:** `cms/apps/web/src/lib/auth-fetch.ts`

### Diagnosis

```bash
grep -n 'signal\|timeout\|AbortController' cms/apps/web/src/lib/auth-fetch.ts
```

### Fix

Use `AbortSignal.any()` to combine both signals:

```typescript
const timeoutController = new AbortController();
const timeoutId = setTimeout(() => timeoutController.abort(), timeoutMs);

const combinedSignal = init?.signal
  ? AbortSignal.any([init.signal, timeoutController.signal])
  : timeoutController.signal;

// Use combinedSignal in the fetch call instead of init?.signal or timeoutController.signal
```

### Verification

```bash
make check-fe
```

---

## 3.5 XSS — Image Alt Text Attribute Injection

**Problem:** `handleInsertImage` uses unescaped string interpolation for `<img>` attributes.

**File:** `cms/apps/web/src/app/projects/[id]/workspace/page.tsx`

### Diagnosis

```bash
grep -n 'handleInsertImage\|imgTag' cms/apps/web/src/app/projects/*/workspace/page.tsx
```

### Fix

Add an escape helper and use it:

```typescript
function escapeAttr(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// Then in handleInsertImage:
const imgTag = `<img src="${escapeAttr(url)}" alt="${escapeAttr(alt)}" width="${width}" ...`;
```

### Verification

```bash
make check-fe
```

---

## 3.6 Blueprint Run — Timeout Too Short

**Problem:** `run()` uses default 30s timeout. `resume()` correctly uses `LONG_TIMEOUT_MS` (120s).

**File:** `cms/apps/web/src/hooks/use-blueprint-run.ts`

### Diagnosis

```bash
grep -n 'LONG_TIMEOUT\|timeoutMs\|authFetch' cms/apps/web/src/hooks/use-blueprint-run.ts
```

### Fix

Add `timeoutMs: LONG_TIMEOUT_MS` to the `authFetch` call in the `run` function. Ensure `LONG_TIMEOUT_MS` is imported (it should be already, used by `resume`).

### Verification

```bash
make check-fe
```

---

## 3.7 `hypothesis` in Production Dependencies

**File:** `pyproject.toml`

### Fix

1. Remove `"hypothesis>=6.100"` from `[project.dependencies]`
2. Add `"hypothesis>=6.100"` to `[dependency-groups] dev` list
3. Re-lock:
   ```bash
   uv lock
   ```

### Verification

```bash
make test  # hypothesis available in dev
```

---

## 3.8 Demo Chat — Streaming Ignores Abort Signal

**Problem:** Demo mode `for` loop doesn't check `controller.signal.aborted`. "Stop" does nothing.

**File:** `cms/apps/web/src/hooks/use-chat.ts`

### Diagnosis

```bash
grep -n 'demo\|aborted\|signal' cms/apps/web/src/hooks/use-chat.ts
```

### Fix

Inside the demo streaming loop (the `for (const word of words)` block), add at the top:

```typescript
if (controller.signal.aborted) break;
```

### Verification

```bash
make check-fe
```

---

## 3.9 `require()` in Collaboration Hook

**Problem:** Synchronous `require("y-protocols/awareness")` may fail in Next.js client bundles.

**File:** `cms/apps/web/src/hooks/use-collaboration.ts`

### Fix

Replace the synchronous require with a dynamic import (the rest of the file already uses this pattern):

```typescript
// BEFORE:
const awareness = new (require("y-protocols/awareness").Awareness)(doc);

// AFTER:
const { Awareness } = await import("y-protocols/awareness");
const awareness = new Awareness(doc);
```

The containing function should already be `async` (it's inside a `useEffect` async IIFE).

### Verification

```bash
make check-fe
```

---

## 3.10 Missing `.env.example` Sections

**File:** `.env.example`

### Diagnosis

```bash
# See what config classes exist
grep -n 'class.*Config.*BaseSettings\|class.*Config.*BaseModel' app/core/config.py

# Compare against what's documented
cat .env.example
```

### Fix

Append these sections to `.env.example`:

```env
# ── Voice Pipeline (Phase 23.5) ──
VOICE__ENABLED=false
VOICE__TRANSCRIBER=openai
VOICE__WHISPER_MODEL=whisper-1
VOICE__MAX_DURATION_S=300
VOICE__MAX_FILE_SIZE_MB=25
VOICE__CONFIDENCE_THRESHOLD=0.7

# ── MCP Tool Server (Phase 23.4) ──
MCP__ENABLED=false
MCP__MAX_RESPONSE_TOKENS=4096
MCP__TOOL_TIMEOUT_S=30
MCP__AUDIT_LOG_ENABLED=true
# MCP__TOOL_ALLOWLIST=  # comma-separated, empty = all tools

# ── BIMI Readiness ──
QA_BIMI__ENABLED=true
QA_BIMI__SVG_FETCH_TIMEOUT_SECONDS=10

# ── Email Engine Schema.org ──
EMAIL_ENGINE__SCHEMA_INJECTION_ENABLED=false
# EMAIL_ENGINE__SCHEMA_INJECTION_TYPES=  # comma-separated

# ── Maizzle Builder Sidecar ──
MAIZZLE_BUILDER_URL=http://localhost:3001
```

### Verification

```bash
# Spot-check: every config class should have at least one env var in .env.example
diff <(grep 'class.*Config' app/core/config.py | sed 's/class //;s/(.*//') \
     <(grep '^#.*──' .env.example | sed 's/.*── //;s/ ──.*//')
```

---

## 3.11 Stale Untracked File Cleanup

### Diagnosis

```bash
# Confirm these are junk
file =2.6.0 =2.9.0
ls apps/
ls cms/cms/
ls cms/app/
```

### Fix

```bash
rm -f =2.6.0 =2.9.0
rm -rf apps/
rm -rf cms/cms/
rm -rf cms/app/
```

### Verification

```bash
# These should no longer appear in git status
git status --short | grep -E '^\?\? (=|apps/|cms/cms/|cms/app/)'
# Should return empty
```

---

## Phase 3 Gate

```bash
make check
make check-fe
```

Both must pass before proceeding to Phase 4.
