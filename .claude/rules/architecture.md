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

Binary pass/fail LLM judges calibrated via TPR/TNR. Key files: `runner.py`, `judge_runner.py`, `judges/`, `dimensions.py`, `synthetic_data_*.py`, `calibration.py`, `qa_calibration.py`, `regression.py`, `skill_ab.py`.

**Inline judges (11.23):** `app/ai/blueprints/inline_judge.py` bridges `JUDGE_REGISTRY` into live blueprint execution on recovery retries (`iteration > 0`). Lightweight model tier, `temperature=0.0`, failure-safe. Config: `BLUEPRINT__JUDGE_ON_RETRY=true`.

## Maizzle Sidecar

`services/maizzle-builder/` — POST /build, POST /preview, GET /health.
