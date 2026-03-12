# Completed Roadmap (Phases 0-10)

All phases below are complete. See `TODO.md` for full task details with security requirements and verification criteria.

## Phase 0 — Foundation Blockers
- [x] 0.1 Database migration for all email-hub models + RLS policies
- [x] 0.2 Initialize shadcn/ui component library in `cms/apps/web/`
- [x] 0.3 Generate OpenAPI TypeScript SDK from backend
- [x] 0.4 Authenticated API client layer (token refresh, error handling, React hooks)

## Phase 1 — Sprint 1: Editor + Build Pipeline
- [x] 1.1 Project dashboard page (`/(dashboard)/page.tsx`)
- [x] 1.2 Project workspace layout (3-pane: editor, preview, AI chat)
- [x] 1.3 Monaco editor (HTML/CSS/Liquid, Can I Email autocomplete)
- [x] 1.4 Maizzle live preview (compile-on-save, viewport toggles, dark mode)
- [x] 1.5 Test persona engine UI (persona selector, device/client context)
- [x] 1.6 Template CRUD + persistence (versioning, restore)

## Phase 2 — Sprint 2: Intelligence + Export
- [x] 2.1 Wire AI provider (Claude/OpenAI, model routing, streaming)
- [x] 2.2 Scaffolder agent (brief -> Maizzle HTML)
- [x] 2.3 Dark Mode agent (inject dark mode CSS + Outlook overrides)
- [x] 2.4 Content agent (copy generation, editor context menu)
- [x] 2.5 AI chat sidebar UI (agent selection, streaming, accept/reject)
- [x] 2.6 Component library v1 -- backend (seed 5-10 components)
- [x] 2.7 Component library browser UI (`/components`)
- [x] 2.8 10-point QA gate system (backend + UI complete)
- [x] 2.9 Raw HTML export + Braze connector UI
- [x] 2.10 RAG knowledge base seeding (Can I Email, best practices)

## Phase 3 — Sprint 3: Client Handoff + Polish
- [x] 3.1 Client approval portal (viewer role, feedback, audit trail)
- [x] 3.2 Rendering intelligence dashboard (QA trends, support matrices)
- [x] 3.3 Dashboard homepage enhancement (real data, activity feed)
- [x] 3.4 Error handling, loading states, UI polish (skeletons, toasts, error pages)
- [x] 3.5 CMS + Nginx Docker stack (7 services healthy)

## Phase 4 — V2
- [x] 4.8 Knowledge base search UI (`/knowledge` page, document browser, hybrid search)
- [x] 4.9 Smart agent memory (conversation history tab in workspace chat)
- [x] 4.10 Version comparison (side-by-side template diff in approval portal)
- [x] 4.11 Custom persona creation (dialog form for new test profiles)
- [x] 4.12 Exportable reports (intelligence dashboard Print/PDF + CSV export)
- [x] 4.13 Blueprint state machine engine (agent orchestration with self-correction, QA gating, recovery routing)
- [x] 4.1 All 9 AI agents complete -- eval-first + skills workflow (Outlook Fixer, Accessibility Auditor, Personalisation, Code Reviewer, Knowledge, Innovation -- all DONE)
- [x] 4.2 Additional CMS connectors (SFMC, Adobe Campaign, Taxi for Email)
- [x] 4.3 Design sync -- multi-provider backend (`app/design_sync/` VSA module: Figma real API + Sketch/Canva stubs, Fernet-encrypted PATs, BOLA enforcement, 19 tests) + frontend rename (`/figma` -> `/design-sync`, provider filter tabs, generic connect dialog)
- [x] 4.4 Litmus / Email on Acid API integration (backend: `app/rendering/` VSA module, Litmus + EoA providers, visual regression)
- [x] 4.5 Advanced features (collaborative editing, localisation, brand guardrails, AI image gen, visual Liquid builder, client briefs)

## Phase 5 — Agent Evaluation System
Applies to ALL 9 agents. No agent goes to production without completing steps 5.1-5.5.
- [x] 5.1 Synthetic test data generation (Scaffolder: 12, Dark Mode: 10, Content: 14 cases done)
- [x] 5.2 Eval runner infrastructure (JSONL trace capture)
- [x] 5.3 Write binary judge prompts per agent per quality dimension
- [x] 5.4 Run evals + error analysis -- live execution complete (36 traces, 16.7% overall pass rate, failure clusters identified)
- [x] 5.5 Judge calibration -- verdicts generated, human label templates scaffolded (540 rows), calibration pending human labels
- [x] 5.6 QA gate calibration -- tooling ready, pending human labels
- [x] 5.7 Blueprint pipeline evals -- 5/5 campaigns passed with self-correction
- [x] 5.8 Regression suite -- baseline established from live data (`traces/baseline.json`), CI integration deferred

## Phase 6 — OWASP API Security Hardening (COMPLETE)
Audit conducted 2026-03-06. Follow-up audit 2026-03-07. Fix pattern: `verify_project_access()` from `app/projects/service.py`.
- [x] 6.1.1-6.1.4 BOLA fixes -- CRITICAL (projects, approvals, connectors, QA override)
- [x] 6.1.5-6.1.10 BOLA fixes -- HIGH/CRITICAL (approvals, rendering, knowledge, WebSocket, AI agents, email builds)
- [x] 6.2.1-6.2.4 Response & error hardening (error sanitizer, LLM circuit breaker, generic error types, auth handler type leakage)
- [x] 6.3.1-6.3.4 Rate limiting & resource controls (per-user Redis quota, per-user WS limit, stream timeout, blueprint cost cap)
- [x] 6.4.1-6.4.3 Business logic (approval state machine, JWT algorithm pinning, nh3 HTML sanitizer)
- [x] 6.5.1-6.5.6 SDC improvements (security-check in `make check`, CI workflow, PR template, memory rate limits, frontend token/type fixes)

