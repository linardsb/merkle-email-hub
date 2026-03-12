# Feature Scope by Stack

## Backend Features (for `be-prime`)
- Auth: JWT HS256, RBAC (admin/developer/viewer), token revocation, brute-force protection
- Projects: ClientOrg, Project, ProjectMember models + RLS; `target_clients` JSON column (priority clients -- QA always checks all 25, priority affects display emphasis + agent attention); `onboarding.py` auto-generates client-specific compatibility subgraphs (Cognee dataset per project); `POST .../onboarding-brief` for manual refresh
- Email Engine: Maizzle build orchestration via sidecar
- Components: versioned component library with dark mode variants; QA bridge (`qa_bridge.py`) runs QA + extracts per-client compatibility; graph export (`graph_export.py`) for Cognee; `ComponentQAResult` join model; `compatibility_badge` on responses
- QA Engine: 10-point check system in `app/qa_engine/checks/`
- Connectors: 4 ESP connectors (Braze, SFMC, Adobe Campaign, Taxi) via ConnectorProvider Protocol + AES-256 credential storage
- Approval: ApprovalRequest, Feedback, AuditEntry models + workflow
- Personas: test subscriber profile presets
- AI: provider registry, model routing (Opus/Sonnet/Haiku), streaming via WebSocket
- Blueprints: state machine engine orchestrating agents with QA gating, recovery routing, bounded self-correction, structured handoffs (`AgentHandoff` with full history + episodic memory persistence), confidence-based routing, component context injection, project subgraph context (LAYER 8), graph-informed route selection (`route_advisor.py` -- audience-aware node skipping/addition), audience-aware competitive feasibility (LAYER 10)
- Knowledge: RAG pipeline with pgvector, hybrid search, document processing; `app/knowledge/graph/` Cognee integration (`GraphKnowledgeProvider` Protocol, `CogneeGraphProvider`, `POST /graph/search`, disabled by default); `app/knowledge/ontology/` email development ontology (25 clients, 365 CSS properties, 1011 support entries, 70 fallbacks -- powers data-driven QA + Cognee graph export); `app/knowledge/ontology/sync/` Can I Email live sync (`CanIEmailSyncPoller` via `DataPoller`, GitHub Trees API -> YAML diff -> graph re-export, `OntologySyncConfig`); `app/knowledge/ontology/competitive_feasibility.py` audience-aware competitive reports (`GET /api/v1/ontology/competitive-report`); `GET /api/v1/ontology/clients` lists all 25 email clients for frontend selectors
- Rendering: cross-client rendering tests (Litmus, EoA) via `RenderingProvider` Protocol, circuit breaker, visual regression comparison
- Design Sync: `app/design_sync/` VSA module -- `DesignSyncProvider` Protocol with Figma (real API via `httpx`), Sketch/Canva (stubs); Fernet-encrypted PAT storage (PBKDF2-derived key); `DesignConnection` + `DesignTokenSnapshot` models; BOLA enforcement via `verify_project_access()` + user-scoped list queries; 6 REST endpoints at `/api/v1/design-sync/`; 19 tests
- Agent Evals: dimension-based synthetic test data, JSONL trace runner, binary LLM judges, TPR/TNR calibration, error analysis, QA gate calibration, blueprint pipeline evals, regression detection (Phase 5); SKILL.md A/B testing (`skill_ab.py` + `skill_override.py` runtime override registry, `make eval-skill-test`)
- Memory: `app/memory/` VSA module -- pgvector Vector(1024) embeddings, HNSW similarity search, temporal decay, 3 memory types (procedural/episodic/semantic), DCG promotion bridge, `MemoryCompactionPoller`
- Phase 7: `AgentHandoff` structured handoffs with full history + episodic memory auto-persistence (`handoff_memory.py`), confidence scoring (threshold 0.5 -> needs_review), `ComponentResolver` for template-aware component context injection, SKILL.md progressive disclosure files for all 9 agents; `BaseAgentService` shared pipeline (`app/ai/agents/base.py`) with `_get_model_tier` + `_should_run_qa` hooks, standardised response schemas (`confidence` + `skills_loaded` on all agents), `to_handoff()` for standardised handoff emission, memory recall wired into blueprint engine, recovery router cycle detection via `handoff_history`; eval-informed prompts (`app/ai/agents/evals/failure_warnings.py`) -- reads `traces/analysis.json`, injects per-agent failure warnings into all 9 `build_system_prompt()` for criteria <85% pass rate, mtime-cached

