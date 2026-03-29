# Product Requirements Document (PRD)

## Email Innovation Hub

**Classification:** Internal / Confidential
**Version:** 4.67
**Date:** 2026-03-29
**Status:** V1 Complete — Sprint 3 done (3.1-3.5); V2 tasks 4.1-4.5, 4.8-4.13 done; ALL 10 AI agents built (eval-first + skills workflow); Phase 5.1-5.8 eval system complete; Phase 6 OWASP complete; Phase 7 complete; Phase 8 Knowledge Graph COMPLETE; Phase 9 Graph-Driven Intelligence COMPLETE; Phase 10 Frontend Integration COMPLETE (10.1-10.12); Phase 11 QA Engine Hardening COMPLETE (11.1-11.25 all done — template-first architecture, inline judges, production trace sampling, eval-driven iteration, client design system & brand pipeline); Phase 12 Design-to-Email Import COMPLETE (12.1-12.9 — protocol extension, asset storage, import models, layout analyzer, AI conversion, component extraction, frontend file browser, design reference panel, SDK + tests); Phase 13 ESP Bidirectional Sync COMPLETE (13.1-13.11 — mock ESP server with 4 API surfaces, sync protocol + providers, encrypted credential management, 8 REST endpoints, frontend sync UI, 93 backend tests, SDK regen); Phase 14 Blueprint Checkpoint & Recovery COMPLETE (14.1-14.7 — checkpoint storage layer, engine save integration, resume from checkpoint, multi-pass pipeline checkpoints, cleanup & observability, frontend resume UI, 47 tests, ADR-006); Phase 15 COMPLETE (15.1-15.5 all done — typed handoff schemas + phase-aware memory decay + adaptive model tier routing + auto-surfacing prompt amendments + bidirectional knowledge graph pre-query); Phase 16 COMPLETE (16.1-16.6 all done — query router intent classification, structured compatibility queries, code-aware HTML chunking, template/component retrieval, CRAG validation loop, multi-representation indexing); Phase 17 COMPLETE (17.1-17.6 all done — Playwright CLI screenshot service with 5 client profiles, ODiff visual regression baseline system with 3 new endpoints, VLM Visual Analysis Agent — 10th AI agent with multimodal defect detection + ontology cross-referencing, auto-fix pipeline integration with LLM correction + re-render verification, frontend Visual QA Dashboard with 6 components + 3-tab dialog + 4 SWR hooks, 28 route tests + 12 judge tests + SDK regeneration; 2639 total backend tests); Phase 18 COMPLETE (18.1-18.5 all done — Email Chaos Engine with 8 profiles + composable degradations + resilience scoring, Property-Based Email Testing with 10 invariants + deterministic generators, Resilience Score Integration & Knowledge Feedback, Frontend Chaos & Property Testing UI, 37 new tests + ADR-007); Phase 19 Outlook Transition Advisor & Email CSS Compiler COMPLETE (19.1-19.5 all done — Outlook Word-Engine Dependency Analyzer + Audience-Aware Migration Planner + Lightning CSS Email Compiler + Frontend Dashboard + Tests & ADR-008; 2882 total backend tests); Phase 20 Gmail AI Intelligence & Deliverability COMPLETE (20.1-20.5 all done — Gmail AI Summary Predictor + Schema.org Auto-Markup + Deliverability Score + BIMI Readiness + Frontend Panel; 111 backend tests); Phase 21 Real-Time Ontology Sync & Competitive Intelligence COMPLETE (21.1 caniemail Auto-Sync Pipeline — `CanIEmailSyncService` with dry-run + Redis state + 24 tests; 21.2 Email Client Rendering Change Detector — 25 CSS feature-detection templates + Playwright rendering + ODiff baselines + weekly poller + 16 tests; 21.3 Competitive Intelligence Dashboard — `OntologySyncPanel` + `CompetitiveReportPanel` with audience filter + 4 SWR hooks + 31 i18n keys + 4 new backend edge case tests; 45 total ontology tests); Phase 22 AI Evolution Infrastructure COMPLETE (22.1 Model Capability Registry — `ModelCapability` StrEnum + `ModelSpec` frozen dataclass + `CapabilityRegistry` singleton + `resolve_model_by_capabilities()` capability-aware routing + config loading from `AI__MODEL_SPECS`; 26 tests; 22.2 Prompt Template Store — `PromptTemplate` model + `PromptTemplateRepository` with auto-versioning + `PromptStoreService` seed from SKILL.md + 7 REST endpoints at `/api/v1/prompts` with admin/developer auth + `skill_override.py` cache integration + startup preloading; 37 tests; 22.3 Token Budget Manager — `TokenBudgetManager` with tiktoken + approximation fallback + `trim_to_budget()` message trimming; 21 tests; 22.4 Fallback Chains & Provider Resilience — `FallbackChain`/`FallbackEntry`/`FallbackEvent` dataclasses + `call_with_fallback()` async cascade + `_is_retryable()` error classifier + `get_fallback_chain()` cached routing + integrated at `ChatService.chat()` and `BaseAgentService.process()` + `AI__FALLBACK_CHAINS` JSON config; 28 tests; 22.5 Cost Governor — `CostGovernor` Redis-backed cost ledger with integer pence storage + per-model pricing table (9 models) + `BudgetStatus` three-tier enforcement (OK/WARNING/EXCEEDED) + `BudgetExceededError` (429) + adapter-layer integration in both providers + `GET /api/v1/ai/cost/report` admin-only + `GET /api/v1/ai/cost/status` admin+developer + in-memory fallback; 34 tests; 22.6 Tests & Documentation — 31 cross-module integration tests across 7 groups verifying full adapter pipeline: token budget ↔ adapter, cost governor ↔ adapter, fallback ↔ service, capability registry ↔ routing, prompt store ↔ skill override, full pipeline E2E, config edge cases; ADR-009 AI Evolution Infrastructure in `docs/ARCHITECTURE.md`; 193 total AI tests); Phase 23 Multimodal Protocol & MCP Agent Interface COMPLETE (23.1 Multimodal Content Block Protocol — `ContentBlock` union types + validation + token estimation; 43 tests; 23.2 Adapter Multimodal Serialization — OpenAI + Anthropic content block serialization + structured output; 41 tests; 23.3 Agent Multimodal Integration — base agent multimodal messages + scaffolder design references + engine LAYER 14; 22 tests; 23.4 MCP Tool Server — `app/mcp/` package with `FastMCP` + 5 tool categories + auth + audit + streamable HTTP at `/mcp`; 23.5 Voice Brief Input Pipeline — `app/ai/voice/` with Whisper API/local transcription + LLM brief extraction + 3 endpoints at `/api/v1/ai/voice/` + config-driven rate limits; 10 tests). Phase 24 Real-Time Collaboration & Visual Builder COMPLETE (24.1 WebSocket Infrastructure & Authentication — `app/streaming/websocket/` package with `CollabConnectionManager` room-based routing + `authenticate_websocket()` JWT auth + `verify_room_access()` BOLA + `RedisPubSubBridge` multi-instance relay + `/ws/collab/{room_id}` endpoint with binary Yjs + JSON awareness protocol + heartbeat + viewer role enforcement + `CollabWebSocketConfig` feature-flagged; 29 tests; 24.2 Yjs CRDT Document Engine — `app/streaming/crdt/` package with `YjsDocumentStore` PostgreSQL persistence + inline compaction + size capping, `YjsSyncHandler` server-side Yjs sync protocol (SyncStep1/Step2/Update), `CollaborativeDocument` model + Alembic migration, CRDT handler integrated into existing `/ws/collab/{room_id}` binary path with feature flag `crdt_enabled`, viewer read-only SyncStep1 support, room init/cleanup lifecycle, `pycrdt` + `pycrdt-websocket` dependencies; frontend: `createHubProvider()` Hub-authenticated WebSocket provider, `createCollabExtension()` Yjs↔CodeMirror 6 binding with Y.UndoManager, `awareness.ts` cursor color palette + collaborator helpers, dual-mode `collaborative` prop on `CodeEditor`; 12 backend tests, 3442 total; 24.3 Collaborative Cursor & Presence Awareness — `components/collaboration/` package with `PresencePanel` sidebar (user list + activity states + follow mode), `CollaborationBanner` toolbar widget (avatar stack + editing count + connection dot), `ConflictResolver` inline merge warning, `remoteCursorStyles()` CodeMirror theme for enhanced cursor labels + animations; `usePresence` hook with enriched collaborators + idle detection + follow mode + cursor broadcasting; extended awareness helpers (`setLocalActivity`, `setLocalCursorState`, `computeActivity`, `getEnrichedCollaborators`); `useCollaboration` exposes awareness ref; `EditorPanel` passes `collaborative` prop; workspace page wires presence panel + follow mode with dynamic `EditorView.scrollIntoView`; `make check-fe` green; 24.4 Visual Email Builder — Component Palette & Canvas — `components/builder/` package with `VisualBuilderPanel` top-level panel replacing LiquidBuilderPanel in EditorPanel "Builder" tab, `ComponentPalette` left sidebar (w-56) with search + category filter pills + draggable component cards via `useDraggable`, `BuilderCanvas` central drop zone with `SectionWrapper` sortable sections + inter-section drop zones via `useDroppable`, `SectionWrapper` per-section selection UI with ring highlight + drag handle + duplicate/delete toolbar + DOMPurify-sanitized content, `BuilderPreview` sandboxed iframe (`sandbox=""`) with zoom support, `DragDropContext` @dnd-kit wrapper with PointerSensor + KeyboardSensor + palette vs reorder detection, `ZoomControls` 50%/75%/100%/125%; `hooks/use-builder.ts` with `useBuilderState()` reducer (50-entry undo/redo via structuredClone history) + `useBuilderPreview()` HTML assembler; `types/visual-builder.ts` with BuilderSection + BuilderState + BuilderAction + PaletteItem types; keyboard shortcuts Ctrl+Z/Shift+Z undo/redo + Delete/Backspace remove + Ctrl+D duplicate + Escape deselect; one-way data flow palette→canvas→HTML (external code edit warning banner); component HTML lazy-fetched via `authFetch` on drop with Map cache; `make check-fe` green; 24.5 Property Panels & Section Configuration — `components/builder/panels/` package with `PropertyPanel` right sidebar (w-80) appearing on section selection with Radix Tabs (Content/Style/Responsive/Advanced) + ScrollArea, `ContentTab` dynamic slot editors driven by `slotDefinitions` from ComponentVersion, `StyleTab` palette-restricted color overrides + font/size selectors + spacing inputs + alignment buttons, `ResponsiveTab` mobile behavior toggles (stack on mobile, full-width images, mobile font size) + desktop/mobile preview mode, `AdvancedTab` CSS class input with regex validation + MSO conditional checkbox + dark mode override key-color list + HTML attribute editor blocking `on*`/`javascript:`/`style` + View Source dialog, `SlotEditor` generic input renderer mapping slot_type to controls (headline→Input, body→Textarea, cta→text+URL, image→src+alt, divider→height+palette color), `PaletteColorPicker` Popover swatch grid with Tooltip role names (no freeform hex); `types/design-system-config.ts` with `DesignSystemConfig` type + `extractPaletteSwatches()` helper; `types/visual-builder.ts` extended with `SlotDefinition`/`DefaultTokens`/`ResponsiveOverrides`/`AdvancedConfig` types; `use-builder.ts` enhanced with `buildTokenStyles()` CSS value sanitization + `buildResponsiveCss()` media queries + MSO conditional/CSS class injection inside `<td>` (valid table HTML) + `createSectionDefaults()`; `visual-builder-panel.tsx` fetches project design system via `authFetch` + renders PropertyPanel conditionally + mobile preview width; `editor-panel.tsx` passes `projectId` prop; `make check-fe` green; 24.6 Builder ↔ Code Bidirectional Sync — `lib/builder-sync/` package: `ast-mapper.ts` HTML parser with 2-strategy detection (annotated data-section-id + structural content-root analysis), `findContentRoot()` deep unwrap with table/tbody transparency, `isColumnGroup()` dynamic column detection (6 heuristics: shared class, %-width sum, px-width sum, inline-block/float, TD siblings, TR parent), `parseInlineStyle()` quote-aware CSS parser, ESP token preservation pipeline (`extractEspTokens`/`restoreEspTokens` for Liquid/Handlebars/AMPscript/ERB with `{0,2000}` ReDoS caps), `internalizeStructuralEsp()` relocates structural-level conditionals from around `<tr>` into `<td>` cells (200 token cap, `{0,10000}` tr content cap), `capturePrecedingContent()` for comment/text node roundtrip, `SectionNode.precedingContent` field; `sync-engine.ts` debounced bidirectional sync (500ms code→builder, 200ms builder→code) with conflict resolution (builder wins), template shell capture on successful parse; `section-markers.ts` strips `data-section-id`/`data-slot-name`/`data-component-id`/`data-component-name` with matched-quote regex; `use-builder.ts` full assembler rewrite — `processSection()` structure-preserving DOM processing (slot fills via selector matching with CTA/image/text handlers, `isSafeUri()` scheme validation, 13-token `TOKEN_CSS_MAP` additive style merging, HTML attribute injection with `on*`/`style`/dangerous-URI blocking, CSS class addition preserving existing classes), `assembleDocument()` template-shell-aware assembly via `findContentRoot` injection or default email shell, `buildResponsiveCss()` 6-rule mobile override system (stack/images/font/hide/padding/align), `buildDarkModeCss()` `@media (prefers-color-scheme:dark)` + `[data-ogsc]` rules with `sanitizeCssProperty()` name validation, `wrapMsoGhostTable()` ghost table pattern, scoped section CSS with `@import`/`@font-face url()` stripping + `} selector {` handling, `sanitizeCssValue()` blocking `expression()`/`behavior:`/`url(javascript|vbscript|data:text/html)`; `visual-builder-panel.tsx` accepts `templateShell` prop + bounded component cache (50-entry FIFO); `types/visual-builder.ts` extended `ResponsiveOverrides` (mobileHide/mobilePaddingOverride/mobileTextAlign) + `SectionNode.precedingContent`; 109 frontend tests (83 builder-sync + 26 existing), `make check-fe` green). Phase 25 Platform Ecosystem & Advanced Integrations IN PROGRESS (25.1 Plugin Architecture DONE — manifest validation, directory discovery, typed registry per plugin_type; 25.2 Plugin Sandbox & Lifecycle DONE — stdlib blocklist, timeout/error isolation, health monitoring, auto-disable; 25.3 Tolgee TMS DONE — client, key extraction, locale builds, RTL handling; 25.4 Tolgee Frontend DONE — translation panel, locale preview, QA matrix, connection dialog; 25.5 Kestra Workflows DONE — client, 6 task wrappers, 4 YAML flow templates, execution polling; 25.6 Penpot Design Pipeline DONE — CSS-to-email converter, component extraction, design sync protocol; 25.7 Typst Report Generator DONE — QA/approval/regression PDF reports with Redis caching; 25.8 Ecosystem Dashboard DONE — unified tab navigation with SWR hooks for all integrations; 25.9 Tests & Documentation DONE — 248 tests across 6 modules (77 plugin + 43 Tolgee + 41 workflow + 24 Penpot + 20 reporting + 43 frontend ecosystem), sample plugin fixture, ADR-012 Platform Ecosystem Architecture; 25.10 Template Learning Pipeline DONE; 25.11 Automatic Skill Extraction DONE; 25.12 Template-to-Eval Pipeline DONE; 25.13 Deliverability Intelligence DONE; 25.14 Multi-Variant Campaign Assembly DONE; remaining: 25.15 tests for 25.10-25.14). Phase 26 Email Build Pipeline Performance & CSS Optimization COMPLETE (26.1 Eliminate Redundant CSS Inlining DONE — `optimize_css()` pre-build pipeline, stages 1-5 only, `MaizzleBuildNode` optimize→build→sanitize flow; 26.2 Per-Build CSS Compatibility Audit DONE — `CSSAuditCheck` 14th QA check with per-client compatibility matrix, `PropertyStatus` enum, `CSSAuditPanel` frontend with coverage bars + filterable matrix + conversion details, `CSSAuditDetails` type, 7 backend tests; 26.3 Template CSS Precompilation DONE — `TemplatePrecompiler` with `precompile()`/`precompile_all()`/`is_stale()`, `CSS_PREOPTIMIZED_MARKER` for build-time skip detection, `GoldenTemplate` precompilation fields, `TemplateRegistry` auto-precompile on load + uploaded, `TemplateAssembler` `dc_replace()` swap, `MaizzleBuildNode` marker-based CSS skip, `POST /api/v1/templates/precompile` admin endpoint, 7 new tests; 26.4 Consolidated Sidecar CSS Pipeline DONE — `postcss-email-optimize.js` PostCSS plugin with ontology-driven elimination/conversion, Lightning CSS minification, `scripts/sync-ontology.js` YAML→JSON sync, `MaizzleBuildNode` passes `target_clients` to sidecar, `EmailEngineService._call_builder()` returns optimization metadata, 7 backend tests + 5 vitest sidecar tests; 26.5 Tests & Documentation DONE — shared conftest with 15 golden templates + 21 component seeds, `test_optimize_css.py` 18 tests, `test_pipeline_equivalence.py` 10 regression tests across all templates + components, `test_performance_benchmark.py` 9 benchmarks with `make bench`, expanded `test_css_audit.py` to 15 tests, expanded `test_precompiler.py` to 14 tests, expanded `postcss-email-optimize.test.js` to 17 tests with ontology sync validation; ALL 5/5 DONE). Phase 27 Email Client Rendering Fidelity & Pre-Send Testing COMPLETE (27.1 Expand Email Client Emulators DONE — 8 emulators, 14 rendering profiles, 44 tests; 27.2 Rendering Confidence Scoring DONE — 4-signal scorer, `GET /confidence/{client_id}`, `RENDERING__CONFIDENCE_ENABLED`; 27.3 Pre-Send Rendering Gate DONE — `RenderingSendGate` backend service + `GatePanel`/`GateClientRow`/`GateSummaryBadge` frontend, wired into export + push-to-ESP dialogs, admin override; 27.4 Emulator Calibration Loop DONE — `EmulatorCalibrator` with ODiff + EMA α=0.3, `CalibrationSampler`, `RENDERING__CALIBRATION__ENABLED`, 13 tests; 27.5 Headless Email Sandbox DONE — SMTP-based Mailpit/Roundcube capture, `DOMDiff`, `RENDERING__SANDBOX__ENABLED`, 25 tests; 27.6 Frontend Rendering Dashboard & Tests DONE — `RenderingDashboard` with preview grid (14 profiles) + confidence summary bar + calibration health panel + full-size preview dialog, `ConfidenceBar` shared component, `use-rendering-dashboard.ts` SWR hooks, 27 frontend tests across 3 test files, Dashboard tab on `/renderings` page). Phase 28 Export Quality Gates & Approval Workflow COMPLETE (28.1 QA Enforcement in Export Flow DONE — `ExportQAGate` with per-project config, `ExportQAConfig` JSON column, `POST /export/pre-check` dry-run endpoint, admin-only `skip_qa_gate` override with audit log, 15 tests; 28.2 Approval Workflow → Export Integration DONE — `ExportApprovalGate` third gate in `ConnectorService.export()`, `Project.require_approval_for_export` boolean column, `ApprovalRepository.get_latest_by_build_id()`, `ApprovalRequiredError`, `skip_approval` admin override with audit log, pre-check includes approval result, 14 tests; 28.3 Approval Frontend UI DONE — `ApprovalRequestDialog` submit-for-approval from workspace Deliver menu + export/push dialogs, `ApprovalGatePanel` blocks export/push when approval required, `useExportPreCheck` combined QA+rendering+approval pre-check hook, `types/approval.ts` domain types matching backend schemas, approval gate wired into `ExportDialog` + `PushToESPDialog` with `buildId` threading, 14 frontend tests). Phase 30 End-to-End Testing & CI Quality COMPLETE (30.1 Playwright E2E User Journey Suite DONE — 32 tests across 9 spec files (auth, dashboard, workspace, builder, export, approval, design-sync, collaboration, ecosystem), shared fixtures (auth + API helper + constants), global setup/teardown with test project isolation, `make e2e-report` target, moved playwright.config.ts to web root; 30.2 Visual Regression Testing DONE — `BaselineGenerator` + `VisualRegressionRunner` with ODiff comparison against committed baselines, 5 golden templates × 14 profiles, `@pytest.mark.visual_regression`, `make rendering-baselines` + `make rendering-regression`, 9 tests; 30.3 Multi-Browser & CLI E2E Coverage DONE — Firefox + WebKit Playwright projects with `BROWSER` env var, per-spec browser skip annotations, builder DnD cross-browser hardening (Firefox dispatchEvent, WebKit focus/Meta key), collaboration WS timeout for Firefox, `make e2e-firefox` + `make e2e-webkit` + `make e2e-all-browsers` targets, CLI E2E testing documentation). Phase 29 Design Import Enhancements IN PROGRESS (29.2 Penpot Converter Integration DONE — `PenpotConverterService` orchestrates design-tree-to-email conversion with email skeleton + MSO conditionals + token-derived styles, `_NodeProps` supplementary visual properties from raw Penpot data, `node_to_email_html()` enhanced with INSTANCE/COMPONENT handling + `props_map` for font/bg/padding injection + `html.escape()` XSS prevention + `_sanitize_css_value()` CSS injection defense, hero image row detection in `_group_into_rows()`, `ScaffolderRequest.initial_html` pipes converter output through to LLM prompt, `DesignImportService` step 5.5 with graceful fallback + `_layout_to_design_nodes()`/`_tokens_to_protocol()` adapters + dynamic provider name in template description, `DESIGN_SYNC__PENPOT_CONVERTER_ENABLED` feature flag, 32 tests (17 converter + 15 integration); remaining: 29.1 brief-only template creation). Phase 31 HTML Import Fidelity & Preview Accuracy COMPLETE (31.1 Maizzle Passthrough DONE — `isPreCompiledEmail()` 4-heuristic detection, sidecar passthrough path skipping `render()`; 31.2 Inline CSS Ontology Pipeline DONE — PostCSS synthetic stylesheet for inline styles, shorthand expansion, design system token mapping; 31.3 Wrapper Metadata Preservation DONE — `WrapperInfo` dataclass captured by `TemplateAnalyzer`; 31.4 Wrapper Reconstruction DONE — `ensure_wrapper()` in `TemplateBuilder`, centering + MSO ghost tables; 31.5 Dark Mode Text Safety DONE — `ensureDarkModeContrast()` luminance-based color replacement, `sandbox="allow-same-origin"` on preview iframe; 31.6 Enriched Typography Tokens DONE — font_weights/line_heights/letter_spacings extraction + color_roles; 31.7 Image Asset Import DONE — `ImageImporter` with HTTP download, dimension detection, `<img>` rewriting; 31.8 Tests & Integration Verification DONE — `TokenPreview` schema gap fix, 32 new backend tests, 2 sidecar tests, 4 frontend component tests, 3 E2E specs, golden template fixture). Phases 32-36 COMPLETE (agent rendering intelligence, design token pipeline, CRAG gate, next-gen design-to-email, universal email design document). Phase 37 Golden Reference Library IN PROGRESS (37.1 golden component library DONE — 14 templates; 37.2 golden reference loader DONE — YAML-indexed loader, 18 tests; 37.3 wire into judge prompts DONE — `format_golden_section()` in 7 HTML judges with token budget, platform/category filtering, inverted framing, 22 tests; 37.4 re-run pipeline & measure DONE — `scripts/eval-compare-verdicts.py` per-criterion flip rate comparison, `make eval-rejudge` + `make eval-compare`, all 9 agents re-judged, 15/35 criteria flagged >20% flip rate, 14 tests; remaining: 37.5 human labeling). Phase 38 Pipeline Fidelity Fix COMPLETE (8 subtasks). Phase 39 Pipeline Hardening COMPLETE (7 subtasks — Figma enrichment, testing infrastructure, quality contracts, custom lint rules, component matcher, conformance gate)

