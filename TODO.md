# Merkle Email Innovation Hub — Implementation Roadmap

> Derived from `Merkle_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

## Architecture Principles (Apply to Every Task)

### Security-First Defaults
- **Zero Trust API**: Every endpoint authenticated + authorized. No implicit trust between services.
- **Input validation**: Pydantic schemas on ALL request bodies. Reject unknown fields.
- **Output sanitisation**: Strip sensitive data from all responses. Never leak stack traces in production.
- **CORS lockdown**: Whitelist allowed origins only. No wildcards in production.
- **Rate limiting**: Per-user + per-endpoint via Redis. AI endpoints get separate higher limits.
- **Audit trail**: Every state-changing API call logged (timestamp, user, action, resource). No credentials in logs.
- **Secrets management**: AES-256 for stored credentials. Environment variables for config. Never hardcode.

### API Security Patterns
- **JWT RS256**: Asymmetric signing (public key verifies, private key signs). 15-min access + 7-day refresh.
- **Token revocation**: Redis-backed blocklist for immediate invalidation on logout.
- **Brute-force protection**: Exponential backoff. Lock after 5 failed attempts (15 min). Redis-tracked.
- **RBAC enforcement**: admin/developer/viewer roles checked at route level via dependency injection.
- **Row-level security**: PostgreSQL RLS on client_id. Database enforces isolation independently of app layer.
- **API key scoping**: External credentials (Braze, Figma) encrypted at rest, scoped to minimum permissions.

### Development Pattern Adjustability
- **Protocol-based interfaces**: All external integrations use Python Protocols. Swap implementations without code changes.
- **Feature flags**: New features gated via `app/core/feature_flags.py`. Enable/disable per environment.
- **Configuration hierarchy**: Pydantic settings with env_nested_delimiter. Override anything via environment variables.
- **Provider registry**: AI, embedding, reranker providers registered at runtime. Add new providers = config change.

---

## Phase 0 — Foundation Blockers

### ~~0.1 Database Migration for Email-Hub Models~~ DONE
**Plan ref:** Section 2.3, 16.2 (Scaffolding)
**What:** Generate Alembic migration for all 7 new module models (ClientOrg, Project, ProjectMember, EmailBuild, Component, ComponentVersion, QAReport, QACheckResult, ExportRecord, ApprovalRequest, Feedback, AuditEntry, Persona). Add PostgreSQL Row-Level Security policies on `client_org_id` columns.
**Security:**
- RLS policies: `CREATE POLICY project_isolation ON projects USING (client_org_id = current_setting('app.current_client_id')::uuid)`
- All new tables inherit TimestampMixin (created_at, updated_at for audit)
- Soft delete on sensitive tables (projects, approval requests)
**Verify:** `make db-migrate` succeeds. All tables created. RLS policies active. CRUD operations on new endpoints persist data.

### ~~0.2 Initialize shadcn/ui Component Library~~ DONE
**Plan ref:** Section 9.1, 1.2 (Frontend Tech Stack)
**What:** Run shadcn/ui init in `cms/apps/web/`. Install foundational components (button, card, input, dialog, tabs, dropdown-menu, sheet, skeleton, table, badge, separator, scroll-area, command, popover, select, textarea). Wire into existing 3-tier design token system in `cms/packages/ui/src/tokens.css`.
**Security:**
- Ensure all form components have proper ARIA attributes
- Input components must sanitise rendered content (XSS prevention)
- Dialog/sheet components must trap focus (accessibility + security)
**Verify:** Components render with correct Merkle brand tokens. Dark mode toggle works. All components pass accessibility audit.

### ~~0.3 Generate OpenAPI TypeScript SDK~~ DONE
**Plan ref:** Section 9.1 (Frontend Architecture)
**What:** Run SDK generation from `cms/packages/sdk/` against running backend (`http://localhost:8891/openapi.json`). Produces typed client for all 43 endpoints.
**Security:**
- SDK must automatically inject Authorization Bearer header from session
- SDK must handle 401 responses with automatic redirect to login
- SDK must never log request bodies containing credentials
**Verify:** Import SDK in a page component. Make typed API call. TypeScript compilation passes. Auth header injected.

### ~~0.4 Authenticated API Client Layer~~ DONE
**Plan ref:** Section 9.1 (Real-time, API Integration)
**What:** Build `cms/apps/web/src/lib/api-client.ts` — wrapper around generated SDK with auth token injection, automatic refresh, error handling, rate limit backoff. Custom React hooks: `useProjects()`, `useTemplate()`, `useQAResults()`, etc.
**Security:**
- Token refresh interceptor: on 401, attempt refresh before redirecting to login
- Never store access tokens in localStorage (use httpOnly cookies or memory-only)
- Request timeout: 30s default, 120s for build/AI endpoints
- Retry logic: max 3 retries with exponential backoff, no retry on 4xx
**Verify:** Login flow works end-to-end. Protected pages redirect to login when unauthenticated. Token refresh works silently.

---

## Phase 1 — Sprint 1: Editor + Build Pipeline (Plan: 2 weeks)

> **Sprint 1 Deliverable (Plan Section 16.4):** "Write email HTML in a browser, see it compile live, and preview as different subscriber profiles."

### ~~1.1 Project Dashboard Page~~ DONE
**Plan ref:** Section 9.2 (Dashboard), V1 #1
**What:** Dashboard page at `/(dashboard)/page.tsx`. Project overview grid, recent activity feed, QA status summary, quick-start template selection. Data from `GET /api/v1/projects` and `GET /api/v1/orgs`.
**Security:**
- Only show projects the authenticated user has access to (RBAC-filtered on backend)
- No client org data leakage across user sessions
**Verify:** Dashboard loads. Shows only user's assigned projects. Empty state for new users.

### ~~1.2 Project Workspace Layout~~ DONE
**Plan ref:** Section 9.2 (Project Workspace), V1 #2
**What:** Split-pane workspace at `/projects/[id]/workspace`. Three resizable panels: editor (left), preview (center/right), AI chat (bottom, collapsible). Use a resizable pane library compatible with React 19.
**Security:**
- Route guard: verify user has access to project before rendering
- Project ID validated server-side (no client-side trust)
**Verify:** Three-pane layout renders. Panels resize. Collapses gracefully on mobile.

### ~~1.3 Monaco Editor Integration~~ DONE
**Plan ref:** Section 9.2 (Monaco Editor), V1 #2
**What:** Embed Monaco Editor with HTML/CSS/Liquid syntax highlighting. Add Can I Email CSS autocomplete (flag unsupported properties inline). Bracket matching, code folding, minimap, search/replace. Editor state persists per template.
**Security:**
- Editor content sanitised before sending to backend (strip script injections)
- Content-Security-Policy headers prevent execution of editor content in host page
- Editor runs in sandboxed context (no access to parent window APIs)
**Verify:** Editor loads with syntax highlighting. Can I Email warnings appear for unsupported CSS. Content persists on save.

