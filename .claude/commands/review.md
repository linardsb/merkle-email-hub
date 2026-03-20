# Review — Code Review Against Quality Standards

Review code changes against these 8 standards. Apply each standard **contextually** — not every file needs every standard (e.g. schemas don't need logging, type definitions don't need tests, utility functions don't need API design review):

1. **Type Safety** — Complete annotations, no untyped functions
2. **Error Handling** — Uses AppError hierarchy, no bare except
3. **Security** — No hardcoded secrets, proper auth checks, SQL injection prevention
4. **Logging** — Structured logging with domain.action_state pattern (service/route layers — not schemas, models, or pure utilities)
5. **Testing** — Unit tests for business logic, proper mocking (not required for trivial config, types, or re-exports)
6. **Architecture** — Follows VSA pattern, proper layer separation
7. **Performance** — No N+1 queries, proper pagination, connection pooling (only for code that touches DB or external calls)
8. **API Design** — Consistent response format, proper HTTP status codes (only for route files)

## Process
1. Read the changed files
2. Check each applicable standard — skip standards that don't apply to the file type
3. Report findings with severity (critical, warning, suggestion). Only mark **critical** if it violates a codified project rule (CLAUDE.md, pyproject.toml, .claude/rules/)
4. Suggest fixes for critical issues