---


> **Implementation status (Phases 0–10):** See [docs/PRD-implementation-status.md](docs/PRD-implementation-status.md)

---

## 1. Product Vision

### Problem

[REDACTED] serves clients across diverse email platforms (Braze, SFMC, Adobe Campaign, Taxi for Email) yet email development remains **fragmented, manual, and siloed between engagements**. Knowledge, components, and rendering fixes developed for one client are invisible to teams working with others. There is no platform designed for the multi-client, multi-platform agency model.

### Vision

A self-hosted, CMS-agnostic platform that centralises email innovation, prototyping, AI-assisted development, design tool integration, and cross-client QA into a single unified workflow. The Hub operationalises the **compound innovation effect**: every innovation, component, and pattern built for one client becomes available to all.

### Core Value Proposition

**"Build it once, use it everywhere, improve it continuously."**

Every piece of email development work becomes a reusable, testable, deployable asset — owned entirely by [REDACTED] with zero vendor lock-in.

---

## 2. Strategic Objectives

| # | Objective | Metric |
|---|-----------|--------|
| 1 | **100% [REDACTED]-Owned IP** | Zero SaaS dependencies; entire stack open-source |
| 2 | **Centralise Innovation** | Single platform for R&D + production across all clients |
| 3 | **CMS-Agnostic Pipeline** | Modular connectors: Braze (V1), SFMC, Adobe, Taxi (V2) |
| 4 | **AI-Powered Development** | 9 specialised sub-agents; 70% local LLM / 30% cloud hybrid |
| 5 | **Cost-Optimised Operations** | Cloud AI spend capped at £60–150/month |
| 6 | **Design-to-Code Bridge** | Figma integration for frictionless handoff (Phase 2) |
| 7 | **GDPR-First Security** | Zero PII in Hub; all data flows anonymised |
| 8 | **Fallback-First QA** | Every innovation ships with verified HTML fallback |

