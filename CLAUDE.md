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
make check           # All checks: backend (lint + types + tests + security) + frontend (types + tests)

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

# Agent evals
make eval-verify     # Pre-flight check: verify LLM provider works
make eval-run        # Run agent evals (generate traces, auto-verifies provider)
make eval-labels     # Scaffold human label templates
make eval-analysis   # Analyze verdicts (failure taxonomy)
make eval-blueprint  # Run blueprint pipeline evals
make eval-regression # Check for regressions vs baseline
make eval-check      # Full eval gate (analysis + regression)
make eval-dry-run    # Full pipeline dry-run (no LLM needed)
make eval-full       # Full pipeline (requires LLM provider)
make eval-baseline   # Run full pipeline + establish baseline (first time)
make eval-calibrate  # Calibrate judges against human labels
make eval-qa-calibrate # Calibrate QA gate against human labels
make eval-skill-test AGENT=scaffolder PROPOSED=path/to/SKILL.md  # A/B test a SKILL.md change

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
│   ├── knowledge/      # RAG pipeline (pgvector, document processing, hybrid search) + graph/ (Cognee) + ontology/ (CSS/client support)
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
│   ├── memory/         # Agent memory (pgvector embeddings, temporal decay, DCG bridge)
│   ├── rendering/      # Cross-client rendering tests (Litmus, Email on Acid)
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
- `COGNEE__ENABLED`, `COGNEE__GRAPH_DB_PROVIDER`, `COGNEE__LLM_PROVIDER` (inherits AI config if empty)
- `ONTOLOGY_SYNC__ENABLED`, `ONTOLOGY_SYNC__INTERVAL_HOURS` (default 168/weekly), `ONTOLOGY_SYNC__GITHUB_TOKEN` (optional, for rate limits)


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
| `projects` | `/api/v1/projects`, `/api/v1/orgs` | Multi-tenant client org isolation, project workspaces, onboarding subgraphs |
| `email_engine` | `/api/v1/email` | Maizzle build pipeline, calls sidecar at `http://maizzle-builder:3001` |
| `components` | `/api/v1/components` | Versioned reusable email components (header, CTA, hero, etc.) |
| `qa_engine` | `/api/v1/qa` | 10-point quality gate system with individual check modules |
| `connectors` | `/api/v1/connectors` | ESP export (Braze, SFMC, Adobe Campaign, Taxi for Email) via ConnectorProvider Protocol |
| `approval` | `/api/v1/approvals` | Client approval workflow with feedback and audit trail |
| `templates` | `/api/v1/templates`, `/api/v1/projects/{id}/templates` | Versioned email templates with soft delete and restore |
| `personas` | `/api/v1/personas` | Test subscriber profiles (device, email client, dark mode) |
| `rendering` | `/api/v1/rendering` | Cross-client rendering tests (Litmus, EoA) with visual regression |
| `knowledge` | `/api/v1/knowledge` | RAG pipeline: document ingestion, hybrid search, tagging (`make seed-knowledge`) |
| `memory` | `/memory` | Agent memory: pgvector semantic search, temporal decay, DCG promotion bridge |
| `blueprints` | `/api/v1/blueprints` | Blueprint state machine engine: orchestrated agent pipelines with self-correction |
| `ontology` | `/api/v1/ontology` | Competitive intelligence reports: audience-scoped feasibility, Hub vs competitor capability matrix |

### QA Gate System (10 checks)

Located in `app/qa_engine/checks/`. Each check implements `async run(html: str) -> QACheckResult`:

