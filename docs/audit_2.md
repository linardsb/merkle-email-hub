# Audit 2 — Full System Bug Fix Plan

**Created:** 2026-03-17
**Source:** Full system audit (lint, types, tests, code review across backend/frontend/infra)
**Total issues:** 42 across 4 phases

## Execution Plan

Run phases **sequentially**. Each phase has a `make check` gate before proceeding.

| Phase | File | Items | Scope | Gate |
|-------|------|-------|-------|------|
| 1 — Critical | [`audit_2_phase1.md`](audit_2_phase1.md) | 2 items (alembic + model kwarg) | 10 files | `make check` |
| 2 — High | [`audit_2_phase2.md`](audit_2_phase2.md) | 6 items (middleware, auth, docker, e2e, routes, signatures) | 15 files | `make check` + `make check-fe` |
| 3 — Medium | [`audit_2_phase3.md`](audit_2_phase3.md) | 11 items (security, race conditions, timeouts, env, cleanup) | 20 files | `make check` + `make check-fe` |
| 4 — Low | [`audit_2_phase4.md`](audit_2_phase4.md) | 23 items (types, deps, i18n, minor frontend) | 25 files | `make check` with **0 errors** |

**Within each phase**, items can be run in parallel where noted. Each phase doc has diagnosis commands, exact fix steps, and verification commands.

**Total files touched:** ~50

---

## Detailed Reference (below)

### Phase 1: Critical & Blocking (must fix first)

### 1.1 Alembic Duplicate Revision ID `a1b2c3d4e5f6`

**Problem:** Two migration files share revision ID `a1b2c3d4e5f6` and same `down_revision`. Alembic cannot resolve the chain — `alembic upgrade head` fails or silently loses DDL.

**Files:**
- `alembic/versions/a1b2c3d4e5f6_add_component_qa_result.py`
- `alembic/versions/a1b2c3d4e5f6_add_design_connections.py`

**Fix:**
1. Run `alembic heads` to confirm the branch conflict
2. Pick one migration to keep the `a1b2c3d4e5f6` ID (whichever was created first — check file timestamps and git log)
3. Assign a new unique revision ID to the other migration (e.g., `b2c3d4e5f6a7`)
4. Update its `down_revision` to point to `a1b2c3d4e5f6` (creating a linear chain: `f1a2b3c4d5e6 → a1b2c3d4e5f6 → b2c3d4e5f6a7`)
5. Update any downstream migration that references the renamed revision as its `down_revision`
6. If both migrations branched from the same parent, create a merge migration: `alembic merge heads -m "merge_component_qa_and_design_connections"`
7. Walk the full chain to verify: `alembic history` should show a single linear path to head
8. Verify: `alembic upgrade head --sql` (dry-run) produces valid DDL

**Verification:** `alembic check` passes, `alembic upgrade head` succeeds on a clean database

---

### 1.2 Blueprint Nodes: `model=` vs `model_override=` Kwarg Mismatch

**Problem:** All 8 blueprint nodes call `provider.complete(messages, model=model)` but both `AnthropicProvider.complete()` and `OpenAICompatProvider.complete()` read `kwargs.get("model_override", self._model)`. The model tier system (complex/standard/lightweight) is silently ignored — every node uses the default model.

**Files to fix (change `model=model` → `model_override=model`):**
- `app/ai/blueprints/nodes/scaffolder_node.py` — line ~108
- `app/ai/blueprints/nodes/dark_mode_node.py` — lines ~77, ~219
- `app/ai/blueprints/nodes/outlook_fixer_node.py` — lines ~82, ~179
- `app/ai/blueprints/nodes/accessibility_node.py` — lines ~86, ~254
- `app/ai/blueprints/nodes/personalisation_node.py` — lines ~90, ~266
- `app/ai/blueprints/nodes/code_reviewer_node.py` — lines ~91, ~204
- `app/ai/blueprints/nodes/knowledge_node.py` — line ~107
- `app/ai/blueprints/nodes/innovation_node.py` — line ~82
- `app/ai/blueprints/nodes/visual_qa_node.py` — check for same pattern

**Fix:**
1. Grep all `provider.complete(` calls across `app/ai/blueprints/nodes/`
2. Replace every `model=model` with `model_override=model`
3. Cross-check: `BaseAgentService.process()` in `app/ai/agents/base.py` already uses `model_override=model` — confirm this is the correct kwarg name by reading the provider's `complete()` signature
4. Consider: should the provider accept both `model` and `model_override`? If so, update both providers to also check `kwargs.get("model")` as a fallback. This is more defensive but adds ambiguity — prefer the single kwarg rename.