---

## 3. Target Users

### Primary Personas

| Persona | Role | Key Goals | Pain Points |
|---------|------|-----------|-------------|
| **Email Developer** | Builds and optimises email HTML | Ship quality campaigns faster; reuse components; automate tedious tasks | Manual QA 2–3hrs/template; Outlook issues found post-send; no shared library |
| **Email Designer** | Creates Figma layouts; approves visual direction | Handoff without fidelity loss; see responsive/dark variants early | Static image handoffs; code never matches design; no live preview |
| **Project/Campaign Lead** | Manages client delivery timeline | Faster turnaround; consistent quality; rendering intelligence | Builds take 3–5 days; no cross-client compatibility visibility |
| **Client Stakeholder** | Approves templates before send | See actual email (not screenshots); structured feedback; audit trail | Approval via email chains; ambiguous feedback; no formal workflow |
| **QA/Testing Lead** | Validates rendering across clients | Automated testing; structured defect reporting | Manual testing across 20+ clients is 3–4 hours per template |

### Secondary Personas

| Persona | Role |
|---------|------|
| **Client IT/Compliance** | GDPR, accessibility, authentication compliance verification |
| **Team New Hires** | Onboards via searchable knowledge base + documented components |
| **Email Team Leadership** | Measures velocity gains, innovation feasibility, resource allocation |