1. `html_validation` — DOCTYPE, structural HTML tags
2. `css_support` — Ontology-powered: scans 365 CSS properties against 25 email clients with severity scoring
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
| Scaffolder | Generate Maizzle HTML from campaign briefs | Sprint 2 | Judge ready (5 criteria), SKILL.md + 4 L3 files |
| Dark Mode | Inject dark mode CSS, Outlook overrides, colour remapping | Sprint 2 | Judge ready (5 criteria), SKILL.md + 3 L3 files |
| Content | Subject lines, preheaders, CTA text, tone adjustment | Sprint 2 | Judge ready (5 criteria) |
| Outlook Fixer | MSO conditionals, VML backgrounds, table fallbacks | V2 | Judge ready (5 criteria), 12 synthetic cases |
| Accessibility Auditor | WCAG AA, contrast, alt text, AI alt generation | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 10 synthetic cases |
| Personalisation | Liquid (Braze), AMPscript (SFMC), dynamic content | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 12 synthetic cases |
| Code Reviewer | Static analysis, redundant code, file size optimisation | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 12 synthetic cases |
| Knowledge | RAG-powered Q&A from knowledge base | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 10 synthetic cases |
| Innovation | Prototype new techniques, feasibility assessment | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 10 synthetic cases |

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
- `judges/` — Binary pass/fail LLM judges: `ScaffolderJudge` (5 criteria), `DarkModeJudge` (5 criteria), `ContentJudge` (5 criteria), `OutlookFixerJudge` (5 criteria), `AccessibilityJudge` (5 criteria), `PersonalisationJudge` (5 criteria), `CodeReviewerJudge` (5 criteria), `KnowledgeJudge` (5 criteria), `InnovationJudge` (5 criteria); `Judge` Protocol, `JUDGE_REGISTRY`, shared prompt template
- `judge_runner.py` — CLI: `python -m app.ai.agents.evals.judge_runner --agent {agent} --traces X --output Y`
- `schemas.py` — Shared dataclasses: `FailureCluster`, `HumanLabel`, `CalibrationResult`, `QACalibrationResult`, `RegressionReport`, `SkillABCriterionDelta`, `SkillABResult`, `SkillABReport`, `BlueprintEvalTrace`
- `error_analysis.py` — Failure clustering + pass rate computation from verdict JSONL (`make eval-analysis`)
- `scaffold_labels.py` — Generates prefilled human label templates from traces+verdicts (`make eval-labels`)
- `calibration.py` — TPR/TNR computation against human labels per criterion
- `qa_calibration.py` — QA gate check-vs-human agreement rates, flags checks <75%
- `blueprint_eval.py` — End-to-end blueprint pipeline runner with 5 test briefs (`make eval-blueprint`)
- `regression.py` — Baseline comparison with configurable tolerance, CI gate exit code (`make eval-regression`)
- `skill_ab.py` — SKILL.md A/B test runner: runs eval suite with current vs proposed SKILL.md, compares per-criterion pass rates, auto-recommends merge/reject (`make eval-skill-test`)

### API Security Patterns

- **JWT HS256**: Pinned algorithm constant in `app/auth/token.py` (not configurable). 15-min access + 7-day refresh tokens. Redis-backed blocklist for revocation.
- **Brute-force protection**: exponential backoff, lock after 5 failed attempts (15 min), Redis-tracked.
- **Row-Level Security**: PostgreSQL RLS on `client_org_id`. Database enforces isolation independently of app layer.
- **Credential storage**: AES-256 for stored API keys (Braze, Figma). Never returned in responses, never logged.
- **AI rate limits**: 20 req/min per user for chat, 5 req/min for generation. Per-user daily quota via Redis (`app/core/quota.py`). Stream timeout 120s. Blueprint daily token cap 500k.
- **WebSocket limits**: Global 100 connections + per-user 5 connections (`app/streaming/manager.py`).
- **LLM output sanitization**: `nh3` (Rust-based) allowlist HTML sanitizer in `app/ai/shared.py`. Preserves email HTML (tables, styles, MSO comments). Approval state machine prevents invalid transitions.
- **Error sanitization**: `get_safe_error_message()` / `get_safe_error_type()` in `app/core/error_sanitizer.py`. All exception handlers (including auth) use sanitized messages — never leak class names or internal details.
- **CI quality gate**: `.github/workflows/ci.yml` runs lint + types + security-check + tests on every push/PR. PR template enforces security checklist.

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
- [x] 4.1 All 9 AI agents complete — eval-first + skills workflow (Outlook Fixer, Accessibility Auditor, Personalisation, Code Reviewer, Knowledge, Innovation — all DONE)
- [x] 4.2 Additional CMS connectors (SFMC, Adobe Campaign, Taxi for Email)
- [x] 4.3 Figma design sync (frontend demo: `/figma` page, connection management, token extraction UI)
- [x] 4.4 Litmus / Email on Acid API integration (backend: `app/rendering/` VSA module, Litmus + EoA providers, visual regression)
- [x] 4.5 Advanced features (collaborative editing, localisation, brand guardrails, AI image gen, visual Liquid builder, client briefs)

