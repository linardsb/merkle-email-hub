# Tech Debt Audit — merkle-email-hub

**Generated:** 2026-04-26
**Branch:** `audit/phase-2-ci-gates`
**Scope:** Backend `app/` (~267k LOC, 870 source files), Frontend `cms/` (~90k LOC), services + infra
**Method:** 7 parallel subagents per module, each producing file:line-cited findings, plus a tooling pass (ruff/pip-audit/grep counts). Final list is deduped and ranked.

---

## Executive Summary

1. **Multi-tenant isolation is a Potemkin village.** Postgres RLS policies exist but the app connects as a `BYPASSRLS` superuser and never issues `SET LOCAL app.current_client_id`; only `app/projects/repository.py` filters by `client_org_id`. **Every other repository (`auth`, `components`, `templates`, `qa_engine`, `knowledge`, `memory`, `briefs`, `approval`) leaks across tenants.** [F001–F003]
2. **Public agent route bypasses the prompt-injection guard.** `_process_structured()` in 7 agent services (`scaffolder` and 6 more) does not call `scan_for_injection`; the HTML path does. The structured branch is reachable from `/api/v1/agents/scaffolder/...`. [F004]
3. **MCP per-user role enforcement is computed but never applied.** `viewer` tokens can invoke writeful tools (`agent_scaffold`, `mcp_batch_execute`). [F005]
4. **An entire orphan transit-data WebSocket subsystem is mounted in production** (`/ws/stream`, ~600 LOC under `app/streaming/{manager,subscriber,routes}.py`). Zero publishers exist. JWT in query string. [F006]
5. **`app/example/` CRUD demo routes are mounted unconditionally** (`/api/v1/items`). [F007]
6. **~1,500 LOC of Phase 48 DAG/Evaluator infrastructure is dormant** (drift, not active harm). Built, tested, gated behind `settings.pipeline.enabled=False` with no caller flipping it. The legacy `BlueprintEngine` is still the production orchestrator. [F008–F009]
7. **`design_sync/` is overweight.** Owns 7 of top 15 hand-written files; `service.py` (2058), `figma/service.py` (1720, 125 `Any` uses), `converter.py` (1601), `converter_service.py` (1519), `component_matcher.py` (1469). Two parallel rendering paths (`converter.py` legacy vs component-template) coexist. [F010–F015]
8. **God-orchestrator hot spots in `app/ai/blueprints/engine.py`** — 1416 LOC, 18 broad `except Exception`, 8 `# type: ignore`. `_build_node_context` is 437 LOC across 18 numbered LAYERs; `_execute_from` is 397 LOC. [F016–F017]
9. **`app/qa_engine/custom_checks.py` is a 3738-LOC god file** with 125 registered check functions and 11 copies of the `_param` helper. The 14 QA check classes around it are 60–110 LOC of identical RuleEngine boilerplate (~900 LOC removable). [F018–F019]
10. **Connector duplication: SFMC≈Adobe (OAuth) and Braze≈Taxi (API-key) are byte-equivalent services.** Production code carries 4 `isinstance(..., dict)` MagicMock guards because of test-fixture leakage. [F020–F021]

**Risk-weighted top concern:** The combination of #1 (RLS inert) and the wider security findings makes this codebase **structurally insecure for multi-tenant deployment** despite the README's "Zero Trust API" claim. Everything else is repayable; that one is a foundation.

---

## Architectural Mental Model

A Vertical-Slice Architecture FastAPI backend (`app/{feature}/{models,schemas,routes,service,repository}.py`) plus a Next.js 16 / React 19 frontend (`cms/`). 27 backend modules, 9 AI agents under `app/ai/agents/`, 14 QA checks under `app/qa_engine/checks/`, 4 ESP connectors under `app/connectors/{braze,sfmc,adobe,taxi}/`. Three sidecars: `services/maizzle-builder/` (Node, MJML/Tailwind email compile), `services/mock-esp/` (test-only), and a Next.js frontend.

The system has gone through ~49 phases of feature roll-outs (per `CLAUDE.md`). Newer phases tend to be **flag-gated, well-tested in isolation, but not wired through the production path** — Phase 47 (visual-verify loop), Phase 48 (DAG executor + evaluator agent + meta-eval), and Phase 49 (tree bridge) are the clearest examples. Older phases have started to calcify into god files (the engine, the converter, the custom_checks file). **The codebase is in an "implementation complete, integration pending" state across multiple recent phases.**

The README claims tenant isolation via Postgres RLS; the actual enforcement layer is empty. The README claims "Zero Trust API"; the public agent endpoints have a structured-output bypass. These are the highest-impact contradictions.

The frontend is in genuinely good shape — zero `as any`, zero raw color primitives, smart-polling discipline enforced — but two files (`custom-icons.tsx` 9882 LOC, `workspace/page.tsx` 848 LOC) and a `@ts-nocheck` cluster in tests carry most of its debt.

---

## Findings