---

## 4. V1 Feature Requirements

### 4.1 Authentication & Workspace Management

**API:** `/api/v1/projects`, `/api/v1/orgs`

- JWT authentication with HS256 signing
- RBAC roles: `admin`, `developer`, `viewer`
- Client-level data isolation (developers see only assigned clients)
- Project workspace scoping with team assignments
- Brute-force protection with exponential backoff

**Acceptance Criteria:**
- Users authenticate and receive scoped JWT
- Developers assigned to Client A cannot access Client B data
- All API calls enforce RBAC validation

### 4.2 Monaco Code Editor + Live Preview

- VS Code-quality embedded editor (Monaco)
- Split-pane layout: code (left) + live preview (right)
- Email-specific syntax highlighting (HTML, CSS, Liquid, AMPscript)
- Can I Email CSS property autocomplete warnings
- Real-time rebuild on change (≤500ms preview update)
- Dark mode preview toggle
- Device preview (desktop, mobile, persona-based)

**Acceptance Criteria:**
- Unsupported CSS property triggers autocomplete warning
- Code change → preview updates without page refresh within 500ms
- Dark mode toggle shows email in both contexts

### 4.3 Maizzle Email Build Pipeline

**API:** `/api/v1/email`

- Compile-on-save via Maizzle sidecar service
- Tailwind CSS inlining + unused class purging
- Responsive transforms (mobile stacking, media queries)
- Plaintext generation
- Production vs development configs
- Build output: production-ready HTML

