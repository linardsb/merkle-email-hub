# CLAUDE.md

## Project Overview

Centralised email platform with AI agents. FastAPI backend, Next.js 16 frontend, PostgreSQL + Redis. Python 3.12+, strict MyPy + Pyright. **Vertical slice architecture** — features under `app/{feature}/`.

## Essential Commands

```bash
make dev             # Backend (:8891) + frontend (:3000)
make check           # All checks (lint + types + tests + security)
make test            # Backend unit tests
make bench           # Performance benchmarks (CSS pipeline)
make lint            # Format + lint (ruff)
make types           # mypy + pyright
make check-fe        # Frontend type-check + unit tests
make db-migrate      # Run migrations
make eval-full       # Full eval pipeline (requires LLM)
make eval-check      # Eval gate (analysis + regression)
make eval-golden     # CI golden test (deterministic, no LLM)
make eval-qa-coverage # Deterministic micro-judges coverage
make sync-ontology   # Sync ontology YAML → sidecar JSON
```

## Token-Efficient Research (MCP Tools)

**jDocMunch** (repo: `local/merkle-email-hub`) — for docs >200 lines (TODO.md, PRD.md, etc.):
- `search_sections(repo, query, doc_path)` → find sections by keyword
- `get_section(repo, section_id)` → read one section (~400t vs 25k for full file)
- `index_local(path, incremental=true, use_ai_summaries=false)` → re-index after big changes
- **NEVER** `get_document_outline` on large docs. **NEVER** `Read` TODO.md/PRD.md in full.

**jCodeMunch** (repo: `local/merkle-email-hub-0ddab3c4`) — for cross-file code research:
- `search_symbols(repo, query, kind, file_pattern)` → find functions/classes/methods
- `find_references(repo, symbol_name)` → find all usages across codebase
- `get_file_outline(repo, file_path)` → file structure without reading full content
- `get_symbol(repo, symbol_name)` → get specific symbol's code
- `index_folder(path, incremental=true, use_ai_summaries=false)` → re-index after big changes

**When to use what:**
| Task | Tool |
|------|------|
| Read docs >200 lines | jDocMunch `search_sections` → `get_section` |
| Read docs <200 lines | `Read` directly |
| "Which files use X?" | jCodeMunch `search_symbols` / `find_references` |
| "What's in this dir?" | jCodeMunch `get_file_tree(repo, path_prefix=...)` |
| "Show me this function" (to edit) | `Read` the file |
| Find exact string | `Grep` |

## Development Guidelines

**Feature file order:** schemas → models → repository → service → exceptions → routes → tests

**Layers:** Routes (thin HTTP) → Service (business logic) → Repository (DB only). Exceptions inherit `AppError`.

**Key imports:** `get_logger` from `app.core.logging`, `get_db` from `app.core.database`, `TimestampMixin` from `app.shared.models`, `escape_like` from `app.shared.utils`. Roles: admin, developer, viewer.

**Config:** Nested Pydantic settings, `env_nested_delimiter="__"` (e.g. `DATABASE__URL`, `AI__PROVIDER`).

## Architecture

