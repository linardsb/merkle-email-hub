# Backend Planning — Create Implementation Plan

Research the codebase and create a self-contained implementation plan.

## Process

1. **Understand the task** — Read the user's requirements carefully
2. **Research existing code** — Use jCodeMunch `search_symbols` and `get_file_outline` to find related features, patterns, and conventions without reading entire files. Use jDocMunch `get_section` to pull relevant architecture sections from `CLAUDE.md` (e.g. `::modules-and-their-purpose#3`, `::api-security-patterns#3`) and task context from `TODO.md` phase sections. Repo: `local/merkle-email-hub`.
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
- [ ] Auth dependency (`get_current_user`) on every route
- [ ] Authorization check (`verify_project_access()`) for resource-scoped endpoints
- [ ] Rate limiting (`@limiter.limit()`) with `Request` parameter
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
- Every new route MUST have `Depends(get_current_user)` and `@limiter.limit()`
- Resource endpoints MUST call `verify_project_access()` before returning data
- Use `get_safe_error_message()`/`get_safe_error_type()` from `app.core.error_sanitizer` for custom error responses

@_shared/python-anti-patterns.md