**Acceptance Criteria:**
- Template with Tailwind compiles to inline CSS within 1 second
- Build output passes W3C email HTML validation
- Plaintext auto-generated for all emails

### 4.4 Component Library v1

**API:** `/api/v1/components`

- 5–10 pre-tested components (header, CTA, product card, footer, hero block)
- Semantic versioning (v1.0.0, v1.1.0)
- Dark mode variants per component
- Outlook-compatible fallback variants
- Component browser with search, code snippets, compatibility matrix
- Cascading inheritance: Global → Client → Project

**Acceptance Criteria:**
- Component renders correctly in light AND dark mode across major clients
- Version update notifies projects using older version
- Browser shows which versions are used where

### 4.5 AI Orchestrator & Agents (V1: 3 agents)

**Infrastructure:** `app/ai/` protocol layer + provider registry

#### Scaffolder Agent
- **Input:** Campaign brief (natural language)
- **Output:** Complete Maizzle template with Tailwind, MSO conditionals, responsive stacking
- **Model:** Claude Opus 4 (complex), Sonnet 4 (iterative)
- **Gate:** Developer review before merge

#### Dark Mode Agent
- **Input:** Email HTML
- **Output:** Enhanced HTML with dark mode media queries, colour token remapping, forced dark mode fixes
- **Patterns:** `@media (prefers-color-scheme: dark)`, `[data-ogsc]`/`[data-ogsb]`
- **Model:** Sonnet 4 (standard), Opus 4 (edge cases)

#### Content Agent
- **Input:** Existing content or brief
- **Output:** Refined copy preserving per-client brand voice
- **Tasks:** Subject lines, preheaders, CTA text, body copy
- **Model:** Local LLMs (70%), Cloud (30% for creative tasks)

**Acceptance Criteria:**
- Scaffolder generates valid HTML from brief within 2 minutes
- Generated HTML passes QA gate checks
- Content agent generates 3 subject line options on demand

### 4.6 Export Pipeline & Braze Connector

**API:** `/api/v1/connectors`

