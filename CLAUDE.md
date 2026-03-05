# CLAUDE.md

## Project Overview

Centralised email development platform with AI-powered agents. Built with **vertical slice architecture** — FastAPI backend, Next.js 16 frontend, PostgreSQL + Redis infrastructure. Python 3.12+, strict type checking with MyPy and Pyright.

## Core Principles

**Vertical Slice Architecture** — Each feature owns its models, schemas, routes, and business logic under `app/{feature}/`. Shared utilities go in `app/shared/` only when used by 3+ features. Core infrastructure in `app/core/`.

**Type Safety (CRITICAL)** — Strict MyPy + Pyright enforced. All functions must have complete type annotations. No `Any` without justification.

**Structured Logging** — `domain.component.action_state` pattern via structlog. Logger: `from app.core.logging import get_logger`.

**Security-First** — Zero Trust API (every endpoint authenticated + authorized). Input validation via Pydantic on ALL request bodies. Output sanitisation (strip sensitive data, never leak stack traces). CORS whitelisted origins only. Rate limiting per-user + per-endpoint via Redis. Audit trail on every state-changing API call.

**Protocol-Based Interfaces** — All external integrations use Python Protocols. Swap implementations without code changes. Provider registry for AI/embedding/reranker at runtime.

## Essential Commands

```bash
# Local development
make db              # Start PostgreSQL + Redis (Docker)
make dev             # Start backend (:8891) + frontend (:3000)
make dev-be          # Backend only
make dev-fe          # Frontend only

# Quality checks — all in one
make check           # All checks: backend (lint + types + tests) + frontend (types + tests)

# Backend checks
make test            # Backend unit tests (pytest)
make lint            # Format + lint (ruff)
make types           # mypy + pyright

# Frontend checks
make check-fe        # Frontend type-check + unit tests
make test-fe         # Frontend unit tests only (vitest)

# Database
make db-migrate      # Run migrations
make db-revision m="description"  # Create new migration

# Knowledge base
make seed-knowledge  # Seed RAG knowledge base (requires DB + embedding provider)

# Docker
make docker          # Full stack (port :80)
make docker-down     # Stop all services
```

## Architecture

### Project Structure

```
merkle-email-hub/
├── app/                # Backend features (VSA)
│   ├── core/           # Infrastructure (config, database, logging, middleware, health, rate_limit, redis)
│   ├── shared/         # Cross-feature utilities (pagination, timestamps, error schemas)
│   ├── auth/           # JWT auth + RBAC + user management
│   ├── example/        # Reference VSA feature ("Items" CRUD)
│   ├── ai/             # AI layer (protocol interfaces, provider registry, chat API)
│   │   ├── agents/     # AI agents (scaffolder, dark_mode, content — per-agent subdirs)
│   │   │   └── evals/  # Agent evaluation framework (synthetic data, runner, judges)
│   │   └── blueprints/ # Blueprint state machine (engine, nodes, definitions, schemas)
│   ├── knowledge/      # RAG pipeline (pgvector, document processing, hybrid search)
│   ├── streaming/      # WebSocket streaming (Pub/Sub, connection manager)
│   │
│   │   ── Email Hub Modules ──
│   ├── projects/       # Client-scoped workspaces (ClientOrg, Project, ProjectMember)
│   ├── email_engine/   # Maizzle build orchestration (calls maizzle-builder sidecar)
│   ├── components/     # Versioned email component library (Component, ComponentVersion)
│   ├── qa_engine/      # 10-point QA gate (10 check implementations in checks/)
│   ├── connectors/     # ESP connectors (Braze Content Block export with Liquid)
│   ├── approval/       # Client approval portal (ApprovalRequest, Feedback, AuditEntry)
│   ├── personas/       # Test persona engine (subscriber profile presets)
│   └── tests/          # Integration tests
├── cms/               # Frontend monorepo (Next.js 16 + React 19)
├── email-templates/   # Maizzle project (layouts, templates, components)
├── services/
│   └── maizzle-builder/  # Node.js sidecar for Maizzle builds (Express, port 3001)
├── alembic/           # Database migrations
├── .claude/           # AI-assisted development commands + rules
├── nginx/             # Reverse proxy
└── pyproject.toml     # Dependencies, tooling config
```

### Database

- **Async SQLAlchemy** with configurable connection pooling
- Base class: `app.core.database.Base`
- Session: `get_db()` from `app.core.database`; standalone: `get_db_context()`
- All models inherit `TimestampMixin` from `app.shared.models`

### Configuration