### ~~1.4 Maizzle Live Preview~~ DONE
**Plan ref:** Section 6.3 (Build Pipeline), 9.2 (Live Preview), V1 #3
**What:** Compile-on-save via `POST /api/v1/email/preview`. Render compiled HTML in sandboxed iframe. Desktop/tablet/mobile viewport toggles. Dark mode preview toggle. Zoom controls.
**Security:**
- Preview iframe uses `sandbox=""` — fully sandboxed (no scripts, no same-origin access)
- Preview iframe loaded via blob URL or srcdoc, never from external URL
- PostMessage communication between editor and preview must validate origin
- No user-generated content executes JavaScript in preview context
**Verify:** Type HTML in editor → compiled preview updates within 2 seconds. Viewport toggles resize iframe. Dark mode toggle works.

### ~~1.5 Test Persona Engine UI~~ DONE
**Plan ref:** Section V1 #10, 16.4
**What:** Persona selector dropdown in preview panel. Load personas from `GET /api/v1/personas`. One-click preview as: "Gmail Desktop", "iPhone Dark Mode", "Outlook 2016", etc. Visual context switching (device frame, email client chrome).
**Security:**
- Personas scoped to project (no cross-project persona leakage)
- Persona data is non-PII (device config, not subscriber data)
**Verify:** Persona selector loads presets. Preview updates to show selected device/client context.

### ~~1.6 Template CRUD + Persistence~~ DONE
**Plan ref:** Section 2.3 (Projects module), V1 #1
**What:** Save/load templates within projects. Template versioning (each save creates a version). Version history sidebar. Restore previous version capability.
**Security:**
- Template content stored encrypted at rest (PostgreSQL column encryption or transparent data encryption)
- Version history includes author + timestamp for audit
- Template access scoped to project members only
**Verify:** Create template → edit → save → reload shows saved content. Version history shows all saves. Restore works.

---

## Phase 2 — Sprint 2: Intelligence + Export (Plan: 2-3 weeks)

> **Sprint 2 Deliverable (Plan Section 16.4):** "Functional AI-assisted email development with automated QA and CMS export."

### ~~2.1 Wire AI Provider to LLM~~ DONE
**Plan ref:** Section 5.5 (AI Model Selection), 5.1 (Agent Architecture)
**What:** Register Claude (via Anthropic SDK) or OpenAI-compatible provider in `app/ai/registry.py`. Add `AI__PROVIDER`, `AI__MODEL`, `AI__API_KEY` to config. Implement model routing logic: Opus for complex, Sonnet for standard, Haiku for lightweight tasks. Verify streaming works via WebSocket.
**Security:**
- API keys stored as environment variables, NEVER in code or database
- AI request/response bodies logged WITHOUT the actual content (log token counts + model + latency only)
- Rate limit AI endpoints separately: 20 req/min per user for chat, 5 req/min for generation
- Input sanitisation: strip any PII patterns from prompts before sending to external API
- AI responses go through output validation before returning to client
**Verify:** `POST /v1/chat/completions` returns streamed response. Model routing selects correct tier. API key is not exposed in logs or errors.

### ~~2.2 Scaffolder Agent~~ DONE
**Plan ref:** Section 5.1 (Scaffolder), V1 #5
**What:** First AI agent — generates Maizzle email HTML from natural language campaign briefs. System prompt defines email constraints (table layouts, inline CSS, MSO conditionals, responsive stacking). Outputs complete Maizzle template source.
**Security:**
- Agent output goes through QA validation before being offered to user
- System prompt includes instruction to never include external URLs or script tags
- Generated HTML sanitised for XSS before rendering in preview
**Verify:** Provide brief "Create a 2-column product showcase email with dark mode support" → get valid Maizzle HTML. Preview renders correctly.

### ~~2.3 Dark Mode Agent~~ DONE
**Plan ref:** Section 5.1 (Dark Mode Agent), V1 #5
**What:** Analyses existing HTML and injects `@media (prefers-color-scheme: dark)` rules, `[data-ogsc]`/`[data-ogsb]` selectors for Outlook, transparent PNG suggestions, colour token remapping. Uses Knowledge Base for client-specific dark mode quirks.
**Security:**
- Agent only modifies CSS/style blocks, never injects script content
- Output diff shown to developer before applying (human-in-the-loop)
**Verify:** Provide email HTML without dark mode → agent returns enhanced version with dark mode CSS. Preview confirms dark mode toggle works.