- Raw HTML export (production-ready, inlined CSS)
- Braze Content Block export with Liquid template wrapper
- Connected Content placeholder support
- Deployment history (timestamp, version, format, status)

**Acceptance Criteria:**
- One-click Braze export creates Content Block within 2 minutes
- Liquid personalisation tokens preserved in export
- Export history searchable by date, template, version

### 4.7 10-Point QA Gate System

**API:** `/api/v1/qa`

| # | Check | Pass Criteria |
|---|-------|--------------|
| 1 | HTML Validation | No critical errors |
| 2 | CSS Support Matrix | All properties supported or fallback provided |
| 3 | File Size | HTML < 102KB (Gmail clipping) |
| 4 | Dark Mode Audit | Readable in light + dark; forced dark handled |
| 5 | Accessibility | Contrast ≥ 4.5:1 (AA); alt text present; semantic structure |
| 6 | Fallback Verification | Email readable without progressive enhancements |
| 7 | Link Validation | No dead links; HTTPS enforced; unsubscribe present |
| 8 | Spam Score | Score < 3.0; image-to-text ratio acceptable |
| 9 | Image Optimization | Explicit dimensions; optimised formats |
| 10 | Brand Compliance | Colour, typography, logo placement match guidelines |

**Gate Behaviour:**
- Template cannot export unless all mandatory checks pass
- Optional checks overridable by senior team with documented reason
- All overrides logged with user, timestamp, reason

### 4.8 RAG Knowledge Base

**Infrastructure:** `app/knowledge/` with pgvector

- Data sources: Can I Email database, email dev best practices, team documentation
- Natural language search
- Knowledge Agent: LLM-synthesised answers from indexed content
- Team can add entries via slash command
- Weekly refresh of public sources

**Acceptance Criteria:**
- "dark mode Outlook" returns 10+ relevant docs
- New team entries indexed and searchable within 1 hour

### 4.9 Smart Agent Memory System

**Infrastructure:** `app/memory/` with pgvector + Redis

The Hub's AI agents are not stateless tools — they learn, remember, and compound knowledge across sessions, projects, and clients. The Smart Agent Memory System gives every agent persistent, searchable, project-scoped memory that improves with every interaction.

#### 4.9.1 Conversation Persistence

- Thread-based conversation storage with full message history
- `Conversation`, `ConversationMessage`, `ConversationSummary` models in PostgreSQL
- Multi-turn context: agents remember prior instructions within a session
- Conversation search: find past interactions by content, agent type, or project
- Token-counted messages for context budget management

**Acceptance Criteria:**
- Developer resumes a conversation from yesterday — agent has full prior context
- Conversations are project-scoped: Client A threads invisible to Client B users
- Search "dark mode fix" returns relevant past agent conversations

#### 4.9.2 RAG-Augmented Chat

- Every chat completion query searches the knowledge base before responding
- Relevant document chunks injected as system context into agent prompts
- Citations returned alongside agent responses (source document + chunk reference)
- Hybrid retrieval: vector similarity + full-text search + RRF fusion (existing `app/knowledge/` pipeline)

**Acceptance Criteria:**
- Agent asked about Outlook rendering automatically retrieves Can I Email data
- Agent responses include source citations from the knowledge base
- No knowledge base query adds more than 200ms latency to chat responses

#### 4.9.3 Agent Memory Entries

- Per-agent-type learned facts stored as embedded entries in pgvector
- Memory types: `procedural` (learned patterns), `episodic` (session logs), `semantic` (durable facts)
- Agents write memories after significant interactions (rendering fix discovered, client preference noted, build pattern established)
- Memory retrieval integrated into agent context loading — relevant memories injected before each response
- `memory_entries` table: `id | agent_type | memory_type | content | embedding(1024) | project_id | metadata(jsonb) | decay_weight | created_at`

**Acceptance Criteria:**
- Dark Mode Agent discovers a Samsung Mail rendering fix → stores as procedural memory
- Next time any agent encounters Samsung Mail, the fix is retrieved automatically
- Agent memories are filterable by type, agent, project, and recency

#### 4.9.4 Context Windowing & Summarisation

- Token budget management: configurable context window per agent (default 8K tokens)
- Automatic summarisation of older messages when context approaches limit
- Summary chain: full messages → compressed summary → archived (searchable but not in active context)
- Priority retention: system prompts and recent messages always preserved; middle messages summarised first

**Acceptance Criteria:**
- 50-message conversation maintains coherent context without exceeding token budget
- Summarised messages remain searchable via conversation search
- Agent performance does not degrade on long conversations

#### 4.9.5 Temporal Decay & Memory Compaction

- Configurable decay half-life per memory type (default: 30 days for episodic, never for procedural)
- Stale memories down-ranked in retrieval results, not deleted
- Periodic compaction job merges redundant memories (e.g., 10 similar Outlook fixes → 1 consolidated entry)
- Evergreen memories (client preferences, architectural decisions) exempt from decay
- Background task via existing `DataPoller` infrastructure

**Acceptance Criteria:**
- A rendering fix from 6 months ago ranks lower than one from last week (unless marked evergreen)
- Compaction reduces memory count by 30%+ without losing unique information
- Memory storage grows sub-linearly relative to conversation volume

#### 4.9.6 Cross-Agent Memory Sharing

- Shared memory pool scoped by project: all agents within a project read from the same memory store
- Agent-specific memories tagged by source agent but readable by all
- Compound knowledge effect: Scaffolder learns a layout pattern → QA Agent knows to test for it → Dark Mode Agent knows how to adapt it
- Memory propagation events: when a high-confidence memory is created, relevant agents are notified in their next invocation
- Cross-project memories available at organisation level for universal patterns (e.g., "Outlook always clips at 102KB")

**Acceptance Criteria:**
- Knowledge Agent stores a rendering fix → Dark Mode Agent retrieves it in the next session
- Cross-project memory: a fix discovered on Client A is available when working on Client B
- Memory sharing respects project isolation — client-specific preferences don't leak

#### 4.9.7 DCG-Based Lightweight Agent Memory (Research — 2026-03-06)

Research into leveraging Destructive Command Guard (dcg) as a lightweight cross-agent memory layer, since dcg already sits in the critical path of every agent's command execution and auto-detects which agent is calling.

