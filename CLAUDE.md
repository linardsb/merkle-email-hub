# CLAUDE.md

## Project Overview

Centralised email platform with AI agents. FastAPI backend, Next.js 16 frontend, PostgreSQL + Redis. Python 3.12+, strict MyPy + Pyright. **Vertical slice architecture** — features under `app/{feature}/`.

## Essential Commands

```bash
make dev             # Backend (:8891) + frontend (:3000)
make check           # All checks (lint + types + tests + security)
make check-full      # All checks + migration lint
make test            # Backend unit tests
make bench           # Performance benchmarks (CSS pipeline)
make lint            # Format + lint (ruff — 26 rule sets)
make lint-fe         # Format + lint frontend (ESLint + Prettier)
make types           # mypy + pyright (both strict)
make check-fe        # Frontend lint + format + type-check + tests
make security-check  # Ruff Bandit security rules
make migration-lint  # Squawk PostgreSQL migration safety
make install-hooks   # Install pre-commit hooks (format, lint, security, secrets, commit msg)
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

## Known Environment Issues

- External processes (linters, background agents, git hooks) may silently revert file edits. After writing/editing files, verify changes persisted before moving on. If changes disappear, re-apply and identify the reverting process.

## Linter Safety

- Ruff TCH auto-fix breaks runtime imports (SQLAlchemy, Pydantic, datetime). Never run `ruff --fix` with TCH rules enabled. Use `--no-fix` for TCH or exclude them entirely.

## Parallel Work Awareness

- Before committing, check `git diff` carefully for changes from other branches or uncommitted parallel work leaking into the current diff. Isolate only the changes relevant to the current phase/task.

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

**Phase 33** (Design Token Pipeline Refactor — continues Phase 31.5–31.6) — refactor existing `converter.py`/`converter_service.py` to use rich layout data Phase 31.6 already extracts but converter ignores. **33.0 DONE** (layout analyzer wired into converter, `_build_props_map_from_nodes()` extracts all fields, MSO reset styles on tables/images/skeleton, `ConversionResult.layout`, dynamic container width, inter-section spacers, nesting depth guard). **33.1 DONE** (Figma Variables API with alias resolution + depth guard, `_rgba_to_hex_with_opacity()` alpha compositing, gradient midpoint extraction, stroke/fill separation, `ExtractedVariable` dataclass, `ExtractedTokens` extended with `variables_source`/`modes`/`stroke_colors`/`variables`). **33.2 DONE** (`token_transforms.py` — `validate_and_transform()` between extraction and consumption, 148-entry CSS named-color map, hex/rgba/hsl normalization, opacity clamping, typography weight snapping + unitless line-height conversion, spacing bounds, deduplication, `TokenWarning` dataclass, warnings surfaced in `DesignTokensResponse`, integrated into `sync_connection()` + `run_conversion()`). **33.5b DONE** (`compatibility.py` — `ConverterCompatibility` ontology facade for converter, `CompatibilityHint` dataclass, `check_and_warn()` convenience method, client-aware token warnings in `validate_and_transform()`, `target_clients` threaded through `converter_service.py`/`import_service.py`/`service.py`, `CompatibilityHintResponse` schema, hints stored in snapshot + surfaced in `DesignTokensResponse`). **33.3 DONE** (typography pipeline — line-height unitless conversion, letter-spacing email-safe clamping, font-family mapping with email-safe fallback stacks). **33.4 DONE** (spacing token pipeline — `convert_spacing()` named scale mapping, padding moved from `<table>` to `<td>` wrapper for Outlook safety, layout-mode-aware row grouping HORIZONTAL→single `<tr>` / VERTICAL→stacked `<tr>`s / fallback→y-position, vertical spacer rows with `font-size:1px;line-height:1px;mso-line-height-rule:exactly`, horizontal gaps via `padding-left` on cells 2+, `item_spacing`/`counter_axis_spacing` extracted in `_build_props_map_from_nodes()`, spacing tokens wired into Scaffolder design context via `convert_spacing()`, `fetch_target_clients()` shared helper). **33.5 DONE** (multi-column layout — `_calculate_column_widths()` proportional/equal/mixed width distribution with gap subtraction and rounding absorption, `_render_multi_column_row()` hybrid `display:inline-block` + MSO ghost table pattern with `cellpadding="0" cellspacing="0"` and `mso-table-lspace:0pt;mso-table-rspace:0pt`, MSO spacer `<td>` for inter-column gaps, `container_width` threaded from `converter_service.py` through all recursive calls, `_group_into_rows()` tolerance increased to 20px + y=None partitioning for auto-layout nodes, compatibility warning for `display:inline-block`). **33.6 DONE** (semantic HTML generation — `_determine_heading_level()` font-size-ratio→h1/h2/h3, `_render_semantic_text()` wraps TEXT in `<h1>`–`<h3>` or `<p style="margin:0 0 10px 0;">` inside `<td>`, multi-line TEXT→multiple `<p>` tags, `_render_button()` bulletproof `<a>` with VML `<v:roundrect>` fallback for Outlook, `_validate_button_contrast()` WCAG AA warning, 44px min touch target, `body_font_size` from `convert_typography()` threaded through `converter_service.py`). **33.7 DONE** (dark mode token extraction & gradient fallbacks — `ExtractedGradient` dataclass with frozen tuple stops, dark mode variable detection from Figma Variables API modes (dark/night/dim patterns), `_compute_gradient_angle()` + `_parse_gradient_stops()` for full gradient data, `_validate_gradient()` angle clamping + stop hex validation, `_apply_magic_colors()` #000→#010101/#FFF→#FEFEFE for Outlook dark mode safety, `_validate_dark_mode_contrast()` WCAG AA 4.5:1 check, `_gradient_to_css()` with `_sanitize_css_value()` on stops, `gradients_map` threaded through `node_to_email_html()` + `_render_multi_column_row()`, `dark_mode_style_block()` 3-tier CSS — `@media (prefers-color-scheme: dark)` with `!important` + `[data-ogsc]`/`[data-ogsb]` for Outlook.com, `dark_mode_meta_tags()` `color-scheme` + `supported-color-schemes`, `DesignGradientResponse`/`DesignGradientStopResponse` schemas, `dark_colors`/`gradients` in `DesignTokensResponse` + design context + snapshot JSON, 23 tests). **33.8 DONE** (design context enrichment & Scaffolder integration — `_build_design_context()` now includes `line_height`/`letter_spacing`/`text_transform` in typography entries + `token_warnings`, `_tokens_to_protocol()` preserves `letter_spacing`/`text_transform`/`text_decoration`, `_layout_to_design_nodes()` creates TEXT children from `section.texts` with full typography + section `height`/`width`/`item_spacing`, `TextBlockResponse` extended with `font_family`/`font_weight`/`line_height`/`letter_spacing`, `get_previous_snapshot()` repository method, `TokenDiffEntry`/`TokenDiffResponse` schemas with `Literal` change type, `get_token_diff()` service + `_compute_token_diff()` static diff engine, `GET /connections/{id}/tokens/diff` endpoint with auth + rate limit, frontend `DesignTokens` type extended with `dark_colors`/`gradients`/`warnings`/`compatibility_hints`, `useTokenDiff` hook, `DesignTokensView` shows dark mode swatches + gradient previews + token warnings + diff badges + enriched typography details, 8 new tests (467 design_sync total)). **33.9 DONE** (builder annotations for visual builder sync — `_next_slot_name()` dedup helper for unique slot IDs per section, `slot_counter: dict[str, int]` threaded through `node_to_email_html()`/`_render_semantic_text()`/`_render_button()`/`_render_multi_column_row()`, `data-slot-name` on headings/body `<p>`/images/CTA `<a>` tags, `data-component-name` with `html.escape()` on section root `<table>`, `data-section-id="section_{idx}"` on `<tr>` wrapper in `converter_service.py`, backward compatible when `slot_counter=None`, 15 new tests (498 design_sync total)). **33.10 DONE** (image asset import for design sync pipeline — `max-width:{w}px` responsive style on IMAGE nodes, `ConversionResult.images` field for image metadata, `converter_image_urls` extraction + `_fill_image_urls()` wiring verified in `import_service.py`, image metadata persisted in `structure_json["images"]` via `dataclasses.replace()` on frozen `ConversionResult`, `ImportedImageResponse` schema, 16 new tests (514 design_sync total)). Remaining: tests (33.11). 1 subtask remaining. **Next — independent of Phase 32, recommended to start first (upstream fixes).**

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
