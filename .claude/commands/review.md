# Review — Code Review Against Quality Standards

Review code changes against these 8 standards:

1. **Type Safety** — Complete annotations, no untyped functions
2. **Error Handling** — Uses AppError hierarchy, no bare except
3. **Security** — No hardcoded secrets, proper auth checks, SQL injection prevention
4. **Logging** — Structured logging with domain.action_state pattern
5. **Testing** — Unit tests for business logic, proper mocking
6. **Architecture** — Follows VSA pattern, proper layer separation
7. **Performance** — No N+1 queries, proper pagination, connection pooling
8. **API Design** — Consistent response format, proper HTTP status codes

## Process
1. Read the changed files
2. Check each standard
3. Report findings with severity (critical, warning, suggestion)
4. Suggest fixes for critical issues
