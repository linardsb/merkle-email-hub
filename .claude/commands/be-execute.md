# Backend Execute — Execute Implementation Plan

Execute a backend implementation plan step by step.

## Process

1. **Read the plan** — Load the plan file specified by the user
2. **Execute each step** — Implement changes one step at a time
3. **Verify after each step** — Run relevant checks to catch issues early
4. **Report progress** — Summarize what was done after each step

## Rules
- Follow the plan exactly — don't add features not in the plan
- Run `uv run ruff format . && uv run ruff check --fix .` after creating/modifying Python files
- All functions must have complete type annotations
- Use structured logging: `logger.info("domain.action_state", key=value)`
- Use nested config: `settings.database.url`, `settings.auth.jwt_secret_key`

@_shared/python-anti-patterns.md
