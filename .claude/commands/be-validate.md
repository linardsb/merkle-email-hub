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
uv run ruff check app/ --select=S --no-fix
```

## Level 5: Convention Checks (via jCodeMunch — no file reads)

Use jCodeMunch to scan for convention violations instead of reading route files:
1. `search_symbols({ "query": "router", "kind": "variable", "file_pattern": "*/routes.py" })` — list all route modules
2. For each route module, `get_file_outline` — check that auth deps and rate limiting are present
3. `search_symbols({ "query": "verify_project_access", "kind": "function" })` then `find_references` — confirm resource-scoped endpoints have authorization
4. `search_symbols({ "query": "get_safe_error", "kind": "function" })` then `find_references` — verify error sanitization usage

Only `Read` a file if you need to fix a violation found above.

## Level 6: Security Conventions
- `find_references({ "symbol_name": "limiter.limit" })` — verify all endpoints have rate limiting
- `find_references({ "symbol_name": "verify_project_access" })` — verify resource authorization
- `find_references({ "symbol_name": "get_safe_error_type" })` — verify error handlers use safe error types
- Grep for `as any` equivalent patterns that bypass type safety

Report results for each level. Fix any issues found automatically.
