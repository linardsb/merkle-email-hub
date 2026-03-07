# Backend Validate — Run All Quality Checks

## Token Efficiency Note
If the project is indexed via jcodemunch, use `search_symbols` and `get_file_outline` to locate convention violations (missing auth deps, rate limiting) in Level 5 instead of reading entire route files.

Run the 5-level validation pyramid:

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

## Level 5: Convention Tests
Check that all routes have auth dependencies and rate limiting.

## Level 6: Security Conventions
- Verify all route files have `@limiter.limit()` on every endpoint
- Verify all resource-scoped endpoints call `verify_project_access()` or equivalent authorization
- Verify error handlers use `get_safe_error_type()`/`get_safe_error_message()` (not hardcoded class names)
- Verify no `as any` equivalent patterns bypass type safety

Report results for each level. Fix any issues found automatically.