## Phase 7 — Agent Capability Improvements
- [x] 7.1 Structured inter-agent handoff schemas (`AgentHandoff` frozen dataclass, full history via `_handoff_history`, auto-persisted to episodic memory via `handoff_memory.py`, exposed in API as `HandoffSummary`)
- [x] 7.2 Eval-informed agent prompts (`failure_warnings.py`, reads `traces/analysis.json`, injects per-agent warnings for criteria <85% pass rate)
- [x] 7.3 Agent confidence scoring (0-1 via `<!-- CONFIDENCE: X.XX -->` HTML comment, threshold 0.5 -> `needs_review` status)
- [x] 7.4 Template-aware component context (`ComponentResolver` Protocol, `DbComponentResolver`, auto-detect `<component>` refs)
- [x] 7.5 Hub Agent Memory System (`app/memory/` VSA module, pgvector Vector(1024), HNSW index, temporal decay, DCG promotion bridge)
- [x] 7.6 DCG cross-agent memory Phase 1 + Agent architecture improvements (`BaseAgentService` shared pipeline, 7 agents refactored, standardised response schemas, `to_handoff()` method, recovery router cycle detection)

## Phase 8 — Knowledge Graph Integration (Cognee)
- [x] 8.1 Cognee integration layer (`app/knowledge/graph/`, `GraphKnowledgeProvider` Protocol, `CogneeGraphProvider`)
- [x] 8.2 Knowledge graph seeding (RAG docs + ontology through Cognee ECL pipeline per domain)
- [x] 8.3 Graph context provider for blueprint nodes
- [x] 8.4 Blueprint outcome logging (`outcome_logger.py` formats+queues to Redis+Memory, `OutcomeGraphPoller`)
- [x] 8.5 Per-agent domain SKILL.md files (all 9 agents: Four Discipline structure, progressive disclosure L1+L2+L3)
- [x] 8.6 Email development ontology (`app/knowledge/ontology/` -- 25 clients, 365 CSS properties, 1011 support entries, 70 fallbacks)

## Phase 9 — Graph-Driven Intelligence Layer
- [x] 9.1 Graph-powered client audience profiles (`audience_context.py`, persona -> ontology bridge)
- [x] 9.2 Can I Email live sync (`CanIEmailSyncPoller`, GitHub API -> YAML diff -> graph re-export, 51 tests)
- [x] 9.3 Component-to-graph bidirectional linking (`qa_bridge.py` + `graph_export.py`, `ComponentQAResult` join model)
- [x] 9.4 Failure pattern propagation across agents (`failure_patterns.py`, dual persist to memory + graph)
- [x] 9.5 Client-specific subgraphs for project onboarding (`onboarding.py`, `target_clients` JSON column)
- [x] 9.6 Graph-informed blueprint route selection (`route_advisor.py`, audience-aware skip/add logic)
- [x] 9.7 Competitive intelligence graph (`competitive_feasibility.py`, audience-aware feasibility scoring)
- [x] 9.8 SKILL.md A/B testing via eval system (`skill_override.py` runtime registry, `skill_ab.py` A/B runner CLI)

## Phase 10 — Full-Stack Agent Workflow (Frontend Integration)
Design principle: QA always checks ALL 25 email clients; "priority clients" affect display emphasis and agent attention, never exclusion.
- [x] 10.1 Project priority clients selector (`target-clients-selector.tsx`, `useEmailClients` + `useUpdateProject` hooks)
- [x] 10.2 Onboarding compatibility brief UI (`compatibility-brief-dialog.tsx`, `useCompatibilityBrief` hook)
- [x] 10.3 Blueprint run trigger & pipeline visualisation (`blueprint-run-dialog.tsx`, `useBlueprintRun` hook)
- [x] 10.4 Blueprint run history & outcomes (`runs-list.tsx` + `run-detail-dialog.tsx` in bottom panel Runs tab)
- [x] 10.5 Component compatibility badges & matrix (`compatibility-badge.tsx`, per-client matrix in detail dialog)
- [x] 10.6 Graph-powered knowledge search (text/graph/ask mode toggle, `graph-search-results.tsx`, `useGraphSearch` hook)
- [x] 10.7 Failure pattern dashboard (tab on `/renderings` page, filterable pattern table, detail dialog)
- [x] 10.8 Agent confidence & handoff visibility (`confidence-indicator.tsx`, `node-handoff-panel.tsx`)
- [x] 10.9 Workspace agent context panel (`agent-context-panel.tsx` as Context tab in bottom panel)
- [x] 10.10 SDK regeneration & type coverage (102 endpoints, 7 local type files migrated to SDK re-exports)
- [x] 10.11 Blueprint-aware chat mode (Blueprint Mode toggle, inline pipeline progress + result card)
- [x] 10.12 Intelligence dashboard enhancements (graph health, blueprint health, agent performance, failure patterns)
