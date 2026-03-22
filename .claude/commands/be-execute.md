# Backend Execute — Execute Implementation Plan

Execute a backend implementation plan step by step.

## Process

1. **Read the plan** — Load the plan file specified by the user
2. **Execute each step** — Implement changes one step at a time
3. **Verify after each step** — Run relevant checks to catch issues early
4. **Report progress** — Summarize what was done after each step

## Security Verification

After each step that adds/modifies routes, verify against the backend security checklist below. Run `uv run ruff check app/{feature}/ --select=S --ignore=S311 --no-fix` on the feature directory only. Full codebase sweep is `/be-validate`.

## Rules

- Follow the plan exactly — don't add features not in the plan
- Run `uv run ruff format . && uv run ruff check --fix .` after creating/modifying Python files

@_shared/backend-conventions.md
@_shared/backend-security-scoped.md
@_shared/python-anti-patterns.md
