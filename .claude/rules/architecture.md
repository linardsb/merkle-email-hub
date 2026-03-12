---
description: Email Hub architecture details — modules, QA checks, agents, eval framework, Maizzle sidecar
globs: "**/*.{py,ts,tsx}"
---

# Email Hub Architecture

## Modules and Their Purpose

| Module | API Prefix | Purpose |
|--------|-----------|---------|
| `projects` | `/api/v1/projects`, `/api/v1/orgs` | Multi-tenant client org isolation, project workspaces, onboarding subgraphs |
| `email_engine` | `/api/v1/email` | Maizzle build pipeline, calls sidecar at `http://maizzle-builder:3001` |
| `components` | `/api/v1/components` | Versioned reusable email components (header, CTA, hero, etc.) |
| `qa_engine` | `/api/v1/qa` | 10-point quality gate system with individual check modules |
| `connectors` | `/api/v1/connectors` | ESP export (Braze, SFMC, Adobe Campaign, Taxi for Email) via ConnectorProvider Protocol |
| `approval` | `/api/v1/approvals` | Client approval workflow with feedback and audit trail |
| `templates` | `/api/v1/templates`, `/api/v1/projects/{id}/templates` | Versioned email templates with soft delete and restore |
| `personas` | `/api/v1/personas` | Test subscriber profiles (device, email client, dark mode) |
| `rendering` | `/api/v1/rendering` | Cross-client rendering tests (Litmus, EoA) with visual regression |
| `knowledge` | `/api/v1/knowledge` | RAG pipeline: document ingestion, hybrid search, tagging (`make seed-knowledge`) |
| `memory` | `/memory` | Agent memory: pgvector semantic search, temporal decay, DCG promotion bridge |
| `blueprints` | `/api/v1/blueprints` | Blueprint state machine engine: orchestrated agent pipelines with self-correction |
| `ontology` | `/api/v1/ontology` | Competitive intelligence reports: audience-scoped feasibility, Hub vs competitor capability matrix |
| `design_sync` | `/api/v1/design-sync` | Multi-provider design tool connections (Figma real API, Sketch/Canva stubs), Fernet-encrypted PAT storage, design token extraction |

## QA Gate System (10 checks)

Located in `app/qa_engine/checks/`. Each check implements `async run(html: str, config: QACheckConfig | None = None) -> QACheckResult`:

1. `html_validation` -- lxml DOM-parsed: 20 structural checks (skeleton, tag integrity, content, email structure, progressive enhancement)
2. `css_support` -- Ontology-powered: scans 365 CSS properties against 25 email clients with severity scoring
3. `file_size` -- Gmail 102KB clipping threshold
4. `link_validation` -- HTTPS enforcement, valid protocols
5. `spam_score` -- Common spam trigger word detection
6. `dark_mode` -- color-scheme meta, prefers-color-scheme, Outlook overrides
7. `accessibility` -- WCAG AA: 24 DOM-parsed checks across 8 groups (language, tables, images, headings, links, content semantics, dark mode, AMP forms) via YAML rule engine
8. `fallback` -- MSO conditional comments, VML namespaces
9. `image_optimization` -- Explicit dimensions, format validation
10. `brand_compliance` -- Placeholder for client brand rules

## Maizzle Builder Sidecar

`services/maizzle-builder/` is a thin Node.js/Express server:
- `POST /build` -- Full build with optional production config
- `POST /preview` -- Development preview build
- `GET /health` -- Health check
- Receives template source + config via HTTP, returns compiled HTML

## AI Agents (9 total) + Blueprint Engine + Eval System

The AI protocol layer (`app/ai/`) provides infrastructure for 9 specialized agents using the provider registry for LLM calls and knowledge module for RAG. The **Blueprint engine** (`app/ai/blueprints/`) orchestrates agents as state machine nodes with deterministic gates (QA, build, export) and bounded self-correction. The **Eval system** (`app/ai/agents/evals/`) validates agent quality via dimension-based synthetic test data, binary LLM judges, and TPR/TNR calibration.

| Agent | Purpose | Phase | Eval Status |
|-------|---------|-------|-------------|
| Scaffolder | Generate Maizzle HTML from campaign briefs | Sprint 2 | Judge ready (5 criteria), SKILL.md + 4 L3 files |
| Dark Mode | Inject dark mode CSS, Outlook overrides, colour remapping | Sprint 2 | Judge ready (5 criteria), SKILL.md + 3 L3 files |
| Content | Subject lines, preheaders, CTA text, tone adjustment | Sprint 2 | Judge ready (5 criteria) |
| Outlook Fixer | MSO conditionals, VML backgrounds, table fallbacks | V2 | Judge ready (5 criteria), 12 synthetic cases |
| Accessibility Auditor | WCAG AA, contrast, alt text, AI alt generation | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 10 synthetic cases |
| Personalisation | Liquid (Braze), AMPscript (SFMC), dynamic content | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 12 synthetic cases |
| Code Reviewer | Static analysis, redundant code, file size optimisation | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 12 synthetic cases |
| Knowledge | RAG-powered Q&A from knowledge base | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 10 synthetic cases |
| Innovation | Prototype new techniques, feasibility assessment | V2 | Judge ready (5 criteria), SKILL.md + 4 L3 files, 10 synthetic cases |

