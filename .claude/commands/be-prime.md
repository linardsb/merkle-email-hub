# Backend Prime — Load Full Backend Context

## Step 0: Index & Discover (jCodeMunch)
1. Run `index_folder({ "path": "<project_root>" })` if not already indexed
2. Run `get_repo_outline` to understand overall project structure
3. Run `get_file_tree` to map the `app/` directory layout
4. Run `search_symbols({ "query": "AppError" })` and similar to discover key abstractions

## Step 1: Load Core Files
Read the following files for full context (these need complete content, not just outlines):

1. Read `/CLAUDE.md` for project overview and conventions
2. Read `/app/core/config.py` for configuration structure
3. Read `/app/core/database.py` for database patterns
4. Read `/app/core/exceptions.py` for error hierarchy
5. Read `/app/shared/schemas.py` for shared response patterns
6. Read `/app/shared/models.py` for model mixins
7. Read `/TODO.md` for the full implementation roadmap and remaining tasks

After reading, summarize what you've loaded.

## Step 2: Assess Task Status
Read `/TODO.md` and extract only the **backend-relevant tasks** below. Use `search_symbols` to check if implementations exist in the codebase rather than reading every file. Report their status (done/not started):

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

**Phase 4 — V2:**
- 4.1 Remaining 6 AI agents
- 4.2 Additional CMS connectors (SFMC, Adobe Campaign, Taxi)
- 4.4 Litmus / Email on Acid API integration
- 4.13 Agent Harness Engineering (TAOR loop, PreCompletionChecklist, Progressive Disclosure, Linter Gates, Progress Log, Model Escalation)

**Phase 5 — Agent Evaluation System:**
- 5.1 Review & harden synthetic test data (security audit)
- 5.2 Write LLM judge prompts (binary pass/fail for all 9 agents)
- 5.3 Run first eval batch & collect JSONL traces
- 5.4 Error analysis on traces (failure taxonomy per agent)
- 5.5 Calibrate judges against human labels (TPR/TNR targets)
- 5.6 Calibrate 10-point QA gate against human labels
- 5.7 Blueprint pipeline end-to-end eval runner
- 5.8 Automated regression suite in CI/CD

Confirm you're ready for backend work.