### Phase 5 — Agent Evaluation System
Applies to ALL 9 agents. No agent goes to production without completing steps 5.1–5.5. See `TODO.md` for full details.
- [x] 5.1 Synthetic test data generation (Scaffolder: 12, Dark Mode: 10, Content: 14 cases done)
- [x] 5.2 Eval runner infrastructure (JSONL trace capture)
- [x] 5.3 Write binary judge prompts per agent per quality dimension
- [x] 5.4 Run evals + error analysis — live execution complete (36 traces, 16.7% overall pass rate, failure clusters identified)
- [x] 5.5 Judge calibration — verdicts generated, human label templates scaffolded (540 rows), calibration pending human labels
- [x] 5.6 QA gate calibration — tooling ready, pending human labels
- [x] 5.7 Blueprint pipeline evals — 5/5 campaigns passed with self-correction
- [x] 5.8 Regression suite — baseline established from live data (`traces/baseline.json`), CI integration deferred

### Phase 6 — OWASP API Security Hardening (COMPLETE)
Audit conducted 2026-03-06. Follow-up audit 2026-03-07. Fix pattern: `verify_project_access()` from `app/projects/service.py`.
- [x] 6.1.1–6.1.4 BOLA fixes — CRITICAL (projects, approvals, connectors, QA override)
- [x] 6.1.5–6.1.10 BOLA fixes — HIGH/CRITICAL (approvals, rendering, knowledge, WebSocket, AI agents, email builds)
- [x] 6.2.1–6.2.4 Response & error hardening (error sanitizer, LLM circuit breaker, generic error types, auth handler type leakage)
- [x] 6.3.1–6.3.4 Rate limiting & resource controls (per-user Redis quota, per-user WS limit, stream timeout, blueprint cost cap)
- [x] 6.4.1–6.4.3 Business logic (approval state machine, JWT algorithm pinning, nh3 HTML sanitizer)
- [x] 6.5.1–6.5.6 SDC improvements (security-check in `make check`, CI workflow, PR template, memory rate limits, frontend token/type fixes)

### Phase 7 — Agent Capability Improvements
Build infrastructure before remaining agents so every new agent inherits patterns from day one.
- [x] 7.1 Structured inter-agent handoff schemas (`AgentHandoff` frozen dataclass, full history via `_handoff_history`, auto-persisted to episodic memory via `handoff_memory.py`, exposed in API as `HandoffSummary`)
- [x] 7.2 Eval-informed agent prompts (`app/ai/agents/evals/failure_warnings.py`, reads `traces/analysis.json`, injects per-agent warnings into all 9 `build_system_prompt()` for criteria <85% pass rate)
- [x] 7.3 Agent confidence scoring (0-1 via `<!-- CONFIDENCE: X.XX -->` HTML comment, threshold 0.5 → `needs_review` status)
- [x] 7.4 Template-aware component context (`ComponentResolver` Protocol, `DbComponentResolver`, auto-detect `<component>` refs, inject metadata into agentic node context)
- [x] 7.5 Hub Agent Memory System (`app/memory/` VSA module, pgvector Vector(1024), HNSW index, temporal decay, DCG promotion bridge, 5 REST endpoints, 19 tests)
- [x] 7.6 DCG cross-agent memory Phase 1 (`destructive_command_guard/src/notes.rs` — `store_note` + `recall_notes` MCP tools, JSONL-based project-scoped note storage, agent auto-detection, file locking for concurrency safety) + Agent architecture improvements (`BaseAgentService` shared pipeline in `app/ai/agents/base.py`, 7 agents refactored, standardised response schemas with `confidence` + `skills_loaded` on all 9 agents, `to_handoff()` method, memory recall in blueprint engine, recovery router cycle detection + keyword collision fix, eval trace fixes)

