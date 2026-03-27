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

See `TODO.md` for details. See `docs/TODO-completed.md` for completed phases 0-31.

Phases 0–31 complete. **Phase 31** (HTML Import Fidelity & Preview Accuracy) **ALL DONE** (8/8 subtasks). **Phase 33** (Design Token Pipeline Overhaul) **ALL DONE** (12/12 subtasks — layout analyzer wiring, Figma Variables API, token transforms & validation, typography pipeline, spacing pipeline, multi-column layout, client-aware conversion, semantic HTML, dark mode & gradients, design context enrichment, builder annotations, image asset import, tests). See `docs/TODO-completed.md` for detailed completion records.

**Phase 32** (Agent Email Rendering Intelligence) — **32.1 DONE** (Centralized client matrix — `data/email-client-matrix.yaml` with 16 client profiles (engine, CSS support, dark mode, known bugs, size limits), `app/knowledge/client_matrix.py` loader with `ClientMatrix` registry + `@lru_cache` singleton + `Literal`-typed `DarkModeProfile`, `AudienceProfile` enriched with `rendering_engines`/`dark_mode_types`/`vml_required`/`clip_threshold_kb` in `audience_context.py`, 5 agent L3 skill files deduplicated (CSS matrices removed, behavioral guidance kept), `scripts/sync-client-matrix.py` ontology drift detection, 33 new tests). **32.2 DONE** (Content agent email rendering awareness — `content_rendering_constraints.md` L3 skill with per-client preheader/subject/CTA/body constraints, `audience_client_ids` threaded through `ContentRequest`→service→prompt detection, skill triggers for subject_line/preheader/cta ops + audience context, SKILL.md L2 client-aware generation rules, 12 new tests (63 content total)). **32.3 DONE** (Import Annotator skill depth — 4 new L3 skill files in `skills/l3/`: `common_email_builders.md` (Stripo/Bee Free/Mailchimp/MJML/Litmus patterns), `css_normalization.md` (vendor prefixes, `!important` density, duplicate properties), `wrapper_detection.md` (centering/background/preheader wrappers, always loaded), `esp_token_edge_cases.md` (AMPscript nested calls, Mailchimp merge tags `*|MERGE|*`, Handlebars partials, Connected Content), `SKILL_FILES` expanded 4→8, `detect_relevant_skills()` updated with builder/CSS/wrapper/ESP-edge heuristics + `dict.fromkeys()` dedup, SKILL.md references updated, 26 new tests (44 import_annotator total)). **32.4 DONE** (Agent knowledge lookup tool — `app/ai/agents/tools/client_lookup.py` with `ClientLookupTool` (single-client `lookup_client_support` for css_support/dark_mode/known_bugs/size_limits/font_support queries) + `MultiClientLookupTool` (batch `lookup_client_support_batch` for N clients x M properties), `ClientLookupParams`/`ClientLookupResult` Pydantic models, `_execute_single_lookup()` shared logic, `get_tool_definitions()` JSON Schema for LLM function calling, module-level `_VALID_QUERY_TYPES` frozenset + singleton tool instances, structured logging (`agents.client_lookup.query`/`agents.client_lookup.batch_query`), blueprint engine LAYER 11.5 injects both tools into `context.metadata` for all agentic nodes, 6 agent SKILL.md files updated with `## Client Rendering Lookup` L2 section (scaffolder, dark_mode, outlook_fixer, accessibility, code_reviewer, innovation), 26 new tests). **32.5 DONE** (Cross-agent insight propagation — `app/ai/blueprints/insight_bus.py` with `AgentInsight` frozen dataclass + `InsightCategory` Literal type, `extract_insights()` from 3 sources (QA fix patterns via `_QA_CHECK_AGENT_MAP` root-cause attribution, handoff `learnings` field, low-confidence advisory), `persist_insights()` per-target-agent semantic memory with `dedup_hash` metadata + per-item error resilience, `recall_insights()` with over-fetch + dedup-at-recall + evidence_count×similarity ranking, `format_insight_context()` with 800-char cap, LAYER 17 in `engine.py` (agentic + `insight_propagation_enabled` flag + audience-scoped), within-run propagation via `AgentHandoff.learnings` tuple + `upstream_learnings` context injection, `extract_and_store_insights()` post-run hook in `outcome_logger.py` wired through `service.py`, `BlueprintRun.insights_extracted` counter, `BlueprintConfig.insight_propagation_enabled` feature flag, 27 new tests). **32.9 DONE** (MCP server agent tools — `app/mcp/tools/agents.py` with `register_agent_tools()` exposing all 9 agents as MCP tools (`agent_scaffold`, `agent_dark_mode`, `agent_content`, `agent_outlook_fix`, `agent_accessibility`, `agent_code_review`, `agent_personalise`, `agent_innovate`, `agent_knowledge`), each with input validation + size limits + enum checks + lazy imports + `_format_agent_result()` formatter with HTML truncation, `_split_csv()` for comma-separated list params, Knowledge agent wired with `get_db_context()` + `KnowledgeService` for RAG, `hub://agents` resource in `resources.py` with `_AGENT_REGISTRY` (9 entries: name/tool/type/description/accepts/returns), server.py updated with `register_agent_tools(mcp)`, 29 new tests in `test_agent_tools.py` (84 MCP total)). **32.6 DONE** (Eval-driven skill file updates — `app/ai/agents/evals/skill_updater.py` with `SkillUpdateDetector` class (detect_update_candidates from analysis.json pass rates < 0.80 + failure count >= 5, generate_patch via LLM temperature=0.0, apply_patches with git branch automation), `CRITERION_SKILL_MAP` 45-entry dict mapping all 9 agents × 5 criteria to L3 skill files, `SkillUpdateCandidate` + `SkillFilePatch` frozen dataclasses in `schemas.py`, tool usage analytics integration (frequent queries > 10 promoted to L2 SKILL.md candidates), duplicate content detection (70% line overlap threshold), `CalledProcessError` handling with best-effort branch cleanup, `scripts/eval-skill-update.py` CLI (`--dry-run`/`--threshold`/`--min-failures`/`--agent`), `eval-skill-update` + `eval-skill-update-apply` Makefile targets, 35 new tests (223 evals total)). **32.7 DONE** (Visual QA feedback loop tightening — `VisualPrecheckNode` pre-QA VLM screenshot defect detection for top 3 audience clients + `VisualComparisonNode` post-build ODiff + VLM drift scoring vs original design, `VisualQAService.detect_defects_lightweight()` fast-path VLM + `compare_screenshots()` ODiff→VLM, `QAVisualDefect` on `QAResultResponse` + `VisualComparisonResult` on `BuildResponse`, QA gate merges visual precheck `StructuredFailure` items, recovery router dynamic `visual_defect:*` routing with multimodal screenshot injection (Layer 14.5), campaign blueprint wired `repair→visual_precheck→qa_gate` + `maizzle_build→visual_comparison→export`, 4 `BlueprintConfig` feature gates (all default off), 35 new tests). **32.11 DONE** (Per-client skill overlays — `OverlayMeta` frozen dataclass + `parse_overlay_meta()` frontmatter parser + `discover_overlays()` `@lru_cache` filesystem scanner with path traversal guard + `apply_overlays()` extend/replace modes with budget-aware priority logic in `skill_loader.py`, `client_id: str | None` kwarg added to `build_system_prompt()` in all 11 agent `prompt.py` files + 9 service wrappers + `BaseAgentService.process()`/`stream_process()`, `BlueprintEngine.__init__(client_id=)` + `NodeContext.metadata["client_id"]` injection in `_build_node_context()`, `service.py` resolves `client_id` from `project.client_org.slug`, 9 agentic nodes extract `client_id` from context (15 callsites across HTML + structured paths), `data/clients/_example/agents/content/skills/brand_voice.md` starter overlay, `scripts/validate-overlays.py` (frontmatter validation + `replaces` reference check + conflict detection), `validate-overlays` + `list-overlays` Makefile targets, 22 new tests). Remaining: tests & integration verification (32.8), skill versioning (32.10), tests for 32.9-32.11 (32.12). **Next — independent of Phase 33.**

