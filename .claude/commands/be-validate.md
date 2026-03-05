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

Report results for each level. Fix any issues found automatically.