Backend: `app/` (VSA features) — `core/`, `shared/`, `auth/`, `ai/` (agents + blueprints + evals + voice + `skills/` automatic skill extraction from templates with `SKILL_EXTRACTION__ENABLED` + multi-variant campaign assembly via `scaffolder/variant_generator.py` with `VARIANTS__ENABLED`), `knowledge/`, `qa_engine/` (14 core checks including per-build CSS compatibility audit + ISP-aware deliverability intelligence + optional resilience check + plugin QA checks), `projects/`, `email_engine/` (CSS compiler with `optimize_css()` for standalone API + precompilation — ontology-driven elimination, conversions, Lightning CSS minification; `MaizzleBuildNode` passes `target_clients` to sidecar for consolidated CSS optimize→build→sanitize; `TemplatePrecompiler` pre-compiles CSS at template registration, marker-based skip at build time), `components/`, `connectors/` (ESP sync + `tolgee/` TMS integration with `TOLGEE__ENABLED`), `approval/`, `personas/`, `memory/`, `rendering/`, `design_sync/` (Figma + `penpot/` provider with CSS-to-email converter, `DESIGN_SYNC__PENPOT_ENABLED`), `streaming/` (data streaming + `websocket/` collab WS with room-based routing, Redis pub/sub bridge, JWT auth + `crdt/` Yjs CRDT document engine with pycrdt persistence, sync protocol, inline compaction), `mcp/` (MCP tool server — 17 tools, streamable HTTP + stdio), `plugins/` (plugin manifest/discovery/loader/registry/API with admin endpoints + sandbox execution with timeout/error isolation + lifecycle manager with health monitoring/auto-disable, `PLUGINS__ENABLED`), `workflows/` (Kestra workflow orchestration — client, service, 6 task wrappers, 4 YAML flow templates, `KESTRA__ENABLED`), `reporting/` (Typst PDF report generation — QA reports, approval packages, regression reports with Redis caching, `REPORTING__ENABLED`), `templates/upload/` (self-serve HTML template upload pipeline — static analysis, slot/token extraction, eval generation, knowledge injection, `TEMPLATES__UPLOAD_ENABLED`). Frontend: `cms/` (`components/builder/` — visual email builder with DnD component palette, sortable canvas, sandboxed preview, undo/redo; `components/builder/panels/` — property panel right sidebar with Content/Style/Responsive/Advanced tabs, palette-restricted color picker, slot editors driven by `slotDefinitions`, design system token overrides, responsive toggles, MSO conditional, HTML attribute editor with security validation; `components/collaboration/` — presence panel, collaboration banner, conflict resolver, remote cursor styles; `hooks/use-builder.ts` — builder state reducer + structure-preserving HTML assembler with slot fill application, 13-token CSS override system, dark mode CSS generation, MSO ghost table wrapping, scoped section CSS, HTML attribute injection, URI/CSS/selector sanitization; `lib/builder-sync/` — bidirectional code↔builder sync: `ast-mapper.ts` HTML parser with ESP token preservation (Liquid/Handlebars/AMPscript/ERB), structural ESP internalization (conditionals moved from around `<tr>` into `<td>` cells), dynamic column group detection, `parseInlineStyle` quote-aware CSS parser; `sync-engine.ts` debounced sync with conflict resolution (builder wins); `section-markers.ts` annotation strip/detect; `annotation-utils.ts` section merge/split/unwrap/rename; `hooks/use-presence.ts` — awareness state + follow mode; `hooks/use-tolgee.ts` — SWR hooks for Tolgee TMS (connection, languages, sync, pull, locale build); `components/tolgee/` — translation key panel, side-by-side locale preview, per-locale QA matrix, in-context translation overlay, connection dialog; `types/design-system-config.ts` — DesignSystemConfig + palette swatch extraction; `components/ecosystem/` — unified ecosystem dashboard with tab navigation (overview quadrants, plugin manager with admin enable/disable/restart, workflow execution panel with Gantt timeline + trigger dialog + log viewer, report generator with session-persisted history + PDF preview, Penpot connection browser); SWR hooks (`use-plugins`, `use-workflows`, `use-reports`, `use-penpot`); types (`plugins`, `workflows`, `reports`, `ecosystem`); route at `/ecosystem` with all-role RBAC; `components/rendering/` — pre-send rendering gate panel with traffic-light verdict badge, per-client confidence bars, admin override + rendering dashboard with preview grid (14 client profiles), confidence summary bar, calibration health panel (admin-only), full-size preview dialog; `hooks/use-rendering-gate.ts` — SWR hooks for gate evaluate + config; `hooks/use-rendering-dashboard.ts` — SWR hooks for screenshots with confidence, calibration summary/history, trigger calibration; `types/rendering-dashboard.ts` — dashboard types; wired into export dialog + push-to-ESP dialog; Dashboard tab on `/renderings` page). Sidecars: `services/maizzle-builder/` (Maizzle build + consolidated CSS pipeline — `postcss-email-optimize.js` PostCSS plugin with ontology-driven elimination/conversion, Lightning CSS minification, `target_clients` param, `optimization` response metadata; `scripts/sync-ontology.js` YAML→JSON ontology sync), `services/mock-esp/` (mock ESP APIs, port 3002). Migrations: `alembic/`.