Nested Pydantic settings with `env_nested_delimiter="__"`:
- `DATABASE__URL`, `DATABASE__POOL_SIZE`
- `REDIS__URL`
- `AUTH__JWT_SECRET_KEY`, `AUTH__ACCESS_TOKEN_EXPIRE_MINUTES`

- `AI__PROVIDER`, `AI__MODEL`, `AI__API_KEY`, `AI__MODEL_COMPLEX`, `AI__MODEL_STANDARD`, `AI__MODEL_LIGHTWEIGHT`


### Shared Utilities

- **Pagination**: `PaginationParams` + `PaginatedResponse[T]` from `app.shared.schemas`
- **Timestamps**: `TimestampMixin` + `utcnow()` from `app.shared.models`
- **Errors**: `AppError` hierarchy in `app.core.exceptions`
- **SQL Escaping**: `escape_like()` from `app.shared.utils`

## Development Guidelines

**Feature file order:** schemas → models → repository → service → exceptions → routes → tests

**Layer responsibilities:**
- **Routes** → HTTP concerns (status codes, dependency injection) — thin, delegate to service
- **Service** → Business logic, validation, logging, orchestration
- **Repository** → Database operations only (no business logic)
- **Exceptions** → Inherit from `AppError` for automatic HTTP status mapping

**Roles:** admin,developer,viewer

## Email Hub Architecture

### Modules and Their Purpose

| Module | API Prefix | Purpose |
|--------|-----------|---------|
| `projects` | `/api/v1/projects`, `/api/v1/orgs` | Multi-tenant client org isolation, project workspaces |
| `email_engine` | `/api/v1/email` | Maizzle build pipeline, calls sidecar at `http://maizzle-builder:3001` |
| `components` | `/api/v1/components` | Versioned reusable email components (header, CTA, hero, etc.) |
| `qa_engine` | `/api/v1/qa` | 10-point quality gate system with individual check modules |
| `connectors` | `/api/v1/connectors` | ESP export (Braze, SFMC, Adobe Campaign, Taxi for Email) via ConnectorProvider Protocol |
| `approval` | `/api/v1/approvals` | Client approval workflow with feedback and audit trail |
| `templates` | `/api/v1/templates`, `/api/v1/projects/{id}/templates` | Versioned email templates with soft delete and restore |
| `personas` | `/api/v1/personas` | Test subscriber profiles (device, email client, dark mode) |
| `knowledge` | `/api/v1/knowledge` | RAG pipeline: document ingestion, hybrid search, tagging (`make seed-knowledge`) |
| `blueprints` | `/api/v1/blueprints` | Blueprint state machine engine: orchestrated agent pipelines with self-correction |

### QA Gate System (10 checks)

Located in `app/qa_engine/checks/`. Each check implements `async run(html: str) -> QACheckResult`:

1. `html_validation` — DOCTYPE, structural HTML tags
2. `css_support` — Flags CSS properties with poor email client support
3. `file_size` — Gmail 102KB clipping threshold
4. `link_validation` — HTTPS enforcement, valid protocols
5. `spam_score` — Common spam trigger word detection
6. `dark_mode` — color-scheme meta, prefers-color-scheme, Outlook overrides
7. `accessibility` — lang attribute, image alt text, table roles
8. `fallback` — MSO conditional comments, VML namespaces
9. `image_optimization` — Explicit dimensions, format validation
10. `brand_compliance` — Placeholder for client brand rules

### Maizzle Builder Sidecar

`services/maizzle-builder/` is a thin Node.js/Express server:
- `POST /build` — Full build with optional production config
- `POST /preview` — Development preview build
- `GET /health` — Health check
- Receives template source + config via HTTP, returns compiled HTML

### AI Agents (9 total) + Blueprint Engine + Eval System

The AI protocol layer (`app/ai/`) provides infrastructure for 9 specialized agents using the provider registry for LLM calls and knowledge module for RAG. The **Blueprint engine** (`app/ai/blueprints/`) orchestrates agents as state machine nodes with deterministic gates (QA, build, export) and bounded self-correction. The **Eval system** (`app/ai/agents/evals/`) validates agent quality via dimension-based synthetic test data, binary LLM judges, and TPR/TNR calibration.

