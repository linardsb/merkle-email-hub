# Backend Execute — Execute Implementation Plan

Execute a backend implementation plan step by step.

## Process

1. **Read the plan** — Load the plan file specified by the user
2. **Execute each step** — Implement changes one step at a time
3. **Verify after each step** — Run relevant checks to catch issues early
4. **Report progress** — Summarize what was done after each step

## Security Verification (scoped to the feature being built)
After each step that adds/modifies routes in the current feature:
- Confirm every new/changed route has `Depends(get_current_user)` and `@limiter.limit()`
- Confirm resource-scoped endpoints call `verify_project_access()`
- Confirm error responses use `AppError` hierarchy (auto-sanitized via `error_sanitizer`)
- Run `uv run ruff check app/{feature}/ --select=S --no-fix` on the feature directory only
- Do NOT scan the entire codebase — `/be-validate` handles the full sweep

## Rules
- Follow the plan exactly — don't add features not in the plan
- Run `uv run ruff format . && uv run ruff check --fix .` after creating/modifying Python files
- All functions must have complete type annotations
- Use structured logging: `logger.info("domain.action_state", key=value)`
- Use nested config: `settings.database.url`, `settings.auth.jwt_secret_key`
- Every new route MUST have auth dependency and rate limiting — no exceptions
- Never return raw exception class names in error responses

@_shared/python-anti-patterns.md