**Phase 33** (Design Token Pipeline Overhaul) **ALL DONE** (12/12 subtasks). See `docs/TODO-completed.md`.

**Phase 35** (Next-Gen Design-to-Email Pipeline — MJML + AI Intelligence + Standards) — 5 pillars: (1) MJML intermediate representation via Maizzle sidecar `/compile-mjml` endpoint + MJML generation backend replacing hand-rolled table HTML + 10 pre-built MJML section templates, (2) Figma node tree normalizer (hidden node removal, GROUP flattening, auto-layout inference, instance resolution, text merging), (3) AI-powered layout intelligence (LLM fallback for unclassifiable sections, semantic content detection for logos/unsubscribe/legal/social, vision-based fidelity scoring comparing Figma screenshots vs rendered HTML via SSIM, self-improving converter via correction learning loop that extracts agent fix patterns as converter rules), (4) W3C Design Tokens v1.0 import/export + caniemail.com live data sync for compatibility checks, (5) Figma webhooks for real-time `FILE_UPDATE` sync with debounced re-conversion + WebSocket push to frontend + section-level conversion caching for < 1s incremental updates. 11 subtasks. **Builds on Phase 33 (tokens) + Phase 27 (rendering). Independent of Phases 32/34.**

**Phase 36** (Universal Email Design Document & Multi-Format Import Hub) — introduces `EmailDesignDocument` JSON Schema v1 as the single canonical contract between ALL input sources and the converter. Refactors converter to consume only this JSON document. Refactors Figma + Penpot adapters to produce `EmailDesignDocument` (layout analysis moves from converter into adapters). MJML import adapter (parse `<mj-*>` markup → `EmailDesignDocument`, round-trip with Phase 35 MJML generation). AI-powered HTML reverse engineering adapter (DOM traversal + import annotator + LLM fallback → `EmailDesignDocument` from arbitrary email HTML). Klaviyo + HubSpot ESP export completing Big 5 (joining existing Braze/SFMC/Adobe Campaign). 7 subtasks. **Builds on Phase 35 (MJML, AI layout). ESP export (36.6) is independent — can start immediately.**

## Compact instructions

Preserve: current task + plan path, modified files, test results, key decisions.
