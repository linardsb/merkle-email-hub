# Plan: Fix Frontend↔Backend Connection Issues

**Created:** 2026-03-19
**Status:** Ready for implementation
**Scope:** All frontend hooks, backend routes, WebSocket, sidecar connections

---

## Audit Summary

Thorough audit of **60+ frontend hooks** against **300+ backend endpoints** across all features. Checked URL paths, HTTP methods, request/response schemas, auth flow, WebSocket connections, sidecar wiring, and CORS config.

**Overall health: ~93% aligned** — 4 broken connections, 4 type/wiring gaps, 3 informational items.

---

## CRITICAL Issues (Will cause 404/500 in production)

### C1. Figma hooks use wrong URL prefix
- **Frontend:** `cms/apps/web/src/hooks/use-figma.ts` calls `/api/v1/figma/connections`, `/api/v1/figma/connections/{id}`, `/api/v1/figma/connections/{id}/tokens`, etc.
- **Backend:** No `/api/v1/figma/` prefix exists. All design providers are unified under `/api/v1/design-sync/` (`app/design_sync/routes.py`)
- **Impact:** All 6 Figma hook endpoints return 404
- **Fix:** Rewrite `use-figma.ts` to use `/api/v1/design-sync/` prefix. The hook already exists as `use-design-sync.ts` with correct URLs — consider whether `use-figma.ts` is redundant or should be a thin wrapper filtering `provider=figma` over design-sync hooks.
- **Files:** `cms/apps/web/src/hooks/use-figma.ts`, possibly `cms/apps/web/src/components/figma/` consumers

### C2. Blueprint runs listing endpoint missing
- **Frontend:** `cms/apps/web/src/hooks/use-blueprint-runs.ts` calls `GET /api/v1/projects/{projectId}/blueprint-runs?status=...&page_size=50` and `GET /api/v1/blueprint-runs/{runId}`
- **Backend:** Neither endpoint exists. `app/projects/routes.py` has no blueprint-runs listing. `app/ai/blueprints/routes.py` only has `/run`, `/resume`, `/failures/*`, and `/runs/{id}/checkpoints`.
- **Impact:** Blueprint run history page shows empty/errors
- **Fix:** Add two backend endpoints:
  1. `GET /api/v1/projects/{project_id}/blueprint-runs` in `app/projects/routes.py` or `app/ai/blueprints/routes.py` — paginated listing filtered by project
  2. `GET /api/v1/blueprint-runs/{run_id}` — single run detail with node results
- **Files:** `app/ai/blueprints/routes.py` (add routes), `app/ai/blueprints/service.py` (add listing logic), possibly new schemas

### C3. Tolgee missing GET connection endpoint
- **Frontend:** `cms/apps/web/src/hooks/use-tolgee.ts` (line ~20-24) calls `GET /api/v1/connectors/tolgee/connections/{connectionId}`
- **Backend:** `app/connectors/tolgee/routes.py` has POST `/connection`, POST `/sync-keys`, POST `/pull`, POST `/build-locales`, GET `/languages/{connection_id}` — but NO GET for individual connection
- **Impact:** Tolgee connection detail view returns 404
- **Fix:** Add `GET /connections/{connection_id}` endpoint to `app/connectors/tolgee/routes.py` returning connection metadata
- **Files:** `app/connectors/tolgee/routes.py`, `app/connectors/tolgee/service.py`

### C4. Chat completions URL routing mismatch
- **Frontend:** `cms/apps/web/src/hooks/use-chat.ts` calls `${API_BASE}/v1/chat/completions` where `API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/proxy"`
- **Backend:** Route is at `/v1/chat/completions` (prefix `/v1` in `app/ai/routes.py`)
- **Problem:** If `API_BASE="/api/proxy"`, the full URL becomes `/api/proxy/v1/chat/completions` which won't match the backend path `/v1/chat/completions`. The Next.js proxy route handler at `src/app/api/v1/[[...path]]/route.ts` only catches `/api/v1/*`, NOT `/api/proxy/*` or `/v1/*`.
- **Impact:** Chat completions may fail depending on environment config
- **Fix:** Verify the routing chain. Either:
  - Change frontend to call `/api/v1/ai/chat/completions` (the backend also mounts under `/api/v1/ai`), OR
  - Add `/v1/*` to the Next.js proxy catch-all, OR
  - Ensure `NEXT_PUBLIC_API_URL` is always set to the direct backend URL (`http://localhost:8891`) in all environments
- **Files:** `cms/apps/web/src/hooks/use-chat.ts`, `cms/apps/web/src/app/api/v1/[[...path]]/route.ts`

---

## MEDIUM Issues (Type mismatches / missing wiring)

### M1. DesignConnection type missing `error_message` field
- **Backend:** `ConnectionResponse` in `app/design_sync/schemas.py` returns `error_message: str | None`
- **Frontend:** `DesignConnection` in `cms/apps/web/src/types/design-sync.ts` does NOT include `error_message`
- **Impact:** Sync error messages from design providers silently dropped in UI
- **Fix:** Add `error_message: string | null` to `DesignConnection` interface
- **Files:** `cms/apps/web/src/types/design-sync.ts`

