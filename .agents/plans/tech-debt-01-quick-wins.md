# Tech Debt 01 — Quick Wins

**Status:** ✅ **LANDED** in commit `eddcd1ac` (PR #40, 2026-04-26).
**Source:** `TECH_DEBT_AUDIT.md` (2026-04-26)
**Scope:** 17 low-effort, medium+ severity items. ~1,400 LOC removed. No architectural decisions.
**Goal:** Prove the audit is actionable, free dead code so later sessions read a smaller codebase.
**Effort spent:** ½ day, single PR.

## Findings addressed

✅ Committed: F006, F007, F015, F022, F023, F031, F040, F046, F047, F050, F054, F056, F058, F062, F063, F064.

⚠️ **Verify F034** (config strict-mode warning) — `app/core/config.py` got 17 lines changed in `eddcd1ac` (likely F062 dead `RateLimitConfig`). Confirm whether `extra="ignore" → "forbid"` (or warn-on-unknown) is in the diff. If not, F034 rolls into a follow-up.

## Follow-up items (audit Quick Wins not scoped in this plan)

The audit's "Quick Wins" section also lists **F027/F028/F029** (auth token strict claims, refresh TTL from config, revocation fail-open metric). These were never in Plan 01's step list — they have moved to **Plan 02 — Part C** (same security theme, same reviewer set).

## Pre-flight

```bash
git checkout -b chore/tech-debt-01-quick-wins
make check  # baseline must be green
```

## Steps

### A. Delete dead public surfaces

| # | Finding | File:Line | Action |
|---|---|---|---|
| 1 | F006 | `app/streaming/manager.py`, `subscriber.py`, `routes.py`, `app/tests/test_ws_per_user_limit.py` | Delete files. Remove import + `app.include_router` line at `app/main.py:401` and `app/main.py:60`. **Do not touch `app/streaming/websocket/`** — that's the CRDT collab WS. **Do not touch `app/streaming/tests/`** — those are CRDT/websocket tests that survive. |
| 2 | F007 | `app/example/` | Delete directory. Remove import at `app/main.py:50` and `include_router` at `app/main.py:388`. |
| 3 | F015 | `app/design_sync/mjml_generator.py`, `app/design_sync/tests/test_mjml_generator.py`, `app/design_sync/penpot/converter.py`, `app/design_sync/penpot/converter_service.py`, `app/design_sync/penpot/tests/test_converter_integration.py` | Delete shims. Verify no imports outside their own test files first: `rg "from app.design_sync.mjml_generator\|app.design_sync.penpot.converter " app/`. If `app/design_sync/penpot/tests/` is empty after the delete, remove the directory. |
| 4 | F015 | `app/core/config.py:356` (`PENPOT_CONVERTER_ENABLED`) | Delete the field. Verify zero readers: `rg "PENPOT_CONVERTER_ENABLED\|penpot_converter_enabled" app/`. |

### B. Tighten security defaults

| # | Finding | File:Line | Action |
|---|---|---|---|
| 5 | F046 | `cms/apps/web/src/app/api/v1/[[...path]]/route.ts:4` | Replace `BACKEND_URL ?? "http://localhost:8891"` with: throw on missing `BACKEND_URL` when `process.env.NODE_ENV === "production"`. |
| 6 | F047 | `cms/apps/web/src/app/api/v1/[[...path]]/route.ts:24-32` | Always overwrite `Authorization` from session when session exists; do not honour client-supplied header. |
| 7 | F031 | `app/auth/service.py:36,53,60,61,73,74` | Replace raw email in Redis key with `hashlib.sha256(email.encode()).hexdigest()[:32]`. Update read + write sites consistently. |
| 8 | F054 | `app/knowledge/service.py` (call site of `repository.search_fulltext`) | Clamp `query_text = query_text[:1024]` before passing to repository. |
| 9 | F056 | `app/qa_engine/repair/brand.py:164-166` | Change logo regex to word-boundary `\blogo\b`. Tighten color regex (`:14, 122`) to only match inside CSS contexts (`style="..."`, `<style>`, `bgcolor=`, `color=`). Add validator on `BrandPalette` Pydantic model: `^#[0-9a-fA-F]{3,8}$` for color fields. |

### C. Resilience / correctness

| # | Finding | File:Line | Action |
|---|---|---|---|
| 10 | F023 | `app/connectors/braze/service.py:84-87`, `sfmc:143-146`, `adobe:146-149`, `taxi:90-93` | Narrow `except Exception` to `(httpx.RequestError, json.JSONDecodeError)`. Let `KeyError`/`TypeError` raise as `ExportFailedError` without lease blame. |
| 11 | F022 | `app/connectors/{braze,sfmc,adobe,taxi}/service.py` constructors | **Step 1 (prerequisite):** create `app/connectors/tests/conftest.py` with an autouse `FakeSettings` fixture that monkeypatches `app.connectors.{braze,sfmc,adobe,taxi}.service._settings` to a typed object whose `credentials.pools` is a real `dict[str, list[str]]` (empty by default). **Step 2:** remove all 4 `isinstance(_settings.credentials.pools, dict)` MagicMock guards + `# pyright: ignore` from the four service constructors. Order matters — guards must stay until the fixture lands or the unit tests will hit `MagicMock` for `pools`. |
| 12 | F040 | `app/notifications/emitter.py:25` | Include `(severity, title)` hash in dedup key: `dedup_key = f"notif:dedup:{event}:{project_id}:{hashlib.sha256(f'{severity}:{title}'.encode()).hexdigest()[:8]}"`. |
| 13 | F058 | `app/core/poller.py:125,146`, `app/core/resilience.py:96` | Replace dynamic `f"poller.{name}.started"` with static `"poller.started"` + `name=self.name` extra field. |

### D. Hygiene

| # | Finding | File:Line | Action |
|---|---|---|---|
| 14 | F050 | `cms/apps/web/src/types/{outlook.ts,chaos.ts,css-compiler.ts}` | Verify each shape exists in `cms/packages/sdk/src/client/types.gen.ts`. Replace file content with re-exports from `@/sdk` and update importers. |
| 15 | F062 | `app/core/config.py:42-50, 92-94` | Verify zero readers of `RateLimitConfig`, `AIConfig.rate_limit_chat`, `AIConfig.rate_limit_generation`: `rg "rate_limit_chat\|rate_limit_generation\|RateLimitConfig" app/`. Delete if confirmed unused. |
| 16 | F063 | `.gitignore` | Append: `=2.0`, `*.zip`, `data/debug/`, `e2e-screenshots/`. Run `git rm --cached` on any already-tracked matches (none expected for `=2.0`). |
| 17 | F064 | `app/auth/service.py:397` | Replace hardcoded `linardsberzins@gmail.com` with `settings.auth.demo_user_email`. Add the field to `AuthConfig` with a default. |

## Verification

```bash
# After each subsection (A-D), run:
make check
make check-fe

# Specific gates:
make test               # pytest must pass
rg "from app.example\|app.streaming.routes\|mjml_generator" app/  # must return 0
rg "PENPOT_CONVERTER_ENABLED" app/  # must return 0
```

## Rollback

Each subsection (A/B/C/D) is independent. Revert per subsection if `make check` fails. Section A is reversible via `git checkout HEAD~1 -- <files>` since deletions are atomic.

## Risk notes

- **F006 / F007 deletions**: Verify `make e2e-smoke` passes — orphan streaming + example routes have no integration tests but the smoke suite hits `/health` and the auth flow only. The only outside test importing the deleted streaming code is `app/tests/test_ws_per_user_limit.py` (deleted alongside) and `app/design_sync/penpot/tests/test_converter_integration.py` for F015 (also deleted).
- **F022 fixture fix**: Create `app/connectors/tests/conftest.py` *before* removing the production guards, otherwise tests fail. The file currently does not exist.
- **F050 SDK re-exports**: `make check-fe` includes `tsc --noEmit` — type drift between hand-written and generated will surface there.

## Done when

- [x] 16 items committed in `eddcd1ac` (PR #40).
- [x] F034 verified — resolved via path B of the audit's stated fix. `_warn_unknown_nested_env_vars()` at `app/core/config/__init__.py:236` runs in `get_settings()` (line 267) and logs `config.unknown_env_var` for typos. `extra="ignore"` retained intentionally so platform-injected vars don't break startup.
- [x] `make check` + `make check-fe` green at merge.
- [x] PR titled `chore(tech-debt): quick wins — F006/F007/F015/F022/F023/F031/F040/F046/F047/F050/F054/F056/F058/F062/F063/F064`.
- [x] In `TECH_DEBT_AUDIT.md`, the 16 findings are marked **RESOLVED** with PR #40.
