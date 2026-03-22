# Backend Security Checks (Per-Feature Scope)

Apply to the feature/files being worked on. Full codebase sweep is `/be-validate`.

## Every new/modified HTTP route must have:
- `Depends(get_current_user)` or `require_role()` — auth dependency
- `@limiter.limit()` — rate limiting (WebSocket endpoints exempt)

**Known exceptions (do NOT flag):**
- `auth/routes.py`: login, bootstrap, refresh — intentionally public
- `core/health.py`: health check — no auth by design
- `streaming/routes.py`, `streaming/websocket/routes.py`: WebSocket — manual JWT validation

## Project-scoped endpoints must have:
- `verify_project_access()` call in the **service layer** (not a route dependency)
- Only for: projects, templates, blueprints, design_sync, approval, ai
- NOT needed for: personas, components, knowledge, ontology, memory, skills, workflows, reporting, plugins, tolgee, connectors

## Input handling:
- Validate via Pydantic schemas (no raw dict access)
- Use `escape_like()` for SQL LIKE/ILIKE patterns

## Error responses:
- Use `AppError` hierarchy (auto-sanitized via `error_sanitizer` middleware)
- Never hardcode class names or leak internal types
- No secrets/credentials in logs or error responses