### M2. ConvertImportArg output_mode loosely typed
- **Backend:** `ConvertImportRequest` defines `output_mode: Literal["html", "structured"]`
- **Frontend:** `ConvertImportArg` uses `output_mode?: string`
- **Impact:** No compile-time protection against invalid values
- **Fix:** Change to `output_mode?: "html" | "structured"`
- **Files:** `cms/apps/web/src/types/design-sync.ts`

### M3. Component "Run QA" button not wired
- **Backend:** `POST /api/v1/components/{id}/versions/{version_number}/qa` exists and works
- **Frontend:** `component-version-timeline.tsx` renders a "Run QA" button but has NO onClick handler
- **Impact:** Users see a QA button that does nothing
- **Fix:** Add onClick handler that calls the backend QA endpoint via a new `useRunComponentQA` mutation hook
- **Files:** `cms/apps/web/src/components/components/component-version-timeline.tsx`, `cms/apps/web/src/hooks/use-components.ts`

### M4. Component version creation doesn't send slot_definitions/default_tokens
- **Backend:** `VersionCreate` schema accepts `slot_definitions: list[SlotHintSchema] | None` and `default_tokens: dict[str, Any] | None`
- **Frontend:** `useCreateVersion` hook and `create-version-dialog.tsx` only send `html_source`, `css_source`, `changelog`
- **Impact:** Visual builder features (slot editing, token overrides) can't be set when creating versions through UI
- **Fix:** Either add form fields to create-version-dialog for slot_definitions/default_tokens, or auto-extract them from html_source on the backend (if not already done)
- **Files:** `cms/apps/web/src/hooks/use-components.ts`, `cms/apps/web/src/components/components/create-version-dialog.tsx`

---

## LOW Issues (Informational / missing features)

### L1. Design origin assignment — backend exists, no frontend UI
- **Backend:** `POST /api/v1/components/{id}/design-origin` with `AssignDesignOriginRequest`
- **Frontend:** No hook or UI component for this
- **Note:** May be intentionally backend-only (used by design-sync import pipeline)

### L2. Backend-only design-sync endpoints
- `POST /api/v1/design-sync/analyze-layout` — no frontend hook
- `POST /api/v1/design-sync/download-assets` — no frontend hook
- `GET /api/v1/design-sync/assets/{connection_id}/{filename}` — used via direct URL, no hook needed
- **Note:** These may be intentionally backend-only or planned for future UI

### L3. CSP headers overly permissive for production
- `next.config.ts` allows `'unsafe-inline'` and `'unsafe-eval'` in script-src
- Acceptable for development, should be tightened for production deployment

---

## Implementation Priority

| # | Issue | Severity | Effort | Order |
|---|-------|----------|--------|-------|
| C1 | Figma hooks wrong prefix | Critical | Small | 1st |
| C4 | Chat completions URL routing | Critical | Small | 2nd |
| C3 | Tolgee missing GET endpoint | Critical | Small | 3rd |
| C2 | Blueprint runs endpoints missing | Critical | Medium | 4th |
| M1 | DesignConnection missing field | Medium | Tiny | 5th |
| M2 | ConvertImportArg loose typing | Medium | Tiny | 6th |
| M3 | Run QA button not wired | Medium | Small | 7th |
| M4 | Version creation missing fields | Medium | Medium | 8th |

---

## Verified Working Connections (No Issues)

These were all checked and confirmed aligned:

- **Auth flow:** Login → JWT → refresh → authFetch injection ✅
- **Next.js proxy:** `/api/v1/*` → backend:8891 ✅
- **Projects** (CRUD, design-system, template-config) ✅
- **Templates** (listing under projects, CRUD, versions) ✅
- **Components** (CRUD, versions, compatibility) ✅
- **QA Engine** (run, results, latest, override) ✅
- **Approvals** (CRUD, decide, feedback, audit) ✅
- **Connectors/ESP** (export, sync connections) ✅
- **Design-Sync** (connections, tokens, imports, convert, extract) ✅
- **Briefs** (connections, items, sync, import) ✅
- **Knowledge** (documents, search, graph) ✅
- **Rendering** (tests, compare, screenshots) ✅
- **Personas** (list, get, create) ✅
- **Email Engine** (build, preview) ✅
- **Plugins** (list, health, enable/disable/restart) ✅
- **Workflows** (list, trigger, execution status/logs) ✅
- **Reports** (QA, approval, regression, download) ✅
- **Collaboration WebSocket** (`/ws/collab/{room_id}`) ✅
- **Maizzle sidecar** (build, preview on port 3001) ✅
- **Mock ESP sidecar** (Braze, SFMC, Adobe, Taxi on port 3002) ✅
- **CORS** (localhost:3000 + localhost:8891, credentials allowed) ✅
- **Middleware** (body size limits, request logging, rate limiting) ✅