**Current dcg infrastructure (already exists):**
- Shared SQLite history DB (`src/history/`) storing `agent_type`, `session_id`, `command`, `outcome`, `working_dir` per evaluation — indexed and queryable
- Agent detection (`src/agent.rs`) identifying Claude Code, Gemini CLI, Aider, Codex, Copilot CLI via env vars and parent process inspection
- MCP server (`src/mcp.rs`) with stdio JSON-RPC — currently exposes `check_command`, `scan_file`, `explain_pattern`
- Per-agent config overrides with trust levels

**Proposed: 2 new MCP tools on the existing dcg server (~150 lines of Rust):**

| Tool | Purpose |
|------|---------|
| `store_note` | Agent writes a key/value observation (key, value, project). Agent identity auto-detected. |
| `recall_notes` | Any agent reads notes filtered by key, agent, project. Returns array of `AgentNote` objects. |

**Storage:** Append-only JSONL at `.dcg/agent_notes.jsonl` per project. No SQLite migration, no new dependencies, no daemon. POSIX-atomic for lines < PIPE_BUF (4KB).

**Key namespace convention:**
- `project.*` — project structure observations (e.g., `project.deletion_pattern`)
- `safety.*` — safety-relevant discoveries (e.g., `safety.cascade_risk`)
- `workflow.*` — workflow preferences (e.g., `workflow.test_command`)
- `config.*` — configuration observations (e.g., `config.env_required`)

**Size limits:** 1024 char value, 500 notes max per project, 128 char key.

**Example flow:**
```
Claude Code calls:  store_note(key="project.deletion_pattern", value="uses soft deletes via SoftDeleteMixin")
Gemini CLI calls:   recall_notes(key="project.deletion_pattern")
  -> gets: [{ agent: "claude-code", value: "uses soft deletes via SoftDeleteMixin", ... }]
```

**Relationship to 4.9.6:** This is a complementary lightweight layer. Section 4.9.6 describes the full pgvector-backed memory system within the Hub application. The dcg MCP approach provides immediate cross-agent memory at the shell/tool layer with zero infrastructure cost — agents that don't use the Hub's API (e.g., running raw CLI commands) still benefit. The two layers can coexist: dcg for lightweight observations during command evaluation, Hub memory for rich semantic memories with embeddings and decay.

**Effort:** ~2-3 hours implementation + tests. 0 new dependencies. 0 schema migrations.

**Reference:** Full PRD at `destructive_command_guard/docs/prd-agent-memory-sharing.md`. Implementation plan at `destructive_command_guard/TODO.md`.

### 4.10 Client Approval Portal

**API:** `/api/v1/approvals`

- Viewer-scoped JWT for client stakeholders
- Live email preview (not screenshots)
- Section-level feedback and comments
- Formal approve / request changes workflow
- Version comparison (side-by-side diff)
- Time-stamped audit trail

**Acceptance Criteria:**
- Client sees live preview, adds comments, approves with timestamp
- Developers notified of feedback immediately
- Full approval history with audit trail

### 4.11 Test Persona Engine

**API:** `/api/v1/personas`

- Pre-configured profiles: device, email client, dark mode, viewport
- 8 default personas (Gmail desktop, Outlook 365, iPhone, Samsung dark, etc.)
- One-click persona preview
- Custom persona creation

**Acceptance Criteria:**
- Select "iPhone Dark Mode" → preview shows email as rendered on iPhone in dark mode
- Template looks correct across all default personas

### 4.12 Rendering Intelligence Dashboard

- Client support matrices (which clients support which innovations)
- Template quality scores (accessibility, file size, rendering consistency)
- Innovation feasibility reports ("AMP works in X% of audience")
- Exportable reports for client presentations

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Target |
|--------|--------|
| Maizzle compile time | ≤ 1 second |
| Preview update | ≤ 500ms after code change |
| API latency (p95) | ≤ 200ms |
| AI Scaffolder first draft | ≤ 2 minutes |
| QA gate full run | ≤ 5 minutes per template |
| Page load | ≤ 2 seconds |
| Production HTML size | ≤ 102KB |

### 5.2 Scalability

- 50+ concurrent users without degradation
- 10,000+ templates across all clients
- 1,000+ knowledge base entries with sub-second search
- 500+ components queryable without delay

### 5.3 Security & Compliance

- JWT HS256 authentication; no plaintext passwords
- AES-256 encryption for API credentials at rest
- Rate limiting per user and endpoint
- GDPR: Zero PII; anonymised AI logs (90-day retention)
- PostgreSQL row-level security for client isolation
- WCAG AA accessibility for Hub UI
- All API calls audit-logged (no credentials in logs)

### 5.4 Availability

- 99.5% uptime SLA
- Graceful degradation (cloud AI → local LLMs; Litmus → Playwright)
- Full recovery ≤ 10 minutes (container redeploy)
- Automated PostgreSQL backups

### 5.5 Maintainability

- Vertical slice architecture (self-contained feature modules)
- Docker Compose deployment with versioned images
- Structured logging (`domain.component.action_state`)
- Environment-based config (dev, staging, production)

---

## 6. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | FastAPI + async SQLAlchemy + PostgreSQL + Redis | Open-source, high-performance async API |
| Frontend | Next.js 16 + React 19 + Tailwind CSS + shadcn/ui | Modern stack; no library lock-in |
| Auth | JWT HS256 + RBAC | In-house; no Auth0 dependency |
| AI | Local LLMs (Ollama/vLLM) + Claude/GPT-4o APIs | Hybrid: 70% local (free) / 30% cloud |
| Email Build | Maizzle (primary) | Full HTML control; Tailwind-native |
| Vector Search | pgvector (PostgreSQL) | Open-source; no Pinecone fees |
| Infrastructure | Docker Compose + nginx + Alembic | Self-hosted on [REDACTED] servers |
| Testing | Playwright (core) + Litmus/EoA (optional) | Built-in speed + optional comprehensive coverage |

---

## 7. Architecture

### Repository Structure

