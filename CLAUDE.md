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
make e2e-report      # Open last Playwright HTML report
make e2e-all-browsers # E2E tests on all browsers (Chromium + Firefox + WebKit)
make rendering-baselines  # Regenerate visual regression baselines
make rendering-regression # Run visual regression tests vs baselines
```

## HTML Email Structure Rules

- **Layout:** `<table>/<tr>/<td>` for ALL structural layout. NEVER use `<div>`/`<p>` for layout (width, flex, float, columns).
- **Text content:** Use `<p style="margin:0 0 10px 0;">` inside `<td>` cells — better for accessibility than bare text (screen readers navigate by paragraphs).
- **Headings:** Use `<h1>`-`<h6>` with inline styles inside `<td>` cells. Screen readers scan by headings.
- **Simple wrappers:** `<div style="text-align:center;">` inside `<td>` is fine. No layout CSS (width/flex/float) on div/p.
- **MSO conditionals:** Ghost table pattern for Outlook. `<div>` inside `<!--[if mso]>` blocks is expected.
- **Spacing:** `padding` on `<td>` only (universal safe combo). `margin:0` reset on every `<p>` and heading.
- **Sanitizer:** `sanitize_web_tags_for_email()` in `app/design_sync/converter.py` — preserves `<p>` inside `<td>`, strips layout divs, preserves MSO blocks.
- See `.agents/plans/upgrade-design-sync-html-generation.md` for the full plan.

## Development Guidelines

**Key imports:** `get_logger` from `app.core.logging`, `get_db` from `app.core.database`, `TimestampMixin` from `app.shared.models`, `escape_like` from `app.shared.utils`. Roles: admin, developer, viewer.

**Config:** Nested Pydantic settings, `env_nested_delimiter="__"` (e.g. `DATABASE__URL`, `AI__PROVIDER`).

**Plans:** Implementation plans in `.agents/plans/` must not exceed 700 lines. Use compact descriptions, tables, and `file:line` references — not full code blocks.

## Architecture

Backend: `app/` (VSA features). Frontend: `cms/`. Sidecars: `services/maizzle-builder/`, `services/mock-esp/`. Migrations: `alembic/`.

**9 AI Agents:** Scaffolder, Dark Mode, Content, Outlook Fixer, Accessibility, Personalisation, Code Reviewer, Knowledge, Innovation. All have 5-criteria judges + SKILL.md files. Structured output mode returns decision schemas merged via `plan_merger.py`.

**Per-Agent Sanitization:** `sanitize_html_xss(html, profile=)` applies agent-specific nh3 allowlists. 10 profiles in `app/ai/shared.py`.

For full architecture details see `.claude/docs/architecture-deep-dive.md`. For architecture quick-reference see `.claude/rules/architecture.md`.

## Roadmap

See `TODO.md` for details. See `docs/TODO-completed.md` for completed phases 0-30.

Phases 0–31 complete. **Phase 31** (HTML Import Fidelity & Preview Accuracy) **ALL DONE** (8/8 subtasks — Maizzle passthrough, CSS ontology pipeline, wrapper metadata capture, wrapper reconstruction, dark mode text safety & sandbox fix, enriched typography & spacing token pipeline, image asset import & dimension preservation, tests & integration verification).

**Phase 32** (Agent Email Rendering Intelligence) — centralized client matrix, agent knowledge lookup, content rendering awareness, import annotator depth, cross-agent learning, eval-driven skill updates, visual QA feedback loop. **Next — independent of Phase 33.**

**Phase 33** (Design Token Pipeline Refactor — continues Phase 31.5–31.6) — refactor existing `converter.py`/`converter_service.py` to use rich layout data Phase 31.6 already extracts but converter ignores. **33.0 DONE** (layout analyzer wired into converter, `_build_props_map_from_nodes()` extracts all fields, MSO reset styles on tables/images/skeleton, `ConversionResult.layout`, dynamic container width, inter-section spacers, nesting depth guard). **33.1 DONE** (Figma Variables API with alias resolution + depth guard, `_rgba_to_hex_with_opacity()` alpha compositing, gradient midpoint extraction, stroke/fill separation, `ExtractedVariable` dataclass, `ExtractedTokens` extended with `variables_source`/`modes`/`stroke_colors`/`variables`). **33.2 DONE** (`token_transforms.py` — `validate_and_transform()` between extraction and consumption, 148-entry CSS named-color map, hex/rgba/hsl normalization, opacity clamping, typography weight snapping + unitless line-height conversion, spacing bounds, deduplication, `TokenWarning` dataclass, warnings surfaced in `DesignTokensResponse`, integrated into `sync_connection()` + `run_conversion()`). **33.5b DONE** (`compatibility.py` — `ConverterCompatibility` ontology facade for converter, `CompatibilityHint` dataclass, `check_and_warn()` convenience method, client-aware token warnings in `validate_and_transform()`, `target_clients` threaded through `converter_service.py`/`import_service.py`/`service.py`, `CompatibilityHintResponse` schema, hints stored in snapshot + surfaced in `DesignTokensResponse`). **33.3 DONE** (typography pipeline — line-height unitless conversion, letter-spacing email-safe clamping, font-family mapping with email-safe fallback stacks). **33.4 DONE** (spacing token pipeline — `convert_spacing()` named scale mapping, padding moved from `<table>` to `<td>` wrapper for Outlook safety, layout-mode-aware row grouping HORIZONTAL→single `<tr>` / VERTICAL→stacked `<tr>`s / fallback→y-position, vertical spacer rows with `font-size:1px;line-height:1px;mso-line-height-rule:exactly`, horizontal gaps via `padding-left` on cells 2+, `item_spacing`/`counter_axis_spacing` extracted in `_build_props_map_from_nodes()`, spacing tokens wired into Scaffolder design context via `convert_spacing()`, `fetch_target_clients()` shared helper). Remaining: multi-column widths (33.5), semantic HTML (33.6), dark mode extraction (33.7), Scaffolder integration (33.8), builder annotations (33.9), image assets (33.10), tests (33.11). 7 subtasks remaining (33.5–33.11), 33.5b prerequisite for 33.7 complete. **Next — independent of Phase 32, recommended to start first (upstream fixes).**

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