## Frontend Features (for `fe-prime`)
- Dashboard: project overview grid, activity feed, QA summary, quick-start
- Workspace: 3-pane layout (Monaco editor + preview + AI chat)
- Monaco Editor: HTML/CSS/Liquid syntax, Can I Email warnings, code folding
- Live Preview: sandboxed iframe, viewport toggles, dark mode, zoom
- Persona Selector: device/client context switching
- Component Browser: grid view, search, detail view with preview + versions
- QA Gate UI: trigger, results checklist, override flow with justification
- Export Console: platform selector (Raw HTML, Braze), export preview
- AI Chat Sidebar: agent toggles, streaming display, accept/reject/merge
- Approval Portal: viewer login, read-only preview, section feedback, approve/reject
- Intelligence Dashboard: QA trends, support matrices, quality scores, graph health, blueprint health, agent performance, failure patterns summary, component coverage
- Knowledge Base Search: document browser, natural language search, domain/tag filters
- Design Sync: `/design-sync` page with provider filter tabs (All/Figma/Sketch/Canva), multi-provider connect dialog, connection cards with provider icons, design token extraction (colors, typography, spacing)
- Client Briefs: Jira/Asana/Monday.com connection cards, brief items, import-to-project
- Brand Guardrails: per-client color/typography/logo rules, CodeMirror linter, toolbar violations badge
- AI Image Generation: workspace dialog with style presets, gallery, insert-into-template
- Localisation: 6 locale stubs (en/ar/de/es/fr/ja), cookie-based switching, RTL, translation management
- Visual Liquid Builder: @dnd-kit drag-and-drop blocks, regex parser/serializer, Code/Visual tabs
- Rendering Tests: `/renderings` page with test list, stats cards, compatibility matrix, screenshot dialog, visual regression comparison, async polling
- Collaborative Editing: Yjs CRDT, y-codemirror.next, collaborator avatars, connection status
- Priority Clients Selector: `target-clients-selector.tsx` multi-select with engine badges, `useEmailClients` + `useUpdateProject` hooks, create dialog + workspace toolbar + project card badges (empty = all clients equal priority, QA always checks all 25)
- Compatibility Brief: `compatibility-brief-dialog.tsx` with per-client CSS constraints, risk summary, regenerate button; `useCompatibilityBrief` hook
- Blueprint Run UI: `blueprint-run-dialog.tsx` trigger with brief cards + `blueprint-pipeline-view`; `runs-list.tsx` + `run-detail-dialog.tsx` in bottom panel Runs tab; `useBlueprintRun` + `useBlueprintRuns` hooks
- Component Compatibility: `compatibility-badge.tsx` on cards (full/partial/issues/untested), per-client matrix in detail dialog
- Graph Knowledge Search: text/graph/ask mode toggle on `/knowledge`, `graph-search-results.tsx` entity cards with relationship labels
- Failure Pattern Dashboard: "Failure Patterns" tab on `/renderings` page with stats cards, filterable table, detail dialog, agent/check filters
- Agent Confidence & Handoff Visibility: `confidence-indicator.tsx` on chat messages (green/yellow/red), `node-handoff-panel.tsx` in blueprint views
- Workspace Agent Context Panel: `agent-context-panel.tsx` as "Context" tab in bottom panel -- audience, failure patterns, SKILL.md, component refs
- SDK Type Coverage: 102 SDK endpoints, 7 local type barrel files re-export from `@email-hub/sdk`, zero `as any` casts