**Verification:** Add a unit test that mocks a provider and asserts `model_override` is passed through from a blueprint node execution. Alternatively, run `make eval-golden` to confirm model routing works.

---

## Phase 2: High Severity

### 2.1 Voice Routes Blocked by Body Size Middleware

**Problem:** `BodySizeLimitMiddleware.UPLOAD_PATHS` only includes `("/api/v1/knowledge",)`. Voice routes at `/api/v1/ai/voice/*` accept audio up to 25MB but the middleware rejects bodies >100KB for unlisted paths.

**File:** `app/core/middleware.py`

**Fix:**
1. Add `"/api/v1/ai/voice"` to `UPLOAD_PATHS` tuple
2. Consider also adding `/mcp` if MCP tools accept large payloads (e.g., email HTML for QA analysis)
3. Review `MAX_BODY_SIZE` (100KB) — is this appropriate for non-upload API routes? Consider raising to 1MB for general API calls

**Verification:** Write a test that sends a >100KB body to a voice endpoint and confirms it's not rejected by middleware

---

### 2.2 MCP Server Authentication

**Problem:** MCP server mounted at `/mcp` with zero auth checks. `verify_mcp_token()` exists in `app/mcp/auth.py` but is never called. All 17+ tools are callable by anyone.

**Files:**
- `app/mcp/auth.py` — has `verify_mcp_token()` ready
- `app/mcp/server.py` — tool registration, no auth middleware
- `app/main.py` — mount point

**Fix (two options, pick one):**
**Option A — Middleware approach (recommended):**
1. Read `app/mcp/auth.py` to understand the token verification logic
2. Create an ASGI middleware wrapper that intercepts requests to `/mcp`, extracts the bearer token, calls `verify_mcp_token()`, and returns 401 if invalid
3. Apply the middleware to the MCP sub-application before mounting in `main.py`
4. Ensure the middleware passes through to the MCP handler on successful auth

**Option B — Per-tool approach:**
1. Add a `get_authenticated_user()` dependency to each MCP tool handler
2. This is more granular but requires touching every tool file

**Verification:** `curl -X POST http://localhost:8891/mcp` without auth returns 401. With valid token, returns tool listing.

---

### 2.3 Docker PostgreSQL Volume Path

**Problem:** Volume mounts to `/var/lib/postgresql` instead of `/var/lib/postgresql/data`. Data lives in container layer, not the named volume.

**File:** `docker-compose.yml`

**Fix:**
```yaml
# Change:
volumes:
  - postgres_data:/var/lib/postgresql
# To:
volumes:
  - postgres_data:/var/lib/postgresql/data
```

**Verification:** `docker-compose down && docker-compose up -d`, insert test data, `docker-compose down && docker-compose up -d`, verify data persists.

---

### 2.4 E2E Test Infrastructure

**Problem:** `make e2e` calls npm scripts that don't exist in `package.json`.

**Files:**
- `cms/apps/web/package.json` — add scripts
- `cms/turbo.json` — add pipeline task
- `Makefile` — deduplicate `e2e`/`e2e-all`

**Fix:**
1. Add to `cms/apps/web/package.json` scripts:
   ```json
   "e2e": "playwright test",
   "e2e:ui": "playwright test --ui"
   ```
2. Add `"e2e"` task to `cms/turbo.json` pipeline (no cache, depends on build)
3. In `Makefile`, either remove `e2e-all` or differentiate it (e.g., `e2e` runs smoke suite, `e2e-all` runs full suite with `--grep` flag)
4. Add missing `.PHONY` declarations for `e2e`, `e2e-all`, `e2e-ui`, and the other 5 missing targets (`docker-logs`, `test-properties`, `sdk-local`, `db-migrate`, `db-revision`, `eval-refresh`, `help`)

**Verification:** `make e2e` launches Playwright (even if tests fail due to missing server, the npm script should resolve)

---

### 2.5 Broken `/dashboard` Route Links

**Problem:** Three pages link to `href="/dashboard"` which doesn't exist. Dashboard is at `/`.

**Files:**
- `cms/apps/web/src/app/not-found.tsx:14`
- `cms/apps/web/src/app/(dashboard)/unauthorized/page.tsx:16`
- `cms/apps/web/src/app/(dashboard)/error.tsx:37`

