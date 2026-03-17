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

Backend: `app/` (VSA features) — `core/`, `shared/`, `auth/`, `ai/` (agents + blueprints + evals + voice), `knowledge/`, `qa_engine/` (11 core checks + optional resilience check), `projects/`, `email_engine/`, `components/`, `connectors/`, `approval/`, `personas/`, `memory/`, `rendering/`, `design_sync/`, `streaming/` (data streaming + `websocket/` collab WS with room-based routing, Redis pub/sub bridge, JWT auth), `mcp/` (MCP tool server — 17 tools, streamable HTTP + stdio). Frontend: `cms/`. Sidecars: `services/maizzle-builder/`, `services/mock-esp/` (mock ESP APIs, port 3002). Migrations: `alembic/`.

## Roadmap

See `TODO.md` for details on upcoming phases. See `docs/TODO-completed.md` for detailed completion records of phases 0-23.

**Upcoming phases (priority order — highest differentiation first):**
- **Phase 24** — Real-Time Collaboration & Visual Builder (24.1 WebSocket infra DONE; remaining: Yjs CRDT engine, collaborative cursors & presence, visual builder canvas & palette, property panels, bidirectional sync, workspace integration, tests & docs)
- **Phase 25** — Platform Ecosystem & Advanced Integrations (9 subtasks: plugin manifest & registry, plugin sandbox & lifecycle, Tolgee TMS, Tolgee frontend, Kestra workflows, Penpot design pipeline, Typst report generator, ecosystem dashboard, tests & docs)

**Completed phases 11.25–23.7** — see `docs/TODO-completed.md` for details (use jDocMunch `search_sections`).
**Next:** Phase 24.2 (Yjs CRDT Document Engine).

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
