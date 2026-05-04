# Backend Validate — Run All Quality Checks

## Level 1: Format + Lint (26 rule sets — scoped to changed files only)
```bash
uv run ruff format .
uv run ruff check --fix .
```
Ruff enforces 26 rule sets: pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade, annotations, bandit, datetimez, pathlib, simplify, perflint, print, pie, pygrep-hooks, return, refurb, boolean-trap, pydocstyle (Google convention).

**IMPORTANT:** Do NOT run `--unsafe-fixes` — it can move imports that break SQLAlchemy/Pydantic at runtime. Only use `--fix` for safe auto-fixes.

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

## Level 4b: Migration Safety (if migrations changed)
```bash
# Only run if alembic/versions/ has changed files
git diff --name-only | grep 'alembic/versions/.*\.py$' | xargs -I{} squawk --reporter=compact {} 2>/dev/null || true
```
Skip if `squawk` is not installed or no migrations changed. Catches unsafe DDL (missing NOT VALID, lock-heavy operations).

## Level 4c: Secret Detection (on changed files only)
```bash
git diff --cached --name-only --diff-filter=ACM | xargs detect-secrets scan --baseline .secrets.baseline 2>/dev/null || true
```
Skip if `detect-secrets` is not installed.

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

## Level 7: CI Parity Gates (conditional on diff scope)

CI runs `make check` (or `make check-full`) which includes several gates beyond Levels 1–4. Each is fast (<5s except where noted) and catches a specific class of recurring drift. Run only the gates whose trigger files appear in the diff:

| Gate | Command | Run when diff touches |
|------|---------|------------------------|
| `.env.example` drift | `make check-env-drift` | `app/core/config/**`, anything adding a Pydantic `Settings` field |
| Falsy-numeric lint | `make lint-numeric` | `app/design_sync/**` |
| Feature flag audit | `make flag-audit` | any `*Config` field rename/removal, anything around feature gates (warns >90d, errors >180d) |
| Overlay validation | `make validate-overlays` | `data/overlays/**`, `app/qa_engine/**` |
| Golden conformance | `make golden-conformance` | `app/design_sync/**`, `email-templates/**` (~10s) |
| Migration lint | `make migration-lint` | `alembic/versions/**` (Squawk; safe DDL gate) |
| Frontend checks | `make check-fe` | `cms/**` (lint + format + types + tests + polling, ~60s) |
| Polling literal scan | `make lint-polling` | `cms/**/hooks/**` |

If unsure or the diff spans many areas, run **`make check`** (≈30s–2min) — it bundles every backend gate above plus Levels 1–4 in one shot and matches CI exactly. For migration changes use **`make check-full`** instead.

When a CI gate fails on push, the fix is almost always a regenerated artifact (`make .env.example`, `make sync-ontology`, snapshot regen) — note which gate failed and add the regenerate step to the same commit, never as a separate "fix CI" follow-up.

Report results for each level. Do NOT auto-fix convention violations — report them for `/be-code-review-fix` to handle with manual review.
