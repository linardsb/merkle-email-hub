# E2E Test — Exploratory Browser Testing

Invoke the global E2ETesting skill for structured exploratory testing.

## Project Context

- **Start**: `NEXT_PUBLIC_DEMO_MODE=true make dev-fe` (frontend only, port 3000) or `make dev` (full stack, backend :8891 + frontend :3000)
- **Demo credentials**: admin / demo123
- **Login**: Email field `input[name='email']`, password field `input[name='password']`
- **API base**: `http://localhost:8891/api/v1`

## Key Journeys

1. **Login** — `/login` → enter demo credentials → dashboard redirect
2. **Dashboard** — `/` → project cards, activity feed, QA summary, quick-start actions
3. **Workspace** — `/workspace` → 3-pane layout (Monaco editor, preview, AI chat)
4. **Components** — `/components` → component grid, search, detail dialog with preview
5. **QA Gate** — workspace QA tab → trigger scan, review 10 checks, override with justification
6. **Export** — workspace export tab → platform selector (Raw HTML, Braze), export preview
7. **Approval** — `/approvals` → approval requests, viewer preview, section feedback
8. **Knowledge** — `/knowledge` → document browser, natural language search, domain/tag filters
9. **Intelligence** — `/intelligence` → QA trends, support matrices, quality scores
10. **Renderings** — `/renderings` → test list, stats cards, compatibility matrix, screenshots

## API Endpoints for Mutation Verification

```bash
# Projects
curl -s http://localhost:8891/api/v1/projects

# Templates
curl -s http://localhost:8891/api/v1/templates

# Components
curl -s http://localhost:8891/api/v1/components

# QA results
curl -s http://localhost:8891/api/v1/qa/results

# Approval requests
curl -s http://localhost:8891/api/v1/approvals
```
