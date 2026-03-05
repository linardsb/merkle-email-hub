# Product Requirements Document (PRD)

## Merkle Email Innovation Hub

**Classification:** Internal / Confidential
**Version:** 2.3
**Date:** 2026-03-05
**Status:** V1 Complete — Sprint 3 done (3.1-3.5); V2 tasks 4.2-4.5, 4.8-4.13 done; remaining: 4.1 (6 agents), Phase 5 (eval pipeline)

---

## 0. Implementation Status

> Last updated: 2026-03-05

### Completed

| Task | Description | Key Deliverables |
|------|-------------|-----------------|
| 0.1 | Database migrations | All email-hub models migrated; PostgreSQL RLS policies on `client_org_id` |
| 0.2 | shadcn/ui component library | 16 foundational components installed; Merkle design tokens wired |
| 0.3 | OpenAPI TypeScript SDK | `cms/packages/sdk/` generates typed client for 61 endpoints; offline generation via `make sdk` |
| 0.4 | Authenticated API client layer | `authFetch` with timeout (30s/120s), 401 redirect interceptor, 429 retry with backoff, 8 domain-specific SWR hooks (`use-projects`, `use-orgs`, `use-components`, `use-email`, `use-qa`, `use-personas`, `use-approvals`, `use-connectors`), `ApiError` class, mutation fetchers |
| 1.1 | Project dashboard page | Dashboard at `/(dashboard)/` with stats cards, project grid, org data; SWR data fetching from live API |
| 1.2 | Project workspace layout | 3-pane resizable workspace at `/projects/[id]/workspace` using `react-resizable-panels` v4; collapsible AI chat panel; full-screen layout (sidebar extracted to dashboard route group); project access verified via backend API |
| 1.3 | Monaco editor integration | Monaco with Maizzle/HTML/CSS/Liquid syntax highlighting; CSS diagnostics for Can I Email warnings; bracket matching, code folding, minimap, search/replace; Ctrl+S save keybinding; editor toolbar with line/col, warning count, minimap/wordwrap toggles; custom dark/light themes |
| 1.6 | Template CRUD + persistence | `app/templates/` VSA module with 9 REST endpoints; `Template` + `TemplateVersion` models with soft delete and immutable versioning; auto-increment version numbers; restore creates new version; project access control via `ProjectService.verify_project_access()`; Alembic migration for both tables; frontend template hooks (`use-templates.ts`) with SWR, save indicator, template selector |
| 2.1 | Wire AI provider to LLM | Anthropic SDK adapter + OpenAI-compatible adapter (5 providers: openai, ollama, vllm, litellm, anthropic); model tier routing (complex/standard/lightweight → concrete models); PII sanitization (email, phone, SSN, credit card patterns); output validation; ChatService with SSE streaming; `POST /v1/chat/completions` with auth + rate limiting |
| 1.4 | Maizzle live preview | Compile-on-save via `POST /api/v1/email/preview` + manual Compile button; sandboxed iframe (`srcdoc`, `sandbox=""` — fully sandboxed, no scripts or same-origin access); viewport toggles (desktop 100%/tablet 768px/mobile 375px); dark mode preview (injected `color-scheme` style); zoom controls (50–200% discrete steps); content sanitized before API call; preview auto-resets on template switch |
| 2.2 | Scaffolder agent | First AI agent in `app/ai/agents/scaffolder/`; system prompt encoding Maizzle/table-layout/MSO/dark-mode/accessibility constraints; HTML extraction from LLM markdown code blocks; server-side XSS sanitization (script, event handlers, javascript:, iframe, data: URIs) preserving MSO conditionals; optional in-memory 10-point QA validation; `POST /api/v1/agents/scaffolder/generate` with SSE streaming support; 5 req/min rate limit; admin/developer RBAC; 19 unit tests |
| 2.3 | Dark Mode agent | Second AI agent in `app/ai/agents/dark_mode/`; system prompt for dark mode CSS injection, Outlook `[data-ogsc]`/`[data-ogsb]` overrides, colour remapping; accepts existing HTML + optional colour overrides/preserve lists; `"standard"` task tier; duplicated XSS sanitization pipeline; QA integration with DarkModeCheck prioritised first; `POST /api/v1/agents/dark-mode/process` with SSE streaming; 5 req/min rate limit; admin/developer RBAC; 23 unit tests |
| 2.5 | AI chat sidebar UI | Full chat interface replacing placeholder in workspace bottom panel; agent toggle bar (Chat, Scaffolder enabled; Dark Mode, Content disabled with "Soon" badge); `useChat` hook with SSE streaming via `fetch` + `ReadableStream` (not EventSource — POST + auth headers required); endpoint routing (chat → `/v1/chat/completions`, scaffolder → `/api/v1/agents/scaffolder/generate`); message bubbles with fenced code block parsing via regex; "Copy" + "Apply to Editor" buttons on HTML code blocks; streaming indicator (pulsing cursor + "Thinking..."); uncontrolled textarea with auto-resize, Enter-to-send, Shift+Enter newlines; Stop button aborts stream; Clear button resets conversation; session-only state (no persistence); 17 i18n keys; all semantic Tailwind tokens |
| 1.5 | Test persona engine UI | Alembic data migration seeding 8 persona presets (Gmail Desktop, Outlook 365, Apple Mail Dark, iPhone Mail, Samsung Mail Dark, Outlook Classic, Gmail Mobile, Yahoo Mail); `PersonaSelector` dropdown component with shadcn `DropdownMenu` showing device icon, viewport width, dark mode indicator per persona; `PreviewIframe` accepts `viewportWidthOverride` for persona-driven custom widths; `PreviewPanel` manages persona state — selecting persona sets viewport + dark mode, manual toggle deselects persona; `usePersonas()` SWR hook wired into workspace page; 5 i18n keys; all semantic Tailwind tokens |
| 2.4 | Content agent | Third AI agent in `app/ai/agents/content/`; 8 operations via single endpoint with `operation` discriminator (subject_line, preheader, cta, body_copy, rewrite, shorten, expand, tone_adjust); plain text output with `---` delimiter for multiple alternatives; subject_line auto-generates 5 alternatives; operation-to-tier routing (shorten/expand → lightweight, all others → standard); automatic spam trigger detection reusing QA engine's `SPAM_TRIGGERS` with context snippets; brand voice override support; `POST /api/v1/agents/content/generate` with SSE streaming; 5 req/min rate limit; admin/developer RBAC; 20 unit tests |
| 2.7 | Component library browser UI | `/(dashboard)/components/page.tsx` with responsive 3-column grid, debounced search (300ms), category filter pills, pagination (12/page); `ComponentCard` with sandboxed preview thumbnail (200px iframe), name, category badge, version; `ComponentDetailDialog` (max-w-3xl) with Preview/Source/Versions tabs — preview has dark mode toggle, source has copy-to-clipboard, versions show changelog; `ComponentPreview` reuses sandboxed iframe pattern (`sandbox=""` — fully sandboxed); loading skeletons, empty/error states; `/components` added to ROLE_PERMISSIONS (all roles); sidebar nav with Blocks icon; 28 i18n keys; all semantic Tailwind tokens |
| 2.6 | Component library v1 — backend | 10 production-ready email components seeded across 4 categories (structure, content, action, commerce, social); `app/components/data/seeds.py` with table-based layouts, inline CSS, `@media (prefers-color-scheme: dark)`, `[data-ogsc]`/`[data-ogsb]` Outlook overrides, MSO conditionals, `role="presentation"`; `app/components/sanitize.py` XSS sanitization (strips script/event handlers/javascript: protocols while preserving MSO comments and dark mode rules); `compatibility` JSON column on `ComponentVersion` for email client support metadata; Alembic migration `c7d2e5f19a83` with schema + data seeding; service layer sanitization on create + version; 25 unit tests (9 sanitization + 16 service) |
| 2.8 (backend) | QA gate system — backend | `QARepository` extracted from service (VSA compliance); `QAOverride` model with unique constraint, audit trail (`overridden_by_id`, `justification`, `checks_overridden` JSON); `QAOverrideNotAllowedError` exception; 4 new API endpoints (`GET /results`, `GET /results/latest`, `GET /results/{id}`, `POST /results/{id}/override` with developer+ RBAC); `build_id` now nullable, `template_version_id` FK added for audit linkage; Alembic migration `d8a3f2b91c47`; 55 unit tests (37 check implementations + 16 service orchestration + conftest fixtures) |
| 2.8 (UI) | QA gate system — frontend | "Run QA" button in workspace toolbar with loading/spinner state; `QAResultsPanel` right sidebar (320px) showing overall score percentage, pass/fail status badge, failed checks (expanded) + passed checks (collapsible), override info banner; `QACheckItem` component with pass/fail/overridden icons, i18n labels with `t.has()` fallback for unknown checks, score progress bars, failure detail text; `QAOverrideDialog` (28rem) with checkbox selection of failing checks, justification textarea (min 10 chars), developer+ RBAC gating via `useSession()`; 5 SWR hooks (`useQARun`, `useQAResult`, `useQALatest`, `useQAResults`, `useQAOverride`); local TypeScript types in `types/qa.ts`; 38 i18n keys in `messages/en.json`; code-reviewed with 5 fixes (stale dialog state via `prevOpen` pattern, unhandled promise `.catch()`, `useMemo` for derived arrays, i18n crash guard) |
| 3.1 | Client approval portal | Backend: `GET /api/v1/approvals/?project_id=X` list endpoint, `GET /api/v1/email/builds/{build_id}` for preview HTML (7 endpoints total). Frontend: `/approvals` list page with status filter tabs (All/Pending/Approved/Rejected/Revision); `/approvals/[id]` detail page with 2-column layout (60% sandboxed preview with viewport/dark mode toggles, 40% side panel with Feedback/Audit Trail tabs); 6 components (`ApprovalStatusBadge`, `ApprovalCard`, `ApprovalPreview`, `ApprovalFeedbackPanel`, `ApprovalAuditTimeline`, `ApprovalDecisionBar`); 8 SWR hooks; decision bar (approve/reject/request-revision) with admin/developer RBAC via `useSession()`; "Submit for Approval" button in workspace toolbar; sidebar nav with ClipboardCheck icon; middleware RBAC (all roles); ~40 i18n keys; all semantic Tailwind tokens |
| 2.9 | Raw HTML export + Braze connector UI | `ExportDialog` (32rem) with two tabs — Raw HTML (client-side Blob download via `URL.createObjectURL`) and Braze (two-phase: production build → `POST /api/v1/connectors/export` with `content_block_name`); state machine (idle→building→exporting→success\|error) with retry; `ExportStatusBadge` + `ExportCard` components; `useExportHistory()` hook via `useSyncExternalStore` + `sessionStorage` (max 100 records, cross-component sync); `/connectors` dashboard page with platform filter tabs (All/Braze/Raw HTML) and export history grid; Export button in workspace toolbar; Plug sidebar nav icon; middleware RBAC (all roles); ~25 i18n keys across `connectors` + `export` namespaces; `types/connectors.ts` local types; all semantic Tailwind tokens |
| 3.2 | Rendering intelligence dashboard | `/intelligence` page with 4 sections: `ScoreOverviewCards` (4-col grid: total runs, avg score, pass rate, overrides); `CheckPerformanceChart` (CSS horizontal bars per QA check, sorted worst-first, threshold-colored); `ScoreTrendBars` (CSS vertical bars of last 20 scores with pass/fail coloring); `RecentResultsTable` (paginated with status badges); "Email Client Rendering" placeholder (Coming Soon — deferred to 4.4). `useQADashboard` hook aggregates 50 results client-side via `useMemo`. `QADashboardMetrics` type. BarChart3 sidebar nav. Middleware RBAC (all roles). ~30 i18n keys. All semantic Tailwind tokens |
| 3.3 | Dashboard homepage enhancement | Dashboard rewritten with 4 stat cards (Total Projects, Components, QA Pass Rate with threshold coloring, Pending Approvals); Quality Overview card with avg score, total runs, overrides, mini trend dots (last 10 pass/fail); Recent Activity feed (latest 5 QA runs); Project grid (top 3 with "View All"); Quick Start with "Open Workspace" + "Browse Components" links. 6 existing SWR hooks, no new backend endpoints. ~20 new i18n keys. All semantic Tailwind tokens |
| 2.10 | RAG knowledge base seeding | 20 curated markdown documents across 3 domains: `css_support` (8 files), `best_practices` (6 files), `client_quirks` (6 files). Async seed command (`app/knowledge/seed.py`) with idempotency. Manifest-driven (`app/knowledge/data/seed_manifest.py`) with per-document metadata, tags, domain classification. 109 unit tests |
| 4.8 | Knowledge base search UI | `/knowledge` page with search-first UX: debounced search bar triggering `POST /api/v1/knowledge/search`, domain filter pills (All/CSS Support/Best Practices/Client Quirks), tag filter pills, dual mode (search results with relevance scores vs document browse grid), pagination, document detail dialog (Content/Metadata tabs). 3 components (`KnowledgeSearchResultCard`, `KnowledgeDocumentCard`, `KnowledgeDocumentDialog`); 6 SWR hooks in `use-knowledge.ts`; `types/knowledge.ts` local types; demo data (20 docs, 3 domains, 15 tags, chunk content); BookOpen sidebar nav; middleware RBAC; ~30 i18n keys; all semantic Tailwind tokens |
| 4.9 | Smart agent memory | Conversation history tab in workspace chat panel. `ChatSession` and `ChatMessage` types; `useChatHistory` hook with `sessionStorage` persistence; `SessionCard` component with timestamp, message count, preview; session list with search/filter; restore previous conversations; 3 components; ~15 i18n keys |
| 4.10 | Version comparison dialog | Side-by-side template version diff in approval portal. `VersionCompareDialog` (max-w-7xl) with dual iframe previews; version selector dropdowns; auto-selects latest two versions; changelog and date metadata; loading/empty states; `useTemplateVersions` hook; ~12 i18n keys in `approvals` namespace |
| 4.11 | Custom persona creation | `CreatePersonaDialog` (max-w-[28rem]) with 7 form fields matching `PersonaCreate` schema; two-column grid layout; slug auto-generation; viewport width validation (200-2000px); email client dropdown (8 options); demo mode mock via mutation-resolver; auto-selects new persona in `PersonaSelector`; ~16 i18n keys |
| 4.12 | Exportable intelligence reports | `ExportReportMenu` dropdown on intelligence dashboard header with Print/PDF (`window.print()`) and CSV export (client-side Blob download). `@media print` styles in tokens.css for clean report output. CSV includes overview metrics, check performance, and quality trend data; ~6 i18n keys |
| 3.4 | Error handling, loading states, UI polish | Shared `EmptyState` component replacing 6 inline empty states; `ErrorState` integration on intelligence + approval detail; route-level `loading.tsx` for intelligence + connectors; `Loader2` spinners on login, persona create, QA override buttons; non-semantic token fixes in 2 dialogs; `fade-in` CSS animation on 5 pages; improved approval detail skeleton |
| 3.5 | CMS + Nginx Docker stack | 7 services healthy (db, redis, migrate, app, cms, maizzle-builder, nginx); 3 `.dockerignore` files (392MB→66MB context); nginx security hardening (blocked paths → 403, header hardening, SSL readiness); configurable `maizzle_builder_url`; `NEXT_PUBLIC_DEMO_MODE` baked into CMS build; `.env.example`; Alembic seed migration fixes |
| 4.3 | Figma design sync (frontend demo) | `/figma` page with connection card grid (status badges, sync/delete actions), design token preview (10 colors, 7 typography styles, 7 spacing values), `ConnectFigmaDialog` form (name, URL, token, project select); 4 components (`FigmaConnectionCard`, `FigmaStatusBadge`, `FigmaDesignTokensView`, `ConnectFigmaDialog`); 6 SWR hooks; optional Figma URL field in `CreateProjectDialog` with auto-connection on submit; demo data (3 connections, 1 token set); Figma sidebar nav icon; ~45 i18n keys |
| 4.13 (Phase 1) | Blueprint State Machine engine | `app/ai/blueprints/` module: `BlueprintEngine` state machine interleaving deterministic and agentic nodes; `BlueprintNode` protocol with progressive context hydration; bounded self-correction (max 2 rounds) with `BlueprintEscalatedError`; 6 node implementations (ScaffolderNode, DarkModeNode, QAGateNode, MaizzleBuildNode, ExportNode, RecoveryRouterNode); campaign blueprint definition with conditional edge routing; `POST /api/v1/blueprints/run` with auth + rate limiting; `BlueprintService` with blueprint registry; 27 unit tests |
| 4.2 | Additional CMS connectors | `ConnectorProvider` Protocol in `app/connectors/protocol.py` for type-safe dispatch; `SUPPORTED_CONNECTORS` registry with lazy instantiation; 3 new packages: `app/connectors/sfmc/` (SFMC Content Areas), `app/connectors/adobe/` (Adobe Campaign delivery fragments), `app/connectors/taxi/` (Taxi Syntax-wrapped templates); each with schemas + service; demo mutation resolver updated for per-connector mock IDs; 16 unit tests (304 total) |
| 4.4 | Litmus / Email on Acid API integration | `app/rendering/` VSA module with `RenderingProvider` Protocol; Litmus + EoA provider implementations (placeholder APIs); `RenderingTest` + `RenderingScreenshot` models; visual regression comparison with per-client diff percentages (2% threshold); `CircuitBreaker` for external API resilience; `RenderingConfig` with provider/API key/polling settings; 4 REST endpoints (`/api/v1/rendering/`): submit, list, get, compare; auth + rate limiting; 12 unit tests (316 total) |
| 4.5 | Advanced features (6 features) | **F1 Collaborative Editing:** Yjs CRDT + y-codemirror.next, `useCollaboration` hook, demo mode simulated collaborator, `CollaboratorAvatars` + `ConnectionStatus` components. **F2 Localisation:** 6 locale stubs (en/ar/de/es/fr/ja), cookie-based `NEXT_LOCALE` switching, RTL `dir` attribute, `/settings` page with `LocaleSelector`, `/settings/translations` management table. **F3 Brand Guardrails:** `/projects/[id]/brand` settings page, `BrandColorEditor`/`BrandTypographyEditor`/`BrandLogoRules`/`BrandForbiddenPatterns` components, CodeMirror `brandLinter` extension, toolbar violations badge. **F4 AI Image Generation:** `ImageGenDialog` (40rem) with style presets grid (6 presets), image gallery, insert `<img>` at cursor; demo picsum.photos placeholders. **F5 Visual Liquid Builder:** @dnd-kit drag-and-drop, regex Liquid parser/serializer, 5 block types (if/for/assign/output/raw), Code/Visual tab switching in `editor-panel.tsx`, live preview with sample data. **F6 Client Briefs:** `/briefs` page mirroring Figma architecture, Jira/Asana/Monday.com connection cards, brief items panel, import-to-project flow. |

