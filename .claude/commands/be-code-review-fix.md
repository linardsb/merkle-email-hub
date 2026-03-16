# Backend Code Review Fix — Diagnose and Fix Issues

Find, diagnose, and fix backend bugs, code review findings, or quality issues.

## Trigger

Use when: bug report, failing test, code review comment, lint/type error, runtime exception, or any issue that needs fixing rather than new feature development.

## Process

### 1. Understand the Issue

Read the user's description. Classify:
- **Bug**: unexpected behaviour, runtime error, wrong output
- **Code review finding**: style, architecture, security, performance issue
- **Test failure**: failing test that needs code or test fix
- **Type/lint error**: mypy, pyright, or ruff violation

### 2. Reproduce / Locate

**Use jCodeMunch for cross-file tracing** (repo: `local/merkle-email-hub-0ddab3c4`):
- `search_symbols(query, kind="function")` to find related functions without reading entire files
- `find_references(symbol)` to trace callers/callees across the codebase
- `get_file_outline(file)` to understand file structure before deciding what to read
- `get_symbol(name)` to read just the specific function you need

Only `Read` the full file when you need to edit it.

**Direct diagnosis:**
- For bugs: find the failing code path. Trace routes → service → repository using jCodeMunch.
- For test failures: run the failing test, read the traceback.
- For type errors: run `uv run pyright {file}` or `uv run mypy {file}` to get the exact error.
- For lint errors: run `uv run ruff check {file}` to see violations.

### 3. Root Cause Analysis

- Trace the issue to its root cause — don't patch symptoms.
- Check if the same pattern exists elsewhere (grep for similar code).
- Identify the minimal set of files that need changes.

### 4. Fix

Apply the fix following project conventions:
- All functions must have complete type annotations
- Use `AppError` hierarchy for error handling (no bare exceptions)
- Use structured logging: `logger.info("domain.action_state", key=value)`
- Follow VSA layer separation (routes → service → repository)
- Don't over-engineer — fix the issue, nothing more

**Security checks (scoped to files being fixed):**
- If touching routes: verify `Depends(get_current_user)` and `@limiter.limit()` are present
- If touching error handling: use `AppError` hierarchy (auto-sanitized), never hardcode class names
- If touching resource access: verify `verify_project_access()` authorization
- If adding user input handling: validate via Pydantic schema, use `escape_like()` for SQL patterns
- Only check the files/module being fixed — full sweep is `/be-validate`

@_shared/python-anti-patterns.md

### 5. Verify

Run the validation pyramid on affected files:

```bash
# Format + lint
uv run ruff format {files}
uv run ruff check --fix {files}

# Type check
uv run pyright {files}
uv run mypy {files}

# Tests — run related tests first, then full suite
uv run pytest {test_file} -v
uv run pytest -v -m "not integration"
```

Fix any issues introduced by the change. Repeat until all checks pass.

### 6. Report

Summarise:
- **Root cause**: what was wrong and why
- **Fix**: what was changed and in which files
- **Verification**: which checks passed
- **Risk**: any side effects or areas to watch

## Rules

- Fix the root cause, not the symptom
- Don't refactor unrelated code while fixing a bug
- Don't add features — only fix the reported issue
- If the fix requires architectural changes, flag it and suggest `/be-planning` instead
- Run verification on every file you touch — never skip type checks
