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

Backend: `app/` (VSA features) — `core/`, `shared/`, `auth/`, `ai/` (agents + blueprints + evals), `knowledge/`, `qa_engine/` (11 checks), `projects/`, `email_engine/`, `components/`, `connectors/`, `approval/`, `personas/`, `memory/`, `rendering/`, `design_sync/`, `streaming/`. Frontend: `cms/`. Sidecars: `services/maizzle-builder/`, `services/mock-esp/` (mock ESP APIs, port 3002). Migrations: `alembic/`.

## Roadmap

See `TODO.md` for details. Completed: phases 0-12, 13.1-13.10 (including 11.22 template-first architecture — all 9 subtasks, 11.23 inline judges, 11.24 production trace sampling, 11.25 design system & brand pipeline, 12.1-12.9 design-to-email import pipeline, 13.1-13.9 ESP bidirectional sync backend + mock server, 13.10 frontend ESP sync UI).

**Completed:** **11.25** client design system & template customisation — all 5 subtasks done (11.25.1 design system model, 11.25.2 component→section bridge, 11.25.3 project-scoped template registry, 11.25.4 agent pipeline constraint injection — design system as generation constraints with role-based token mapping + locked fills + brand color sweep, 11.25.5 consistency enforcement — `BrandRepair` stage 8 in repair pipeline + e2e brand enforcement tests). **12.1** protocol extension + Figma API integration (file structure, components, image export — 3 new protocol methods + Figma implementation + schemas + routes). **12.2** asset storage pipeline (`DesignAssetService` — download, resize ≤1200px, local storage, authenticated serving with CSP headers, cascade delete on connection removal). **12.3** design import models & migration (`DesignImport` + `DesignImportAsset` models, 6-state workflow, nullable `result_template_id` FK, repository CRUD, Alembic migration, Pydantic schemas). **12.4** layout analyzer & brief generator (`LayoutAnalyzer` pure-function section detection + `BriefGenerator` markdown output, 2 new endpoints: `POST /analyze-layout`, `POST /generate-brief`). **12.5** AI-assisted conversion pipeline (`DesignImportService` orchestrator with own DB session via `get_db_context`, two-phase UX: create import with brief → trigger conversion, `DesignContextSchema` for Scaffolder with image URLs + layout + tokens, `build_design_context_section()` prompt injection, 4 new endpoints: `POST /imports`, `GET /imports/{id}`, `PATCH /imports/{id}/brief`, `POST /imports/{id}/convert` 202 Accepted, atomic Template+TemplateVersion creation, state machine validation, 24 tests). **12.6** component extraction (`ComponentExtractor` — Figma components → Hub Component + ComponentVersion with Scaffolder-generated HTML, category detection, duplicate handling via Figma origin in `compatibility` JSON, background job via `asyncio.create_task`, `POST /connections/{id}/extract-components` 202 Accepted). **12.7** frontend file browser & import dialog (recursive `DesignFileBrowser` tree with thumbnails + checkbox selection, tabbed `DesignImportDialog` with 4-step Import Design wizard and 3-step Extract Components wizard, 8 new SWR hooks, `/figma` consolidated into `/design-sync`, 44 i18n keys across 6 locales). **12.8** design reference panel in workspace (right sidebar with `DesignReferencePanel` — auto-detect design import by template via `GET /imports/by-template/{id}`, manual connection picker fallback, `AssetViewer` image gallery, `TokenDisplay` with 10 token interactions: insert-at-cursor, find-and-highlight, replace-in-selection, copy-as-formats context menu, usage heatmap badges, drag-and-drop to editor, off-brand color auto-correct, CSS variables generator, hover spotlight, Tailwind utility copy; `useEditorBridge` hook with `highlightField` CodeMirror extension, `CodeEditor` forwardRef, i18n across 6 locales). **12.9** SDK regeneration & full test suite (TypeScript SDK regenerated via `@hey-api/openapi-ts` covering all 17 design-sync endpoints, 36 route tests for every endpoint + auth/role enforcement, 178 total design_sync tests, `make check` all green). **13.1–13.6** mock ESP server (`services/mock-esp/` — standalone FastAPI sidecar with SQLite, 4 ESP API surfaces: Braze Content Blocks, SFMC Content Builder, Adobe Campaign Delivery, Taxi Templates; per-ESP auth patterns; 44 seeded templates with ESP-specific personalization syntax). **13.7** ESP sync protocol, model & migration (`ESPSyncProvider` Protocol, `ESPConnection` model with Fernet-encrypted credentials, BOLA-safe repository, `ESPSyncConfig` registered on Settings, Alembic migration). **13.8** per-ESP sync providers (4 `httpx.AsyncClient` implementations: `BrazeSyncProvider`, `SFMCSyncProvider`, `AdobeSyncProvider`, `TaxiSyncProvider`). **13.9** sync service & routes (`ConnectorSyncService` — credential validation, encrypted storage, BOLA, template import/push; 8 REST endpoints at `/api/v1/connectors/sync/` with auth + rate limiting). **13.10** frontend ESP sync UI (2-tab connectors page Export History | ESP Sync, 7 new components: `ESPConnectionCard`, `CreateESPConnectionDialog` with dynamic credential fields per provider, `ESPTemplateBrowser` with search, `ESPTemplatePreviewDialog` with sandboxed iframe, `PushToESPDialog`; 8 SWR hooks in `use-esp-sync.ts`; "Push to ESP" button in workspace toolbar; 65 i18n keys across 6 locales; `make check-fe` green). **Next:** 13.11 (tests, SDK regen, Docker integration).

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
