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

See `TODO.md` for details. Completed: phases 0-10, tasks 11.1-11.21, 11.22.1-11.22.3.

**Active:** 11.22 Template-first hybrid architecture (subtasks 1-3 done, 4-9 remaining, plan: `.agents/plans/11.22-deterministic-agent-architecture.md`). Next: 11.22.4 (cascading auto-repair). Then 11.23-11.24, Phase 12 (Figma import), Phase 13 (ESP sync).

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