| ID | Cat | File:Line | Sev | Eff | Description | Recommendation |
|---|---|---|---|---|---|---|
| **F001** | Security/Multi-tenant | `alembic/versions/fdd89fceac29_add_rls_policies_for_tenant_isolation.py:23-39`; `.env.example:8` | Critical | L | RLS policies depend on `current_setting('app.current_client_id')` but **no code path issues `SET LOCAL`**, and the app connects as `postgres` superuser (BYPASSRLS). RLS is inert. | Either (a) commit to RLS — add a request-scoped middleware that runs `SELECT set_config('app.current_client_id', :id, true)` per request and switch to a non-superuser DB role; or (b) delete the RLS migrations and enforce isolation in the repository layer. Don't keep both half-built. |
| **F002** | Security/Multi-tenant | `app/auth/repository.py`, `app/components/repository.py`, `app/templates/repository.py`, `app/qa_engine/repository.py`, `app/knowledge/repository.py`, `app/memory/repository.py`, `app/briefs/repository.py`, `app/approval/repository.py` | Critical | M | Only `app/projects/repository.py:78-79,97-98` filters by `client_org_id`. All other repositories return rows across tenants. Combined with F001, any authenticated user can list/access components/templates/QA/knowledge/memory/briefs/approvals across orgs. | Add `client_org_id` to every list/get query. Make the user's org a required scope on the auth dependency and pass it through service → repository. |
| **F003** | Security/Authz | `app/projects/routes.py:73-83`; `app/projects/service.py:77-101` | Critical | S | `GET /projects` accepts `?client_org_id=N` and passes it through unchecked. A non-admin user passing another org's id gets that org's projects. | Reject the query param for non-admin roles; default-scope to the requester's `current_user.client_org_id`. |
| **F004** | Security/Prompt injection | `app/ai/agents/scaffolder/service.py:134-159`; `app/ai/agents/scaffolder/routes.py:27-28`; same pattern in 6 other agent services | Critical | S | **RESOLVED** (Plan 02). `_scan_request` runs in `BaseAgentService._process_impl` before the output-mode branch and writes back sanitized text via `_apply_sanitized_input` for the structured-pipeline path. All 7 agents covered by `_user_input_field`; `test_injection_guard_coverage.py` parametrizes the matrix. |
| **F005** | Security/Authz | `app/mcp/auth.py:35-43`; `app/mcp/server.py:52-56` | Critical | M | **RESOLVED** (Plan 02). `MCPAuthMiddleware` plumbs the verified-token scopes into `current_scopes_var`; `@require_scope` gates each of the 27 tools (26 in `app/mcp/tools/` + `mcp_batch_execute`). Wrap order is `scope_check → cache → original` so denied calls never hit the cache. `_enforce_scope_declarations` fails server boot if any tool ships without the marker. |
| **F006** | Dead code/Security | `app/streaming/manager.py:32-223`, `subscriber.py:22-96`, `routes.py:69`; mounted at `app/main.py:401` | Critical | S | The `/ws/stream` endpoint subscribes to `stream:data:*` and returns transit-data-shaped attributes (`feed_id`, `route_id`). Zero publishers exist anywhere in the repo. JWT taken from query string. ~600 LOC + tests. | Delete `manager.py`, `subscriber.py`, `routes.py`, the WS mount, and the test directory. The CRDT collab WS at `app/streaming/websocket/` is unrelated and stays. |
| **F007** | Dead code | `app/example/routes.py:20`; `app/main.py:50,388` | Critical | S | Demo Item CRUD scaffold ships in production at `/api/v1/items`. 240 LOC + 122-LOC test file. | Delete `app/example/` and the import in `main.py`. |
| **F008** | Architecture | `app/ai/blueprints/nodes/evaluator_node.py:27`; `app/ai/blueprints/engine.py:580-600` | High | S | **RESOLVED** (Plan 05, Path B). `EvaluatorNode`, the evaluator agent, and the engine evaluator-revision routing (`evaluator_revision_count`, `"revise"` edge condition, max_revisions cap) are parked under `prototypes/ai-pipeline/`. Re-import requires evaluator calibration baseline. See `docs/phase-48-status.md`. |
| **F009** | Architecture | `app/ai/pipeline/executor.py:63`; `settings.pipeline.enabled=False` (`app/core/config.py:817`) | High | M | **RESOLVED** (Plan 05, Path B). The DAG executor, contracts, registry, adapters, hook system, and `adversarial_gate` are parked under `prototypes/ai-pipeline/`. `PipelineConfig`, `HookConfig`, `EvaluatorConfig`, and the `PIPELINE__` / `AI__EVALUATOR__` env hints are gone from `app/core/config.py` and `feature-flags.yaml`. See `docs/phase-48-status.md`. |
| **F010** | God function | `app/design_sync/converter.py:616-1166` (`node_to_email_html`, 551 LOC, 16 params) | Critical | M | Recursive renderer with 16 threaded args (section_map, button_ids, gradients_map, slot_counter, parent_bg, parent_font, _depth, …) and embedded type dispatch over `DesignNode`. Untestable in isolation. | Extract per-node-type renderers; bundle threaded params into a frozen `RenderContext` dataclass. |
| **F011** | God function | `app/design_sync/converter_service.py:649-973` (`_convert_with_components`, 325 LOC) | Critical | M | Owns sibling detection, matching, rendering, repeating-group dispatch, custom-component generation, tree bridge, verification loop, contract validation. Single function = whole pipeline. | Split into 4–6 staged private methods returning intermediate dataclasses (`MatchPhase`, `RenderPhase`, `VerifyPhase`). |
| **F012** | God class | `app/design_sync/service.py:131-1729` (`DesignSyncService`, 49 methods) | Critical | M | Provider abstraction + connections + tokens + structure + components + assets + layout analysis + briefs + imports + conversion + webhooks + project access in one class. | Carve `ConnectionService`, `AssetsService`, `ImportService`, `WebhookService`. Boundaries already exist as section comments. |
| **F013** | Dead/legacy | `app/design_sync/converter_service.py:1013-1156` (`_convert_recursive`); shims at `:441,505,1024` called from `app/design_sync/service.py:362`, `app/design_sync/penpot/service.py:165` | Critical | L | Legacy recursive renderer + 2 "Legacy entry points" shims still wired with no deprecation warning emitted, no metric, no removal date. The `node_to_email_html` chain is ~750 LOC. | Add structured logging at the 2 entry points to measure fallback hit rate; emit `DeprecationWarning`; gate behind a flag and schedule removal. |
| **F014** | God file | `app/design_sync/figma/service.py:1239-1454` (`_parse_node`, 216 LOC) and `:683-846` (`_parse_variables`, 164 LOC) | High | M | 1720-LOC Figma JSON parser, 125 `Any` references, 7 `# type: ignore`. Conflates bbox / fill / stroke / gradient / text / child / depth-limit / type-mapping. | Extract `_parse_visual_props`, `_parse_text_props`, `_parse_layout_props`. Introduce TypedDicts at the Figma JSON boundary (`figma/raw_types.py`). |
| **F015** | Dead code | `app/design_sync/mjml_generator.py` (443 LOC); `app/design_sync/penpot/converter.py` shim; `DESIGN_SYNC__PENPOT_CONVERTER_ENABLED` flag (`config.py:356`) never read | High | S | `mjml_generator.py` only referenced from its own test. Penpot converter is a re-export shim. The flag has zero callers. | Delete all three. ~700 LOC saved. |
| **F016** | God function | `app/ai/blueprints/engine.py:738` (`_build_node_context`, 437 LOC, 18 numbered LAYERs) | High | L | Every new context concern bolted on as another LAYER. Mutates `context.metadata` in-place; ordering is critical and untestable. | Split into per-layer methods returning `dict[str, Any] \| None`; merge from a list. Behaviour-preserving refactor. |
| **F017** | God function | `app/ai/blueprints/engine.py:270` (`_execute_from`, 397 LOC) | High | L | Cost cap + evaluator routing (lines 580-600) + confidence routing + recovery + checkpoint persistence in one function. | Extract `_handle_node_result`, `_apply_evaluator_verdict`, `_persist_checkpoint_if_enabled`. |
| **F018** | God file | `app/qa_engine/custom_checks.py` (3738 LOC, 125 registered checks, 11 copies of `_param`) | Critical | M | Already organized by section comments at lines 158, 845, 1620, 1725, 2069, 2275, 2436, 2703, 2892, 3193, 3473. | Mechanical split into `app/qa_engine/custom_checks/{html,a11y,mso,dark_mode,link,file_size,spam,brand,image,css,personalisation}.py` with side-effect imports in `__init__.py`. Single shared `_param` helper. |
| **F019** | Boilerplate | `app/qa_engine/checks/{html_validation,dark_mode,accessibility,fallback,file_size,link_validation,image_optimization,brand_compliance,personalisation_syntax,spam_score,css_support,liquid_syntax,rendering_resilience}.py` | High | M | 14 check classes × 60–110 LOC each, all calling `RuleEngine.evaluate` with the same scaffolding. ~900 LOC of identical structure. | Introduce `RuleEngineCheck(name, rules_path, cache_clear=None, severity="warning")` factory + a registry table. `css_audit.py` and `deliverability.py` stay bespoke. |
| **F020** | Duplication | `app/connectors/sfmc/service.py:23-158` ↔ `app/connectors/adobe/service.py:23-161` | Critical | M | **RESOLVED** (Plan 04). `app/connectors/_base/oauth.py` `OAuthConnectorService` ABC owns the token cache, `_get_access_token` with refresh-grace, `_parse_pool_credentials` json+shape validation, and 401-evict-and-retry-once. SFMC and Adobe each shrink to ~44 LOC overriding `_token_url`, `_asset_url`, `_build_payload`, `_external_id_from_response`, plus Adobe's `auth_request_encoding="form"` and 86399s `default_token_ttl` overrides. |
| **F021** | Duplication | `app/connectors/braze/service.py:18-98` ↔ `app/connectors/taxi/service.py:18-104` | Critical | M | **RESOLVED** (Plan 04). `app/connectors/_base/api_key.py` `ApiKeyConnectorService` ABC owns pool init, lease lifecycle, export pipeline, error wrapping. Braze (44 LOC) and Taxi (44 LOC) each override `_endpoint`, `_auth_header`, `_build_payload`, `_external_id_from_response`, `_mock_external_id`. OAuth ABC inherits from this one — header logic shared. |
| F022 | Test leak | `app/connectors/{braze,sfmc,adobe,taxi}/service.py` constructor `isinstance(_settings.credentials.pools, dict)` guards | High | S | **RESOLVED** (Plan 04). The `isinstance` MagicMock guards are gone; `ApiKeyConnectorService.__init__` checks `_settings.credentials.enabled and self.service_name in _settings.credentials.pools` directly. Tests inject typed `Settings` via the existing `monkeypatch.setattr("…get_settings", lambda: real_settings)` fixture, now extended to patch `app.connectors._base.api_key` as well (`raising=False`). |
| F023 | Resilience | `app/connectors/{braze,sfmc,adobe,taxi}/service.py` `except Exception → report_failure(0)` | High | S | **RESOLVED** (Plan 04). The shared `ApiKeyConnectorService.export` and `OAuthConnectorService.export` narrow to `(httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError)`. `KeyError` parsing the response body propagates uncaught (no lease blame). Per-service tests assert `lease.report_failure.assert_not_awaited()` for the `KeyError` case. |
| F024 | Cache hygiene | `app/connectors/sfmc/service.py:30`, `adobe:30` (`_token_cache: ClassVar[dict]`) | High | S | **RESOLVED** (Plan 04). `app/core/cache.py` provides a generic `LruWithTtl[K, V]` (maxsize=64, default_ttl 3600s, refresh-grace 60s, OrderedDict-backed). `OAuthConnectorService.__init__` instantiates a per-instance `LruWithTtl[str, str]`; `ClassVar` token caches are gone. 10 unit tests cover get/put/expiry/eviction/per-call TTL. |
| F025 | Boilerplate | `app/ai/agents/evals/runner.py:548` (`run_agent`, 159 LOC, per-agent if-ladder) | High | M | New agent = edit central function. Each per-agent runner is 50–60 LOC of identical setup/serialize/save. | Replace with `dict[AgentName, Callable]` registry + shared `_run_case` template. |
| F026 | Adapter dup | `app/ai/adapters/anthropic.py:105-200` ↔ `app/ai/adapters/openai_compat.py:115-210` | High | M | `_apply_token_budget`, `_check_cost_budget`, `_check_vision_capability`, `_extract_structured_output`, `_build_messages_payload` skeleton — ~150 LOC duplicated. | Extract `BaseLLMProvider(ABC)` in `app/ai/adapters/base.py`; subclasses override `complete`/`stream`/`_format_payload` only. |
| F027 | Token security | `app/auth/token.py:127-152` | High | S | `decode_token` doesn't pass `options={"require": ["exp","iat","type","jti"]}`, no `iss`/`aud`, and `payload.get("jti", "")` lets JTI-less tokens through `is_token_revoked("")` → False. | Make JTI required; reject empty. Add `iat` and `type` requirements. |
| F028 | Token security | `app/auth/routes.py:32` `REFRESH_TOKEN_TTL_SECONDS = 604800` | High | S | Hardcoded, decoupled from `AuthConfig.refresh_token_expire_days`. If config is extended past 7 days, revoked refresh tokens become reusable past their denylist TTL. | Compute TTL from settings. |
| F029 | Token security | `app/auth/token.py:118-124` | High | S | Token revocation fails open on Redis outage. Replayable revoked tokens during outages. | Surface a metric and consider an in-memory short-window denylist as a fallback. |
| F030 | Token security | `app/auth/routes.py:43-56`, `app/auth/service.py:350-355` (`/bootstrap`) | High | S | Public `/bootstrap` admin-creation endpoint guarded only by `ENVIRONMENT=development` + zero-user check. Misconfigured staging = first hit gets admin. | Additionally require loopback origin or an env-bound bootstrap secret. |
| F031 | Multi-tenant | `app/auth/service.py:36,53,60,61,73,74` (`f"auth:lockout:{email}"`) | Medium | S | Raw email is the Redis key. `redaction.py` redacts log values, not Redis keys. | SHA-256 the email for the key. |
| F032 | Config | `app/core/config.py` (928 LOC, 50 nested config classes, ~371 fields) | High | L | Single import pulls everything. New phase = same file as old phase. Top-of-churn artifact. | Split per domain (`config/auth.py`, `config/ai.py`, `config/qa.py`, `config/design_sync.py`); re-export. |
| F033 | Config | `.env.example` (125 lines) covers ~65 of ~371 settings | High | M | 82% drift. New operators have no map of available knobs. | Generate `.env.example` from Pydantic model schema; add a CI check that fails if a setting isn't documented. |
| F034 | Config | `app/core/config.py:835` `extra="ignore"` | Medium | S | `AUT__JWT_SECRET_KEY` (typo) silently accepted; users see a placeholder secret + 401. | Switch to `extra="forbid"` outside test, or add a startup pass that warns on unknown `*__*` env vars. |
| F035 | Flag sprawl | `BlueprintConfig` (15 flags), `AIConfig` (~25 flags), `PipelineConfig` (6 unused), `DESIGN_SYNC__*` (47 flags) | High | M | No deprecation policy; many flags default `False` with no caller flipping them. | Run `make flag-audit` quarterly; remove flags untouched > 180 days. Group experimental ones into `*ExperimentsConfig`. |
| F036 | Pool size | `app/core/config.py:18-20` `pool_size=3, max_overflow=5` (8 connections) | High | S | FastAPI async + WS + 9 background pollers = starvation under modest load. | Bump to a defensible minimum (20+) and document scaling guidance. |
| F037 | Resilience | `app/email_engine/service.py:264` `httpx.AsyncClient(timeout=30.0)` | High | M | No retry, no circuit breaker. Every email build goes through this Maizzle call. | Add `tenacity` retry + `CircuitBreaker` mirror of `app/rendering/service.py:16`. |
| F038 | Resilience | `app/scheduling/engine.py:78-81` leader lock without fencing | High | M | `redis.set(LEADER_KEY, pid, nx=True, ex=…)`. A paused leader (GC, swap) → second leader acquires; original wakes and runs jobs. | Use UUID identity + CAS (`SET … XX` only when value matches), or Redlock. |
| F039 | Concurrency | `app/scheduling/engine.py:139-141` `_evaluate_jobs` awaits jobs inline | Medium | M | A long job blocks the next tick. | `asyncio.create_task(self._execute_job(...))` with a tracking set. |
| F040 | Notification dedup | `app/notifications/emitter.py:25` dedup key `f"notif:dedup:{event}:{project_id}"` | High | S | Same event + project but different severity/title gets squashed. "QA gate warning" silences "QA gate critical" if they fire within 5 min. | Include hash of `(severity, title)` in the key. |
| F041 | Frontend god file | `cms/apps/web/src/components/icons/custom-icons.tsx` (9882 LOC, 332 icons, ~130 used) | Critical | M | TS checks 9.8k lines on every build; IntelliSense sluggish. | Split into per-icon files re-exported from a barrel; or migrate to `lucide-react` for the standard set + a thin custom layer. |
| F042 | Frontend god component | `cms/apps/web/src/app/projects/[id]/workspace/page.tsx` (848 LOC, 23 useState, 5 useEffect) | High | L | 6 dialog booleans, agent param parsing, presence, follow-mode, panel sizing, keyboard shortcuts all in one component. | Extract `useWorkspaceTemplate`, `useWorkspaceDialogs`, `useWorkspaceFollowMode`, `useAgentMode`. |
| F043 | Frontend types | 12 files with `// @ts-nocheck` — all in `cms/apps/web/src/{hooks,components}/__tests__/` | High | M | Wholesale escape hatches added rather than typing each mock. The only `@ts-nocheck` in the codebase. | Replace with `vi.mocked<typeof useSWR>(...)` and `Mocked<typeof import("...")>` per test. |
| F044 | Frontend god hook | `cms/apps/web/src/hooks/use-builder.ts` (630 LOC) | High | M | Reducer + HTML assembler (`processSection`, `buildResponsiveCss`, `buildDarkModeCss`, `wrapMsoGhostTable`, `assembleDocument`) in one file. The assembler has no dedicated test. | Split into `hooks/use-builder.ts` (state) and `lib/builder/html-assembler.ts` (pure functions, snapshot-tested). |
| F045 | Frontend security | `cms/apps/web/src/lib/auth-fetch.ts:4-5,97`; `cms/apps/web/src/lib/sdk.ts:11-49` | Medium | S | Module-level token cache, 60s TTL, never invalidated on 401. `clearTokenCache()` exported but called nowhere. The 429 retry interceptor uses raw `fetch(request)` not `authFetch`, so retried requests are unauthenticated. | Wire `clearTokenCache` into the 401 interceptor; route the 429 retry through `authFetch`. |
| F046 | Frontend security | `cms/apps/web/src/app/api/v1/[[...path]]/route.ts:4` (`BACKEND_URL ?? "http://localhost:8891"`) | High | S | Production deploy without `BACKEND_URL` silently routes to localhost. | Throw at module init when `NODE_ENV === "production"` and the env var is missing. |
| F047 | Frontend security | `cms/apps/web/src/app/api/v1/[[...path]]/route.ts:24-32` | High | S | Proxy keeps client-supplied `Authorization` header if present (only adds session token when missing). Stolen token can override the session. | Always overwrite from session when a session exists. |
| F048 | Frontend security | `cms/apps/web/src/hooks/use-collaboration.ts:41` (TODO: "Retrieve JWT token from session for auth") | High | M | Collaboration WebSocket connects without auth in current code. | Wire JWT into the WS connection, or block the route until done. |
| F049 | Frontend SDK drift | `cms/packages/sdk/openapi.json` regenerated manually; no CI gate | Medium | M | 185 paths / 315 schemas in the SDK; no `make sdk-check` to detect backend drift. | Add a CI step that exports the live OpenAPI from a booted backend and diffs against the checked-in `openapi.json`. |
| F050 | Frontend types dup | `cms/apps/web/src/types/{outlook.ts:4, chaos.ts:4, css-compiler.ts:4}` (TODO: "Replace with SDK re-exports after `make sdk` regeneration") | Medium | S | SDK has been regenerated (mtime Apr 25). Hand-written types are duplicates of generated ones. | Delete the three files; import from `@/sdk`. |
| F051 | Frontend security | `cms/apps/web/middleware.ts:7-21,53-72` | Medium | M | `ROLE_PERMISSIONS` hardcodes 14 routes. Routes not in the map render unauth'd content one frame before the client-side redirect (auth call wrapped in swallow-all try/catch). | Default-deny: any route not in the allowlist should require admin or 404. Log the catch. |
| F052 | KnowledgeService | `app/knowledge/service.py:73-1048` (god class, 22 methods, 7 responsibilities) | High | L | Ingestion + CRUD + search + routed search + tags + graph + auto-tagging in one class. | Split into `IngestionService`, `SearchService`, `TagService`, `GraphSearchService`. |
| F053 | KnowledgeService | `app/knowledge/service.py:457-545` (RRF + rerank inline) | High | S | RRF dict accumulation, top-k slicing, rerank, result reconstruction inlined in `search()`. | Extract `app/knowledge/fusion.py` with `rrf_fuse(...)` and `apply_rerank(...)`. |
| F054 | DoS | `app/knowledge/repository.py:299-341` `func.plainto_tsquery('simple', query_text)` uncapped | High | S | Not SQL injection (constant config), but a 100KB query becomes a 100KB tsquery scan. | Clamp `query_text[:1024]` at the service boundary. |
| F055 | Repair pipeline | `app/qa_engine/repair/pipeline.py:66-72` `except Exception` warns + continues with corrupted HTML | Medium | S | Stage failure adds a warning string but downstream stages keep building on potentially corrupted DOM. | On failure, revert to pre-stage HTML; emit structured event with `stage`, `error_type`. |
| F056 | Repair injection | `app/qa_engine/repair/brand.py:14,122,138-147,164-166` | Medium | S | Hex regex `#[0-9a-fA-F]{6}\b` runs over entire HTML (rewrites tracking URLs). `_repair_logo` regex matches any class/alt/id containing "logo" substring (false positives on `catalogue`, `login`). Footer injection trusts `palette.text` at template time. | Restrict color regex to CSS contexts; word-boundary `\blogo\b`; validate palette fields with regex at the Pydantic layer. |
| F057 | Migration squash | `alembic/versions/` 46 migrations; `2eb1d5b05ad3_merge_heads.py` is a merge artifact | Medium | M | Single linear head currently, but 46 migrations is high; `make db-squash` exists per CLAUDE.md. | Execute the squash on a maintenance window. |
| F058 | Logging | `app/core/poller.py:125,146`, `app/core/resilience.py:96` (`f"poller.{name}.started"`) | Medium | S | Dynamic event names break the `domain.action_state` invariant claimed in `.claude/rules/backend.md`; explodes Loki/Promtail label cardinality per poller name. | Static event name + `name=self.name` extra field. |
| F059 | PII redaction | `app/core/database.py:24` `engine.echo` enabled in dev; `app/core/exceptions.py:111` uses stdlib `logger.error(extra=…)` | Medium | M | SQL echo bypasses `redact_event_dict` (structlog only). Stdlib `extra=` may not flow through redaction either. | Disable echo or pipe through redaction; route exception logging through structlog. |
| F060 | Tracking sprawl | `app/design_sync/{converter_traces.py, converter_insights.py, converter_memory.py, correction_tracker.py, converter_regression.py}` + `diagnose/` | Medium | S | 5 modules writing JSONL/JSON traces with overlapping concerns. | Unify in one `traces/` subpackage with a single `TraceWriter`. |
| F061 | Color/util duplication | `app/qa_engine/deliverability_analyzer.py:88-141`, `app/qa_engine/repair/brand.py:17-25`, `app/design_sync/converter.py` (`_relative_luminance`, `_contrast_ratio`) | Medium | S | Same color math (hex→RGB, brightness, distance) implemented 3 places. | Extract `app/shared/color.py`; rename design_sync's leading-underscore helpers to public. |
| F062 | Dead config flag | `app/core/config.py:42-50, 92-94` (`RateLimitConfig`, `AIConfig.rate_limit_chat/_generation`) | Medium | S | No consumer; all `@limiter.limit(...)` decorators use string literals. | Wire them up or delete. |
| F063 | Repo hygiene | Root: `=2.0` (stray pip flag), `Merkle_Email_Innovation_Hub_Plan.md.zip`, `pitch.html.zip`, 423 plan files in `.agents/plans/`, `docs/TODO-completed.md` (664KB / 6298 LOC), `data/debug/` (33MB), 51 files in `docs/` (incl. eval-labeling-tool.html 448KB) | Medium | S | Untracked binaries / archives at the repo root; debug data under version control via gitignore exception. `.agents/plans/` is becoming a plan archive. | Add `=2.0`, `*.zip`, `data/debug/`, `e2e-screenshots/` to `.gitignore`; rotate `TODO-completed.md` per quarter; archive plans older than the active phase. |
| F064 | Demo email leak | `app/auth/service.py:397` (`linardsberzins@gmail.com` hardcoded in seed) | Medium | S | Personal email in repo seed data. | Move to `settings.auth.demo_user_email`. |
| F065 | Untested orchestrator | `app/design_sync/converter_service.py` (1519 LOC, no `tests/test_converter_service.py`) | High | M | Hot path with 4 functions >80 LOC; behaviour exercised only indirectly via snapshot tests. | Add unit tests for the `_convert_with_components` branch matrix (sibling on/off, tree on/off, custom-comp on/off, verify on/off). |
| F066 | Untested connectors | No `app/connectors/tests/test_{braze,sfmc,adobe,taxi}_service.py` | High | M | The 4 services with the highest production impact (auth, retries, lease) are tested only via generic `test_export.py`. | Add per-service tests covering 401 retry, lease failure, malformed JSON, KeyError on response. |
| F067 | Untested QA checks | `app/qa_engine/tests/test_checks.py` is 1944 LOC mega-file; no per-check splits | Medium | M | Hard to navigate, slow to run targeted. | Split per-check mirroring `app/qa_engine/checks/`; add a per-check coverage gate. |
| F068 | Frontend test split | `cms/apps/web/src/hooks/__tests__/use-data-hooks{,-2,-3}.test.ts` (615 + 715 + 990 LOC) | Medium | M | Numbered split with no semantic basis; 30 LOC SWR mock boilerplate duplicated 3×. | Co-locate per-hook (`use-projects.test.ts`, etc.) or extract shared `__tests__/setup.ts`. |
| F069 | Token cache scope | `app/connectors/sfmc/service.py:62`, `adobe:64` (`client_id` SHA-256[:16]) | Medium | S | **RESOLVED** (Plan 04). `OAuthConnectorService._cache_key` returns `f"{self.service_name}:{credentials['client_id']}"` — full `client_id`, no truncation, prefixed by service to prevent cross-vendor collisions. No SHA-256[:16] anywhere. |
| F070 | Provider abstraction leak | `app/ai/agents/base.py:74,358,365` (`getattr(request, "output_mode", default)`) | Medium | S | Agent request boundary fully untyped (`Any`). | Define `AgentRequest(Protocol)` with `output_mode`, `effective_tier`, `client_id`. |

