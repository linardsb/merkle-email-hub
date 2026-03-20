# Backend Execute — Execute Implementation Plan

Execute a backend implementation plan step by step.

## Process

1. **Read the plan** — Load the plan file specified by the user
2. **Execute each step** — Implement changes one step at a time
3. **Verify after each step** — Run relevant checks to catch issues early
4. **Report progress** — Summarize what was done after each step

## Security Verification (scoped to the feature being built)
After each step that adds/modifies routes in the current feature:
- Confirm every NEW route added in this step has `Depends(get_current_user)` or `require_role()` and `@limiter.limit()`. Known exceptions: public auth endpoints (login/bootstrap/refresh), health checks, WebSocket endpoints (use manual JWT validation)
- For project-scoped features: confirm service layer calls `verify_project_access()` (this is a service method, not a route dependency)
- Confirm error responses use `AppError` hierarchy (auto-sanitized via `error_sanitizer`)
- Run `uv run ruff check app/{feature}/ --select=S --ignore=S311 --no-fix` on the feature directory only
- Do NOT scan the entire codebase — `/be-validate` handles the full sweep

## Rules
- Follow the plan exactly — don't add features not in the plan
- Run `uv run ruff format . && uv run ruff check --fix .` after creating/modifying Python files
- All functions must have complete type annotations
- Use structured logging: `logger.info("domain.action_state", key=value)`
- Use nested config: `settings.database.url`, `settings.auth.jwt_secret_key`
- Every new HTTP route MUST have auth dependency (`get_current_user` or `require_role()`) and `@limiter.limit()`, unless it is a public endpoint documented in the plan
- Never return raw exception class names in error responses

@_shared/python-anti-patterns.md
