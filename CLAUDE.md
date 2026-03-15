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

**Active:** **11.25** client design system & template customisation (11.25.1 design system model done, 11.25.2 component→section bridge done — `app/components/section_adapter.py`, `SectionAdapter` + `SlotHint` + `ComponentVersionLike` Protocol, slot_definitions on ComponentVersion; remaining: 11.25.3-11.25.5). Then Phase 12 (Figma import), Phase 13 (ESP sync).

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