**Fix:** Change `href="/dashboard"` to `href="/"` in all three files.

**Verification:** Navigate to `/nonexistent` — the "Back to Dashboard" link should go to `/`.

---

### 2.6 Agent Signature Mismatches (mypy errors)

**Problem:** 6 agent services don't accept the `context_blocks` parameter added to `BaseAgentService` in Phase 23.1. Multimodal context blocks will be silently dropped if these agents are called with them.

**Files (add `context_blocks` parameter to `process` and/or `stream_process`):**
- `app/ai/agents/personalisation/service.py:225` — `stream_process`
- `app/ai/agents/dark_mode/service.py:211` — `stream_process`
- `app/ai/agents/content/service.py:280` — `process`
- `app/ai/agents/outlook_fixer/service.py:188,322` — `process` + `stream_process`
- `app/ai/agents/code_reviewer/service.py:269,409` — `process` + `stream_process`
- `app/ai/agents/accessibility/service.py:206` — `stream_process`

**Fix:**
1. Read `app/ai/agents/base.py` to get the exact signature of `process()` and `stream_process()` including the `context_blocks` parameter type
2. For each agent, add the `context_blocks` parameter with the same type and default value (`None`)
3. Agents don't need to *use* the blocks yet — just accept the parameter so the interface contract is fulfilled
4. If the agent can benefit from multimodal context (e.g., content agent, accessibility), wire the blocks into the prompt assembly

**Verification:** `make types` — the 6 `[override]` errors should be gone

---

## Phase 3: Medium Severity

### 3.1 Body Size Middleware Chunked Encoding Bypass

**Problem:** Middleware only checks `Content-Length` header. `Transfer-Encoding: chunked` bypasses it entirely.

**File:** `app/core/middleware.py`

**Fix:**
1. After the `Content-Length` check, add a streaming body reader that counts bytes as they're consumed
2. If accumulated bytes exceed the limit, return 413 mid-stream
3. Alternative simpler approach: if no `Content-Length` header is present and path is not in `UPLOAD_PATHS`, reject the request outright (most legitimate API clients send Content-Length)

```python
# After existing Content-Length check:
content_length = request.headers.get("content-length")
if content_length is None and path not in self.UPLOAD_PATHS:
    # Reject requests without Content-Length on non-upload paths
    return JSONResponse(status_code=411, content={"detail": "Content-Length required"})
```

**Verification:** `curl -H "Transfer-Encoding: chunked" --data-binary @large_file http://localhost:8891/api/v1/projects` returns 411/413

---

### 3.2 Blueprint Cost Tracking Race Condition

**Problem:** Budget check after node execution, usage not recorded if budget exceeded, concurrent runs can double-spend.

**File:** `app/ai/blueprints/engine.py:411-425`

**Fix:**
1. Move `record_usage()` to run unconditionally BEFORE the budget check (record first, then check if we should stop)
2. For concurrency: use an atomic Redis INCRBY for budget tracking instead of check-then-record
3. At minimum, ensure `record_usage` is always called even when breaking:
   ```python
   record_usage(...)  # Always record
   remaining = check_budget(...)
   if remaining <= 0:
       break
   ```

**Verification:** Unit test: run a node that exceeds budget, assert usage is still recorded

---

### 3.3 Circuit Breaker State Property Side Effect

**Problem:** `state` property returns `HALF_OPEN` without updating `self._state`. `__aenter__` reads property, `__aexit__` reads `self._state`.

**File:** `app/core/resilience.py:62-68`

**Fix:**
```python
@property
def state(self) -> CircuitState:
    if self._state == CircuitState.OPEN:
        if time.monotonic() - self._last_failure_time >= self._timeout:
            self._state = CircuitState.HALF_OPEN  # Actually transition
            return CircuitState.HALF_OPEN
    return self._state
```

**Verification:** Unit test: open circuit, wait timeout, assert `self._state` is `HALF_OPEN`

---

### 3.4 `authFetch` Timeout Lost When Caller Provides Signal

**Problem:** Caller's signal replaces internal timeout signal. Streaming requests can hang indefinitely.

**File:** `cms/apps/web/src/lib/auth-fetch.ts:28-36`

**Fix:** Use `AbortSignal.any()` to combine the caller's signal with the timeout signal:
```typescript
const timeoutController = new AbortController();
const timeoutId = setTimeout(() => timeoutController.abort(), timeoutMs);
const combinedSignal = init?.signal
  ? AbortSignal.any([init.signal, timeoutController.signal])
  : timeoutController.signal;
```