---

## Top 5 — Fix These First

### 1. Close the multi-tenant hole (F001 + F002 + F003)
Decide RLS-or-repo, then apply uniformly. The repo-layer path is faster and more debuggable:

```python
# app/core/database.py — add
async def get_scoped_db(
    user: Annotated[User, Depends(get_current_user)],
) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        session.info["client_org_id"] = user.client_org_id
        yield session

# Every repository: read session.info["client_org_id"] and add to .where(...)
# Every list endpoint: drop ?client_org_id= from non-admin role
```

The RLS migrations should be reverted (or made functional with `SET LOCAL`) — currently they're a security comment that doesn't compile.

### 2. Move `scan_for_injection` into `BaseAgentService._process_impl` (F004)
A single ~3-line change covers all 7 agents, including the structured-output bypass.

```python
# app/ai/agents/base.py:351 (before output_mode branch)
result = scan_for_injection(req.brief, mode=settings.security.prompt_guard_mode)
if not result.passed:
    raise PromptInjectionError(result.reason)
```

Add a regression test that asserts both `output_mode="html"` and `output_mode="structured"` raise on a known injection payload.

### 3. Decide Phase 48 — ship or park (F008 + F009 + F030 in app/ai)
~1,500 LOC of DAG + evaluator + adversarial-gate-hook is built and tested but not on the production path. The longer it sits, the further the legacy `BlueprintEngine` drifts. Two acceptable end-states:
- (a) Land the executor switch behind `settings.pipeline.enabled` in `app/ai/blueprints/service.py:164` and run the legacy + DAG paths in shadow mode for 2 weeks.
- (b) Move `app/ai/pipeline/`, `app/ai/blueprints/nodes/evaluator_node.py`, and `app/ai/hooks/builtin/adversarial_gate.py` to a `prototypes/` branch. Re-import when ready.

