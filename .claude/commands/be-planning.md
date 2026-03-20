# Backend Planning — Create Implementation Plan

Research the codebase and create a self-contained implementation plan.

## Process

1. **Understand the task** — Read the user's requirements carefully
2. **Research existing code** — Use jCodeMunch (repo from `list_repos`) for all code research:
   - `search_symbols({ "query": "...", "kind": "function|class", "file_pattern": "app/..." })` — find related features
   - `get_file_outline` on candidate files — understand structure without reading
   - `get_symbol` — read specific functions/classes, not entire files
   - `find_references` — trace usage across the codebase
   - `get_file_tree({ "path_prefix": "app/{feature}" })` — discover feature layout

   Use jDocMunch (repo: `local/merkle-email-hub`) for docs:
   - `search_sections({ "query": "...", "doc_path": "CLAUDE.md" })` → `get_section` for architecture context
   - `search_sections({ "query": "...", "doc_path": "TODO.md" })` → `get_section` for task context

   **Only `Read` files you will list in "Files to Create/Modify"** — not for research.

3. **Identify files to create/modify** — List every file that needs changes
4. **Write the plan** — Step-by-step instructions that another agent can follow

## Plan Format

Save the plan to `.agents/plans/{feature-name}.md` with this structure:

```markdown
# Plan: {Feature Name}

## Context
{Why this change is needed}

## Files to Create/Modify
- `app/{feature}/models.py` — {what changes}
- ...

## Implementation Steps
1. {Step with exact code or clear instructions}
2. ...

## Security Checklist (scoped to this feature's endpoints)
For every new or modified endpoint in this plan, address:
- [ ] Auth dependency (`get_current_user` or `require_role()`) on every HTTP route, unless intentionally public (document why)
- [ ] Authorization check (`verify_project_access()` in service layer) for project-scoped endpoints only
- [ ] Rate limiting (`@limiter.limit()`) with `Request` parameter on all HTTP routes (WebSocket exempt)
- [ ] Input validation via Pydantic schemas (no raw dict access)
- [ ] Error responses use `AppError` hierarchy (auto-sanitized, no class name leakage)
- [ ] No secrets/credentials in logs or error responses
Only check the feature being planned — full codebase security sweep is `/be-validate`.

## Verification
- [ ] `make check` passes (includes lint, types, tests, frontend, security-check)
- [ ] New endpoints have auth + rate limiting
- [ ] Error responses don't leak internal types
```

## Rules
- Follow Vertical Slice Architecture (models, schemas, repository, service, exceptions, routes, tests)
- Use `from app.core.logging import get_logger` for structured logging
- Use `from app.core.exceptions import AppError` hierarchy for errors
- All functions must have complete type annotations
- Use nested config: `settings.database.url`, `settings.auth.jwt_secret_key`, etc.
- Every new HTTP route MUST have `Depends(get_current_user)` or `require_role()` and `@limiter.limit()`, unless intentionally public (document in plan). WebSocket endpoints use manual JWT validation.
- Project-scoped endpoints MUST call `verify_project_access()` in the service layer (not all endpoints are project-scoped)
- Error responses are auto-sanitized via `AppError` hierarchy and global `error_sanitizer` middleware — no need to call sanitizer functions in routes

@_shared/python-anti-patterns.md
