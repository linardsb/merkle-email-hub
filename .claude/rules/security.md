---
description: Security rules for all code
globs: "**/*.{py,ts,tsx}"
---

# Security Rules

- NEVER hardcode secrets, API keys, or passwords in source code
- NEVER commit .env files or credentials
- Use `escape_like()` for SQL LIKE/ILIKE patterns
- Use bcrypt for password hashing (never MD5/SHA)
- HTTPBearer with auto_error=False for auth dependencies
- Generic error messages for auth failures ("Invalid email or password")
- Rate limit all public endpoints
- Validate and sanitize all user input
