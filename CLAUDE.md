# CLAUDE.md

## Project Overview

Centralised email platform with AI agents. FastAPI backend, Next.js 16 frontend, PostgreSQL + Redis. Python 3.12+, strict MyPy + Pyright. **Vertical slice architecture** — features under `app/{feature}/`.

## Essential Commands

```bash
make dev             # Backend (:8891) + frontend (:3000)
make check           # All checks (lint + types + tests + security + golden conformance)
make check-full      # All checks + migration lint
make golden-conformance  # Golden template conformance gate (design_sync)
make test            # Backend unit tests
make bench           # Performance benchmarks (CSS pipeline)
make lint            # Format + lint (ruff — 26 rule sets)
make lint-fe         # Format + lint frontend (ESLint + Prettier)
make types           # mypy + pyright (both strict)
make check-fe        # Frontend lint + format + type-check + tests
make security-check  # Ruff Bandit security rules
make lint-numeric    # Falsy-numeric anti-pattern check (design_sync)
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

Phases 0–36 complete. Phase 37 (golden reference library) in progress — 37.1 done (14 golden reference templates in `email-templates/components/golden-references/`: VML/MSO, dark mode, accessibility, ESP tokens for Braze/SFMC/Adobe Campaign/Klaviyo, innovation CSS carousel/accordion/AMP/kinetic hover). 37.2 done (`app/ai/agents/evals/golden_references.py` — YAML-indexed loader with `get_references_for_criterion()` and `get_references_for_agent()`, 80-line snippet cap, `@lru_cache`, path traversal prevention, 18 tests). Phase 38 (pipeline fidelity fix) complete — all 8 subtasks done. Phase 39 (pipeline hardening) complete — all 7 subtasks done. 39.1 Figma API enrichment, 39.2 testing infrastructure, 39.3 dual MJML path eliminated, 39.4 automated quality contracts, 39.5 custom lint rules, 39.6 component matcher improvements (`_score_candidates()` multi-candidate scoring, 3 new component types product-grid/category-nav/image-gallery, slot fill validation, `match_confidences` on `ConversionResult`), 39.7 golden template conformance gate. See `TODO.md` for summary. See `docs/TODO-completed.md` for detailed completion records.

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
