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
email-hub/
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
│   ├── qa_engine/      # 11-point QA gate (11 check implementations in checks/)
│   ├── connectors/     # ESP connectors (Braze Content Block export with Liquid)
│   ├── approval/       # Client approval portal (ApprovalRequest, Feedback, AuditEntry)
│   ├── personas/       # Test persona engine (subscriber profile presets)
│   ├── memory/         # Agent memory (pgvector embeddings, temporal decay, DCG bridge)
│   ├── rendering/      # Cross-client rendering tests (Litmus, Email on Acid)
│   ├── design_sync/    # Multi-provider design tool sync (Figma API, Sketch/Canva stubs)
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
- `DESIGN_SYNC__ENCRYPTION_KEY` (if empty, derived from `AUTH__JWT_SECRET_KEY` via PBKDF2)

### Shared Utilities

- **Pagination**: `PaginationParams` + `PaginatedResponse[T]` from `app.shared.schemas`
- **Timestamps**: `TimestampMixin` + `utcnow()` from `app.shared.models`
- **Errors**: `AppError` hierarchy in `app.core.exceptions`
- **SQL Escaping**: `escape_like()` from `app.shared.utils`

<!-- Detailed architecture (modules, QA checks, agents, eval framework, security patterns): see .claude/rules/architecture.md -->

## Development Guidelines

**Feature file order:** schemas → models → repository → service → exceptions → routes → tests

**Layer responsibilities:**
- **Routes** → HTTP concerns (status codes, dependency injection) — thin, delegate to service
- **Service** → Business logic, validation, logging, orchestration
- **Repository** → Database operations only (no business logic)
- **Exceptions** → Inherit from `AppError` for automatic HTTP status mapping

**Roles:** admin,developer,viewer

## Implementation Roadmap

See `TODO.md` for active task details (phases 11-13). Completed phases (0-10): see `docs/TODO-completed.md`.

