# Tech Debt 02 — Public-API Security

**Source:** `TECH_DEBT_AUDIT.md`
**Scope:** Close two Critical security holes on the public API surface, plus auth-token quick wins that were dropped from Plan 01.
**Goal:** Prompt-injection guard runs on every agent code path; MCP per-user scopes are enforced; JWT decode is strict.
**Estimated effort:** ½ day, single PR.
**Prerequisite:** ✅ Plan 01 landed (`eddcd1ac` / PR #40).

## Findings addressed

F004 (prompt-injection bypass on structured-output path) — Critical
F005 (MCP role scopes computed but not enforced) — Critical
F027 (JWT `decode_token` does not require `exp`/`iat`/`type`/`jti`) — High
F028 (`REFRESH_TOKEN_TTL_SECONDS` hardcoded, decoupled from `AuthConfig`) — High
F029 (token revocation Redis fail-open silent) — High

## Pre-flight

```bash
git checkout -b sec/tech-debt-02-api-guards
make check  # baseline green
```

## Part A — F004: Move `scan_for_injection` into the base agent

### Current state

- The scan is invoked via `_secure_user_message()` in `app/ai/agents/base.py:223`, which does **two things**: (a) calls `scan_for_injection`, (b) wraps in `<USER_INPUT>` delimiter.
- HTML branch calls `_secure_user_message` at `:374`. Streaming path also calls it at `:509`.
- Structured branch (`_process_structured` in 7 services) dispatches at `:353` and does NOT call `_secure_user_message` — so the scan never runs in structured mode.
- `app/ai/agents/scaffolder/routes.py` accepts `output_mode="structured"` — publicly reachable.
- `pipeline.py:90` only calls `sanitize_prompt` (PII), not the injection guard.

### Steps

1. **Split `_secure_user_message` into two helpers** in `app/ai/agents/base.py`:
   ```python
   def _scan_request(self, request: Any) -> Any:
       """Scan injection-bearing fields on the request. May mutate (strip mode) or raise (block mode)."""
       settings = get_settings()
       if not settings.security.prompt_guard_enabled:
           return request
       # Scan whatever the agent considers user input (delegate to subclass hook).
       raw = self._build_user_message(request)
       scan = scan_for_injection(raw, mode=settings.security.prompt_guard_mode)
       # block mode: scan_for_injection already raises PromptInjectionError
       # strip mode: subclass override re-applies sanitized text to its request schema (e.g. brief, html)
       if scan.sanitized is not None and scan.sanitized != raw:
           request = self._apply_sanitized_input(request, scan.sanitized)
       return request

   def _wrap_user_message(self, raw: str) -> str:
       """Delimiter wrap only — no scan (already done upstream)."""
       return f"<USER_INPUT agent={self.agent_name!r}>\n{raw}\n</USER_INPUT>"
   ```
2. **Call `_scan_request` once at the top of `_process_impl`** (before the `output_mode` dispatch at `:351`) so structured mode is also covered:
   ```python
   request = self._scan_request(request)
   output_mode = self._get_output_mode(request)
   ```
3. **Replace `_secure_user_message` callsites** at `:374` and `:509` with `_wrap_user_message` (scan no longer redundant).
4. **Add `_apply_sanitized_input` hook** on `BaseAgentService` with a default that uses `dataclasses.replace`/`model_copy` to set the agent's primary input field. Override per-agent only if multiple fields need scanning (e.g. Dark Mode scans `html`, Knowledge scans `question`).
5. **Audit the 7 `_process_structured` overrides** — confirm none are reached without going through `_process_impl`. The only direct callers are unit tests that bypass intentionally:
   - `app/ai/agents/scaffolder/service.py:134`
   - `app/ai/agents/dark_mode/service.py:126`
   - `app/ai/agents/content/service.py:201`
   - `app/ai/agents/accessibility/service.py:115`
   - `app/ai/agents/code_reviewer/service.py:179`
   - `app/ai/agents/personalisation/service.py:137`
   - `app/ai/agents/outlook_fixer/service.py:105`
6. **Pipeline path** (`app/ai/agents/scaffolder/pipeline.py:90`): keep `sanitize_prompt(brief)` (PII redaction is orthogonal). Verify guard reaches the pipeline through `ScaffolderService._process_structured` → `pipeline.execute()` → guard already ran in `_process_impl`. Add a docstring comment noting "G1 injection guard runs upstream in `BaseAgentService._process_impl`".

### Tests

Add `app/ai/agents/tests/test_injection_guard_coverage.py`:
```python
@pytest.mark.parametrize("output_mode", ["html", "structured"])
async def test_injection_guard_runs_on_both_modes(output_mode, ...):
    # known injection payload; assert PromptInjectionError raised
```
Parametrize over all 7 agents.

## Part B — F005: Enforce MCP per-user scopes

### Current state

- `app/mcp/auth.py:35-43` builds `_role_to_scopes` (admin → read+write+admin, developer → read+write, viewer → read).
- `app/mcp/server.py` only checks "auth result non-None". No tool reads scopes.
- **27 `@mcp.tool` decorators total**: 26 across `app/mcp/tools/*.py` + `mcp_batch_execute` meta-tool at `app/mcp/server.py:167`.

### Tool inventory & scope classification

| File | Tools | Suggested scope |
|------|-------|-----------------|
| `tools/agents.py` (9) | `agent_scaffold`, `agent_dark_mode`, `agent_content`, `agent_outlook_fix`, `agent_accessibility`, `agent_code_review`, `agent_personalise`, `agent_innovate`, `agent_knowledge` | `write` (LLM calls) |
| `tools/qa.py` (5) | `qa_check`, `email_production_readiness`, `outlook_analyze`, `gmail_predict` | `read` |
|  | `chaos_test` | `write` (LLM-driven generation) |
| `tools/knowledge.py` (3) | `knowledge_search`, `css_support_check`, `safe_css_alternatives` | `read` |
| `tools/ai.py` (3) | `ai_cost_status`, `deliverability_score`, `bimi_check` | `read` |
| `tools/email.py` (2) | `css_optimize`, `inject_schema_markup` | `read` (deterministic transforms) |
| `tools/rendering.py` (2) | `email_visual_check`, `visual_diff` | `read` |
| `tools/templates.py` (2) | `list_templates`, `search_components` | `read` |
| `server.py` (1 meta) | `mcp_batch_execute` | `write` (can dispatch to write tools) |

Cross-check the 14 read tools against `CACHEABLE_TOOLS` in `app/mcp/optimization.py` — they should match (cacheable ⇔ read-only).

### Steps

1. **Pass scopes through the MCP request context.** In `app/mcp/server.py`, store the resolved `scopes` set on the FastMCP context object (per FastMCP's session/context pattern — see existing usage of `ctx`).
2. **Add a scope-gate decorator** in `app/mcp/auth.py`:
   ```python
   def require_scope(scope: Literal["read", "write", "admin"]):
       def decorator(fn):
           @functools.wraps(fn)
           async def wrapper(*args, ctx, **kwargs):
               if scope not in ctx.session.scopes:
                   raise PermissionError(f"tool requires scope: {scope}")
               return await fn(*args, ctx=ctx, **kwargs)
           return wrapper
       return decorator
   ```
3. **Apply `@require_scope` to every tool** per the classification table above. Concretely:
   - `app/mcp/tools/agents.py` — all 9 `agent_*` tools → `@require_scope("write")`.
   - `app/mcp/tools/qa.py` — `chaos_test` → `write`; `qa_check`, `email_production_readiness`, `outlook_analyze`, `gmail_predict` → `read`.
   - `app/mcp/tools/knowledge.py` — `knowledge_search`, `css_support_check`, `safe_css_alternatives` → `read`.
   - `app/mcp/tools/ai.py` — `ai_cost_status`, `deliverability_score`, `bimi_check` → `read`.
   - `app/mcp/tools/email.py` — `css_optimize`, `inject_schema_markup` → `read`.
   - `app/mcp/tools/rendering.py` — `email_visual_check`, `visual_diff` → `read`.
   - `app/mcp/tools/templates.py` — `list_templates`, `search_components` → `read`.
   - `app/mcp/server.py:167` — `mcp_batch_execute` → `@require_scope("write")` (can dispatch to write tools; per-call scope is also enforced by the inner tool's own decorator).
4. **Default-deny new tools.** Add a runtime check in `_register_schemas` (in `app/mcp/server.py`) that fails server startup if a tool has no `@require_scope` decorator (use a registry sentinel attribute set on the wrapper, e.g. `wrapper._mcp_required_scope = scope`). Failing closed at boot is safer than warn-only.

### Tests

Add `app/mcp/tests/test_scope_enforcement.py`:
```python
@pytest.mark.parametrize("role,tool,expected", [
    ("viewer",    "agent_scaffold",   "denied"),
    ("developer", "agent_scaffold",   "allowed"),
    ("viewer",    "knowledge_search", "allowed"),
    ("admin",     "mcp_batch_execute","allowed"),
    ...
])
```

## Part C — Auth token quick wins (rolled in from Plan 01 backlog)

These three items are Quick Wins per `TECH_DEBT_AUDIT.md` line 170 but were not scoped into Plan 01's step list. Bundled here because the reviewer set (`app/auth/`) is the same as Part B's MCP auth changes.

### C1. F027 — Strict required claims in `decode_token`

`app/auth/token.py:127-152`. Currently `jwt.decode(...)` does not pass `options={"require": [...]}`, and `payload.get("jti", "")` lets JTI-less tokens through `is_token_revoked("")` → False.

```python
# app/auth/token.py — decode_token
payload = jwt.decode(
    token,
    settings.auth.jwt_secret_key,
    algorithms=[_JWT_ALGORITHM],
    options={"require": ["exp", "iat", "type", "jti"]},
)
jti = payload["jti"]  # required, no .get() with empty default
if not jti:
    raise InvalidTokenError("missing jti")
```

Add a test in `app/auth/tests/test_token.py` (create file if absent) that asserts a hand-rolled token without `jti` is rejected.

### C2. F028 — Refresh TTL computed from config

`app/auth/routes.py:32`. Replace the hardcoded `REFRESH_TOKEN_TTL_SECONDS = 604800` with:

```python
def _refresh_ttl_seconds() -> int:
    return get_settings().auth.refresh_token_expire_days * 86400
```

Update the two callsites in `routes.py` (refresh issue + revocation denylist TTL). Verify nothing else imports the old constant: `rg "REFRESH_TOKEN_TTL_SECONDS" app/`.

### C3. F029 — Metric on Redis fail-open in revocation check

`app/auth/token.py:118-124`. The `is_token_revoked` Redis call swallows exceptions and returns `False`. Add a structured-log + counter:

```python
except (redis.ConnectionError, redis.TimeoutError) as exc:
    logger.warning("auth.token_revocation_check_unavailable", error=str(exc), jti=jti[:8])
    # TODO follow-up: consider in-memory short-window denylist as fallback (audit comment)
    return False
```

Plus an optional Prometheus counter if the project exposes one (check `app/core/metrics.py`); if not, structured-log only.

### C4. Tests

Add to `app/auth/tests/test_token.py`:
- `test_decode_rejects_token_without_jti`
- `test_decode_rejects_token_without_exp`
- `test_refresh_ttl_follows_config` (parametrize over `refresh_token_expire_days = 1, 7, 30`)
- `test_revocation_check_fails_open_emits_warning` (mock Redis, assert log captured)

## Verification

```bash
make check
make test
# Manual MCP probe (server running):
curl -s -X POST http://localhost:8891/mcp/tools/agent_scaffold \
  -H "Authorization: Bearer <viewer_token>" -d '{...}' | jq .  # 403 expected
# Manual JWT probe — hand-craft token without jti, expect 401:
python -c "import jwt; print(jwt.encode({'sub':'1','exp':9999999999,'iat':1,'type':'access'}, 'CHANGE-ME-IN-PRODUCTION-this-is-not-a-real-secret', algorithm='HS256'))" \
  | xargs -I{} curl -s -H "Authorization: Bearer {}" http://localhost:8891/api/v1/projects | head -c 200
```

## Rollback

Three independent reverts:
- Part A: revert the `base.py` change; the HTML path's original guard at `:374` reactivates.
- Part B: revert per-tool decorators; behaviour returns to "any auth'd user can call any tool".
- Part C: each of C1/C2/C3 is a single-file revert (`app/auth/token.py` or `app/auth/routes.py`).

## Risk notes

- **F004 — direct `_process_structured` callers** (`app/ai/agents/scaffolder/tests/test_tree_builder.py:363` and `:418`) intentionally bypass the security envelope. Inputs there are benign, so leave them — but document via comment that direct calls skip the guard.
- **F004 — `_secure_user_message` is split, not deleted.** The delimiter wrap (`<USER_INPUT>`) is still required at the LLM-message boundary; only the scan moves upstream. Keep `_wrap_user_message()` callers at `:374` and `:509`.
- **F005 — decorator ordering**: `@mcp.tool()` must remain outermost so FastMCP sees the wrapped function; `@require_scope` sits below it. Then the cache wrapper from `app/mcp/optimization.py:_wrap_cacheable_tools` runs *inside* the scope check (deny before cache lookup) — verify by reading order of `_wrap_cacheable_tools` application in `_register_schemas`.
- **F005 — context shape**: confirm the resolved `scopes` reach the tool wrapper. FastMCP exposes session state via `ctx.session` or `ctx.request_context`; pick whichever is consistent with the existing `auth.py:authenticate` return path.

## Done when

- [ ] Both modes (`html`, `structured`) guarded for all 7 agents — regression test green.
- [ ] All 27 MCP tools annotated with `@require_scope` (26 in `tools/*.py` + `mcp_batch_execute` in `server.py`).
- [ ] `_register_schemas` startup check fails closed if any tool lacks `_mcp_required_scope`.
- [ ] Viewer token cannot call `agent_scaffold` — manual curl confirms 403.
- [ ] `decode_token` rejects tokens missing `exp`/`iat`/`type`/`jti` — test green.
- [ ] Refresh TTL follows `AuthConfig.refresh_token_expire_days` — test green.
- [ ] Revocation Redis fail-open emits structured-log warning — test green.
- [ ] PR titled `sec(api): prompt-injection guard + MCP scopes + auth-token strictness (F004 F005 F027 F028 F029)`.
- [ ] Mark F004, F005, F027, F028, F029 as **RESOLVED** in `TECH_DEBT_AUDIT.md`.
