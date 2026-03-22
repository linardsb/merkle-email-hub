# Backend Conventions

- All functions MUST have complete type annotations
- Use `AppError` hierarchy — never raise bare Exception
- Structured logging: `logger.info("domain.action_state", key=value)`
- Nested config: `settings.database.url`, `settings.auth.jwt_secret_key`
- VSA layer separation: routes (thin HTTP) → service (business logic) → repository (DB only)
- Feature file order: schemas → models → repository → service → exceptions → routes → tests