### ~~2.4 Content Agent~~ DONE
**Plan ref:** Section 5.1 (Content Agent), 15.4 (Competitive Feature — new capability #1)
**What:** Generates and refines email marketing copy: subject lines, preheaders, CTA text, body copy. Supports rewrite, shorten, expand, and tone adjustment. Brand voice constraints applied per client. Integrates into Monaco editor as context menu: select text → right-click → "Refine with AI."
**Security:**
- Brand voice constraints loaded from project settings, not hardcoded
- Content suggestions never include personal data patterns
- Generated copy flagged if it matches spam trigger patterns
**Verify:** Select text in editor → right-click → "Refine with AI" → get alternatives. Subject line generation produces 5 options.

### ~~2.5 AI Chat Sidebar UI~~ DONE
**Plan ref:** Section 9.2 (AI Orchestrator panel), V1 #5
**What:** Collapsible bottom panel in workspace. Agent selection toggles (Scaffolder, Dark Mode, Content). Natural language input with streaming response display. Code block rendering in responses. Accept/reject/merge controls to apply AI output to editor. Conversation history per session.
**Security:**
- WebSocket connection authenticated via JWT (validated on connect)
- Conversation history stored per-user, per-project (no cross-user visibility)
- AI conversation logs retained 90 days maximum (Plan Section 8.3)
- Merge operation creates a new template version (audit trail)
**Verify:** Open chat → select Scaffolder → provide brief → streamed response appears → click "Apply" → code merged into editor.

### ~~2.6 Component Library v1 — Backend~~ DONE
**Plan ref:** Section V1 #4, 2.3 (Component Library module)
**What:** Seed 5-10 pre-tested Maizzle email components: header, footer, CTA button, hero block, product card, spacer, social icons, image block, text block, divider. Each with dark mode variant, Outlook fallback, version metadata, and compatibility matrix stub.
**Security:**
- Component content validated on upload (no script injection in HTML components)
- Version immutability: published versions cannot be modified, only new versions created
- Component ownership tracked (author, last modifier)
**Verify:** `GET /api/v1/components` returns 5-10 components. Each has at least one version. Dark mode variant accessible.

### ~~2.7 Component Library Browser UI~~ DONE
**Plan ref:** Section 9.2 (Component Library), V1 #4
**What:** Page at `/components`. Grid view with component preview thumbnails. Search by name, type, client scope. Component detail view: rendered preview (light + dark mode), HTML source, version history, compatibility matrix table, usage documentation.
**Security:**
- Component previews rendered in sandboxed iframes (same as live preview)
- Components scoped: Global visible to all, Client-scoped visible to project members only
**Verify:** Browse components. Search filters work. Click component → see detail view with preview + source + versions.

### ~~2.8 10-Point QA Gate System~~ DONE
**Plan ref:** Section 7.2 (QA Pipeline), V1 #7
**What:** QA trigger button in workspace toolbar. Runs `POST /api/v1/qa/run` with current template HTML. Results displayed as pass/fail checklist with details per check. Gate enforcement: warn/block on export if checks fail. Senior override with documented justification.
**Backend:** Repository layer (`QARepository`), `QAOverride` model with audit trail, 4 new API endpoints (`GET /results`, `GET /results/latest`, `GET /results/{id}`, `POST /results/{id}/override`), Alembic migration `d8a3f2b91c47`, 55 unit tests (37 checks + 16 service + conftest fixtures).
**Frontend:** "Run QA" button in workspace toolbar with loading state; `QAResultsPanel` right sidebar (320px) with overall score, status badge, failed/passed checks (collapsible), override info; `QACheckItem` rows with pass/fail icons, score bars, i18n labels with fallback; `QAOverrideDialog` (28rem) with check selection, justification textarea (min 10 chars), developer+ RBAC; 5 SWR hooks (`useQARun`, `useQAResult`, `useQALatest`, `useQAResults`, `useQAOverride`); local TypeScript types in `types/qa.ts`; 38 i18n keys; code-reviewed (5 fixes: stale dialog state, unhandled promise, memoization, i18n crash guard).
**Security:**
- QA results stored with template version (audit: which version was tested)
- Override requires admin/developer role + written justification (logged)
- Override audit entry includes who, when, why, which checks bypassed
**Verify:** Click "Run QA" → 10 checks execute → results display inline. Failing checks show detail. Override flow works with audit logging.

### ~~2.9 Raw HTML Export + Braze Connector UI~~ DONE
**Plan ref:** Section 3.1 (Connector Architecture), V1 #6
**What:** Export console at `/export` or inline in workspace. Platform selector: Raw HTML download, Braze Content Blocks push. Export preview shows what will be sent. Braze connector: configure API key (encrypted), push as Content Block with Liquid packaging.
**Frontend:** `ExportDialog` (32rem) with two tabs — Raw HTML (client-side Blob download via `URL.createObjectURL`) and Braze (two-phase: production build → `POST /api/v1/connectors/export` with `content_block_name`); state machine (idle→building→exporting→success|error) with retry; `ExportStatusBadge` + `ExportCard` for history grid; `useExportHistory()` hook via `useSyncExternalStore` + `sessionStorage` (max 100 records, cross-component sync without context provider); `/connectors` dashboard page with platform filter tabs (All/Braze/Raw HTML); Export button in workspace toolbar; Plug sidebar nav icon; middleware RBAC (all roles); ~25 i18n keys across `connectors` + `export` namespaces; all semantic Tailwind tokens.
**Security:**
- Braze API key encrypted with AES-256 before storage. Never returned in API responses. Never logged.
- Credential scope validation: verify API key has minimum required permissions before storing
- Export creates audit entry (who exported, when, where, which template version)
- Export blocked if QA gate has failures (unless overridden with justification)
**Verify:** Configure Braze credentials → export template → Content Block appears in Braze sandbox. Raw HTML download produces valid file.

### ~~2.10 RAG Knowledge Base Seeding~~ DONE
**Plan ref:** Section V1 #8, 13.3 (Data Bootstrapping)
**What:** Seed knowledge base with: Can I Email CSS support data (automated crawl), email dev best practices (curated entries), email client rendering quirks (team knowledge capture). Verify hybrid search (vector + fulltext) returns relevant results for email development queries.
**Implementation:** 20 curated markdown documents across 3 domains: `css_support` (8 files — layout, box model, typography, colors, borders, media queries, selectors, dark mode), `best_practices` (6 files — table layout, responsive, images, CTA buttons, accessibility, file size), `client_quirks` (6 files — Outlook Windows, Gmail, Apple Mail/iOS, Yahoo, Samsung, Outlook.com). Async seed command (`app/knowledge/seed.py`) processes documents through full RAG pipeline (extract → chunk → embed → store) with idempotency (skips existing by filename). Manifest-driven (`app/knowledge/data/seed_manifest.py`) with per-document metadata, tags, and domain classification. 109 unit tests validate manifest structure, file integrity, and content format.
**Security:**
- Knowledge entries classified: public (Can I Email), internal (best practices), confidential (client quirks)
- Client-specific quirks tagged with client_org_id (access-controlled)
- Embedding model runs on infrastructure Merkle controls (no PII sent to external embedding APIs)
**Verify:** `make seed-knowledge` ingests all 20 documents. Search "Outlook dark mode background image" → get relevant Can I Email data + rendering quirk entries. Knowledge Agent uses RAG context in responses.

---

## Phase 3 — Sprint 3: Client Handoff + Polish (Plan: 1-2 weeks)

> **Sprint 3 Deliverable (Plan Section 16.4):** "Complete V1 that clients can log into for approvals, QA data is visible, and the team has a tool they want to use daily."

### ~~3.1 Client Approval Portal~~ DONE
**Plan ref:** Section V1 #9, 9.2 (QA Dashboard approval workflow)
**What:** Approval routes at `/approvals`. Viewer role login (scoped to assigned projects only). Live email preview (read-only, sandboxed iframe). Section-level feedback annotations (click to highlight, leave comment). Global feedback textarea. Approve/request changes buttons. Version comparison (diff between current and last-reviewed version). Email/Slack notification when review is ready. Time-stamped audit trail of all approvals, changes, feedback.
**Backend:** Added `GET /api/v1/approvals/?project_id=X` list endpoint and `GET /api/v1/email/builds/{build_id}` for preview HTML. 7 API endpoints total (list, create, get, decide, add feedback, list feedback, audit trail).
**Frontend:** `/approvals` list page with status filter tabs (All/Pending/Approved/Rejected/Revision); `/approvals/[id]` detail page with 2-column layout (60% sandboxed preview with viewport/dark mode toggles, 40% side panel with Feedback/Audit tabs); 6 components (`ApprovalStatusBadge`, `ApprovalCard`, `ApprovalPreview`, `ApprovalFeedbackPanel`, `ApprovalAuditTimeline`, `ApprovalDecisionBar`); 8 SWR hooks (`useApprovals`, `useApproval`, `useCreateApproval`, `useApprovalDecide`, `useApprovalFeedback`, `useAddFeedback`, `useApprovalAudit`, `useBuild`); decision bar with approve/reject/request-revision buttons (admin/developer RBAC via `useSession()`); "Submit for Approval" button in workspace toolbar; ClipboardCheck sidebar nav icon; middleware RBAC for all roles; ~40 i18n keys; all semantic Tailwind tokens.
**Security:**
- Viewer role: READ ONLY. Cannot edit templates, run builds, export, or access other modules
- Approval URLs use signed tokens (not guessable IDs) — expire after 30 days
- Feedback content sanitised (no script injection via comments)
- Notification emails contain no template content (link back to portal only)
- Audit trail immutable: entries can be created, never modified or deleted
- Session timeout: 30 minutes inactivity for viewer role
**Verify:** Client logs in with viewer credentials → sees only their project's emails → leaves section feedback → approves → audit trail shows complete history.

### ~~3.2 Rendering Intelligence Dashboard~~ DONE
**Plan ref:** Section V1 #11, 12.6 (Compound Innovation Effect)
**What:** Dashboard at `/intelligence` with QA quality trends, per-check analytics, and recent results. Client-side aggregation from `GET /api/v1/qa/results` (no backend aggregation endpoint needed).
**Frontend:** `/intelligence` page with 4 sections: `ScoreOverviewCards` (4-column grid: total runs, avg score, pass rate, overrides); `CheckPerformanceChart` (CSS horizontal bars showing avg score per QA check, sorted worst-first, colored by threshold — green >=80%, yellow >=50%, red <50%); `ScoreTrendBars` (CSS vertical bars of last 20 results' overall scores with pass/fail coloring); `RecentResultsTable` (paginated table with status badges, score, checks passed, date); "Email Client Rendering" placeholder card with "Coming Soon" badge (deferred to task 4.4 Litmus integration). `useQADashboard` hook fetches 50 results and computes all metrics via `useMemo`. `QADashboardMetrics` type in `types/qa.ts`. BarChart3 sidebar nav icon. Middleware RBAC (all roles). ~30 i18n keys in `intelligence` namespace. All semantic Tailwind tokens.
**Security:**
- Dashboard data aggregated — no individual subscriber data ever displayed
- Export dashboard as PDF requires developer+ role
- Analytics data retention: 12 months, then aggregated
**Verify:** Dashboard shows QA trends. Support matrix populates from accumulated QA results. Template quality scores calculate correctly.

### ~~3.3 Dashboard Homepage Enhancement~~ DONE
**Plan ref:** Section 9.2 (Dashboard)
**What:** Enhance Phase 1.1 dashboard with real data: project overview grid with status indicators, recent activity feed (builds, QA runs, exports, approvals), team workload summary, QA status at a glance (pass rate), quick-start template selection (from component library).
**Frontend:** Dashboard page rewritten with 4 stat cards (Total Projects, Components, QA Pass Rate with threshold coloring, Pending Approvals with warning state); Quality Overview card (2/3 width) with avg score, total runs, overrides count, mini trend dots (last 10 QA results pass/fail); Recent Activity feed (1/3 width) showing latest 5 QA runs with score and date; Project grid (top 3 with "View All" link); Quick Start card with "Open Workspace" + "Browse Components" action links. 6 existing SWR hooks used (`useProjects`, `useOrgs`, `useComponents`, `useQADashboard`, `useQAResults`, `useApprovals`); no new backend endpoints. ~20 new i18n keys in `dashboard` namespace. All semantic Tailwind tokens.
**Security:**
- Activity feed shows only actions on user's accessible projects
- No sensitive data in activity summaries (e.g., "Template exported to Braze" not "Template exported to Braze API key ending in ...xyz")
**Verify:** Dashboard shows real project data. Activity feed updates in near-realtime. Quick-start creates new template from component.

### ~~3.4 Error Handling, Loading States, UI Polish~~ DONE
**Plan ref:** Section 16.2 (Polish + Glue)
**What:** Skeleton loaders on all data-fetching pages. Toast notifications for async operations (build started, export completed, QA passed). Proper 404/403/500 error pages. Form validation with inline errors. Optimistic updates where safe. Offline detection.
**Frontend:** Shared `EmptyState` component (`components/ui/empty-state.tsx`) replacing 6 ad-hoc inline empty states across approvals, connectors, intelligence, components, knowledge pages; `ErrorState` integration on intelligence page and approval detail page; route-level `loading.tsx` skeletons for intelligence and connectors; improved approval detail skeleton matching 2-pane layout; `Loader2` spinner on login, persona create, and QA override submit buttons; non-semantic shadcn alias tokens fixed in `create-persona-dialog.tsx` and `qa-override-dialog.tsx` (`border-input`→`border-input-border`, `bg-background`→`bg-input-bg`, `placeholder:text-muted-foreground`→`placeholder:text-input-placeholder`, `focus:border-ring/ring-ring`→`focus:border-input-focus/ring-input-focus`, `accent-primary`→`accent-interactive`, `hover:bg-accent`→`hover:bg-surface-hover`, `bg-primary text-primary-foreground`→`bg-interactive text-foreground-inverse`); `fade-in` CSS animation (`@keyframes` + `--animate-fade-in` token) added to `tokens.css` and applied to content wrappers on 5 major pages; 403 unauthorized page already existed at `(dashboard)/unauthorized/page.tsx`.
**Security:**
- Error pages never expose stack traces, internal paths, or configuration
- 403 page: "You don't have access to this resource" — no detail about what the resource is
- API errors: structured error responses with error codes, not raw exception messages
- Client-side error boundary catches React crashes gracefully
**Verify:** Navigate to invalid URL → 404 page. Access forbidden resource → 403 page. Kill backend → graceful offline state. All forms validate before submit.

### ~~3.5 CMS + Nginx Docker Stack~~ DONE
**Plan ref:** Section 16.2 (Deployment), 10 (Infrastructure)
**What:** Get `cms` container building and healthy (pnpm install + next build + standalone output). Wire nginx reverse proxy: `/` → cms (port 3000), `/api/` → app (port 8891), `/ws` → app WebSocket. SSL termination ready (cert volume mount). Full `docker compose up` with all 7 services healthy.
**Implementation:** 3 `.dockerignore` files (root, cms/, maizzle-builder/) reducing build context from 392MB to 66MB; configurable `maizzle_builder_url` in `app/core/config.py`; `INTERNAL_API_URL` and `MAIZZLE_BUILDER_URL` env vars in docker-compose; nginx security hardening (blocked `.env`/`.git`/`alembic`/`__pycache__` paths returning 403, `include mime.types`); commented SSL server block + cert volume mount; CSP `connect-src 'self'` for nginx-proxied deployment; `NEXT_PUBLIC_DEMO_MODE=true` baked into CMS Docker build; Dockerfile shebang fix for UV_LINK_MODE=copy; `.env.example` documenting all deployment vars; Alembic seed migration fixes (timestamps, system user FK). All 7 services healthy: db, redis, migrate (exited 0), app, cms, maizzle-builder, nginx.
**Security:**
- Nginx: rate limiting (100 req/s per IP), request body size limit (10MB), header hardening (X-Frame-Options DENY, X-Content-Type-Options nosniff, Strict-Transport-Security, Referrer-Policy strict-origin-when-cross-origin)
- Nginx: block access to `.env`, `.git`, `alembic/`, `__pycache__/` paths
- All containers: non-root user, `no-new-privileges`, `cap_drop: ALL`, minimal `cap_add`
- Redis: password-protected, not exposed to host in production
- PostgreSQL: not exposed to host in production (only via Docker network)
- Health check endpoints public; all other endpoints require auth
**Verify:** `docker compose up` → all 7 services healthy. `curl localhost:80` → CMS frontend. `curl localhost:80/api/v1/health` → backend health. `curl localhost:80/.env` → 403.

---

## Phase 4 — V2 Roadmap (Plan Section 16.1: V2 Iterations)

### ~~4.8 Knowledge Base Search UI~~ DONE
**Plan ref:** Section 4.8 (RAG Knowledge Base — "Natural language search"), `.agents/plans/4.8-knowledge-base-search.md`
**What:** Frontend search page at `/knowledge`. Search-first UX with large search bar, domain filter pills (All/CSS Support/Best Practices/Client Quirks), tag filter pills, dual mode (search results with relevance scores vs document browse grid), pagination, document detail dialog (Content/Metadata tabs). Full demo mode data layer (20 documents, 15 tags, search with scoring). Completes PRD 4.8 acceptance criteria for "Natural language search" UI.
**Frontend:** `/knowledge` page with debounced search (400ms) triggering `POST /api/v1/knowledge/search`; browse mode with paginated `GET /api/v1/knowledge/documents` (domain/tag filtering); `KnowledgeSearchResultCard` (filename, domain badge, chunk preview, relevance score bar); `KnowledgeDocumentCard` (title, description, tags, domain, chunk count); `KnowledgeDocumentDialog` (max-w-3xl, Content/Metadata tabs with scrollable chunks); `use-knowledge.ts` with 6 SWR hooks (`useKnowledgeDocuments`, `useKnowledgeDocument`, `useKnowledgeDocumentContent`, `useKnowledgeDomains`, `useKnowledgeTags`, `useKnowledgeSearch`); `types/knowledge.ts` local types; demo data in `lib/demo/data/knowledge.ts` (20 docs, 3 domains, 15 tags, chunk content for 5 key docs); demo resolver routes for all 5 GET endpoints + 1 POST search; loading skeleton; BookOpen sidebar nav icon; middleware RBAC (all roles); ~30 i18n keys in `knowledge` namespace; all semantic Tailwind tokens.
**Security:**
- Knowledge document previews rendered as text only (no HTML execution)
- Search input debounced to prevent API flooding
- Domain/tag filters validated against known values in demo mode
**Verify:** `/knowledge` page loads with 20 document cards. Search "dark mode" returns relevant results with scores. Domain/tag filters narrow results. Document dialog shows chunks and metadata. `pnpm build` passes.

### ~~4.9 Smart Agent Memory~~ DONE
**Plan ref:** `.agents/plans/4.9-smart-agent-memory.md`
**What:** Conversation history tab in workspace chat panel with session persistence, search, and restore.
**Frontend:** `ChatSession` and `ChatMessage` types in `types/chat-history.ts`; `useChatHistory` hook with `sessionStorage` persistence; `SessionCard` component with timestamp, message count, preview; session list with search/filter; restore previous conversations; 3 components in `components/workspace/chat/`; ~15 i18n keys in `workspace` namespace.
**Verify:** Chat history tab shows previous sessions. Search filters sessions. Restoring a session loads messages. `pnpm build` passes.

### ~~4.10 Version Comparison Dialog~~ DONE
**Plan ref:** `.agents/plans/4.10-version-comparison.md`
**What:** Side-by-side template version diff in approval portal for visual comparison.
**Frontend:** `VersionCompareDialog` (max-w-7xl) with dual sandboxed iframe previews; version selector dropdowns; auto-selects latest two versions; changelog and date metadata; loading/empty states; `useTemplateVersions` hook; ~12 i18n keys in `approvals` namespace.
**Verify:** "Compare Versions" button appears on approval detail page. Dialog opens with two versions side by side. Dropdown changes versions. `pnpm build` passes.

### ~~4.11 Custom Persona Creation~~ DONE
**Plan ref:** `.agents/plans/4.11-custom-persona-creation.md`
**What:** Dialog form enabling users to create custom email client test profiles.
**Frontend:** `CreatePersonaDialog` (max-w-[28rem]) with 7 form fields matching `PersonaCreate` schema; two-column grid layout; slug auto-generation; viewport width validation (200-2000px); email client dropdown (8 options); demo mode mock via mutation-resolver; auto-selects new persona in `PersonaSelector`; ~16 i18n keys in `workspace` namespace.
**Verify:** "Create Persona" menu item in persona dropdown. Dialog submits and new persona appears. `pnpm build` passes.

### ~~4.12 Exportable Intelligence Reports~~ DONE
**Plan ref:** `.agents/plans/4.12-exportable-reports.md`
**What:** Export button on intelligence dashboard for client presentation reports.
**Frontend:** `ExportReportMenu` dropdown with Print/PDF (`window.print()`) and CSV export (client-side Blob download with overview metrics, check performance, quality trend); `@media print` styles in `tokens.css`; ~6 i18n keys in `intelligence` namespace.
**Verify:** Export dropdown renders on intelligence page. Print opens browser dialog. CSV downloads with correct data. `pnpm build` passes.

### 4.13 Agent Harness Engineering (Phase 1: Blueprint Engine ✅)
**Plan ref:** Section 5.1 (Agent Architecture), harnessing_agents.txt (Industry Research)
**What:** Implement the agent harness layer — the execution loop, progressive disclosure, and self-verification scaffolding that surrounds each AI agent. The harness is model-agnostic infrastructure that transforms agents from single-pass generators into iterative, self-correcting production workers. Based on patterns from Claude Code, Cursor, Manus, SWE-Agent, and the Four Disciplines Framework.
**Phase 1 Implementation (Blueprint State Machine):** `app/ai/blueprints/` — State machine engine interleaving deterministic nodes (QA gate, Maizzle build, Braze export) with agentic nodes (scaffolder, dark mode), implementing bounded self-correction (max 2 rounds), progressive context hydration, and recovery routing. Shared utilities extracted to `app/ai/shared.py`. `POST /api/v1/blueprints/run` endpoint (3/min rate limit, admin/developer RBAC). Campaign blueprint graph: scaffolder → qa_gate → (pass) maizzle_build → export / (fail) recovery_router → fixer → qa_gate loop. 22 files, 27 tests, all passing lint + types.

**Harness Components:**

1. **TAOR Execution Loop (Think-Act-Observe-Repeat)** — Replace single-pass agent execution with an iterative loop: agent thinks about the task, acts (generates output), observes results (runs validation), and repeats if validation fails. Each agent gets a configurable max iteration count (default: 3) and exit conditions.

2. **PreCompletionChecklist Middleware** — Intercepts agent "done" signals and forces a final verification pass against the original task specification. Prevents the "Ralph Wiggum Loop" where agents declare victory without testing. For example: Scaffolder generates HTML → harness runs QA checks automatically → if accessibility fails, error logs fed back to agent for self-correction.

3. **Progressive Disclosure (Context Economy)** — Lazy-load agent skills and knowledge instead of pre-loading everything into context. Agent receives only tool names as static context; full definitions fetched on-demand when the agent selects a tool. Knowledge base queries scoped to the current check/task, not the entire corpus. Target: 26x token efficiency improvement (based on industry benchmarks). Prevents "Context Rot" where agents lose track of goals in long sessions.

4. **Linter-Gated Guardrails** — Deterministic safety nets that don't rely on LLM reasoning:
   - HTML structure validation runs automatically on every agent file save (rejected if invalid)
   - Risk classification via lightweight model (Haiku) auditing commands before execution
   - Brand compliance rules enforced as hard constraints ("Must-Nots" like "never modify brand-reserved colours")
   - QA gate results fed back as harness-level rejections, not just suggestions

5. **Progress Log & Task Decomposition** — `agent-progress.json` per session where agents record features tested, bugs fixed, and decisions made. Long tasks decomposed into 2-hour independently verifiable sub-tasks. Prevents "lost in the middle" attention degradation on long trajectories.

6. **Model-Agnostic Escalation** — Harness-level routing: local LLM (Ollama/vLLM) handles 70-90% of routine tasks → harness monitors output confidence → auto-escalates to frontier model (Claude Opus) when confidence drops below threshold or when multi-step rendering conflicts detected. Swap models without code changes via the existing provider registry.

**Harness Benefits Table:**

| Harness Pattern | QA Agent Impact | Strategic Value |
|-----------------|----------------|-----------------|
| TAOR Loop | Agents iterate on bug fixes autonomously | Reduces manual developer rework |
| Progressive Disclosure | Agents only see tokens needed for current test | 26x token efficiency improvement |
| Constraint Architecture | Defines "Must-Nots" (e.g., brand-reserved colours) | 100% brand compliance |
| Task Decomposition | Full-campaign audits split into verifiable sub-tasks | Increases reliability and speed |
| Linter Gates | Invalid HTML rejected before QA stage | Catches errors deterministically |
| Model Escalation | Routine tasks local, complex tasks cloud | Reduces API cost by 70-90% |

**Security:**
- Harness-level audit trail for every agent iteration (who triggered, what changed, why it looped)
- Escalation decisions logged (which model, why escalated, confidence scores)
- Brand constraint violations blocked deterministically — never delegated to LLM judgement
- Progress logs scoped to project (no cross-project leakage)
**Verify:** Agent executes with TAOR loop (visible iteration count in UI). PreCompletionChecklist catches intentionally broken HTML. Progressive disclosure reduces token usage measurably. Local → cloud escalation triggers on complex tasks. Progress log persists across sessions.

### 4.1 Remaining 6 AI Agents
**Plan ref:** Section 5.1 (Agent Architecture)
- **Outlook Fixer**: MSO conditionals, VML backgrounds, table-based fallbacks
- **Accessibility Auditor**: WCAG AA checks, contrast ratios, alt text, touch targets, AI alt text generation
- **Personalisation Agent**: Liquid (Braze), AMPscript (SFMC), dynamic content logic
- **Code Reviewer**: Static analysis, redundant code, unsupported CSS, file size optimisation
- **Knowledge Agent**: RAG-powered Q&A from knowledge base
- **Innovation Agent**: Prototype new techniques, assess feasibility, generate fallback strategies

### ~~4.2 Additional CMS Connectors~~ DONE
**Plan ref:** Section 3.1 (~2-3 days each), `.agents/plans/4.2-additional-cms-connectors.md`
**What:** Add SFMC, Adobe Campaign, and Taxi for Email backend connectors following the Braze pattern. All three are placeholder implementations (mock API calls) matching the Braze style.
**Backend:** `ConnectorProvider` Protocol in `app/connectors/protocol.py` for type-safe dispatch; `SUPPORTED_CONNECTORS` registry mapping connector type strings to provider classes with lazy instantiation and caching; 3 new connector packages: `app/connectors/sfmc/` (SFMCConnectorService — Content Builder Content Area with AMPscript packaging), `app/connectors/adobe/` (AdobeConnectorService — delivery content fragments with Adobe IMS packaging), `app/connectors/taxi/` (TaxiConnectorService — Taxi Syntax-wrapped templates); each with schemas + service following Braze pattern; 16 unit tests (4 protocol conformance + 12 provider tests); demo mutation resolver updated for per-connector mock IDs.
**Security:**
- All connector services satisfy `ConnectorProvider` Protocol (runtime-checkable)
- No credential storage yet (placeholder implementations) — AES-256 encryption deferred to real API integration
- Export audit trail via existing `ExportRecord` model (unchanged)
**Verify:** `make test` passes (304 tests). All 4 connectors dispatch correctly via `POST /api/v1/connectors/export`. Frontend export dialog works with sfmc/adobe_campaign/taxi in demo mode. `connector_type` validation returns 422 for unsupported types.

### ~~4.3 Figma Design Sync (Frontend Demo)~~ DONE
**Plan ref:** Section 4 (Design Tool Integration), `.agents/plans/figma-design-sync.md`
**What:** Dedicated `/figma` page for managing Figma file connections and extracting design tokens. Connection card grid with status badges (connected/syncing/error/disconnected), sync and delete actions, design token preview (colors grid, typography list, spacing bars). Connect Figma dialog with name, file URL, access token, and project selector. Optional Figma URL field added to Create Project dialog with auto-connection on submit. Full demo mode data layer (3 connections, 1 token set with 10 colors, 7 typography styles, 7 spacing values).
**Frontend:** `/figma` page with `FigmaConnectionCard`, `FigmaStatusBadge`, `FigmaDesignTokensView`, `ConnectFigmaDialog` components; 6 SWR hooks in `use-figma.ts`; `types/figma.ts` local types; demo data in `lib/demo/data/figma.ts`; demo resolver + mutation-resolver routes; Figma sidebar nav icon; middleware RBAC (all roles); ~45 i18n keys in `figma` namespace; optional Figma URL field in `CreateProjectDialog`; loading skeleton; all semantic Tailwind tokens.
**Remaining:** Real Figma REST API integration, change webhook handling, plugin ecosystem (Emailify, Email Love, MigmaAI) — deferred to backend implementation phase.
**Verify:** `/figma` page loads with 3 demo connections. Connect dialog creates new connection. Clicking connected card shows design tokens. Sync/delete actions work. Create Project dialog has optional Figma URL field. `pnpm build` passes.

### 4.4 Litmus / Email on Acid API Integration
**Plan ref:** Section 7.2 (Cross-Client Render)
- API integration for 20+ client rendering screenshots
- Visual regression detection
- Rendering report generation

### ~~4.5 Advanced Features~~ DONE
- ~~Real-time collaborative editing (CRDT/OT — Yjs + y-codemirror.next, demo mode with simulated collaborator)~~ DONE
- ~~Localisation engine (6 locale stubs, cookie-based switching, RTL support, translation management table)~~ DONE
- ~~Per-client brand guardrails (brand settings page, CodeMirror linter extension, toolbar violations badge)~~ DONE
- ~~AI image generation (workspace dialog, style presets, gallery, insert-into-template)~~ DONE
- ~~Visual Liquid builder UI (@dnd-kit drag-and-drop, regex parser/serializer, Code/Visual tab switching)~~ DONE
- ~~Client brief system integration (Jira/Asana/Monday.com connection cards, brief items, import-to-project)~~ DONE

---

## Phase 5 — Agent Evaluation System (Specification Engineering Layer)

> **Objective:** Build the "Evaluation Design" primitive from the Four Disciplines framework (Section 06 of pitch). **This eval framework applies to ALL 9 agents** — the 3 currently implemented and the 6 planned. Every agent that enters the Hub must pass through the same eval pipeline before it touches production work. No agent ships without: synthetic test data, an LLM judge, human-calibrated baselines, and a regression gate. This is not optional infrastructure — it is the mechanism that makes Specification Engineering real.

> **Applies to ALL agents:**
> | # | Agent | Status | Eval Status |
> |---|-------|--------|-------------|
> | 1 | **Scaffolder** | Implemented | Synthetic data created (12 cases) |
> | 2 | **Dark Mode** | Implemented | Synthetic data created (10 cases) |
> | 3 | **Content** | Implemented | Synthetic data created (14 cases) |
> | 4 | **Outlook Fixer** | Planned (4.1) | Eval data needed on build |
> | 5 | **Accessibility Auditor** | Planned (4.1) | Eval data needed on build |
> | 6 | **Personalisation Agent** | Planned (4.1) | Eval data needed on build |
> | 7 | **Code Reviewer** | Planned (4.1) | Eval data needed on build |
> | 8 | **Knowledge Agent** | Planned (4.1) | Eval data needed on build |
> | 9 | **Innovation Agent** | Planned (4.1) | Eval data needed on build |
>
> **Rule: No agent goes to production without completing steps 5.1-5.5 for that agent.** Steps 5.6-5.8 apply system-wide.

> **Progress:**
> - [x] Eval framework scaffolded (`app/ai/agents/evals/`)
> - [x] Dimensions defined for Scaffolder, Dark Mode, Content
> - [x] Synthetic data created for 3 implemented agents (36 test cases total)
> - [x] Real-world email patterns sourced (Litmus, MailChimp, Parcel.io, email-darkmode repo, Mailmeteor)
> - [x] Eval runner CLI created (`runner.py`)
> - [ ] 5.1 — Review & harden test data (security audit)
> - [ ] 5.2 — Write LLM judge prompts (3 of 9 agents)
> - [ ] 5.3 — Run first eval batch & collect traces
> - [ ] 5.4 — Error analysis on traces
> - [ ] 5.5 — Calibrate judges against human labels
> - [ ] 5.6 — Calibrate 10-point QA gate
> - [ ] 5.7 — Blueprint pipeline eval runner
> - [ ] 5.8 — Automated regression suite in CI/CD
> - [ ] Eval data for Outlook Fixer (on agent build)
> - [ ] Eval data for Accessibility Auditor (on agent build)
> - [ ] Eval data for Personalisation Agent (on agent build)
> - [ ] Eval data for Code Reviewer (on agent build)
> - [ ] Eval data for Knowledge Agent (on agent build)
> - [ ] Eval data for Innovation Agent (on agent build)

### Per-Agent Eval Requirements (Mandatory for ALL 9 Agents)

Every agent — whether built now or in task 4.1 — must have:
1. **Synthetic test data** (`synthetic_data_<agent>.py`) — 10-12 dimension-based test cases with real-world inputs
2. **LLM judge prompt** (`judge_<agent>.py`) — binary pass/fail on 3-5 subjective criteria the QA gate can't catch
3. **Human calibration** — 20 expert-labeled outputs, TPR > 0.85, TNR > 0.80
4. **Adversarial test cases** — 1-2 prompt injection / edge case inputs per agent
5. **Regression baseline** — known-good scores stored in version control

### Current State (3 of 9 Agents)
- Synthetic test data created for 3 implemented agents: `app/ai/agents/evals/`
  - `synthetic_data_scaffolder.py` — 12 test cases (MSO ghost tables, VML, Gmail clipping, vague/contradictory briefs)
  - `synthetic_data_dark_mode.py` — 10 test cases with 5 real-world HTML templates (Outlook data-ogsc/ogsb, VML preservation, already-dark, brand-heavy)
  - `synthetic_data_content.py` — 14 test cases across all 8 operations (spam triggers from real blocklists, PII detection, healthcare/finance compliance)
  - `dimensions.py` — failure-prone dimension definitions per agent
  - `runner.py` — CLI runner that outputs JSONL traces
- Real-world email patterns sourced from: Litmus, MailChimp Design Reference, Parcel.io, email-darkmode repo, StackOverflow Design, Mailmeteor spam lists
- **6 agents still need eval data** — to be created as each agent is built (task 4.1)

### 5.1 Review & Harden Synthetic Test Data (Scaffolder, Dark Mode, Content)
**What:** Review the 36 synthetic test cases for completeness, realism, and security. Verify no real client data or credentials leaked into test fixtures. Add 2-3 missing edge cases per agent identified during review. Ensure all HTML fixtures are self-contained (no external resource dependencies).
**Applies to:** Scaffolder, Dark Mode, Content (current 3). **Repeat this step for each new agent built in task 4.1.**
**Security:**
- Audit all test HTML for embedded URLs (must be placehold.co or example.com only)
- Verify no real brand names, client data, or API keys in any fixture
- Test inputs must not contain prompt injection attempts (add 1-2 adversarial test cases per agent)
**Verify:** All 36+ test cases load without errors. `python -m app.ai.agents.evals.runner --agent all --output traces/` executes (even if agents return errors due to no LLM configured). No real client data in any fixture.

### 5.2 Write LLM Judge Prompts — Binary Pass/Fail (ALL Agents)
**What:** Following the evals-skills `write-judge-prompt` methodology, create binary pass/fail LLM judges for subjective quality criteria that the 10-point QA gate cannot catch. **One judge per agent (9 total when complete)**, each evaluating 3-5 subjective criteria.
**Judges for currently implemented agents:**
- **Scaffolder Judge:** Does the HTML faithfully implement the brief? Is the layout email-client appropriate (not web-only patterns)? Are MSO conditionals correctly structured?
- **Dark Mode Judge:** Are dark mode colors visually coherent (not just technically present)? Is the original HTML preserved without structural changes? Are Outlook selectors complete?
- **Content Judge:** Is the copy compelling and on-brand? Does the tone match the request? Are spam triggers absent while maintaining persuasiveness?
**Judges for planned agents (create when each agent is built):**
- **Outlook Fixer Judge:** Are MSO conditionals correctly targeted? Is VML well-formed? Are existing styles preserved?
- **Accessibility Judge:** Is generated alt text meaningful (not just "image")? Are WCAG AA violations correctly identified and prioritised?
- **Personalisation Judge:** Is Liquid/AMPscript syntactically correct? Does the logic match the natural language intent? Are edge cases (null data, empty arrays) handled?
- **Code Reviewer Judge:** Are flagged issues genuine (not false positives)? Are suggestions actionable? Is severity appropriate?
- **Knowledge Agent Judge:** Is the answer grounded in retrieved context (faithful)? Is it relevant to the query? Are source citations accurate?
- **Innovation Agent Judge:** Is the feasibility assessment accurate? Is the fallback strategy robust? Does audience coverage estimate match reality?
**Security:**
- Judge prompts must NOT include the agent's system prompt (information leakage)
- Judge prompts must NOT make external API calls
- Judge outputs must be structured JSON (pass/fail + reasoning), never freeform
**Verify:** Each judge prompt produces consistent binary pass/fail on 5 hand-labeled examples. Inter-run agreement > 90% on the same inputs.

### 5.3 Run First Eval Batch & Collect Traces (Scaffolder, Dark Mode, Content)
**What:** Configure a working LLM provider (can be local Ollama or cloud API). Run all 36 test cases through the 3 implemented agents. Collect full JSONL traces: input, output, timing, model, QA results. Store in `traces/` directory (gitignored). **Repeat for each new agent as it's built.**
**Security:**
- `traces/` directory added to `.gitignore` (may contain LLM outputs)
- Trace files must not be committed to version control
- LLM API keys used for eval only — separate from production keys if possible
- Rate limit eval runs (not all 36 at once — batch of 5 with delays)
**Verify:** 36 JSONL trace files generated. Each trace has: id, agent, input, output, timing, error status. No API key or credential in trace data.

### 5.4 Error Analysis on Collected Traces (ALL Agents)
**What:** Following the evals-skills `error-analysis` methodology, manually read through all traces. Categorise failures into a taxonomy per agent (e.g., "layout wrong", "MSO missing", "color contrast failed", "brief misinterpreted"). Compute failure rates per category. Prioritise the top 3 failure modes for each agent. **This step runs for every agent — it is how we discover what each agent gets wrong.**
**Security:**
- Error analysis results stored as structured data (not freeform text that could leak into prompts)
- Failure taxonomy scoped to technical categories (no client-identifying information)
**Verify:** Failure taxonomy document with categories, counts, and examples. Top 3 failure modes per agent identified with severity rating.

### 5.5 Calibrate Judges Against Human Labels (ALL Agents)
**What:** Following the evals-skills `validate-evaluator` methodology, have a domain expert (email developer) manually label 20 agent outputs per agent as pass/fail. Run the LLM judges on the same outputs. Compute TPR (true positive rate) and TNR (true negative rate). Target: TPR > 0.85, TNR > 0.80. **Every agent needs this — no agent's judge is trusted without human calibration.**
**Security:**
- Human labels stored separately from traces (no contamination)
- Labeling interface does not expose system prompts or agent internals
- Label data is project-scoped and access-controlled
**Verify:** Confusion matrix per judge. TPR and TNR meet targets. If not, iterate on judge prompts and re-calibrate.

### 5.6 Calibrate the 10-Point QA Gate (System-Wide)
**What:** Using the human-labeled outputs from 5.5, measure the QA gate's agreement with human judgment across all agents. Identify which of the 10 checks have low precision or recall. Adjust thresholds or add new checks where the gate misses failures that humans catch.
**QA checks to calibrate:** html_validation, brand_compliance, css_support, image_optimization, accessibility, dark_mode, spam_score, fallback, file_size, link_validation
**Security:**
- QA gate threshold changes tracked in version control with justification
- No QA check bypassed without the existing override + audit trail mechanism
**Verify:** Per-check precision and recall against human labels. At least 8/10 checks have precision > 0.80. Any underperforming checks documented with improvement plan.

### 5.7 Blueprint Pipeline Eval Runner (System-Wide)
**What:** Extend the eval runner to test the full Blueprint Engine end-to-end. Feed briefs through `BlueprintEngine.run()` and capture the entire graph execution: which nodes ran, iteration counts, QA retries, recovery routing decisions, final convergence. Test the self-correction loop: inject briefs that will fail QA on first pass and verify the pipeline recovers within 2 rounds. **As new agents join the blueprint graph, their nodes are covered by this runner.**
**Security:**
- Blueprint traces include token usage (cost tracking)
- Escalation events logged (when pipeline gives up and escalates to human)
- No infinite loop possible (MAX_TOTAL_STEPS=20 already enforced)
**Verify:** 5 end-to-end blueprint traces collected. At least 2 show successful self-correction (QA fail → recovery → pass). Escalation triggers correctly on intentionally unfixable inputs.

### 5.8 Automated Regression Suite (ALL Agents, System-Wide)
**What:** Wire eval runner into CI/CD. On model update or prompt change: run 10 representative test cases per agent, evaluate with judges, compare scores to baseline. Block deployment if pass rate drops > 10% from baseline. **This gate covers every agent in the system — when a new agent is added, its test cases and judge are added to the regression suite.** This is the "Evaluation Design" primitive in action.
**Security:**
- CI/CD eval runs use dedicated API keys with eval-only permissions
- Baseline scores stored in version control (not in database)
- Regression alerts go to team channel, not to clients
- Eval results never exposed in production API responses
**Verify:** Change a prompt → CI runs eval suite → regression detected → deployment blocked with report. Restore prompt → eval passes → deployment proceeds.

### Per-Agent Eval Specifications (Reference for Task 4.1)

**When building each of the remaining 6 agents, complete steps 5.1-5.5 for that agent before merging to main.**

| Agent | Eval Type | Key Dimensions | Judge Criteria |
|-------|-----------|----------------|----------------|
| **Outlook Fixer** | Code-based (MSO structure) + judge | Input complexity, Outlook version targeting, VML usage | MSO targeting correct? VML well-formed? Existing styles preserved? |
| **Accessibility Auditor** | Code-based (WCAG rules) + judge (alt text) | Violation severity, image context, heading structure | Alt text meaningful? Violations correctly identified? Severity appropriate? |
| **Personalisation Agent** | Code-based (syntax) + judge (logic) | ESP platform, conditional complexity, data source types | Syntax valid? Logic matches intent? Edge cases handled? |
| **Code Reviewer** | Mostly code-based (linting) | Code smell types, file size, CSS support matrix | Issues genuine? Suggestions actionable? Severity appropriate? |
| **Knowledge Agent** | RAG evals (Recall@k, faithfulness) | Query type, knowledge domain, answer specificity | Answer grounded in context? Relevant? Citations accurate? |
| **Innovation Agent** | Judge-based (feasibility, fallbacks) | Technique novelty, client coverage, fallback robustness | Feasibility accurate? Fallback robust? Coverage estimate real? |

---

## Security Checklist (Run Before Each Sprint Demo)

- [ ] All new endpoints have auth dependency injection
- [ ] All new endpoints have rate limiting configured
- [ ] All request schemas validate input (no raw strings to DB)
- [ ] All response schemas exclude sensitive fields
- [ ] No credentials in logs (grep for password, secret, key, token in log output)
- [ ] New database tables have appropriate RLS policies
- [ ] Frontend forms sanitise input before API calls
- [ ] Preview iframes use sandbox attribute
- [ ] Error responses don't leak internal details
- [ ] Audit entries created for all state-changing operations
- [ ] CORS configuration checked (no wildcards)
- [ ] Docker containers run as non-root
- [ ] New environment variables documented in `.env.example`

---

## Success Criteria (Plan Section 14.2)

| Metric | Target (3 months) | Target (6 months) |
|--------|-------------------|-------------------|
| Campaign build time | 1-2 days (from 3-5) | Under 1 day |
| Cross-client rendering defects | Caught before export | Near-zero reaching client |
| Component reuse rate | 30-40% | 60%+ |
| AI agent adoption | Team actively using 3 agents | Agents embedded in daily workflow |
| Knowledge base entries | 200+ indexed | 500+, team contributing |
| Cloud AI API spend | Under £600/month | Under £600/month |