The "stable beneath a default-False flag" status is the worst of both worlds.

### 4. Decompose `engine.py` god functions (F016 + F017)
Plan a dedicated 2–3-day refactor of `_build_node_context` and `_execute_from`. Extraction is mechanical; risk lives in ordering of LAYERs. Snapshot existing blueprint runs against a fixture, refactor, replay. No behavioural change.

### 5. Delete dead code: `app/example/`, `app/streaming/{manager,subscriber,routes}.py`, `mjml_generator.py`, `penpot/converter.py` shim, `DESIGN_SYNC__PENPOT_CONVERTER_ENABLED` (F006 + F007 + F015)
~1,400 LOC removed in an afternoon. The `/ws/stream` endpoint is also a security surface — it's a public WS subscribing to a Redis pattern with no publisher.

---

## Quick Wins — Low Effort, Medium+ Severity

- [ ] **F007** — Delete `app/example/` (~30 min).
- [ ] **F006** — Delete orphan `/ws/stream` subsystem.
- [ ] **F015** — Delete `mjml_generator.py`, `penpot/converter.py` shim, dead flag.
- [x] **F020 + F021 + F022 + F023 + F024 + F069** — Connector dedup landed (Plan 04). `ApiKey` + `OAuth` ABCs in `app/connectors/_base/`, `LruWithTtl` in `app/core/cache.py`, vendor services ≤50 LOC each, `KeyError` no longer blames lease, `client_id` cache key untruncated.
- [ ] **F027 + F028 + F029** — JWT `decode_token` strict claims; refresh TTL from config; revocation metric on Redis fail-open.
- [ ] **F031** — SHA-256 the email in `auth:lockout:*` Redis keys.
- [ ] **F040** — Notification dedup key includes `(severity, title)` hash.
- [ ] **F046 + F047** — Throw on missing `BACKEND_URL` in prod; always overwrite proxy `Authorization` from session.
- [ ] **F050** — Delete the 3 hand-written `types/{outlook,chaos,css-compiler}.ts` duplicates.
- [ ] **F054** — Clamp `query_text[:1024]` before tsquery.
- [ ] **F056** — Word-boundary `\blogo\b`; validate palette colors with regex.
- [ ] **F058** — Static event names in `poller.py` / `resilience.py`.
- [ ] **F062** — Wire or delete `RateLimitConfig` + `AIConfig.rate_limit_*`.
- [ ] **F063** — Add `=2.0`, `*.zip`, `data/debug/`, `e2e-screenshots/` to `.gitignore`.
- [ ] **F064** — Move hardcoded personal email to settings.