### Phase 11 — QA Engine Hardening & Agent Quality Improvements
Upgrade QA checks from shallow string matching to DOM-parsed validation, add new checks, fix worst agent failure modes. Target: 95%+ issue detection, 60%+ agent eval pass rate. **33 tasks (31 BE, 0 FE, 2 BOTH)**
- [x] `BE` 11.1 QA check configuration system (`QACheckConfig` model, per-project overrides, `defaults.yaml`)
- [x] `BE` 11.2 HTML validation — DOM parser upgrade (`lxml`, 20 DOM-parsed checks across 5 groups, configurable deductions)
- [x] `BE` 11.2a Shared QA rule engine — YAML-driven check definitions (`rule_engine.py`, `rules/email_structure.yaml`, `rules/accessibility.yaml`, refactor 11.2 to rule-driven, RAG integration)
- [x] `BE` 11.3 Accessibility — WCAG AA coverage (24 YAML rules across 8 groups, 21 custom check functions, rule engine wrapper)
- [x] `BE` 11.4 Fallback — MSO conditional parser (balanced pairs, VML nesting, namespace validation, ghost tables)
- [x] `BE` 11.5 Dark mode — semantic validation (meta tag correctness, non-empty media queries, color coherence)
- [x] `BE` 11.6 Spam score — production trigger database (59 weighted triggers, word boundaries, formatting heuristics, obfuscation detection)
- [x] `BE` 11.7 Link validation — HTML parser + URL format check (proper extraction, `urlparse`, ESP template syntax)
- [x] `BE` 11.8 File size — multi-client thresholds (Yahoo 75KB, Outlook 100KB, content breakdown, gzip estimate)
- [x] `BE` 11.9 Image optimization — comprehensive validation (all images, dimension values, format support, tracking pixels)
- [x] `BE` 11.10 CSS support — syntax validation & vendor prefixes (`cssutils`, vendor prefix detection, external stylesheet flag, !important overuse, @import, 8 YAML rules)
- [x] `BE` 11.11 Brand compliance — per-project rules engine (colors, typography, required elements, forbidden patterns, 7 YAML rules, brand analyzer)
- [x] `BE` 11.12 New check — personalisation syntax validation (7 ESPs: Braze/Liquid, SFMC/AMPscript, Adobe/JSSP, Klaviyo/Django, Mailchimp/Merge, HubSpot/HubL, Iterable/Handlebars; 12 YAML rules, personalisation_validator.py)
- [x] `BE` 11.13 Outlook Fixer agent — MSO diagnostic validator (post-generation `validate_mso_conditionals()`, programmatic repair, LLM retry with error context, `mso_repair.py`, blueprint node MSO warnings in `AgentHandoff`)
- [x] `BE` 11.14 Dark Mode agent — deterministic meta tag injector (`meta_injector.py`, `_post_process()` override, contextvars thread-safe, L3 skill file, 32 tests)
- [x] `BE` 11.15 Scaffolder agent — MSO-first generation (always-load MSO skill, `css_email_reference` registered, `_post_process()` MSO validation via `validate_mso_conditionals()`, `contextvars` thread-safe warnings, blueprint node MSO warnings in `AgentHandoff`, expanded `mso_vml_quick_ref.md` with 5 bug-fix patterns, SKILL.md MSO-first emphasis, 5 tests)
- [x] `BE` 11.16 Personalisation agent — per-platform syntax validator (`ESPPlatform` 3→7, `SKILL_FILES` 4→8, `format_syntax_warnings()` shared helper, `_post_process()` override with contextvars, `PersonalisationResponse.syntax_warnings`, blueprint node emits warnings in `AgentHandoff`, SKILL.md post-gen validation section, 28 tests)
- [x] `BE` 11.17 Code Reviewer agent — actionability framework (`actionability.py` with agent tagging + vague pattern detection + QA cross-check; `ResponsibleAgent` literal type; `CodeReviewService.process()` 4-step pipeline with selective retry; SKILL.md expanded allowlist + actionable format spec; 10 registered skills; blueprint node agent tagging; 20 eval cases, 57 tests)
- [x] `BE` 11.18 Accessibility agent — alt text quality framework (`alt_text_validator.py` with 4 image categories + generic/filename/prefix/length checks; `_post_process()` with contextvars; SKILL.md 7 categories incl. landmarks + contrast ratios; blueprint node alt warnings in `AgentHandoff`; 14 eval cases, 29 tests)
- [x] `BE` 11.19 Content agent — length guardrails (`length_guardrail.py` with `LengthLimit` per-operation limits + ratio validation; `process()` override with selective retry; `ContentResponse.length_warnings`; SKILL.md hard limits; 18 eval cases, 51 tests)
- [x] `BE` 11.20 Recovery router — enriched failure context (`StructuredFailure` + `AllowedScope` in `protocols.py`, `scope_validator.py`, QA gate produces structured failures, priority-based routing with fingerprint cycle detection, per-agent scope constraints, legacy fallback, 26 tests)
- [ ] `BE` 11.21 Deterministic micro-judges — map judge criteria to QA checks, `judge_criteria_map.py`, `make eval-qa-coverage`
- [ ] `BE` 11.22 Template-first hybrid architecture — 16.7% → 99%+ structural / 97%+ overall (LLM makes decisions in JSON, deterministic code assembles HTML)
  - [ ] `BE` 11.22.1 Golden template library (15-20 pre-validated email skeletons, 100% QA pass, content slots — `app/ai/templates/`)
  - [ ] `BE` 11.22.2 Structured output schema (`EmailBuildPlan` JSON — template selection, slot fills, design tokens, personalisation config)
  - [ ] `BE` 11.22.3 Multi-pass generation pipeline (3 focused LLM calls: layout→content→design, per-field retry, parallel slots)
  - [ ] `BE` 11.22.4 Cascading auto-repair pipeline (`repair_pipeline.py` — 7-stage deterministic fix: structure→MSO→dark mode→a11y→personalisation→size→links)
  - [ ] `BE` 11.22.5 SKILL.md rewrite — architect prompts not generator prompts (all 9 agents return structured decisions, not HTML)
  - [ ] `BE` 11.22.6 Context assembly optimisation (`context_budget.py` — per-pass budgets, selective SKILL.md, handoff summarisation)
  - [ ] `BE` 11.22.7 Novel layout fallback (`TemplateComposer` — compose from section blocks when no golden template matches)
  - [ ] `BE` 11.22.8 Agent role redefinition (tighten specialisation — each agent owns a slice of `EmailBuildPlan`, no raw HTML generation)
  - [ ] `BOTH` 11.22.9 Eval-driven iteration loop (milestones: 70%→85%→95%→97%→99%+, regression detection, new template-selection eval dimensions)
