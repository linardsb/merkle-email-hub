# Backend Validate — Run All Quality Checks

## Level 1: Format + Lint
```bash
uv run ruff format .
uv run ruff check --fix .
```

## Level 2: Type Checking
```bash
uv run mypy app/
uv run pyright app/
```

## Level 3: Unit Tests
```bash
uv run pytest -v -m "not integration"
```

## Level 4: Security Lint
```bash
uv run ruff check app/ --select=S --ignore=S311 --no-fix
```

## Level 5: Convention Checks (via jCodeMunch — no file reads)

Use jCodeMunch to scan for convention violations instead of reading route files:
1. `search_symbols({ "query": "router", "kind": "variable", "file_pattern": "*/routes.py" })` — list all route modules
2. For each route module, `get_file_outline` — check that auth deps (`get_current_user` or `require_role()`) and `@limiter.limit()` are present

**Known exceptions — do NOT flag these:**
- `auth/routes.py`: bootstrap, login, refresh endpoints are intentionally public
- `core/health.py`: health check has no auth (by design)
- `streaming/routes.py`, `streaming/websocket/routes.py`: WebSocket endpoints use manual JWT validation, not `Depends`-based auth, and have no `@limiter.limit()`

3. For **project-scoped** routes only (projects, templates, blueprints, design_sync, approval, ai), verify that the service layer calls `verify_project_access()`. This is a service method — not a standalone function. App-global modules (personas, components, knowledge, ontology, memory, skills, workflows, reporting, plugins, tolgee, connectors) are NOT project-scoped and do NOT need this check.

Only `Read` a file if you need to fix a violation found above.

## Level 6: Security Conventions
- `find_references({ "symbol_name": "limiter.limit" })` — verify all HTTP routes have rate limiting (WebSocket routes are exempt)
- For project-scoped modules, verify `verify_project_access()` is called in the service layer

Report results for each level. Do NOT auto-fix convention violations — report them for `/be-code-review-fix` to handle with manual review.