## Agent Evaluation Framework

Located in `app/ai/agents/evals/`. Based on the [evals-skills methodology](https://github.com/hamelsmu/evals-skills) -- binary pass/fail LLM judges calibrated against human labels.

**Per-agent eval requirements (all 9 agents):**
1. Dimension-based synthetic test data (failure-prone axes of variation)
2. Binary pass/fail judge prompts (one per quality dimension)
3. Eval runner traces (JSONL with input, output, timing, errors)
4. Error analysis (failure clustering, root cause identification)
5. Judge calibration (TPR/TNR against human labels, not raw accuracy)

**Eval files:**
- `dimensions.py` -- Failure-prone axes per agent (layout complexity, client quirks, etc.)
- `synthetic_data_{agent}.py` -- Test cases with real-world data (MSO code, VML, spam triggers)
- `runner.py` -- CLI: `python -m app.ai.agents.evals.runner --agent scaffolder --output traces/`
- `judges/` -- Binary pass/fail LLM judges: `ScaffolderJudge` (5 criteria), `DarkModeJudge` (5 criteria), `ContentJudge` (5 criteria), `OutlookFixerJudge` (5 criteria), `AccessibilityJudge` (5 criteria), `PersonalisationJudge` (5 criteria), `CodeReviewerJudge` (5 criteria), `KnowledgeJudge` (5 criteria), `InnovationJudge` (5 criteria); `Judge` Protocol, `JUDGE_REGISTRY`, shared prompt template
- `judge_runner.py` -- CLI: `python -m app.ai.agents.evals.judge_runner --agent {agent} --traces X --output Y`
- `schemas.py` -- Shared dataclasses: `FailureCluster`, `HumanLabel`, `CalibrationResult`, `QACalibrationResult`, `RegressionReport`, `SkillABCriterionDelta`, `SkillABResult`, `SkillABReport`, `BlueprintEvalTrace`
- `error_analysis.py` -- Failure clustering + pass rate computation from verdict JSONL (`make eval-analysis`)
- `scaffold_labels.py` -- Generates prefilled human label templates from traces+verdicts (`make eval-labels`)
- `calibration.py` -- TPR/TNR computation against human labels per criterion
- `qa_calibration.py` -- QA gate check-vs-human agreement rates, flags checks <75%
- `blueprint_eval.py` -- End-to-end blueprint pipeline runner with 5 test briefs (`make eval-blueprint`)
- `regression.py` -- Baseline comparison with configurable tolerance, CI gate exit code (`make eval-regression`)
- `skill_ab.py` -- SKILL.md A/B test runner: runs eval suite with current vs proposed SKILL.md, compares per-criterion pass rates, auto-recommends merge/reject (`make eval-skill-test`)

## API Security Patterns

- **JWT HS256**: Pinned algorithm constant in `app/auth/token.py` (not configurable). 15-min access + 7-day refresh tokens. Redis-backed blocklist for revocation.
- **Brute-force protection**: exponential backoff, lock after 5 failed attempts (15 min), Redis-tracked.
- **Row-Level Security**: PostgreSQL RLS on `client_org_id`. Database enforces isolation independently of app layer.
- **Credential storage**: AES-256 for ESP API keys (Braze); Fernet (PBKDF2-derived) for design tool PATs (`app/design_sync/crypto.py`). Never returned in responses, never logged.
- **AI rate limits**: 20 req/min per user for chat, 5 req/min for generation. Per-user daily quota via Redis (`app/core/quota.py`). Stream timeout 120s. Blueprint daily token cap 500k.
- **WebSocket limits**: Global 100 connections + per-user 5 connections (`app/streaming/manager.py`).
- **LLM output sanitization**: `nh3` (Rust-based) allowlist HTML sanitizer in `app/ai/shared.py`. Preserves email HTML (tables, styles, MSO comments). Approval state machine prevents invalid transitions.
- **Error sanitization**: `get_safe_error_message()` / `get_safe_error_type()` in `app/core/error_sanitizer.py`. All exception handlers (including auth) use sanitized messages -- never leak class names or internal details.
- **CI quality gate**: `.github/workflows/ci.yml` runs lint + types + security-check + tests on every push/PR. PR template enforces security checklist.