- [ ] `BE` 11.23 Inline eval judges — selective LLM judge on recovery retries (`inline_judge.py`, judge verdict in API, opt-in per blueprint)
- [ ] `BOTH` 11.24 Production trace sampling — async judge worker, production verdicts → `failure_warnings.py` feedback loop (`production_sampler.py`)

### Phase 12 — Design-to-Email Import Pipeline
Pull Figma designs, AI-convert to Maizzle templates via Scaffolder agent, extract components, import images. Extends `app/design_sync/` module. Figma only (Sketch/Canva stubs unchanged). **9 tasks (6 BE, 2 FE, 1 BOTH)**
- [ ] `BE` 12.1 Protocol extension + Figma API integration (3 new methods: `get_file_structure`, `list_components`, `export_images`)
- [ ] `BE` 12.2 Asset storage pipeline (`DesignAssetService`, download/resize/serve with BOLA)
- [ ] `BE` 12.3 Design import models & migration (`DesignImport`, `DesignImportAsset`, repository CRUD, schemas)
- [ ] `BE` 12.4 Layout analyzer & brief generator (Figma structure → email sections → markdown brief)
- [ ] `BE` 12.5 AI-assisted conversion pipeline (`DesignImportService` orchestrator, Scaffolder integration, 6 new endpoints)
- [ ] `BE` 12.6 Component extraction (Figma components → Hub Component + ComponentVersion via Scaffolder)
- [ ] `FE` 12.7 Frontend file browser & import dialog (tree view, multi-step wizard, component extraction panel)
- [ ] `FE` 12.8 Design reference in workspace (bottom panel tab with design image + tokens)
- [ ] `BOTH` 12.9 SDK regeneration & tests (all new modules tested, SDK covers new endpoints)

### Phase 13 — ESP Bidirectional Sync & Mock Servers
Transform 4 ESP connectors from export-only stubs into bidirectional sync with mock ESP servers. **11 tasks (8 BE, 1 FE, 1 BOTH, 1 INFRA)**
- [ ] `INFRA` 13.1 Mock ESP server — core infrastructure (FastAPI app, SQLite, per-ESP auth, Docker)
- [ ] `INFRA` 13.2 Mock ESP — Braze Content Blocks API
- [ ] `INFRA` 13.3 Mock ESP — SFMC Content Builder API
- [ ] `INFRA` 13.4 Mock ESP — Adobe Campaign Delivery API
- [ ] `INFRA` 13.5 Mock ESP — Taxi for Email API
- [ ] `INFRA` 13.6 Mock ESP — Seed Data (44 templates with ESP-specific personalisation tags)
- [ ] `BE` 13.7 Backend — ESP sync protocol, model & migration (`ESPSyncProvider`, `ESPConnection`, Fernet encryption)
- [ ] `BE` 13.8 Backend — per-ESP sync providers (Braze, SFMC, Adobe, Taxi via `httpx`)
- [ ] `BE` 13.9 Backend — sync service & routes (8 endpoints at `/api/v1/connectors/sync`)
- [ ] `FE` 13.10 Frontend — ESP sync UI (connection cards, template browser, import/push workflows)
- [ ] `BOTH` 13.11 Tests, SDK & Docker integration

<!-- Feature scope by stack (backend + frontend feature lists): see docs/feature-scope.md -->

## Compact instructions

When compacting, preserve:
- Current task context and active plan file path
- List of all files modified in this session
- Test commands run and their results
- Key decisions made during this session