**Verification:** Test that a streaming request with a custom signal still times out after `LONG_TIMEOUT_MS`

---

### 3.5 XSS via Image Alt Text Injection

**Problem:** `handleInsertImage` uses string interpolation without escaping for `alt`/`url`.

**File:** `cms/apps/web/src/app/projects/[id]/workspace/page.tsx:401-406`

**Fix:** Escape double quotes and angle brackets in `alt` and `url` before interpolation:
```typescript
function escapeAttr(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
const imgTag = `<img src="${escapeAttr(url)}" alt="${escapeAttr(alt)}" ...`;
```

**Verification:** Insert an image with `alt='test" onload="alert(1)'` — verify the attribute is escaped in the output HTML

---

### 3.6 Blueprint Run Timeout Too Short

**Problem:** `run()` uses default 30s timeout, `resume()` correctly uses 120s.

**File:** `cms/apps/web/src/hooks/use-blueprint-run.ts:46-53`

**Fix:** Add `timeoutMs: LONG_TIMEOUT_MS` to the `authFetch` call in `run()`, matching `resume()`.

**Verification:** Confirm `LONG_TIMEOUT_MS` is imported and used in both `run` and `resume`

---

### 3.7 `hypothesis` in Production Dependencies

**File:** `pyproject.toml`

**Fix:** Move `"hypothesis>=6.100"` from `[project.dependencies]` to `[dependency-groups] dev`

**Verification:** `uv sync --no-dev && python -c "import hypothesis"` should fail (not installed in prod)

---

### 3.8 Demo Chat Streaming Ignores Abort Signal

**Problem:** Demo mode streaming loop doesn't check `controller.signal.aborted`. "Stop" button doesn't actually stop the loop.

**File:** `cms/apps/web/src/hooks/use-chat.ts:112-121`

**Fix:** Add abort check inside the loop:
```typescript
for (const word of words) {
  if (controller.signal.aborted) break;
  // ... existing streaming logic
}
```

**Verification:** Start demo chat, click Stop mid-stream — message should stop immediately

---

### 3.9 `require()` in Collaboration Hook

**Problem:** Synchronous `require("y-protocols/awareness")` may not work in Next.js client bundles.

**File:** `cms/apps/web/src/hooks/use-collaboration.ts:43`

**Fix:** Replace with dynamic import matching the rest of the file's pattern:
```typescript
const { Awareness } = await import("y-protocols/awareness");
const awareness = new Awareness(doc);
```

**Verification:** Frontend builds without error, collaboration demo mode initializes

---

### 3.10 Missing `.env.example` Sections

**File:** `.env.example`

**Fix:** Add these sections with sensible defaults:
```env
# Voice Pipeline (Phase 23.5)
VOICE__ENABLED=false
VOICE__TRANSCRIBER=openai
VOICE__WHISPER_MODEL=whisper-1
VOICE__MAX_DURATION_S=300
VOICE__MAX_FILE_SIZE_MB=25
VOICE__CONFIDENCE_THRESHOLD=0.7

# MCP Tool Server (Phase 23.4)
MCP__ENABLED=false
MCP__MAX_RESPONSE_TOKENS=4096
MCP__TOOL_TIMEOUT_S=30
MCP__AUDIT_LOG_ENABLED=true
# MCP__TOOL_ALLOWLIST=  # comma-separated, empty = all tools

# BIMI Readiness
QA_BIMI__ENABLED=true
QA_BIMI__SVG_FETCH_TIMEOUT_SECONDS=10

# Email Engine Schema.org
EMAIL_ENGINE__SCHEMA_INJECTION_ENABLED=false
# EMAIL_ENGINE__SCHEMA_INJECTION_TYPES=  # comma-separated

# Maizzle Builder Sidecar
MAIZZLE_BUILDER_URL=http://localhost:3001
```

**Verification:** Diff `.env.example` against `app/core/config.py` — all config classes should have corresponding env vars documented

---

### 3.11 Stale Untracked File Cleanup

**Files to delete:**
- `=2.6.0` — pip artifact
- `=2.9.0` — pip artifact
- `apps/` — stale empty skeleton at repo root
- `cms/cms/` — nested duplicate workspace
- `cms/app/` — backend Python code misplaced in frontend