**Engine Taxonomy:** `OntologyRegistry` has engine-level query methods (`clients_by_engine`, `engine_support`, `engines_not_supporting`, `engine_market_share`). `CssSupportCheck` includes engine-level summary in output.

**Per-Agent Sanitization:** `sanitize_html_xss(html, profile=)` applies agent-specific nh3 allowlists. 10 profiles in `app/ai/shared.py`. `BaseAgentService.sanitization_profile` class attribute wires into `_post_process()`.

**Email Client Emulators:** `app/rendering/local/emulators.py` — 8 email client sanitizer emulators (Gmail Web, Outlook.com, Yahoo Web, Yahoo Mobile, Samsung Mail, Outlook Desktop/Word, Thunderbird, Android Gmail) with 14 rendering profiles in `profiles.py`. `EmulatorRule` chain-of-rules pattern with `confidence_impact` field. Integrated via `RenderingProfile.emulator_id`.

**Rendering Confidence Scoring:** `app/rendering/local/confidence.py` — `RenderingConfidenceScorer` computes per-client confidence (0–100) from 4 signals: emulator rule coverage (0.25), CSS compatibility via ontology (0.25), calibration accuracy from seeds (0.35), layout complexity penalty (0.15). `confidence_seeds.yaml` holds per-emulator accuracy seeds. Scores attached to `ScreenshotClientResult` response + stored in `RenderingScreenshot` model. `GET /confidence/{client_id}` endpoint (async, DB-first seed lookup). Feature-flagged via `RENDERING__CONFIDENCE_ENABLED`.

**Emulator Calibration Loop:** `app/rendering/calibration/` — `EmulatorCalibrator` compares local emulator screenshots against external provider ground truth (Litmus/EoA/sandbox) via ODiff. `CalibrationRecord` + `CalibrationSummary` models with EMA-smoothed accuracy (`alpha=0.3`). `CalibrationSampler` rate-limits calibrations per client per day with 3x boost for new emulators, 2x for stale. DB-first seed lookup in `RenderingConfidenceScorer.get_seed_with_db()` replaces YAML seeds once calibration data exists. Endpoints: `GET /calibration/summary`, `POST /calibration/trigger` (admin), `GET /calibration/history/{client_id}`. Feature-flagged via `RENDERING__CALIBRATION__ENABLED`.

**Headless Email Sandbox:** `app/rendering/sandbox/` — SMTP-based real sanitizer capture. Sends email via `aiosmtplib` to Mailpit, captures post-sanitizer DOM, computes structural `DOMDiff` (removed elements/attributes/CSS properties, modified styles). `SandboxProfile` registry (mailpit, roundcube). Playwright-based webmail capture for Roundcube. Docker Compose `sandbox` profile for Mailpit + Roundcube. Admin-only endpoints: `POST /sandbox/test`, `GET /sandbox/health`. Feature-flagged via `RENDERING__SANDBOX__ENABLED`.

**Progressive Enhancement:** `TemplateAssembler` Step 11 applies `tier_strategy="progressive"` — wraps modern CSS in MSO conditionals with Word-engine fallback.

## Roadmap

See `TODO.md` for details on upcoming phases. See `docs/TODO-completed.md` for detailed completion records of phases 0-27.

**Upcoming phases (priority order — highest differentiation first):**
- ~~**Phase 26**~~ — Email Build Pipeline Performance & CSS Optimization — **ALL DONE** (5/5 subtasks — optimize_css pre-build pipeline, per-build CSS audit, template precompilation, consolidated sidecar CSS pipeline, tests & benchmarks)
- ~~**Phase 27**~~ — Email Client Rendering Fidelity & Pre-Send Testing — **ALL DONE** (6/6 subtasks — 27.1 expand emulators, 27.2 rendering confidence scoring, 27.3 pre-send rendering gate, 27.4 emulator calibration loop, 27.5 headless email sandbox, 27.6 frontend rendering dashboard & tests)

**Completed phases 0–27** — see `docs/TODO-completed.md` for details (use jDocMunch `search_sections`).

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