### In Progress

No tasks currently in progress. V1 (Sprints 1-3) is complete. V2 task 4.1 (6 remaining AI agents) remains. Phase 5 (agent evaluation pipeline, steps 5.3-5.8) is pending. Blueprint engine Phase 2 (SSE streaming, multi-blueprint definitions) is planned.

### Infrastructure Built

- **Backend:** Full VSA implementation across 8 email-hub modules with CRUD, pagination, RBAC, rate limiting, soft delete
- **Frontend:** Next.js 16 monorepo with next-intl (6 locales with cookie-based switching, RTL support), auth middleware, RBAC route guards, semantic Tailwind tokens, shared `ErrorState`/`EmptyState` components, route-level loading skeletons, fade-in animations, Yjs CRDT collaborative editing, @dnd-kit visual Liquid builder
- **SDK Pipeline:** `openapi-ts` generates typed fetch client from backend OpenAPI spec; `make sdk` for regeneration
- **API Client:** Interceptor-based error handling with automatic auth refresh, typed error classes, SWR cache integration, 20 domain-specific hooks
- **AI Layer:** Protocol-based LLM abstraction with provider registry, model tier routing, PII sanitization, output validation, SSE streaming; Blueprint state machine engine for multi-node orchestration with self-correction
- **Connector Architecture:** Data-driven ESP connector frontend supporting 5 platforms (Raw HTML, Braze, SFMC, Adobe Campaign, Taxi); backend `ConnectorProvider` Protocol with all 4 ESP connectors implemented (placeholder APIs)
- **Rendering Tests:** `RenderingProvider` Protocol with Litmus + Email on Acid providers; cross-client rendering with visual regression detection; circuit breaker resilience
- **Docker Deployment:** 7-service Docker Compose stack behind nginx reverse proxy; security-hardened containers (non-root, cap_drop ALL, no-new-privileges); SSL termination ready; `.env.example` for deployment config
- **Testing:** Backend pytest (316 tests); Frontend Vitest + React Testing Library (`make test-fe`)