**Fix:** `rm -rf =2.6.0 =2.9.0 apps/ cms/cms/ cms/app/`

**Verification:** `git status` shows these are no longer listed as untracked

---

## Phase 4: Low Severity & Cleanup

### 4.1 Test Type Errors

**Ontology sync tests** (`app/knowledge/ontology/sync/tests/test_service.py`):
- 15 `[method-assign]` errors — refactor to use `mocker.patch.object()` or `unittest.mock.patch.object()` instead of direct method assignment

**Deliverability tests** (`app/qa_engine/tests/test_deliverability.py`):
- 13 `[no-untyped-def]` errors — add `Any` type annotations to test function parameters (fixtures)

**Prompt store test** (`app/ai/tests/test_prompt_store.py:499`):
- 1 `[unused-ignore]` — remove the stale `# type: ignore` comment

**Verification:** `make types` passes with 0 errors

---

### 4.2 Unused/Stale Dependencies

**File:** `pyproject.toml`

- Remove `pydub>=0.25.1` (unused — voice pipeline uses raw bytes)
- Add `pyyaml>=6.0` as explicit dependency (currently transitive, used in 5+ production files)
- Remove mypy override for `jose.*` (stale — `python-jose` was removed)

**Verification:** `uv sync && make test` — all tests still pass

---

### 4.3 `Number(params.id)` NaN Validation

**Files:**
- `cms/apps/web/src/app/projects/[id]/workspace/page.tsx:66`
- `cms/apps/web/src/app/(dashboard)/approvals/[id]/page.tsx:23`
- `cms/apps/web/src/app/(dashboard)/projects/[id]/brand/page.tsx:20`

**Fix:** Add validation:
```typescript
const projectId = Number(params.id);
if (Number.isNaN(projectId)) {
  notFound(); // or redirect("/")
}
```

---

### 4.4 Hardcoded English DOMAIN_LABELS (i18n)

**Files (duplicated in 3 places):**
- `cms/apps/web/src/app/(dashboard)/knowledge/page.tsx:29-31`
- `cms/apps/web/src/components/knowledge/knowledge-search-result.tsx:8-10`
- `cms/apps/web/src/components/knowledge/knowledge-document-card.tsx:8-10`

**Fix:**
1. Add `knowledge.domainLabels.*` keys to all 6 locale files (`en.json`, `de.json`, `ar.json`, `es.json`, `fr.json`, `ja.json`)
2. Replace hardcoded objects with `useTranslations("knowledge")` calls
3. Deduplicate: create a shared constant or utility if the same labels are needed in 3 components

---

### 4.5 Makefile Cleanup

**File:** `Makefile`

- Add missing `.PHONY`: `docker-logs test-properties e2e-ui sdk-local db-migrate db-revision eval-refresh help`
- Remove or differentiate `e2e-all` from `e2e`

---

### 4.6 Other Minor Frontend Issues

| Issue | File | Fix |
|-------|------|-----|
| `useMemo` stale `docRef` | `use-collaboration.ts:145-147` | Add `doc` to deps or use state instead of ref |
| Module-level `blockIdCounter` | `use-liquid-builder.ts:8` | Move inside hook or use `useRef` |
| `selectedNodeIdsRef` plain object | `design-file-browser.tsx:208` | Use `useRef` |
| `handleEspExport` stale closure | `export-dialog.tsx:188` | Use `useRef` for `espStates` |
| Visual QA stale `handleCapture` | `visual-qa-dialog.tsx:77-81` | Add to dep array or use ref |
| `useDeleteVoiceBrief` null `projectId` | `use-voice-briefs.ts:104` | Guard with `if (!projectId) return` |
| Approval page hardcoded "Build #" | `approvals/[id]/page.tsx:102` | Use `t("approvals.buildNumber", { id })` |

---

## Execution Order Summary

| Order | Phase | Items | Est. Scope |
|-------|-------|-------|------------|
| 1 | Critical | 1.1 (alembic), 1.2 (model kwarg) | 10 files |
| 2 | High | 2.1–2.6 (middleware, auth, docker, e2e, routes, signatures) | 15 files |
| 3 | Medium | 3.1–3.11 (security, race conditions, timeouts, env, cleanup) | 20 files |
| 4 | Low | 4.1–4.6 (types, deps, i18n, minor frontend) | 25 files |

**Total files touched:** ~50
**Verification gate:** `make check` (lint + types + tests + security) must pass after each phase
