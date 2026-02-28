# Python Anti-Patterns — Avoid These

## Type Annotations
1. Never use `dict` without type params → `dict[str, Any]`
2. Never use `list` without type params → `list[str]`
3. Use `X | None` not `Optional[X]`
4. Use `list[X]` not `List[X]` (Python 3.12+)
5. All function params and return types must be annotated

## Imports
6. Use `from __future__ import annotations` only if needed for forward refs
7. Never `from module import *`
8. Sort imports with isort (ruff handles this)

## Security
9. Never hardcode secrets — use `settings.auth.jwt_secret_key`
10. Never use `eval()` or `exec()`
11. Use `escape_like()` for LIKE queries
12. Use `bcrypt` for password hashing (never MD5/SHA)
13. Never log passwords, tokens, or API keys

## Database
14. Always use parameterized queries (SQLAlchemy handles this)
15. Never commit in repository methods that don't own the transaction
16. Use `await db.execute(select(...))` not raw SQL strings
17. Always use `async with` for database sessions

## Pydantic
18. Use `DomainValidationError` not `ValidationError` (naming clash)
19. Use `model_validate()` not `from_orm()` (Pydantic v2)
20. Use `model_dump()` not `dict()` (Pydantic v2)

## Logging
21. Use `from app.core.logging import get_logger`
22. Events: `domain.action_state` (e.g., `items.create_completed`)
23. Include relevant context: `logger.info("items.created", item_id=item.id)`
24. Use `exc_info=True` for error logging with tracebacks