---

## 1. Product Vision

### Problem

Merkle serves clients across diverse email platforms (Braze, SFMC, Adobe Campaign, Taxi for Email) yet email development remains **fragmented, manual, and siloed between engagements**. Knowledge, components, and rendering fixes developed for one client are invisible to teams working with others. There is no platform designed for the multi-client, multi-platform agency model.

### Vision

A self-hosted, CMS-agnostic platform that centralises email innovation, prototyping, AI-assisted development, design tool integration, and cross-client QA into a single unified workflow. The Hub operationalises the **compound innovation effect**: every innovation, component, and pattern built for one client becomes available to all.

### Core Value Proposition

**"Build it once, use it everywhere, improve it continuously."**

Every piece of email development work becomes a reusable, testable, deployable asset — owned entirely by Merkle with zero vendor lock-in.

---

## 2. Strategic Objectives

| # | Objective | Metric |
|---|-----------|--------|
| 1 | **100% Merkle-Owned IP** | Zero SaaS dependencies; entire stack open-source |
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

- JWT authentication with RS256 signing
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

- JWT RS256 authentication; no plaintext passwords
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
| Auth | JWT RS256 + RBAC | In-house; no Auth0 dependency |
| AI | Local LLMs (Ollama/vLLM) + Claude/GPT-4o APIs | Hybrid: 70% local (free) / 30% cloud |
| Email Build | Maizzle (primary) | Full HTML control; Tailwind-native |
| Vector Search | pgvector (PostgreSQL) | Open-source; no Pinecone fees |
| Infrastructure | Docker Compose + nginx + Alembic | Self-hosted on Merkle servers |
| Testing | Playwright (core) + Litmus/EoA (optional) | Built-in speed + optional comprehensive coverage |

---

## 7. Architecture

### Repository Structure

```
merkle-email-hub/
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

| Aspect | SaaS Competitors | Merkle Hub |
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