---

## Things That Look Bad But Are Actually Fine

These were considered for inclusion and rejected — listing them so the reasoning is durable.

- **`figma/service.py` size (1720 LOC)** — almost entirely Figma JSON parsing. Each walker function genuinely needs to share traversal state. Splitting helps readability, but the size is load-bearing complexity, not debt. Address via TypedDicts (F014), not file split.
- **`component_matcher.py` (1469 LOC)** — load-bearing scoring tables for 150+ components. Heuristics are intentionally explicit; the long file is mostly data, not logic.
- **`email_design_document.py` (1167 LOC)** — central document model with explicit `to_*`/`from_*` round-trips. The size buys schema stability; `from_legacy()` is the contract that lets the rest of the codebase shed the legacy converter incrementally.
- **`_convert_recursive` legacy fallback in `converter_service.py:530`** — load-bearing safety net when MJML compile fails. Removing it would lose the fallback. Only the un-instrumented "Legacy entry points" shims are debt (F013).
- **47 `DESIGN_SYNC__*` flags** — many gate genuinely independent features (VLM verify, sibling detection, tree bridge, custom-component gen). Sprawl reflects phase-by-phase rollouts where flag-gating is correct. Triage individual unused flags rather than consolidating wholesale.
- **`from typing import Any` in 51 design_sync files** — most are at JSON deserialization boundaries (Figma/Penpot APIs). TypedDicts would help (F014), but `Any` at the boundary is correct.
- **`152 # type: ignore` markers** — cluster on three boundaries: SQLAlchemy `Mapped[T]` descriptor assignment, provider Protocol covariance with `**kwargs`, and optional-dep imports. Tooling-debt, not type-debt.
- **`396 dict[str, Any] / : Any` occurrences** — most are LLM JSON payload boundaries. Type narrowing here adds noise without safety.
- **`11 synthetic_data_*.py` files at ~6500 LOC** — fixture data, not duplicated logic. 0–1 function defs per file. YAML migration is nice-to-have, not urgent.
- **7 `_process_structured` overrides across agents** — return types differ. Per-agent override is correct; the duplication is the LLM-call wrapper, which is the real refactor (separate finding).
- **`mock_traces.py` "untested"** — 4 callers all behind `--dry-run`. Effectively tested via `test_dry_run_pipeline.py`.
- **Bare `except Exception` in Redis-touching helpers** (`app/auth/service.py:42,62,76`, `app/core/quota.py:43-130`, `app/core/feature_flags.py:53-98`) — deliberate fail-open paths on Redis outage. Correct resilience pattern.
- **`HS256` JWT pinned in `app/auth/token.py:18`** — refusing to read alg from config is a deliberate algorithm-confusion mitigation, not a config gap.
- **`_DUMMY_HASH` always-run on user-not-found** (`app/auth/service.py:111`) — timing normalization. Intentional.
- **Caching of ORM `User` in `_user_cache`** (`app/auth/dependencies.py:32`) — `expire_on_commit=False` + `db.expunge(user)` make it correct. Documented hazard.
- **`AuthConfig.jwt_secret_key` default of "CHANGE-ME-IN-PRODUCTION..."** — passes Pydantic's `min_length=32`, refused at prod boot via sentinel (`config.py:911-917` and `main.py:85-96`). Intentional dev convenience.
- **Connector `except Exception → ExportFailedError(...) from exc`** — wrapping is the right pattern; preserves cause via `from exc`.
- **`125 functions in custom_checks.py`** — verified all 125 are wired via `register_custom_check`. Size is the issue (F018), not abandonment.
- **No `escape_like` usage in `qa_engine/knowledge/connectors`** — verified zero `.ilike()`/`.like()` calls with user input. The pattern is correctly applied where used elsewhere (`auth/repository.py:65`, `projects/repository.py:82`, `components/repository.py:184`).
- **`@ts-expect-error` in `cms/apps/web/src/app/api/v1/[[...path]]/route.ts:42`** — `duplex: "half"` is correct Node 18+ streaming syntax not yet in `RequestInit` types. Justified.
- **All `useSWR` `refreshInterval: interval`** — every hit is `useSmartPolling(POLL.*)`, not a literal. `make lint-polling` passes. The grep result looked alarming but is a false positive.
- **`react-resizable-panels v4`** — the new official major; v3 is deprecated. Recent Renovate bump is correct.
- **`processSection` calling `DOMPurify` on innerHTML in the builder preview** — slot fills can contain user HTML; sanitizing at every render boundary is correct.
- **`assembleDocument` doing DOMParser merge for shell import** — alternative (string concatenation) breaks Outlook MSO conditional comments. Necessary complexity.
- **`next-auth: 5.0.0-beta.31`** — the only viable v5 target; Auth.js v5 stable hasn't shipped. Catch-and-render (F051) is the actual fix, not the beta itself.
- **`bench` excluded from `make test`** — perf tests are gated; appropriate for unit-test scope.
- **Branched-heads merge migration `2eb1d5b05ad3`** — currently single head per `alembic heads`; the merge artifact is harmless. Squash (F057) cleans it up cosmetically.

