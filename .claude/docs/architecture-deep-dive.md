---
purpose: Complete architecture reference — vertical slice layout, AI agent pipeline, blueprint engine, eval system, design system, QA gate
when-to-use: When working on cross-cutting concerns, adding new modules, or debugging agent/blueprint/eval interactions
size: ~300 lines
source: docs/ARCHITECTURE.md
---

<!-- Scout header above. Sub-agents: read ONLY the header to decide relevance. Load full content only if needed. -->

# Architecture Deep Dive

## Vertical Slice Architecture

Each feature lives under `app/{feature}/` with its own schemas, models, repository, service, exceptions, routes, and tests. No shared "controllers" or "handlers" directories.

**Feature file creation order:** schemas → models → repository → service → exceptions → routes → tests

**Layer responsibilities:**
- **Routes**: Thin HTTP layer. Auth dependency, rate limiting, delegate to service, return response.
- **Service**: Business logic, validation, orchestration, logging. Never touches HTTP concerns.
- **Repository**: Database operations ONLY. No business logic, no logging of business events.

## API Modules

| Module | Prefix | Purpose |
|--------|--------|---------|
| projects | `/api/v1/projects` | Project CRUD, design systems |
| email_engine | `/api/v1/email` | Email compilation, CSS processing |
| components | `/api/v1/components` | Reusable component library |
| qa_engine | `/api/v1/qa` | QA checks, chaos testing, property testing, outlook analysis |
| connectors | `/api/v1/connectors` | ESP sync (Braze, SFMC, Adobe, Taxi) |
| approval | `/api/v1/approvals` | Client review portal |
| templates | `/api/v1/templates` | Template registry + versions |
| personas | `/api/v1/personas` | Brand voice personas |
| rendering | `/api/v1/rendering` | Screenshots, visual diff, baselines |
| knowledge | `/api/v1/knowledge` | RAG knowledge base, ontology |
| memory | `/memory` | Agent memory persistence |
| blueprints | `/api/v1/blueprints` | AI pipeline orchestration |
| ontology | `/api/v1/ontology` | Email client compatibility data |
| design_sync | `/api/v1/design-sync` | Figma integration |

## AI Agent System

### 9 Agents
Scaffolder, Dark Mode, Content, Outlook Fixer, Accessibility, Personalisation, Code Reviewer, Knowledge, Innovation.

All agents:
- Inherit from `BaseAgentService`
- Have a `SKILL.md` prompt file
- Have a 5-criteria LLM judge for evaluation
- Can operate in structured output mode (returning decision schemas instead of raw HTML)

### Blueprint Engine
State machine orchestrator in `app/ai/blueprints/engine.py`. Executes agent nodes in dependency order defined by blueprint YAML. Features:
- **Checkpoint/resume**: Save state after each node, resume from failure point
- **Typed handoffs**: `AgentHandoff` payloads carry structured data between nodes
- **Inline judges**: On retry (`iteration > 0`), run LLM judge before accepting output
- **13 context layers**: Each node gets layered context (system → project → design system → knowledge prefetch)
- **Adaptive routing**: Model tier selection based on historical success rates

### Structured Output Mode (11.22.8)
7 downstream agents return structured decision schemas (`app/ai/agents/schemas/*_decisions.py`). `plan_merger.py` merges decisions into `EmailBuildPlan`. `TemplateAssembler` is the single HTML generation point.

## QA Engine

### 11 Core Checks (`app/qa_engine/checks/`)
html_validation, css_support, file_size, link_validation, spam_score, dark_mode, accessibility, fallback (MSO), image_optimization, brand_compliance, personalisation_syntax.

Each: `async run(html, config) -> QACheckResult`

### Extended QA
- **Chaos Engine** (18.1): 8 degradation profiles (Gmail strip, Outlook Word, dark mode inversion, etc.)
- **Property Testing** (18.2): 10 email invariants with Hypothesis-based fuzzing
- **Rendering Resilience** (18.3): Optional check #12, runs chaos + threshold scoring
- **Outlook Analyzer** (19.1): 7 Word-engine dependency detection rules + modernizer
- **CSS Compiler** (19.3): Lightning CSS 7-stage pipeline with ontology-driven conversions

## Eval System (`app/ai/agents/evals/`)

Binary pass/fail LLM judges. Key components:
- `runner.py` — orchestrates eval runs
- `judge_runner.py` — executes individual judges
- `calibration.py` — TPR/TNR calibration against human labels
- `regression.py` — 3pp per-agent tolerance enforcement
- `golden_cases.py` — 7 deterministic CI templates (`make eval-golden`)
- `production_sampler.py` — probabilistic sampling of live runs for judge evaluation
- `improvement_tracker.py` — records pass rate deltas to `traces/improvement_log.jsonl`

## Design System Pipeline (11.25)

Per-project brand identity: `BrandPalette`, `Typography`, `LogoConfig`, `FooterConfig`.

Pipeline flow:
1. `DesignSystem` JSON on `Project` model
2. `ScaffolderPipeline._design_pass_from_system()` builds `DesignTokens` deterministically
3. `TemplateAssembler` applies role-based palette replacement, font swap, logo enforcement
4. `BrandRepair` (stage 8) corrects off-palette colors post-generation
5. Brand compliance QA check validates final output

## Configuration

Nested Pydantic settings with `env_nested_delimiter="__"`:
- `settings.database.url` ← `DATABASE__URL`
- `settings.ai.provider` ← `AI__PROVIDER`
- `settings.qa_chaos.enabled` ← `QA_CHAOS__ENABLED`

Feature flags follow pattern: `{MODULE}__{FEATURE}_ENABLED` defaulting to `off` for new features.