| Agent | Purpose | Phase | Eval Status |
|-------|---------|-------|-------------|
| Scaffolder | Generate Maizzle HTML from campaign briefs | Sprint 2 | Synthetic data ready (12 cases) |
| Dark Mode | Inject dark mode CSS, Outlook overrides, colour remapping | Sprint 2 | Synthetic data ready (10 cases) |
| Content | Subject lines, preheaders, CTA text, tone adjustment | Sprint 2 | Synthetic data ready (14 cases) |
| Outlook Fixer | MSO conditionals, VML backgrounds, table fallbacks | V2 | Pending |
| Accessibility Auditor | WCAG AA, contrast, alt text, AI alt generation | V2 | Pending |
| Personalisation | Liquid (Braze), AMPscript (SFMC), dynamic content | V2 | Pending |
| Code Reviewer | Static analysis, redundant code, file size optimisation | V2 | Pending |
| Knowledge | RAG-powered Q&A from knowledge base | V2 | Pending |
| Innovation | Prototype new techniques, feasibility assessment | V2 | Pending |

### Agent Evaluation Framework

Located in `app/ai/agents/evals/`. Based on the [evals-skills methodology](https://github.com/hamelsmu/evals-skills) — binary pass/fail LLM judges calibrated against human labels.

**Per-agent eval requirements (all 9 agents):**
1. Dimension-based synthetic test data (failure-prone axes of variation)
2. Binary pass/fail judge prompts (one per quality dimension)
3. Eval runner traces (JSONL with input, output, timing, errors)
4. Error analysis (failure clustering, root cause identification)
5. Judge calibration (TPR/TNR against human labels, not raw accuracy)

**Eval files:**
- `dimensions.py` — Failure-prone axes per agent (layout complexity, client quirks, etc.)
- `synthetic_data_{agent}.py` — Test cases with real-world data (MSO code, VML, spam triggers)
- `runner.py` — CLI: `python -m app.ai.agents.evals.runner --agent scaffolder --output traces/`
- Judge prompts and calibration data added per Phase 5 steps (see TODO.md)

### API Security Patterns

- **JWT RS256**: 15-min access + 7-day refresh tokens. Redis-backed blocklist for revocation.
- **Brute-force protection**: exponential backoff, lock after 5 failed attempts (15 min), Redis-tracked.
- **Row-Level Security**: PostgreSQL RLS on `client_org_id`. Database enforces isolation independently of app layer.
- **Credential storage**: AES-256 for stored API keys (Braze, Figma). Never returned in responses, never logged.
- **AI rate limits**: 20 req/min per user for chat, 5 req/min for generation. Separate from general rate limits.

## Implementation Roadmap

See `TODO.md` for full task details with security requirements and verification criteria.

### Phase 0 — Foundation Blockers
- [x] 0.1 Database migration for all email-hub models + RLS policies
- [x] 0.2 Initialize shadcn/ui component library in `cms/apps/web/`
- [x] 0.3 Generate OpenAPI TypeScript SDK from backend
- [x] 0.4 Authenticated API client layer (token refresh, error handling, React hooks)

### Phase 1 — Sprint 1: Editor + Build Pipeline
- [x] 1.1 Project dashboard page (`/(dashboard)/page.tsx`)
- [x] 1.2 Project workspace layout (3-pane: editor, preview, AI chat)
- [x] 1.3 Monaco editor (HTML/CSS/Liquid, Can I Email autocomplete)
- [x] 1.4 Maizzle live preview (compile-on-save, viewport toggles, dark mode)
- [x] 1.5 Test persona engine UI (persona selector, device/client context)
- [x] 1.6 Template CRUD + persistence (versioning, restore)

### Phase 2 — Sprint 2: Intelligence + Export
- [x] 2.1 Wire AI provider (Claude/OpenAI, model routing, streaming)
- [x] 2.2 Scaffolder agent (brief → Maizzle HTML)
- [x] 2.3 Dark Mode agent (inject dark mode CSS + Outlook overrides)
- [x] 2.4 Content agent (copy generation, editor context menu)
- [x] 2.5 AI chat sidebar UI (agent selection, streaming, accept/reject)
- [x] 2.6 Component library v1 — backend (seed 5-10 components)
- [x] 2.7 Component library browser UI (`/components`)
- [x] 2.8 10-point QA gate system (backend + UI complete)
- [x] 2.9 Raw HTML export + Braze connector UI
- [x] 2.10 RAG knowledge base seeding (Can I Email, best practices)

### Phase 3 — Sprint 3: Client Handoff + Polish
- [x] 3.1 Client approval portal (viewer role, feedback, audit trail)
- [x] 3.2 Rendering intelligence dashboard (QA trends, support matrices)
- [x] 3.3 Dashboard homepage enhancement (real data, activity feed)
- [x] 3.4 Error handling, loading states, UI polish (skeletons, toasts, error pages)
- [x] 3.5 CMS + Nginx Docker stack (7 services healthy)

### Phase 4 — V2
- [x] 4.8 Knowledge base search UI (`/knowledge` page, document browser, hybrid search)
- [x] 4.9 Smart agent memory (conversation history tab in workspace chat)
- [x] 4.10 Version comparison (side-by-side template diff in approval portal)
- [x] 4.11 Custom persona creation (dialog form for new test profiles)
- [x] 4.12 Exportable reports (intelligence dashboard Print/PDF + CSV export)
- [x] 4.13 Blueprint state machine engine (agent orchestration with self-correction, QA gating, recovery routing)
- [ ] 4.1 Remaining 6 AI agents (Outlook Fixer, Accessibility, Personalisation, Code Reviewer, Knowledge, Innovation)
- [x] 4.2 Additional CMS connectors (SFMC, Adobe Campaign, Taxi for Email)
- [x] 4.3 Figma design sync (frontend demo: `/figma` page, connection management, token extraction UI)
- [ ] 4.4 Litmus / Email on Acid API integration
- [x] 4.5 Advanced features (collaborative editing, localisation, brand guardrails, AI image gen, visual Liquid builder, client briefs)

### Phase 5 — Agent Evaluation System
Applies to ALL 9 agents. No agent goes to production without completing steps 5.1–5.5. See `TODO.md` for full details.
- [x] 5.1 Synthetic test data generation (Scaffolder: 12, Dark Mode: 10, Content: 14 cases done)
- [x] 5.2 Eval runner infrastructure (JSONL trace capture)
- [ ] 5.3 Write binary judge prompts per agent per quality dimension
- [ ] 5.4 Run evals + error analysis (failure clustering)
- [ ] 5.5 Judge calibration (TPR/TNR against human labels)
- [ ] 5.6 QA gate calibration (align 10-point checks with eval findings)
- [ ] 5.7 Blueprint pipeline evals (end-to-end multi-agent traces)
- [ ] 5.8 Regression suite + CI integration

## Feature Scope by Stack

### Backend Features (for `be-prime`)
- Auth: JWT RS256, RBAC (admin/developer/viewer), token revocation, brute-force protection
- Projects: ClientOrg, Project, ProjectMember models + RLS
- Email Engine: Maizzle build orchestration via sidecar
- Components: versioned component library with dark mode variants
- QA Engine: 10-point check system in `app/qa_engine/checks/`
- Connectors: 4 ESP connectors (Braze, SFMC, Adobe Campaign, Taxi) via ConnectorProvider Protocol + AES-256 credential storage
- Approval: ApprovalRequest, Feedback, AuditEntry models + workflow
- Personas: test subscriber profile presets
- AI: provider registry, model routing (Opus/Sonnet/Haiku), streaming via WebSocket
- Blueprints: state machine engine orchestrating agents with QA gating, recovery routing, bounded self-correction
- Knowledge: RAG pipeline with pgvector, hybrid search, document processing
- Agent Evals: dimension-based synthetic test data, JSONL trace runner, binary LLM judges, TPR/TNR calibration (Phase 5)

### Frontend Features (for `fe-prime`)
- Dashboard: project overview grid, activity feed, QA summary, quick-start
- Workspace: 3-pane layout (Monaco editor + preview + AI chat)
- Monaco Editor: HTML/CSS/Liquid syntax, Can I Email warnings, code folding
- Live Preview: sandboxed iframe, viewport toggles, dark mode, zoom
- Persona Selector: device/client context switching
- Component Browser: grid view, search, detail view with preview + versions
- QA Gate UI: trigger, results checklist, override flow with justification
- Export Console: platform selector (Raw HTML, Braze), export preview
- AI Chat Sidebar: agent toggles, streaming display, accept/reject/merge
- Approval Portal: viewer login, read-only preview, section feedback, approve/reject
- Intelligence Dashboard: QA trends, support matrices, quality scores
- Knowledge Base Search: document browser, natural language search, domain/tag filters
- Figma Sync: connection management, design token extraction (colors, typography, spacing)
- Client Briefs: Jira/Asana/Monday.com connection cards, brief items, import-to-project
- Brand Guardrails: per-client color/typography/logo rules, CodeMirror linter, toolbar violations badge
- AI Image Generation: workspace dialog with style presets, gallery, insert-into-template
- Localisation: 6 locale stubs (en/ar/de/es/fr/ja), cookie-based switching, RTL, translation management
- Visual Liquid Builder: @dnd-kit drag-and-drop blocks, regex parser/serializer, Code/Visual tabs
- Collaborative Editing: Yjs CRDT, y-codemirror.next, collaborator avatars, connection status

## Compact instructions

When compacting, preserve:
- Current task context and active plan file path
- List of all files modified in this session
- Test commands run and their results
- Key decisions made during this session