---

## Open Questions for the Maintainer

1. **RLS intent.** Were the RLS migrations (`fdd89fceac29`, `e5f2a9b73d14`) intended to be active, or were they exploratory? The decision affects whether F001 is a "fix RLS" or "remove RLS" task.
2. **Phase 48 status.** Is the DAG executor + evaluator agent + meta-eval intended to ship in Phase 50, or has direction changed since Phase 49 landed? If parking, the unwired hooks (`adversarial_gate.py`) and node (`evaluator_node.py`) should also park.
3. **`app/example/` lifetime.** Is this the copier-template's leftover, or kept intentionally as a reference pattern? If reference, it should not be mounted in `main.py`.
4. **`/ws/stream` origin.** The transit-data shape suggests this came from a project template. Confirm — if so, document the canonical "remove the example streaming" step in `CONTRIBUTING.md`.
5. **`QADeliverabilityConfig` rollout.** The deliverability check (620 LOC) ships off-by-default per `app/qa_engine/CLAUDE.md`. What's the activation criterion?
6. **`KnowledgeService.proactive_qa_enabled = False`** — Phase 48.12 shipped with the flag off. What flips it?
7. **Manual SDK regen.** Is `pnpm generate-sdk:fetch` someone's local task, or do you intend to add a CI gate? The 268KB `types.gen.ts` is the largest non-icon asset in `cms/`.
8. **`docs/audit_2_phase{1..4}.md`.** A prior audit from 2026-03-17 listed 42 items across 4 phases. Cross-referenced selectively:
   - Audit 2 §1.1 (alembic dup `a1b2c3d4e5f6`) — **RESOLVED** (only one file with that revision id remains).
   - Audit 2 §2.2 (MCP server auth) — **OVERLAPS WITH F005** here. Audit 2 proposed an ASGI middleware wrapping `verify_mcp_token`; my F005 extends it to per-user scope enforcement. The middleware step may be done already; the scope step is open.
   - Audit 2 §3.1 (BodySizeLimitMiddleware chunked-encoding bypass) — was the documented fix landed? `app/core/middleware.py:62-67` rejects chunked POST/PUT/PATCH on non-upload paths, which matches Audit 2's prescription, but the side-effect (rejecting legitimate streaming SDK clients) is now visible.
   - Was the rest of Audit 2 worked through, or did it stall? Several other items here (F033 env-example drift, F036 pool size) overlap with Audit 2's High/Medium tier and may already have proposed fixes.
9. **Notification dedup window.** 5 minutes is hardcoded as the window for `notif:dedup:*`. Is this configurable per channel, or is the cross-channel single-value intentional?
10. **`AuthConfig.demo_user_password = "admin"`** in dev. Production sentinel only fires on `ENVIRONMENT=production`. If you run staging with a different env name, this leaks. Intentional? <!-- pragma: allowlist secret -->
