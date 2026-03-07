## Summary

<!-- Brief description of what this PR does and why -->

## Security Checklist

- [ ] All new endpoints require authentication (`get_current_user` / `require_role`)
- [ ] Endpoints that access resources verify authorization (`verify_project_access`)
- [ ] User input is validated via Pydantic schemas
- [ ] Error responses use sanitized messages (`get_safe_error_message` / `get_safe_error_type`)
- [ ] No `as any` type casts that bypass safety checks
- [ ] Rate limiting applied to public/expensive endpoints
- [ ] No secrets, API keys, or credentials in code
- [ ] `make check` passes (lint + types + test + security-check)

## Test Plan

<!-- How was this tested? Include relevant test commands and results -->