### Phase 8 — Knowledge Graph Integration (Cognee)
Replace flat RAG with graph-structured knowledge using Cognee. Agents get structured entity relationships instead of similar text chunks. Depends on Phase 7 infrastructure.
- [x] 8.1 Cognee integration layer (`app/knowledge/graph/`, `GraphKnowledgeProvider` Protocol, `CogneeGraphProvider`, `POST /graph/search` endpoint, optional dep `cognee[graph]`, 8 tests)
- [x] 8.2 Knowledge graph seeding (`seed.py` feeds RAG docs + ontology through Cognee ECL pipeline per domain)
- [x] 8.3 Graph context provider for blueprint nodes (`graph_context.py` structured relationships in agent context)
- [x] 8.4 Blueprint outcome logging (`outcome_logger.py` formats+queues to Redis+Memory, `OutcomeGraphPoller` drains into Cognee, 19 tests)
- [x] 8.5 Per-agent domain SKILL.md files (all 9 agents: Four Discipline structure, progressive disclosure L1+L2+L3)
- [x] 8.6 Email development ontology (`app/knowledge/ontology/` — Python-native, 25 clients, 365 CSS properties, 1011 support entries, 70 fallbacks, data-driven QA, Cognee graph export, 51 tests)

### Phase 9 — Graph-Driven Intelligence Layer
Leverages Phase 8 knowledge graph across the entire Hub — personas, components, blueprints, competitive intel, skill evolution. Depends on Phase 8 core operational.
- [x] 9.1 Graph-powered client audience profiles (`audience_context.py`, persona → ontology bridge, engine/service/6 nodes wired, 15 tests)
- [x] 9.2 Can I Email live sync (`app/knowledge/ontology/sync/` — `CanIEmailSyncPoller`, GitHub API → YAML diff → graph re-export, 51 tests)
- [x] 9.3 Component-to-graph bidirectional linking (`qa_bridge.py` + `graph_export.py`, `ComponentQAResult` join model, 2 new endpoints, compatibility badge on `ComponentResponse`, 20 tests)
- [x] 9.4 Failure pattern propagation across agents (`failure_patterns.py` — extract from QA failures + handoff history, dual persist to memory + graph, recall into engine LAYER 9 by agent + client_ids, 27 tests)
- [x] 9.5 Client-specific subgraphs for project onboarding (`onboarding.py` generates scoped docs from ontology, `target_clients` JSON column, LAYER 8 engine context, `POST .../onboarding-brief` endpoint, 14 tests)
- [x] 9.6 Graph-informed blueprint route selection (`route_advisor.py` — `RoutingPlan` with audience-aware skip/add logic, engine pre-execution routing, `RoutingDecisionResponse` in API, 724 lines tests)
- [x] 9.7 Competitive intelligence graph (`competitive_feasibility.py` — audience-aware feasibility scoring, `GET /api/v1/ontology/competitive-report` endpoint, LAYER 10 enhanced with audience coverage, 35 tests)
- [x] 9.8 SKILL.md A/B testing via eval system (`skill_override.py` runtime registry, `skill_ab.py` A/B runner CLI, all 9 prompt.py files wired, `make eval-skill-test`, 17 tests)

### Phase 10 — Full-Stack Agent Workflow (Frontend Integration)
Wire Phase 8-9 backend intelligence into the frontend. Depends on Phase 8 + 9 backend complete, Phase 0-3 frontend foundation. Design principle: QA always checks ALL 25 email clients; "priority clients" affect display emphasis and agent attention, never exclusion.
- [x] 10.1 Project priority clients selector (`target-clients-selector.tsx` multi-select, `GET /api/v1/ontology/clients` endpoint, `useEmailClients` + `useUpdateProject` hooks, create dialog + workspace toolbar integration, project card badges, i18n keys, 4 backend tests — empty = all clients equal priority)

## Feature Scope by Stack

