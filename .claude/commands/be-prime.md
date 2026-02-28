# Backend Prime — Load Full Backend Context

Load the complete backend context for this project. Read the following files to understand the architecture:

1. Read `/CLAUDE.md` for project overview and conventions
2. Read `/app/core/config.py` for configuration structure
3. Read `/app/core/database.py` for database patterns
4. Read `/app/core/exceptions.py` for error hierarchy
5. Read `/app/shared/schemas.py` for shared response patterns
6. Read `/app/shared/models.py` for model mixins

After reading, summarize what you've loaded.

Then read `/TODO.md` and extract only the **backend-relevant tasks** below. Report their status (done/not started) based on what exists in the codebase:

**Phase 0 — Foundation Blockers:**
- 0.1 Database migration for all email-hub models + RLS policies
- 0.3 Generate OpenAPI TypeScript SDK (backend must be running)

**Phase 1 — Sprint 1: Editor + Build Pipeline:**
- 1.6 Template CRUD + persistence (versioning, restore)

**Phase 2 — Sprint 2: Intelligence + Export:**
- 2.1 Wire AI provider (Claude/OpenAI, model routing, streaming)
- 2.2 Scaffolder agent (brief → Maizzle HTML)
- 2.3 Dark Mode agent (inject dark mode CSS + Outlook overrides)
- 2.4 Content agent (copy generation, editor context menu)
- 2.6 Component library v1 — backend (seed 5-10 components)
- 2.8 10-point QA gate system (run, results, override flow)
- 2.9 Raw HTML export + Braze connector
- 2.10 RAG knowledge base seeding

**Phase 3 — Sprint 3: Client Handoff + Polish:**
- 3.1 Client approval portal (viewer role, feedback, audit trail)
- 3.5 CMS + Nginx Docker stack (7 services healthy)

**Phase 4 — Post-MVP:**
- 4.1 Remaining 6 AI agents
- 4.2 Additional CMS connectors (SFMC, Adobe Campaign, Taxi)

Confirm you're ready for backend work.
