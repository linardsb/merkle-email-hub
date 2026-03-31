# CLAUDE.md

## Project Overview

Centralised email platform with AI agents. FastAPI backend, Next.js 16 frontend, PostgreSQL + Redis. Python 3.12+, strict MyPy + Pyright. **Vertical slice architecture** — features under `app/{feature}/`.

## Essential Commands

```bash
make dev             # Backend (:8891) + frontend (:3000)
make check           # All checks (lint + types + tests + security + golden conformance + flag audit)
make check-full      # All checks + migration lint
make golden-conformance  # Golden template conformance gate (design_sync)
make flag-audit      # Feature flag lifecycle audit (warns >90d, errors >180d)
make test            # Backend unit tests
make bench           # Performance benchmarks (CSS pipeline)
make test-collab     # CRDT collaboration tests (convergence + Hypothesis property-based)
make lint            # Format + lint (ruff — 26 rule sets)
make lint-fe         # Format + lint frontend (ESLint + Prettier)
make types           # mypy + pyright (both strict)
make check-fe        # Frontend lint + format + type-check + tests
make security-check  # Ruff Bandit security rules
make lint-numeric    # Falsy-numeric anti-pattern check (design_sync)
make migration-lint  # Squawk PostgreSQL migration safety
make install-hooks   # Install pre-commit hooks (format, lint, security, secrets, commit msg)
make db-migrate      # Run migrations
make db-squash       # Squash migrations to single baseline (destructive, confirmation required)
make eval-full       # Full eval pipeline (requires LLM)
make eval-check      # Eval gate (analysis + regression)
make eval-golden     # CI golden test (deterministic, no LLM)
make eval-qa-coverage # Deterministic micro-judges coverage
make sync-ontology   # Sync ontology YAML → sidecar JSON
make e2e-report      # Open last Playwright HTML report
make e2e-smoke         # Smoke E2E tests (@smoke tagged, Chromium only)
make e2e-all-browsers # E2E tests on all browsers (Chromium + Firefox + WebKit)
make rendering-baselines  # Regenerate visual regression baselines
make rendering-regression # Run visual regression tests vs baselines
make snapshot-test        # Snapshot regression tests (included in make test; standalone convenience)
make snapshot-capture CASE=5  # Capture converter output for visual review
make snapshot-visual      # Visual fidelity metrics (requires Playwright, separate from CI)
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

Phases 0–36 complete. Phase 37 (golden reference library) complete — 37.1 done (14 golden reference templates). 37.2 done (YAML-indexed loader, 18 tests). 37.3 done (golden references wired into all 7 judge prompts, 22 tests). 37.4 done (re-run against file-based component output from 40.7, verdict comparison, 21/45 criteria flagged >20% flip rate). 37.5 done (540 rows human-labeled, calibration validated TPR ≥ 0.85 / TNR ≥ 0.80). Phase 38 (pipeline fidelity fix) complete — all 8 subtasks done. Phase 39 (pipeline hardening) complete — all 7 subtasks done. 39.1 Figma API enrichment, 39.2 testing infrastructure, 39.3 dual MJML path eliminated, 39.4 automated quality contracts, 39.5 custom lint rules, 39.6 component matcher improvements (`_score_candidates()` multi-candidate scoring, 3 new component types product-grid/category-nav/image-gallery, slot fill validation, `match_confidences` on `ConversionResult`), 39.7 golden template conformance gate. Phase 40 (converter snapshot regression testing) complete — all 7 subtasks done. 40.1 snapshot infrastructure, 40.2 3 active cases (MAAP 9/13, Starbucks 5/9, Mammut 12/18; approach B), 40.3 Figma design screenshot capture (`_capture_design_image()`, 13 tests), 40.4 Playwright visual regression (`test_snapshot_visual.py` — converter + reference fidelity vs `design.png`, ODiff pixel diff, HTTP server for images, Pillow resize for dimension mismatch, `visual_report.json` per case, `visual_threshold` in manifest), 40.5 CI gate, 40.6 image frame export (16 tests), 40.7 unified component resolution (89 components). Phase 41 (converter background color continuity + VLM classification) planned — Track A: image edge color sampler, adjacent-section bgcolor propagation, text color inversion for dark backgrounds, snapshot regression cases. Track B: batch frame screenshot export service, VLM-assisted component matcher fallback for ambiguous sections, VLM-assisted section type classification (hybrid rule + VLM merge in `analyze_layout()`, `VLMSectionClassifier` in `vlm_classifier.py`, `DESIGN_SYNC__VLM_CLASSIFICATION_ENABLED`). Tracks A and B independent. Phase 43 (judge feedback loop) planned — auto-generate correction examples from calibration disagreements, inject into judge prompts, judge skill files for domain knowledge, Knowledge agent integration, calibration regression gate. Unblocked (37.5 complete). Phase 44 (workflow hardening & operational maturity) 9/12 done — 44.1 E2E smoke CI, 44.2 Renovate, 44.3 feature flag lifecycle, 44.5 operational runbooks, 44.6 migration squash, 44.7 CRDT tests, 44.8 SDK drift detection, 44.9 observability stack (Grafana+Loki+Promtail), 44.10 contributing guide all complete. Remaining: 44.4 adversarial eval pass (depends on eval pipeline Phases 37-43), 44.11 prompt injection detection for agent inputs, 44.12 PII redaction in logs/eval traces. Phase 45 (scheduling, notifications & build debounce) planned — cron scheduling engine (Redis-backed), scheduled QA sweeps, ontology sync & rendering baseline jobs, notification channel abstraction (Slack/Teams/Email), workflow event notifications, build & webhook debounce layer for CRDT collaboration. Phase 46 (provider resilience & connector extensibility) planned — credential pool with rotation and cooldowns (Redis-backed), LLM provider key rotation, ESP connector key rotation, credential health dashboard, dynamic ESP connector discovery via existing plugin system. Phase 47 (VLM visual verification loop & component library expansion) planned — Track A: visual verify loop (section-level screenshot cropping, VLM section-by-section comparison with ODiff pre-filter, deterministic correction applicator, render→compare→correct iteration loop with convergence detection, `DESIGN_SYNC__VLM_VERIFY_ENABLED`). Track B: component library expansion (89→150+ components — countdown timers, testimonials, pricing tables, zigzag layouts, etc.) + extended matcher scoring + AI custom component generation via Scaffolder for unmatched sections (`DESIGN_SYNC__CUSTOM_COMPONENT_ENABLED`). Track C: diagnostic trace enhancement. Fidelity ladder: Phase 40 ~85% → Phase 41 ~93% → Phase 47 verify loop ~97% → Phase 47 component expansion ~99%. See `docs/TODO-completed.md` for detailed completion records.

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