```
email-hub/
├── app/                    # Backend (FastAPI, VSA)
│   ├── core/               # Infrastructure (config, db, logging, middleware)
│   ├── shared/             # Cross-feature (pagination, timestamps, errors)
│   ├── auth/               # JWT + RBAC
│   ├── projects/           # Client orgs, workspaces, team assignments
│   ├── email_engine/       # Maizzle build orchestration
│   ├── components/         # Versioned email component library
│   ├── qa_engine/          # 10-point QA gate (10 check modules)
│   ├── connectors/         # ESP connectors (Braze V1)
│   ├── approval/           # Client approval portal
│   ├── personas/           # Test persona engine
│   ├── ai/                 # AI protocol layer + provider registry
│   ├── knowledge/          # RAG pipeline (pgvector)
│   └── streaming/          # WebSocket pub/sub
├── cms/                    # Frontend (Next.js 16 + React 19)
├── email-templates/        # Maizzle project (layouts, templates, components)
├── services/
│   └── maizzle-builder/    # Node.js sidecar (Express, port 3001)
├── alembic/                # Database migrations
├── docker-compose.yml      # Full stack orchestration
└── nginx/                  # Reverse proxy
```

### Key Architectural Patterns

- **Vertical Slice Architecture:** Each feature owns models → schemas → repository → service → routes → tests
- **Multi-tenancy:** Client-level data isolation via `client_org_id` foreign keys + RBAC
- **CMS-Agnostic Connectors:** Decoupled email creation from delivery platform
- **Protocol-based AI:** Model-agnostic provider registry; swap providers without code changes
- **Sidecar Pattern:** Maizzle builds delegated to Node.js service via HTTP
- **Fallback-First:** Every innovation requires verified HTML fallback before export

---

## 8. Implementation Roadmap

### Sprint 1 — Foundation (Weeks 1–2)
- Auth, workspace management, project RBAC
- Monaco editor integration + Maizzle live preview
- Test persona engine
- **Exit Criteria:** Developer writes email in browser, sees live preview, switches personas

### Sprint 2 — Intelligence (Weeks 3–5)
- AI orchestrator + 3 V1 agents (Scaffolder, Dark Mode, Content)
- Component library v1 (5 components)
- Braze connector
- QA gate system (10 checks)
- RAG knowledge base v1
- **Exit Criteria:** Generate email from brief → refine → QA check → export to Braze

### Sprint 3 — Client Experience (Weeks 6–7)
- Client approval portal
- Rendering intelligence dashboard
- UI polish + performance optimisation
- Team onboarding
- **Exit Criteria:** Clients approve via live preview; dashboard shows innovation feasibility

### V2 Phases
- **V2 Phase 1:** Figma integration, SFMC/Adobe/Taxi connectors, advanced AI agents
- **V2 Phase 2:** Localisation, collaborative editing, visual conditional logic, AI image generation

---

## 9. Success Metrics

### Team Productivity

| Metric | Baseline | 3-Month Target | 6-Month Target |
|--------|----------|----------------|----------------|
| Campaign build time | 3–5 days | 1–2 days | < 1 day |
| Component reuse rate | 0% | 30–40% | 60%+ |
| Manual QA hours | 2–3 hrs/template | < 15 min | < 10 min |
| Rendering defects reaching client | 10–15% | < 5% | < 1% |
| Knowledge base entries | 0 | 200+ | 500+ |
| Cloud AI monthly spend | N/A | < £150 | < £150 |
| New developer onboarding | 2–3 weeks | < 1 week | < 1 day |

### Client Outcomes

| Metric | Baseline | Target |
|--------|----------|--------|
| Approval cycle | 3–5 days | < 24 hours |
| Time to launch variants | 1 day/variant | < 1 hour |
| Campaign velocity | 1 per 5 days | 2–3 per 5 days |

### Business Impact

| Metric | Target |
|--------|--------|
| Cost per campaign | Reduced 40–60% via automation + reuse |
| Competitive positioning | Innovation partner, not production vendor |
| IP value | Growing asset (components + knowledge + AI skills) |

---

## 10. Cost Projections

### Build Investment
- 2–3 experienced developers, 5–7 weeks
- AI-assisted development accelerates delivery

### Monthly Operational Costs

| Category | Estimate |
|----------|----------|
| Server infrastructure | £100–300 |
| GPU for local LLMs | £150–400 |
| Cloud AI APIs (30%) | £60–150 |
| Litmus/EoA (optional) | £0–400 |
| Software licences | **£0** |
| **Total** | **£310–1,250/month** |

vs. SaaS alternatives: £50K–150K+/year

---

## 11. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Outlook rendering edge cases | High | Medium | Dedicated Outlook Fixer agent; MSO conditional library; Litmus testing |
| Cloud AI cost overrun | Medium | Low | 70/30 local/cloud routing; budget caps; prompt caching |
| Team adoption resistance | Medium | High | Gradual onboarding; parallel workflow; visible productivity wins early |
| Email client CSS fragmentation | High | Medium | Can I Email integration; QA gate catches issues pre-export |
| Knowledge base cold start | Medium | Low | Seed with Can I Email + existing team documentation |
| Braze API rate limits | Low | Medium | Queue + batch export requests; retry with backoff |

---

## 12. Competitive Differentiation

| Aspect | SaaS Competitors | [REDACTED] Hub |
|--------|-----------------|-----------|
| Target user | Single brand, single CMS | Multi-client agency, any CMS |
| AI capability | Generic content generation | 9 specialised email dev agents |
| Developer experience | Visual builders | Full code control (Monaco + Maizzle) |
| Knowledge leverage | Within single brand | Across all clients (RAG) |
| Component reuse | Within one brand | Global → Client → Project cascading |
| Rendering intelligence | "Does it render?" | "What % of audience supports this?" |
| Cost model | Per-seat SaaS (£2K–10K+/yr/user) | Self-hosted (£0 licence cost) |
| Vendor lock-in | CMS + tool + templates | None; everything exportable |

---

## Appendix: Definition of Done

Every feature must satisfy before shipping:

- [ ] Code review: 2 developers approve
- [ ] Unit tests: ≥80% coverage; critical paths tested
- [ ] Integration tests: no breaking changes to other modules
- [ ] Manual QA: acceptance criteria signed off
- [ ] Accessibility: WCAG AA; keyboard navigation
- [ ] Performance: meets latency targets
- [ ] Security: auth/RBAC enforced; no credential leaks
- [ ] Documentation: API docs, inline comments for complex logic
- [ ] Deployment: backwards-compatible migrations; rollback plan
