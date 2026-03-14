---
description: Email Hub architecture — modules, QA checks, agents, eval framework
globs: "**/*.{py,ts,tsx}"
---

# Architecture Reference

## API Modules

projects (`/api/v1/projects`), email_engine (`/api/v1/email`), components (`/api/v1/components`), qa_engine (`/api/v1/qa`), connectors (`/api/v1/connectors`), approval (`/api/v1/approvals`), templates (`/api/v1/templates`), personas (`/api/v1/personas`), rendering (`/api/v1/rendering`), knowledge (`/api/v1/knowledge`), memory (`/memory`), blueprints (`/api/v1/blueprints`), ontology (`/api/v1/ontology`), design_sync (`/api/v1/design-sync`).

## QA Gate (11 checks in `app/qa_engine/checks/`)

html_validation, css_support, file_size, link_validation, spam_score, dark_mode, accessibility, fallback (MSO), image_optimization, brand_compliance, personalisation_syntax. Each: `async run(html, config) -> QACheckResult`.

## 9 AI Agents

Scaffolder, Dark Mode, Content, Outlook Fixer, Accessibility, Personalisation, Code Reviewer, Knowledge, Innovation. All have 5-criteria judges + SKILL.md files. Blueprint engine orchestrates as state machine nodes.

**Structured output mode (11.22.8):** 7 downstream agents return structured decision schemas (`app/ai/agents/schemas/*_decisions.py`) instead of raw HTML. `plan_merger.py` merges decisions into `EmailBuildPlan`. `TemplateAssembler` is the single HTML generation point. Outlook Fixer is diagnostic-only in structured mode.

## Eval System (`app/ai/agents/evals/`)

Binary pass/fail LLM judges calibrated via TPR/TNR. Key files: `runner.py`, `judge_runner.py`, `judges/`, `dimensions.py`, `synthetic_data_*.py`, `calibration.py`, `qa_calibration.py`, `regression.py`, `skill_ab.py`, `improvement_tracker.py`, `golden_cases.py`.

**Inline judges (11.23):** `app/ai/blueprints/inline_judge.py` bridges `JUDGE_REGISTRY` into live blueprint execution on recovery retries (`iteration > 0`). Lightweight model tier, `temperature=0.0`, failure-safe. Config: `BLUEPRINT__JUDGE_ON_RETRY=true`.

**Eval-driven iteration (11.22.9):** `improvement_tracker.py` records pass rate deltas to `traces/improvement_log.jsonl`. `golden_cases.py` validates 7 templates deterministically in CI (`make eval-golden`). `dimensions.py` includes template-first criteria (template_selection_accuracy, slot_fill_quality, design_token_coherence). `regression.py` enforces 3pp per-agent tolerance via `AGENT_REGRESSION_TOLERANCE`. Scaffolder has 22 synthetic test cases (10 template selection edge cases added).

**Production trace sampling (11.24):** `app/ai/agents/evals/production_sampler.py` closes the eval feedback loop. Successful blueprint runs are probabilistically enqueued to Redis (`service.py` post-run hook), `ProductionJudgeWorker` (DataPoller) processes the queue with LLM judges, verdicts append to `traces/production_verdicts.jsonl`, `refresh_analysis()` merges with synthetic verdicts into `traces/analysis.json`. Existing `failure_warnings.py` reads merged analysis — agents learn from production failures. Config: `EVAL__PRODUCTION_SAMPLE_RATE` (default `0.0` = disabled). Command: `make eval-refresh`.

## Design System (11.25.1)

Per-project brand identity in `app/projects/design_system.py`. `DesignSystem` Pydantic model (frozen) with `BrandPalette`, `Typography`, `LogoConfig`, `FooterConfig`, `SocialLink`. Stored as JSON column on `Project`. API: GET/PUT/DELETE `/api/v1/projects/{id}/design-system`. `design_system_to_brand_rules()` bridges to brand compliance params. Brand compliance check auto-derives rules from design system via `_enrich_config_from_design_system()` when no explicit `qa_profile` brand rules exist (read-time, no stale data).

## Maizzle Sidecar

`services/maizzle-builder/` — POST /build, POST /preview, GET /health.
