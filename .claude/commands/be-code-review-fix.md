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

**jCodeMunch** (repo from `list_repos`) for cross-file tracing:
- `search_symbols(query, kind)` — find related functions/classes
- `find_references(symbol_name)` — trace callers/callees across codebase
- `get_file_outline(file_path)` — understand file structure before deciding what to read
- `get_symbol(symbol_name)` — read just the specific function you need

Only `Read` the full file when you need to edit it.

**Direct diagnosis:**
- For bugs: find the failing code path. Trace routes → service → repository.
- For test failures: run the failing test, read the traceback.
- For type errors: run `uv run pyright {file}` or `uv run mypy {file}` to get the exact error.
- For lint errors: run `uv run ruff check {file}` to see violations.

### 3. Root Cause Analysis

- Trace the issue to its root cause — don't patch symptoms.
- Check if the same pattern exists elsewhere (grep for similar code).
- Identify the minimal set of files that need changes.

### 4. Fix

Apply the fix following project conventions (see below). Don't over-engineer — fix the issue, nothing more. Verify against the backend security checklist for any routes you touch.

### 5. Verify

Run the validation pyramid on affected files:

```bash
# Format + lint (26 rule sets: security, simplify, performance, docstrings, etc.)
uv run ruff format {files}
uv run ruff check --fix {files}

# Security-specific lint
uv run ruff check {files} --select=S --ignore=S311 --no-fix

# Type check
uv run pyright {files}
uv run mypy {files}

# Tests — run related tests first, then full suite
uv run pytest {test_file} -v
uv run pytest -v -m "not integration"
```

**NEVER** use `--unsafe-fixes` or run `ruff check --fix .` on the entire repo — only lint files you're actively changing.

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

@_shared/backend-conventions.md
@_shared/backend-security-scoped.md
@_shared/python-anti-patterns.md
