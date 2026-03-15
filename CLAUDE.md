# CLAUDE.md

## Project Overview

Centralised email platform with AI agents. FastAPI backend, Next.js 16 frontend, PostgreSQL + Redis. Python 3.12+, strict MyPy + Pyright. **Vertical slice architecture** — features under `app/{feature}/`.

## Essential Commands

```bash
make dev             # Backend (:8891) + frontend (:3000)
make check           # All checks (lint + types + tests + security)
make test            # Backend unit tests
make lint            # Format + lint (ruff)
make types           # mypy + pyright
make check-fe        # Frontend type-check + unit tests
make db-migrate      # Run migrations
make eval-full       # Full eval pipeline (requires LLM)
make eval-check      # Eval gate (analysis + regression)
make eval-golden     # CI golden test (deterministic, no LLM)
make eval-qa-coverage # Deterministic micro-judges coverage
```

## Development Guidelines

**Feature file order:** schemas → models → repository → service → exceptions → routes → tests

**Layers:** Routes (thin HTTP) → Service (business logic) → Repository (DB only). Exceptions inherit `AppError`.

**Key imports:** `get_logger` from `app.core.logging`, `get_db` from `app.core.database`, `TimestampMixin` from `app.shared.models`, `escape_like` from `app.shared.utils`. Roles: admin, developer, viewer.

**Config:** Nested Pydantic settings, `env_nested_delimiter="__"` (e.g. `DATABASE__URL`, `AI__PROVIDER`).

## Architecture

Backend: `app/` (VSA features) — `core/`, `shared/`, `auth/`, `ai/` (agents + blueprints + evals), `knowledge/`, `qa_engine/` (11 checks), `projects/`, `email_engine/`, `components/`, `connectors/`, `approval/`, `personas/`, `memory/`, `rendering/`, `design_sync/`, `streaming/`. Frontend: `cms/`. Sidecar: `services/maizzle-builder/`. Migrations: `alembic/`.

## Roadmap

See `TODO.md` for details. Completed: phases 0-10, tasks 11.1-11.24 (including 11.22 template-first architecture — all 9 subtasks, 11.23 inline judges, 11.24 production trace sampling).

**Completed:** **11.25** client design system & template customisation — all 5 subtasks done (11.25.1 design system model, 11.25.2 component→section bridge, 11.25.3 project-scoped template registry, 11.25.4 agent pipeline constraint injection — design system as generation constraints with role-based token mapping + locked fills + brand color sweep, 11.25.5 consistency enforcement — `BrandRepair` stage 8 in repair pipeline + e2e brand enforcement tests). **12.1** protocol extension + Figma API integration (file structure, components, image export — 3 new protocol methods + Figma implementation + schemas + routes). **12.2** asset storage pipeline (`DesignAssetService` — download, resize ≤1200px, local storage, authenticated serving with CSP headers, cascade delete on connection removal). **12.3** design import models & migration (`DesignImport` + `DesignImportAsset` models, 6-state workflow, nullable `result_template_id` FK, repository CRUD, Alembic migration, Pydantic schemas). **12.4** layout analyzer & brief generator (`LayoutAnalyzer` pure-function section detection + `BriefGenerator` markdown output, 2 new endpoints: `POST /analyze-layout`, `POST /generate-brief`). **12.6** component extraction (`ComponentExtractor` — Figma components → Hub Component + ComponentVersion with Scaffolder-generated HTML, category detection, duplicate handling via Figma origin in `compatibility` JSON, background job via `asyncio.create_task`, `POST /connections/{id}/extract-components` 202 Accepted). **Next:** 12.5 (AI-assisted conversion pipeline), Phase 13 (ESP sync).

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
