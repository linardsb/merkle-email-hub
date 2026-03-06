# Security Audit — Browser + API Security Testing

Invoke the global E2ETesting skill's SecurityAudit workflow.

## Project Context

- **API base**: `http://localhost:8891/api/v1`
- **Auth**: JWT HS256, 15-min access + 7-day refresh tokens, Redis blocklist
- **Rate limits**: 20 req/min AI chat, 5 req/min generation, general per-endpoint limits
- **Demo credentials**: admin / demo123

## Attack Surface

### Auth Endpoints
- `POST /api/v1/auth/login` — login (brute-force protected, 5 attempts → 15 min lock)
- `POST /api/v1/auth/register` — registration
- `POST /api/v1/auth/refresh` — token refresh
- `POST /api/v1/auth/logout` — token revocation

### Protected API Endpoints
- `/api/v1/projects` — project CRUD (scoped by client_org_id, RLS enforced)
- `/api/v1/templates` — template CRUD with versioning
- `/api/v1/components` — component library management
- `/api/v1/qa` — QA engine (trigger scans, read results)
- `/api/v1/connectors` — ESP export (Braze, SFMC credentials — AES-256 encrypted)
- `/api/v1/approvals` — approval workflow (role-gated: admin/developer/viewer)
- `/api/v1/knowledge` — RAG knowledge base
- `/api/v1/rendering` — rendering test management
- `/api/v1/email` — Maizzle build pipeline
- `/api/v1/personas` — test persona management
- `/api/v1/blueprints` — blueprint state machine
- `/api/v1/ai/chat` — AI chat (rate limited separately)

### Security-Critical Checks
1. **RLS isolation** — verify projects from org A aren't visible to org B
2. **Credential storage** — connector API keys must never appear in responses
3. **Role enforcement** — viewer role cannot create/update/delete
4. **Token revocation** — logged-out tokens must be rejected
5. **SQL injection** — test LIKE/ILIKE patterns use `escape_like()`
6. **Error disclosure** — no stack traces in production error responses
