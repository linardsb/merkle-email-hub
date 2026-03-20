# Plan: Fix LLM & AI Agent Connection Issues

**Created:** 2026-03-19
**Status:** Ready for implementation
**Scope:** All frontend→backend→LLM provider connection chains

---

## Audit Summary

Traced every LLM connection end-to-end: frontend hook → Next.js proxy → FastAPI handler → provider adapter → external API. The provider infrastructure (registry, adapters, cost governor) is solid. The issues are in the **frontend routing layer** that sits in front of it.

---

## Architecture Overview

```
Frontend Hooks
  ↓ authFetch() with Bearer JWT
Next.js Proxy (/api/v1/[[...path]])
  ↓ fetch(BACKEND_URL + pathname)
FastAPI Backend
  ↓ Provider Registry → get_llm(settings.ai.provider)
LLM Adapters (AnthropicProvider | OpenAICompatProvider)
  ↓ SDK/httpx call
External API (Anthropic / OpenAI / Ollama / vLLM)
```

**Providers registered:** anthropic, openai, ollama, vllm, litellm
**Embeddings:** Separate config (`EMBEDDING__*`), uses OpenAI SDK
**Cost governor:** Redis-backed monthly budget in GBP, checks before every LLM call

---

## Issues

### L1. Chat completions URL routing mismatch (CRITICAL)

**The problem:**
- `use-chat.ts` builds URL as `${API_BASE}/v1/chat/completions`
- `API_BASE` defaults to `process.env.NEXT_PUBLIC_API_URL || "/api/proxy"`
- When `API_BASE = "/api/proxy"` → final URL = `/api/proxy/v1/chat/completions`
- Next.js catch-all proxy lives at `/api/v1/[[...path]]` — only matches `/api/v1/*`
- `/api/proxy/v1/*` has NO handler → **404**

**When it works by accident:**
- If `NEXT_PUBLIC_API_URL = "http://localhost:8891"` (set in `.env.local`) → bypasses proxy entirely, calls backend directly → works
- But this means the frontend makes cross-origin calls, relying on CORS

**When it breaks:**
- Production or any env where `NEXT_PUBLIC_API_URL` is unset
- The `/api/proxy` default path doesn't exist as a route

**Fix options (pick one):**

**Option A — Align URL to use /api/v1/ prefix (recommended):**
```typescript
// use-chat.ts — change URL construction
// FROM:
return `${API_BASE}/v1/chat/completions`;
// TO:
return `/api/v1/ai/chat/completions`;
```
This uses the existing Next.js proxy at `/api/v1/[[...path]]` which forwards to the backend. The backend mounts AI routes at `/api/v1/ai/` (confirmed in `app/ai/routes.py` with prefix and `app/main.py` include). The catch-all strips `/api/v1/` and forwards, so the backend receives `/api/v1/ai/chat/completions`.

Wait — need to verify: the backend AI router uses prefix `/v1` not `/api/v1/ai`. Check `app/main.py` for how the AI router is included.

**Verification needed before implementing:**
1. Check exact prefix in `app/main.py` where AI router is included — is it `/v1` or `/api/v1/ai`?
2. Check if the Next.js proxy strips `/api/v1` or passes the full path
3. Test: does `http://localhost:8891/api/v1/ai/chat/completions` return 200?

**Option B — Add /v1/ proxy route:**
Create `cms/apps/web/src/app/api/v1/ai/[[...path]]/route.ts` or expand the existing catch-all to also handle `/v1/*` paths.

**Option C — Keep direct backend URL but make it required:**
Require `NEXT_PUBLIC_API_URL` in all environments, document it as mandatory. This means CORS must be configured for the frontend origin in all deployments.

**Files:** `cms/apps/web/src/hooks/use-chat.ts`, possibly `cms/apps/web/src/app/api/` proxy routes, `app/main.py`

---

### L2. Scaffolder streaming URL — same pattern, works differently

**Current state:**
- `use-chat.ts` builds scaffolder URL as `${API_BASE}/api/v1/agents/scaffolder/generate`
- When `API_BASE = "http://localhost:8891"` → `http://localhost:8891/api/v1/agents/scaffolder/generate` → works (direct)
- When `API_BASE = "/api/proxy"` → `/api/proxy/api/v1/agents/scaffolder/generate` → **404** (double prefix)

**Fix:** Same as L1 — normalize to use `/api/v1/agents/scaffolder/generate` (relative, goes through proxy)

**Files:** `cms/apps/web/src/hooks/use-chat.ts`

---

### L3. Voice pipeline — frontend hooks missing

**Current state:**
- Backend has 3 voice endpoints: `/api/v1/voice/transcribe`, `/brief`, `/run`
- No frontend hooks found for voice features
- These may be backend-only / API-only features

**Action:** Verify if voice UI exists. If not, this is informational only — the backend endpoints work.

**Files:** Search for voice/audio UI components in `cms/`

---

### L4. Knowledge graph search — verify embedding provider config

**Current state:**
- Embeddings use a SEPARATE config from chat LLM: `EMBEDDING__PROVIDER`, `EMBEDDING__API_KEY`, `EMBEDDING__MODEL`
- If only `AI__API_KEY` is set but `EMBEDDING__API_KEY` is not, knowledge search will fail
- The embedding provider defaults to `openai` with `text-embedding-3-small`