### Backend Features (for `be-prime`)
- Auth: JWT HS256, RBAC (admin/developer/viewer), token revocation, brute-force protection
- Projects: ClientOrg, Project, ProjectMember models + RLS; `target_clients` JSON column (priority clients — QA always checks all 25, priority affects display emphasis + agent attention); `onboarding.py` auto-generates client-specific compatibility subgraphs (Cognee dataset per project); `POST .../onboarding-brief` for manual refresh
- Email Engine: Maizzle build orchestration via sidecar
- Components: versioned component library with dark mode variants; QA bridge (`qa_bridge.py`) runs QA + extracts per-client compatibility; graph export (`graph_export.py`) for Cognee; `ComponentQAResult` join model; `compatibility_badge` on responses
- QA Engine: 10-point check system in `app/qa_engine/checks/`
- Connectors: 4 ESP connectors (Braze, SFMC, Adobe Campaign, Taxi) via ConnectorProvider Protocol + AES-256 credential storage
- Approval: ApprovalRequest, Feedback, AuditEntry models + workflow
- Personas: test subscriber profile presets
- AI: provider registry, model routing (Opus/Sonnet/Haiku), streaming via WebSocket
- Blueprints: state machine engine orchestrating agents with QA gating, recovery routing, bounded self-correction, structured handoffs (`AgentHandoff` with full history + episodic memory persistence), confidence-based routing, component context injection, project subgraph context (LAYER 8), graph-informed route selection (`route_advisor.py` — audience-aware node skipping/addition), audience-aware competitive feasibility (LAYER 10)
- Knowledge: RAG pipeline with pgvector, hybrid search, document processing; `app/knowledge/graph/` Cognee integration (`GraphKnowledgeProvider` Protocol, `CogneeGraphProvider`, `POST /graph/search`, disabled by default); `app/knowledge/ontology/` email development ontology (25 clients, 365 CSS properties, 1011 support entries, 70 fallbacks — powers data-driven QA + Cognee graph export); `app/knowledge/ontology/sync/` Can I Email live sync (`CanIEmailSyncPoller` via `DataPoller`, GitHub Trees API → YAML diff → graph re-export, `OntologySyncConfig`); `app/knowledge/ontology/competitive_feasibility.py` audience-aware competitive reports (`GET /api/v1/ontology/competitive-report`); `GET /api/v1/ontology/clients` lists all 25 email clients for frontend selectors
- Rendering: cross-client rendering tests (Litmus, EoA) via `RenderingProvider` Protocol, circuit breaker, visual regression comparison
- Agent Evals: dimension-based synthetic test data, JSONL trace runner, binary LLM judges, TPR/TNR calibration, error analysis, QA gate calibration, blueprint pipeline evals, regression detection (Phase 5); SKILL.md A/B testing (`skill_ab.py` + `skill_override.py` runtime override registry, `make eval-skill-test`)
- Memory: `app/memory/` VSA module — pgvector Vector(1024) embeddings, HNSW similarity search, temporal decay, 3 memory types (procedural/episodic/semantic), DCG promotion bridge, `MemoryCompactionPoller`
- Phase 7: `AgentHandoff` structured handoffs with full history + episodic memory auto-persistence (`handoff_memory.py`), confidence scoring (threshold 0.5 → needs_review), `ComponentResolver` for template-aware component context injection, SKILL.md progressive disclosure files for all 9 agents; `BaseAgentService` shared pipeline (`app/ai/agents/base.py`) with `_get_model_tier` + `_should_run_qa` hooks, standardised response schemas (`confidence` + `skills_loaded` on all agents), `to_handoff()` for standardised handoff emission, memory recall wired into blueprint engine, recovery router cycle detection via `handoff_history`; eval-informed prompts (`app/ai/agents/evals/failure_warnings.py`) — reads `traces/analysis.json`, injects per-agent failure warnings into all 9 `build_system_prompt()` for criteria <85% pass rate, mtime-cached

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
- Rendering Tests: `/renderings` page with test list, stats cards, compatibility matrix, screenshot dialog, visual regression comparison, async polling
- Collaborative Editing: Yjs CRDT, y-codemirror.next, collaborator avatars, connection status
- Priority Clients Selector: `target-clients-selector.tsx` multi-select with engine badges, `useEmailClients` + `useUpdateProject` hooks, create dialog + workspace toolbar + project card badges (empty = all clients equal priority, QA always checks all 25)

## Compact instructions

When compacting, preserve:
- Current task context and active plan file path
- List of all files modified in this session
- Test commands run and their results
- Key decisions made during this session
