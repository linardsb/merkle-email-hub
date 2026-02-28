# Backend Planning — Create Implementation Plan

Research the codebase and create a self-contained implementation plan.

## Process

1. **Understand the task** — Read the user's requirements carefully
2. **Research existing code** — Find related features, patterns, and conventions
3. **Identify files to create/modify** — List every file that needs changes
4. **Write the plan** — Step-by-step instructions that another agent can follow

## Plan Format

Save the plan to `.agents/plans/{feature-name}.md` with this structure:

```markdown
# Plan: {Feature Name}

## Context
{Why this change is needed}

## Files to Create/Modify
- `app/{feature}/models.py` — {what changes}
- ...

## Implementation Steps
1. {Step with exact code or clear instructions}
2. ...

## Verification
- [ ] `make lint` passes
- [ ] `make types` passes
- [ ] `make test` passes
```

## Rules
- Follow Vertical Slice Architecture (models, schemas, repository, service, exceptions, routes, tests)
- Use `from app.core.logging import get_logger` for structured logging
- Use `from app.core.exceptions import AppError` hierarchy for errors
- All functions must have complete type annotations
- Use nested config: `settings.database.url`, `settings.auth.jwt_secret_key`, etc.

@_shared/python-anti-patterns.md