**Action:** Ensure `.env.example` documents that `EMBEDDING__API_KEY` must be set separately if using knowledge search. Add validation or fallback to `AI__API_KEY` if `EMBEDDING__API_KEY` is unset.

**Files:** `app/core/config.py`, `app/knowledge/embedding.py`, `.env.example`

---

### L5. Cost governor — silent failure if Redis unavailable

**Current state:**
- Cost governor is Redis-backed (`AI__COST_GOVERNOR_ENABLED=true`)
- If Redis is down, the governor may raise exceptions that block LLM calls
- Need to verify: does it fail-open (allow LLM calls) or fail-closed (block them)?

**Action:** Verify error handling in `cost_governor.py`. If it fails-closed, add fail-open behavior with warning log.

**Files:** `app/ai/cost_governor.py`

---

### L6. Blueprint run history — no backend endpoint (cross-ref from connection plan)

**Current state:**
- Frontend `use-blueprint-runs.ts` calls `GET /api/v1/projects/{id}/blueprint-runs`
- This endpoint doesn't exist on the backend
- Users can trigger blueprint runs but cannot view their history

**Impact on LLM features:** Users run expensive LLM pipeline ($0.50–$2.00 per run) but can't see results afterward.

**Fix:** Add listing endpoint to `app/ai/blueprints/routes.py`:
- `GET /api/v1/blueprints/runs?project_id={id}&status={s}&page_size={n}` — paginated listing
- `GET /api/v1/blueprints/runs/{run_id}` — single run detail with node results
- Update frontend hook to use the correct path

**Files:** `app/ai/blueprints/routes.py`, `app/ai/blueprints/service.py`, `cms/apps/web/src/hooks/use-blueprint-runs.ts`

---

## Implementation Priority

| # | Issue | Impact | Effort | Status |
|---|-------|--------|--------|--------|
| L1 | Chat completions URL routing | Chat broken without env var | Small | **Already fixed** — dual-mount in main.py:342 + proxy-aware `buildUrl()` |
| L2 | Scaffolder URL same issue | Scaffolder broken without env var | Tiny | **Already fixed** — same proxy-aware pattern |
| L6 | Blueprint run history missing | Can't view LLM results | Medium | **Already implemented** — `runs_router` in routes.py + main.py:377 |
| L4 | Embedding API key fallback | Knowledge search may fail silently | Small | **Fixed** — falls back to `AI__API_KEY` when `EMBEDDING__API_KEY` unset |
| L5 | Cost governor Redis resilience | LLM calls may block if Redis down | Small | **Already handled** — in-memory fallback in `_increment()` / `_get_monthly_total()` |
| L3 | Voice frontend hooks | No UI for voice features | Info only | N/A |

---

## Verified Working (No Issues)

| Component | Status |
|-----------|--------|
| Provider registry (anthropic, openai, ollama, vllm, litellm) | ✅ |
| AnthropicProvider — SDK init, streaming, cost reporting | ✅ |
| OpenAICompatProvider — httpx client, base_url config, streaming | ✅ |
| Model tier routing (complex/standard/lightweight) | ✅ |
| Cost governor — budget check, recording, monthly rollup | ✅ |
| JWT auth on all LLM routes | ✅ |
| Daily user quota (Redis-backed) | ✅ |
| Rate limiting per endpoint | ✅ |
| SSE streaming format (OpenAI-compatible) | ✅ |
| Frontend SSE parsing in use-chat.ts | ✅ |
| Blueprint engine → agent → provider chain | ✅ |
| Scaffolder → provider → streaming chain | ✅ |
| Knowledge embedding provider (separate config) | ✅ |
| Inline judges on blueprint retry | ✅ |
| Production trace sampling | ✅ |

---

## Env Vars Reference

```bash
# === LLM Chat/Agents ===
AI__PROVIDER=anthropic              # Provider name (anthropic|openai|ollama|vllm|litellm)
AI__MODEL=claude-opus-4-20250514   # Default model
AI__API_KEY=sk-...                  # Required (except local endpoints)
AI__BASE_URL=                       # Optional, for custom endpoints

# Model tiers (optional, falls back to AI__MODEL)
AI__MODEL_COMPLEX=claude-opus-4-20250514
AI__MODEL_STANDARD=claude-sonnet-4-20250514
AI__MODEL_LIGHTWEIGHT=claude-haiku-4-5-20251001

# === Cost Governance ===
AI__COST_GOVERNOR_ENABLED=false     # Enable budget tracking
AI__MONTHLY_BUDGET_GBP=600.0       # Monthly cap
AI__BUDGET_WARNING_THRESHOLD=0.8   # Warning at 80%

# === Embeddings (separate from chat) ===
EMBEDDING__PROVIDER=openai
EMBEDDING__MODEL=text-embedding-3-small
EMBEDDING__API_KEY=sk-...           # ⚠️ Must be set separately from AI__API_KEY
EMBEDDING__DIMENSION=1536

# === Frontend ===
NEXT_PUBLIC_API_URL=http://localhost:8891  # ⚠️ If unset, chat/scaffolder break (L1/L2)
BACKEND_URL=http://localhost:8891          # Next.js proxy target
```
