# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
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
- **JWT HS256**: HMAC-SHA256 signing with pinned algorithm constant. 15-min access + 7-day refresh.
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
**Verify:** Components render with correct [REDACTED] brand tokens. Dark mode toggle works. All components pass accessibility audit.

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
- Embedding model runs on infrastructure [REDACTED] controls (no PII sent to external embedding APIs)
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

### ~~4.1 Remaining 6 AI Agents~~ DONE
**Plan ref:** Section 5.1 (Agent Architecture), `.agents/plans/outlook-fixer-agent.md`
**Prerequisite:** Complete Phase 7 Step 1 (blueprint infrastructure: 7.1 + 7.3 + 7.4) and Step 2 (retrofit existing agents) BEFORE building new agents. This ensures every new agent inherits `AgentHandoff` schemas, confidence scoring, and component context from day one — no retrofitting needed.

**Build Order (prioritised):**
1. ~~**Outlook Fixer**~~ DONE — SKILL.md + 4 L3 skill files, service/prompt/schemas, blueprint node, recovery router integration, 12 synthetic test cases, 5-criteria judge, dry-run verified (535 tests pass)
2. ~~**Accessibility Auditor**~~ DONE — SKILL.md + 4 L3 skill files (wcag_email_mapping, alt_text_guidelines, color_contrast, screen_reader_behavior), service/prompt/schemas, blueprint node, recovery router integration, 10 synthetic test cases, 5-criteria judge (wcag_aa_compliance, alt_text_quality, contrast_ratio_accuracy, semantic_structure, screen_reader_compatibility), dry-run verified (540 tests pass)
3. ~~**Personalisation Agent**~~ DONE — SKILL.md + 4 L3 skill files (braze_liquid, sfmc_ampscript, adobe_campaign_js, fallback_patterns), service/prompt/schemas, blueprint node, recovery router integration, 12 synthetic test cases (4 Braze, 4 SFMC, 3 Adobe Campaign, 1 mixed), 5-criteria judge (syntax_correctness, fallback_completeness, html_preservation, platform_accuracy, logic_match), dry-run verified (540 tests pass)
4. ~~**Code Reviewer**~~ DONE — SKILL.md + 4 L3 skill files (redundant_code, css_client_support, nesting_validation, file_size_optimization), service/prompt/schemas, blueprint node, recovery router integration (css_support + file_size routed to code_reviewer), 12 synthetic test cases, 5-criteria judge (issue_genuineness, suggestion_actionability, severity_accuracy, coverage_completeness, output_format), dry-run verified (542 tests pass)
5. ~~**Knowledge Agent**~~ DONE — SKILL.md (pre-existing L1+L2) + 4 L3 skill files (rag_strategies, email_client_engines, can_i_email_reference, citation_rules), service/prompt/schemas, blueprint node (advisory — not in QA→recovery loop), 10 synthetic test cases (CSS property support, best practices, client quirks, comparisons, troubleshooting, edge cases), 5-criteria judge (answer_accuracy, citation_grounding, code_example_quality, source_relevance, completeness), dry-run verified (542 tests pass)
6. ~~**Innovation Agent**~~ DONE — SKILL.md (pre-existing L1+L2) + 4 L3 skill files (css_checkbox_hacks, amp_email, css_animations, feasibility_framework), service/prompt/schemas, blueprint node (advisory — not in QA→recovery loop), 10 synthetic test cases, 5-criteria judge (technique_correctness, fallback_quality, client_coverage_accuracy, feasibility_assessment, innovation_value), dry-run verified (191 AI tests pass)

#### Eval-First + Skills Build Pattern (applies to ALL agents)

Based on Anthropic's [Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills) pattern and real eval data from Phase 5.4-5.8 live execution. Each new agent follows this workflow:

```
1. SKILL.md first    → Write domain skill with progressive disclosure (L1 metadata, L2 instructions, L3+ reference files)
2. Synthetic data    → 10-12 dimension-based test cases in evals/synthetic_data_{agent}.py
3. Judge prompts     → 3-5 binary pass/fail criteria in evals/judges/{agent}.py
4. Generate traces   → make eval-run --agent {agent}
5. Error analysis    → make eval-analysis → identify skill gaps
6. Iterate skill     → Refine SKILL.md targeting failure clusters → re-eval → measure delta
7. Baseline          → make eval-baseline when pass rates stabilise
```

**Skill Structure (per agent):**
```
app/ai/agents/{agent}/
├── service.py          # Agent code — loads SKILL.md at runtime
├── prompt.py           # System prompt (thin — references SKILL.md)
├── schemas.py          # Input/output schemas
├── SKILL.md            # L1: YAML frontmatter (name, description) + core instructions
├── skills/             # L3+: Progressive disclosure reference files
│   ├── {topic}.md      # Loaded on-demand when agent detects relevance
│   └── ...
└── evals/              # Agent-specific eval data (shared runner/judges)
```

**Key principle:** Skills are testable via the eval system. Each skill file's impact is measurable: add skill → re-eval → check if target criteria improve. No guessing.

**Existing skill asset:** `app/ai/agents/html-email-innovation.skill` — 668-line production skill covering Outlook bug fixes (15 patterns), VML, dark mode, Braze/Liquid, accessibility, responsive layouts. To be decomposed into per-agent SKILL.md files.

**Real eval failure data informing agent priorities:**
| Eval Failure (Phase 5.4-5.8) | Target Agent | SKILL.md Source |
|---|---|---|
| scaffolder:mso_conditional_correctness 0% | Outlook Fixer | html-email-innovation.skill Parts 1-2 |
| scaffolder:accessibility_baseline 8% | Accessibility Auditor | html-email-innovation.skill Part 4 |
| scaffolder:dark_mode_readiness 25% | (Dark Mode agent skill refinement) | html-email-innovation.skill Section 5 |
| dark_mode:html_preservation 10% | (Dark Mode agent skill refinement) | html-email-innovation.skill Section 5 |
| content:operation_compliance 57% | (Content agent skill refinement) | — |

### ~~4.2 Additional CMS Connectors~~ DONE
**Plan ref:** Section 3.1 (~2-3 days each), `.agents/plans/4.2-additional-cms-connectors.md`
**What:** Add SFMC, Adobe Campaign, and Taxi for Email backend connectors following the Braze pattern. All three are placeholder implementations (mock API calls) matching the Braze style.
**Backend:** `ConnectorProvider` Protocol in `app/connectors/protocol.py` for type-safe dispatch; `SUPPORTED_CONNECTORS` registry mapping connector type strings to provider classes with lazy instantiation and caching; 3 new connector packages: `app/connectors/sfmc/` (SFMCConnectorService — Content Builder Content Area with AMPscript packaging), `app/connectors/adobe/` (AdobeConnectorService — delivery content fragments with Adobe IMS packaging), `app/connectors/taxi/` (TaxiConnectorService — Taxi Syntax-wrapped templates); each with schemas + service following Braze pattern; 16 unit tests (4 protocol conformance + 12 provider tests); demo mutation resolver updated for per-connector mock IDs.
**Security:**
- All connector services satisfy `ConnectorProvider` Protocol (runtime-checkable)
- No credential storage yet (placeholder implementations) — AES-256 encryption deferred to real API integration
- Export audit trail via existing `ExportRecord` model (unchanged)
**Verify:** `make test` passes (304 tests). All 4 connectors dispatch correctly via `POST /api/v1/connectors/export`. Frontend export dialog works with sfmc/adobe_campaign/taxi in demo mode. `connector_type` validation returns 422 for unsupported types.

### ~~4.3 Design Sync — Multi-Provider Backend + Frontend Rename~~ DONE
**Plan ref:** Section 4 (Design Tool Integration), `.agents/plans/figma-design-sync.md`
**What:** Full `app/design_sync/` VSA module with multi-provider architecture. `DesignSyncProvider` Protocol with 3 implementations: `FigmaDesignSyncService` (real Figma REST API — `httpx` calls to `/v1/files/{key}` and `/v1/files/{key}/styles`, parses colors/typography/spacing), `SketchDesignSyncService` (stub), `CanvaDesignSyncService` (stub). Fernet-encrypted PAT storage (PBKDF2-derived from `DESIGN_SYNC__ENCRYPTION_KEY` or `AUTH__JWT_SECRET_KEY`). `DesignConnection` + `DesignTokenSnapshot` SQLAlchemy models with cascade delete. BOLA enforcement via `verify_project_access()` on single-resource ops + user-scoped list queries (admin sees all projects, others see owned + member projects). 6 REST endpoints at `/api/v1/design-sync/` with auth + rate limiting. Frontend renamed from `/figma` → `/design-sync` with provider filter tabs (All/Figma/Sketch/Canva), generic connect dialog with provider dropdown, provider icons. All hooks/types/components/demo data/i18n updated. 19 backend tests, Alembic migration.
**Backend:** `app/design_sync/` — `protocol.py` (Protocol + dataclasses), `crypto.py` (Fernet encrypt/decrypt), `models.py`, `schemas.py` (field mapping for frontend compat), `repository.py`, `service.py` (provider registry, BOLA), `routes.py`, `exceptions.py`; `figma/service.py` (real API), `sketch/service.py` (stub), `canva/service.py` (stub); `tests/test_service.py` (19 tests); `DesignSyncConfig` in `app/core/config.py`; `cryptography>=44.0.0` in `pyproject.toml`.
**Frontend:** `/design-sync` page with `DesignConnectionCard`, `DesignStatusBadge`, `DesignTokensView`, `ConnectDesignDialog`, `ProviderIcon` components; 6 SWR hooks in `use-design-sync.ts`; `types/design-sync.ts`; demo data with `provider` field; i18n `designSync` namespace; nav link updated.
**Remaining:** Change webhook handling, plugin ecosystem (Emailify, Email Love, MigmaAI), pagination on list endpoint.
**Verify:** `/design-sync` page loads. Connect dialog creates connection with provider selection. Sync triggers real Figma API (with valid PAT). Design tokens extracted. `make check` passes (lint, types, 19 tests).

### ~~4.4 Litmus / Email on Acid API Integration~~ DONE
**Plan ref:** Section 7.2 (Cross-Client Render), `.agents/plans/4.4-litmus-eoa-integration.md`
**What:** New `app/rendering/` VSA module for cross-client rendering tests via Litmus and Email on Acid APIs. `RenderingProvider` Protocol (same pattern as `ConnectorProvider`) with `submit_test`, `poll_status`, `get_results` methods. Two provider implementations: `litmus/` and `eoa/` (placeholder APIs). `RenderingTest` + `RenderingScreenshot` DB models. Repository with eager-loaded screenshots, filtered list/count, pending poller query. `RenderingService` with circuit breaker (`CircuitBreaker` from `app/core/resilience`), visual regression comparison (per-client diff percentage with 2% threshold). `RenderingConfig` in `app/core/config.py` (`RENDERING__PROVIDER`, `RENDERING__LITMUS_API_KEY`, `RENDERING__EOA_API_KEY`, polling settings). 4 REST endpoints under `/api/v1/rendering/` (submit, list, get, compare) with auth + rate limiting. 12 unit tests (316 total).
- ~~API integration for 20+ client rendering screenshots~~ DONE
- ~~Visual regression detection~~ DONE
- ~~Rendering report generation~~ DONE
- ~~Frontend UI alignment with backend schemas~~ DONE — Types, hooks, demo data aligned to backend `RenderingTestResponse`/`ScreenshotResult`; 6 components updated + 1 new (`VisualRegressionDialog`); API paths fixed (`/rendering/` not `/renderings/`); async polling, pagination, HTML input, visual regression comparison UI

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
> | 4 | **Outlook Fixer** | Implemented (4.1) | 12 synthetic cases, 5-criteria judge |
> | 5 | **Accessibility Auditor** | Implemented (4.1) | 10 synthetic cases, 5-criteria judge |
> | 6 | **Personalisation Agent** | Implemented (4.1) | 12 synthetic cases, 5-criteria judge |
> | 7 | **Code Reviewer** | Implemented (4.1) | 12 synthetic cases, 5-criteria judge |
> | 8 | **Knowledge Agent** | Implemented (4.1) | 10 synthetic cases, 5-criteria judge |
> | 9 | **Innovation Agent** | Implemented (4.1) | 10 synthetic cases, 5-criteria judge |
>
> **Rule: No agent goes to production without completing steps 5.1-5.5 for that agent.** Steps 5.6-5.8 apply system-wide.

> **Progress:**
> - [x] Eval framework scaffolded (`app/ai/agents/evals/`)
> - [x] Dimensions defined for Scaffolder, Dark Mode, Content
> - [x] Synthetic data created for 3 implemented agents (36 test cases total)
> - [x] Real-world email patterns sourced (Litmus, MailChimp, Parcel.io, email-darkmode repo, Mailmeteor)
> - [x] Eval runner CLI created (`runner.py`)
> - [ ] 5.1 — Review & harden test data (security audit)
> - [x] 5.2 — Write LLM judge prompts (3 of 9 agents)
> - [ ] 5.3 — Run first eval batch & collect traces
> - [x] 5.4 — Error analysis tooling built (`error_analysis.py` CLI, failure clustering, pass rate computation; 11 unit tests)
> - [x] 5.5 — Judge calibration tooling built (`calibration.py` TPR/TNR + `scaffold_labels.py` prefilled label templates; 11 unit tests)
> - [x] 5.6 — QA gate calibration tooling built (`qa_calibration.py` check-vs-human agreement; 9 unit tests)
> - [x] 5.7 — Blueprint pipeline eval runner built (`blueprint_eval.py` with 5 test briefs; 8 unit tests)
> - [x] 5.8 — Regression detection built (`regression.py` baseline comparison + `make eval-check` CI gate; 10 unit tests)
> - [x] 5.4-5.8 — **Dry-run pipeline**: `--dry-run` flag on runner/judge/blueprint CLIs; `mock_traces.py` deterministic generators; `make eval-dry-run` exercises full pipeline without LLM; `make eval-full`/`eval-calibrate`/`eval-qa-calibrate` targets; 9 integration tests (58 eval tests total)
> - [x] 5.4-5.8 — **Live execution hardening**: `verify_provider.py` pre-flight check (`make eval-verify`); incremental JSONL writing (crash-safe); `--skip-existing` resume flag on runner + judge_runner; `eval-run` auto-verifies provider before running
> - [x] 5.4-5.8 — **Live execution** (2026-03-09): 36 traces + 36 verdicts via `anthropic:claude-sonnet-4`. Baseline established (16.7% overall pass rate). Blueprint evals 5/5 passed (100% QA with self-correction). Human labeling pending (540 rows in `traces/*_human_labels.jsonl`)
> - [x] Eval data for Outlook Fixer — 12 synthetic cases, 5-criteria judge (`OutlookFixerJudge`), blueprint node + recovery router integration
> - [x] Eval data for Accessibility Auditor — 10 synthetic cases, 5-criteria judge (`AccessibilityJudge`), blueprint node + recovery router integration
> - [x] Eval data for Personalisation Agent — 12 synthetic cases, 5-criteria judge (`PersonalisationJudge`), blueprint node + recovery router integration
> - [x] Eval data for Code Reviewer — 12 synthetic cases, 5-criteria judge (`CodeReviewerJudge`), blueprint node + recovery router integration
> - [x] Eval data for Knowledge Agent — 10 synthetic cases, 5-criteria judge (`KnowledgeJudge`), advisory blueprint node (no recovery router — Q&A agent)
> - [x] Eval data for Innovation Agent — 10 synthetic cases, 5-criteria judge (`InnovationJudge`), advisory blueprint node (no recovery router — generator agent)

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
- Binary LLM judges implemented for 4 agents: `app/ai/agents/evals/judges/` package with `ScaffolderJudge` (5 criteria), `DarkModeJudge` (5 criteria), `ContentJudge` (5 criteria), `OutlookFixerJudge` (5 criteria: mso_conditional_correctness, vml_wellformedness, html_preservation, fix_completeness, outlook_version_targeting); shared `Judge` Protocol, `parse_judge_response()` with markdown fence handling; `JUDGE_REGISTRY` for dispatch; `judge_runner.py` CLI with batched execution and rate limiting
- **All 9 agents have eval data** — synthetic test cases + LLM judges for every agent

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
**Tooling built:** `app/ai/agents/evals/error_analysis.py` — CLI that reads verdict JSONL, clusters failures by (agent, criterion), computes per-criterion pass rates, identifies top 3 failure modes. Run via `make eval-analysis`. 11 unit tests.
**Security:**
- Error analysis results stored as structured data (not freeform text that could leak into prompts)
- Failure taxonomy scoped to technical categories (no client-identifying information)
**Verify:** Failure taxonomy document with categories, counts, and examples. Top 3 failure modes per agent identified with severity rating.

### 5.5 Calibrate Judges Against Human Labels (ALL Agents)
**What:** Following the evals-skills `validate-evaluator` methodology, have a domain expert (email developer) manually label 20 agent outputs per agent as pass/fail. Run the LLM judges on the same outputs. Compute TPR (true positive rate) and TNR (true negative rate). Target: TPR > 0.85, TNR > 0.80. **Every agent needs this — no agent's judge is trusted without human calibration.**
**Tooling built:** `app/ai/agents/evals/scaffold_labels.py` — generates prefilled JSONL label templates from traces+verdicts (user fills `human_pass` true/false). `app/ai/agents/evals/calibration.py` — CLI that computes TPR/TNR per criterion against human labels. Run via `make eval-labels` then manual labeling. One file per agent containing both judge + QA criteria. 11 unit tests.
**Security:**
- Human labels stored separately from traces (no contamination)
- Labeling interface does not expose system prompts or agent internals
- Label data is project-scoped and access-controlled
**Verify:** Confusion matrix per judge. TPR and TNR meet targets. If not, iterate on judge prompts and re-calibrate.

### 5.6 Calibrate the 10-Point QA Gate (System-Wide)
**What:** Using the human-labeled outputs from 5.5, measure the QA gate's agreement with human judgment across all agents. Identify which of the 10 checks have low precision or recall. Adjust thresholds or add new checks where the gate misses failures that humans catch.
**QA checks to calibrate:** html_validation, brand_compliance, css_support, image_optimization, accessibility, dark_mode, spam_score, fallback, file_size, link_validation
**Tooling built:** `app/ai/agents/evals/qa_calibration.py` — CLI that runs all 10 QA checks on trace HTML, compares pass/fail against human labels, reports per-check agreement rate and flags checks <75% for tuning. 9 unit tests.
**Security:**
- QA gate threshold changes tracked in version control with justification
- No QA check bypassed without the existing override + audit trail mechanism
**Verify:** Per-check precision and recall against human labels. At least 8/10 checks have precision > 0.80. Any underperforming checks documented with improvement plan.

### 5.7 Blueprint Pipeline Eval Runner (System-Wide)
**What:** Extend the eval runner to test the full Blueprint Engine end-to-end. Feed briefs through `BlueprintEngine.run()` and capture the entire graph execution: which nodes ran, iteration counts, QA retries, recovery routing decisions, final convergence. Test the self-correction loop: inject briefs that will fail QA on first pass and verify the pipeline recovers within 2 rounds. **As new agents join the blueprint graph, their nodes are covered by this runner.**
**Tooling built:** `app/ai/agents/evals/blueprint_eval.py` — CLI with 5 test briefs (happy_path_simple, dark_mode_recovery, complex_layout_retry, vague_brief, accessibility_heavy). Captures per-node traces with step/retry counts, token usage, elapsed time. 8 unit tests.
**Security:**
- Blueprint traces include token usage (cost tracking)
- Escalation events logged (when pipeline gives up and escalates to human)
- No infinite loop possible (MAX_TOTAL_STEPS=20 already enforced)
**Verify:** 5 end-to-end blueprint traces collected. At least 2 show successful self-correction (QA fail → recovery → pass). Escalation triggers correctly on intentionally unfixable inputs.

### 5.8 Automated Regression Suite (ALL Agents, System-Wide)
**What:** Wire eval runner into CI/CD. On model update or prompt change: run 10 representative test cases per agent, evaluate with judges, compare scores to baseline. Block deployment if pass rate drops > 10% from baseline. **This gate covers every agent in the system — when a new agent is added, its test cases and judge are added to the regression suite.** This is the "Evaluation Design" primitive in action.
**Tooling built:** `app/ai/agents/evals/regression.py` — CLI that compares current pass rates against stored baseline with configurable tolerance (default 10%). `--update-baseline` flag. Exits code 1 on regression (CI gate). `make eval-check` combines analysis + regression. 10 unit tests. **Note:** CI integration deferred — Makefile targets only for now.
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

## Phase 6 — OWASP API Top 10 Security Hardening

Audit conducted 2026-03-06 using CodeQL + Semgrep + manual route review. Root cause: `current_user` is authenticated at route level but NOT passed to service layer for authorization. The `templates` module does this correctly with `verify_project_access()` — replicate across all affected modules.

### 6.1 BOLA Fixes — Add `verify_project_access()` to All Resource Endpoints
**Affects:** `approval/`, `connectors/`, `qa_engine/`, `rendering/`, `knowledge/`, `projects/`
**Pattern:** Pass `current_user` to service → call `verify_project_access(resource.project_id, user)` before read/write

- [x] 6.1.1 `PATCH /projects/{id}` — ~~any developer can update ANY project~~ DONE — `verify_project_access()` added (CRITICAL)
- [x] 6.1.2 `POST /approvals/{id}/decide` — ~~any user can approve/reject ANY approval~~ DONE — all 7 approval endpoints protected (CRITICAL)
- [x] 6.1.3 `POST /connectors/export` — ~~any developer can export ANY build by ID~~ DONE — build→project FK chain verified (CRITICAL)
- [x] 6.1.4 `POST /qa/results/{id}/override` — ~~any developer can override ANY QA result~~ DONE — QA→build→project FK chain verified (CRITICAL)
- [x] 6.1.5 `GET/POST /approvals/{id}/*` — ~~all approval endpoints lack project access checks~~ DONE — `_verify_approval_access()` helper (HIGH)
- [x] 6.1.6 `POST /rendering/compare` — ~~can compare any two test IDs without ownership~~ DONE — both test project IDs verified (HIGH)
- [x] 6.1.7 `GET /knowledge/documents/{id}/download` — already role-gated (admin/developer), no project-scoped changes needed (HIGH)
- [x] 6.1.8 WebSocket `/ws/stream` — ~~no multi-tenant isolation~~ DONE — project_id filter validated against membership (HIGH)
- [x] 6.1.9 AI agent endpoints — ~~agents accept briefs without project scoping~~ DONE — optional project_id with access check (HIGH)
- [x] 6.1.10 `GET /email/builds/{build_id}` — ~~any authenticated user can fetch any build by ID~~ DONE — `verify_project_access(build.project_id, user)` added to `EmailEngineService.get_build()` (CRITICAL)

### ~~6.2 Response & Error Hardening~~ DONE
- [x] 6.2.1 `POST /email/build` — ~~raw exception messages leaked to client~~ DONE — `error_sanitizer.py` central safe message registry; `email_engine` + `connectors` store generic messages in DB, log real errors server-side (HIGH)
- [x] 6.2.2 LLM provider calls — ~~no circuit breaker~~ DONE — `_ResilientLLMProvider` wraps all LLM `complete()` calls with `CircuitBreaker` (5 failures → 60s open); all adapter/agent/service error messages genericized (no provider names, status codes, or raw exceptions) (HIGH)
- [x] 6.2.3 Error handler leaks exception class names to client — DONE — `get_safe_error_type()` returns generic categories (`not_found`, `forbidden`, `ai_error`, etc.); `get_safe_error_message()` with MRO-walking safe message lookup; passthrough for validation errors only; 21 unit tests (MEDIUM)
- [x] 6.2.4 Auth exception handlers (`invalid_credentials_handler`, `account_locked_handler`) leaked `"InvalidCredentialsError"` / `"AccountLockedError"` type strings — DONE — now use `get_safe_error_message/type()`, returning `"authentication_error"` / `"account_locked"` generic types; 2 new tests (HIGH)

### ~~6.3 Rate Limiting & Resource Controls~~ DONE
- [x] 6.3.1 AI quota per-IP (in-memory) → per-user (Redis) — DONE — `UserQuotaTracker` in `app/core/quota.py` (Redis-backed with in-memory fallback); `app/ai/routes.py` keyed by `current_user.id`; 7 unit tests (MEDIUM)
- [x] 6.3.2 Per-user WebSocket connection limit — DONE — `ConnectionManager` tracks `_user_connections` dict; `max_connections_per_user=5` config; broadcast cleanup syncs user tracking; 7 unit tests (MEDIUM)
- [x] 6.3.3 Timeout on LLM streaming responses — DONE — `asyncio.timeout(stream_timeout_seconds)` in `ChatService.stream_chat()`; sends `finish_reason: "timeout"` chunk; `stream_timeout_seconds=120` config; 2 unit tests (MEDIUM)
- [x] 6.3.4 Blueprint daily cost cap — DONE — `BlueprintCostTracker` in `app/core/quota.py` (Redis-backed); checks budget after each node, breaks with `cost_cap_exceeded`; `daily_token_cap=500k` config; `user_id` threaded route→service→engine; 4 unit tests (MEDIUM)

### ~~6.4 Business Logic Hardening~~ DONE
- [x] 6.4.1 Approval state machine — prevent invalid transitions (MEDIUM)
- [x] 6.4.2 JWT algorithm — pin HS256 constant, remove config override, align docs (MEDIUM)
- [x] 6.4.3 LLM output sanitization — replace regex with nh3 allowlist sanitizer (MEDIUM)

### ~~6.5 Security Development Cycle (SDC) Improvements~~ DONE
- [x] 6.5.1 `make check` now includes `security-check` — developers cannot skip Bandit security lint (SDC)
- [x] 6.5.2 CI workflow (`.github/workflows/ci.yml`) — backend (lint + types + security + test) and frontend (types + test) on push/PR to main (SDC)
- [x] 6.5.3 PR template (`.github/PULL_REQUEST_TEMPLATE.md`) — security checklist (auth, authz, input validation, error sanitization, rate limiting) (SDC)
- [x] 6.5.4 Memory routes missing rate limiting — DONE — all 5 `/memory/` endpoints now have `@limiter.limit()` (10/min writes, 30/min reads) (MEDIUM)
- [x] 6.5.5 Frontend token expiry mismatch — DONE — `auth.ts` now reads JWT `exp` claim via `getExpFromToken()` instead of hardcoded 14-min offset; removed `(user as any)` type casts (MEDIUM)
- [x] 6.5.6 Export history sessionStorage validation — DONE — `isValidRecord()` type guard validates parsed JSON shape before use (MEDIUM)

---

## Phase 7 — Agent Capability Improvements

**Plan ref:** Section 5.1 (Agent Architecture), Section 5.6 (Smart Agent Memory), Section 5.7 (Agent Harness Architecture)
**What:** Enhancements to agent quality, coordination, and self-improvement that go beyond what the current plan covers. These build on the existing blueprint engine, eval system, and RAG pipeline — wiring things together rather than building new systems.

### Execution Strategy

Run evals first to establish a baseline, build Phase 7 infrastructure before the remaining 6 agents, then integrate Cognee so every new agent inherits all patterns from day one.

~~**Step 0 — Eval Baseline (Phase 5.4-5.8 execution)**~~ DONE (2026-03-09)
Live eval executed: 36 traces + 36 verdicts via `anthropic:claude-sonnet-4`. Baseline: 16.7% overall (scaffolder 46.7%, dark_mode 82%, content 85.7%). Blueprint evals 5/5 passed. Top failures: mso_conditionals (0%), accessibility (8%), html_preservation (10%). Data unblocks 7.2 (eval-informed prompts) and 4.1 (skill-first agent builds).

~~**Step 1 — Blueprint Infrastructure (7.1 + 7.3 + 7.4)**~~ DONE
Built `AgentHandoff` frozen dataclass, `ComponentMeta`, `ComponentResolver` Protocol in `protocols.py`. Engine stores/propagates handoff, checks confidence < 0.5 → `needs_review` status. Async `_build_node_context` with component context injection. `extract_confidence()`/`strip_confidence_comment()` in `shared.py`. `DbComponentResolver` in `resolvers.py`. `HandoffSummary` in API response schema. 21 new tests.

~~**Step 2 — Retrofit Existing Agents (Scaffolder, Dark Mode)**~~ DONE
Updated ScaffolderNode + DarkModeNode to emit `AgentHandoff` with confidence scores and component refs. DarkModeNode reads upstream handoff warnings. RecoveryRouterNode reads handoff warnings for dark mode routing hints. System prompts updated with confidence assessment instructions. Content agent retrofit deferred (no blueprint node yet).

~~**Step 2.5 — Full Handoff History + Memory Persistence Bridge**~~ DONE (2026-03-09)
Extended `BlueprintRun._handoff_history` to accumulate ALL handoffs (not just latest). Downstream nodes receive `context.metadata["handoff_history"]` with full chain. API response includes `handoff_history: list[HandoffSummary]`. Created `handoff_memory.py` bridge that auto-persists each handoff as episodic memory via `on_handoff` callback. Wired into `BlueprintService.run()`. Failure-safe (callback errors logged, never crash pipeline). 4 new tests (8 total handoff tests).

~~**Step 2.6 — SKILL.md Files for Existing Agents (Scaffolder, Dark Mode)**~~ DONE (2026-03-09)
Created progressive disclosure SKILL.md files for Scaffolder (L1+L2 + 4 L3 files: client_compatibility, maizzle_syntax, mso_vml_quick_ref, table_layouts) and Dark Mode (L1+L2 + 3 L3 files: client_behavior, color_remapping, outlook_dark_mode). Services updated with `detect_relevant_skills()` + `build_system_prompt()` for on-demand skill loading based on brief analysis.

~~**Step 3 — Cognee Integration + Ontology + Seeding (8.1 + 8.6 + 8.2)**~~ DONE (2026-03-10)
~~8.1 Cognee integration layer~~ DONE: `app/knowledge/graph/` module with `GraphKnowledgeProvider` Protocol + `CogneeGraphProvider` implementation; `CogneeConfig` in settings (disabled by default, inherits AI config); `POST /api/v1/knowledge/graph/search` endpoint (auth + 20/min rate limit, chunks + completion modes); `GraphError` → `AppError` hierarchy; cognee as optional dependency (`pip install -e ".[graph]"`); 8 unit tests (568 total). ~~8.6 Email development ontology~~ DONE: `app/knowledge/ontology/` Python-native module — 25 email clients, 365 CSS properties, 1011 support entries, 70 fallback relationships in YAML data files; `OntologyRegistry` singleton with indexed lookups; `unsupported_css_in_html()` query powering data-driven QA; `export_ontology_documents()` for Cognee graph ingestion; `css_support.py` QA check replaced with ontology-powered scan; 51 tests (661 total). ~~8.2 Knowledge graph seeding~~ DONE: `_seed_ontology_graph()` added to `seed.py` feeding ontology-derived documents into Cognee ECL pipeline alongside existing RAG document seeding.

~~**Step 4 — Graph Context Provider + SKILL.md Files (8.3 + 8.5)**~~ DONE (2026-03-10)
~~8.3 Graph context provider~~ DONE: `app/ai/blueprints/graph_context.py` wired into blueprint engine `_build_node_context()`. ~~8.5 SKILL.md files~~ DONE: All 9 agents have progressive disclosure SKILL.md (L1+L2) + L3 skill files with on-demand loading via `detect_relevant_skills()` + `build_system_prompt()`.

~~**Step 5 — Build Remaining 6 Agents WITH Phase 7+8 Patterns (Task 4.1)**~~ DONE (Outlook Fixer, Accessibility Auditor, Personalisation, Code Reviewer, Knowledge, Innovation — all complete)
Each new agent inherits handoff/confidence/context/graph/SKILL.md infrastructure from day one. No retrofitting needed.

~~**Step 5.5 — Agent Architecture Improvements (`.agents/plans/agent-improvements.md`)**~~ DONE (2026-03-09)
All 6 phases complete. `BaseAgentService` shared pipeline extracted (`app/ai/agents/base.py`) — 7 agents refactored, ~500 lines removed. Thread-safe `_get_model_tier` + `_should_run_qa` hooks replace singleton state mutation. Prompt gap fixes (scaffolder MSO/a11y/dark mode MANDATORY, content num_alternatives). Recovery router: "fallback" keyword collision fixed + cycle detection via `handoff_history`. Eval trace fix (dark mode input HTML stored, judge graceful degradation). Response schemas standardised: `confidence` + `skills_loaded` on all 9 agents; `to_handoff()` on BaseAgentService. Memory recall wired into blueprint engine `_build_node_context()`. 544 tests pass.

~~**Step 6 — Eval-Informed Prompts (7.2)**~~ DONE (2026-03-09)
Created `app/ai/agents/evals/failure_warnings.py` — reads `traces/analysis.json` (from `make eval-analysis`), filters per-agent criteria below 85% pass rate, generates formatted warning fragments injected into all 9 agent `build_system_prompt()` between L2 SKILL.md and L3 reference files. Mtime-cached, max 5 warnings per agent (worst-first), mock reasoning cleanup, graceful degradation when no analysis file exists. 16 new tests, 560 total passing. Plan: `.agents/plans/eval-informed-prompts.md`.

~~**Step 7 — Outcome Logging (8.4)**~~ DONE (2026-03-10)
`outcome_logger.py` formats blueprint run outcomes as narrative summaries + queues to Redis + stores in pgvector Memory. `OutcomeGraphPoller` background task drains Redis queue into Cognee graph with batch processing and leader election. Fire-and-forget pattern ensures graph/memory errors never impact blueprint API. 19 tests.

### ~~7.1 Structured Inter-Agent Handoff Schemas~~ DONE (extended 2026-03-09)
**What:** Define typed handoff contracts between agents in blueprint pipelines. Currently agents chain via raw HTML output. Instead, each agent should emit a structured handoff object containing: the output artifact, metadata about decisions made (e.g., "used 2-column layout", "applied VML fallback for hero"), warnings/caveats, and context the next agent needs.
**Why:** Dark Mode agent receiving raw HTML from Scaffolder doesn't know which design patterns were used, which components were pulled in, or what trade-offs were made. Structured handoffs eliminate "undoing each other's work."
**Implementation:** `AgentHandoff` frozen dataclass in `app/ai/blueprints/protocols.py` with `artifact`, `decisions`, `warnings`, `component_refs`, `confidence` fields. Blueprint engine passes handoff objects between nodes. **Extended:** Full handoff history accumulates in `BlueprintRun._handoff_history` — all nodes see every prior node's decisions via `context.metadata["handoff_history"]`. Auto-persisted to episodic memory via `handoff_memory.py` bridge (`on_handoff` callback). API response includes `handoff_history: list[HandoffSummary]`.
**Retrofit:** Updated Scaffolder, Dark Mode to emit `AgentHandoff`. RecoveryRouterNode reads upstream warnings.
**Security:** Handoff objects scoped to blueprint session. No cross-project leakage. Decisions logged to audit trail. Memory persistence failure-safe (callback errors logged, never crash pipeline).
**Verify:** Blueprint pipeline passes structured handoff between scaffolder → dark_mode nodes. Full history available to all downstream nodes. Handoffs auto-persisted to memory. 8 unit tests (4 original + 4 history/callback tests).

### ~~7.2 Eval-Informed Agent Prompts~~ DONE (2026-03-09)
**What:** Feed common failure patterns from eval error analysis (`make eval-analysis`) back into agent system prompts automatically. When eval clusters show recurring failures (e.g., "Scaffolder consistently misses MSO conditionals for 3-column layouts"), inject those as explicit warnings in the agent's prompt.
**Why:** Eval system already captures failure clusters in `error_analysis.py`. Currently this data sits in JSONL files — it should actively improve agent performance in a feedback loop.
**Prerequisite:** ~~Requires real eval traces from Phase 5.4-5.8 live execution.~~ DONE — baseline established 2026-03-09 with real failure patterns available in `traces/analysis.json`.
**Implementation:** `app/ai/agents/evals/failure_warnings.py` — reads `traces/analysis.json`, filters per-agent criteria <85% pass rate, formats `## KNOWN FAILURE PATTERNS` prompt section (max 5 warnings, worst-first, mock reasoning cleanup). All 9 agent `prompt.py` files call `get_failure_warnings("agent_name")` in `build_system_prompt()`, injecting between L2 SKILL.md and L3 reference files. Mtime-based caching avoids re-reading JSON per call. Graceful degradation (returns `None` if no analysis file). Plan: `.agents/plans/eval-informed-prompts.md`.
**Security:** Failure patterns contain no user data (only aggregated error categories). No new routes or API surface. Analysis path hardcoded, not user-controllable.
**Verify:** 16 unit tests in `app/ai/agents/evals/tests/test_failure_warnings.py`. 560 total tests pass. With `traces/analysis.json` present, agents get failure warnings. Without it, prompts unchanged.

### ~~7.3 Agent Confidence Scoring~~ DONE
**What:** Agents emit a confidence score (0-1) alongside their output, based on self-assessment of task complexity, knowledge gaps, and output quality. Blueprint engine uses confidence to decide: high confidence → proceed to QA, low confidence → route to human review instead of burning retry loops.
**Why:** Prevents wasting 2-3 self-correction rounds on tasks the agent knows it can't solve. Surfaces genuinely hard problems to developers faster.
**Implementation:** `confidence` field on agent response schema. Configurable threshold per agent (default: 0.6). Blueprint engine checks confidence before routing to QA vs human review node. Confidence calibrated against eval pass rates over time.
**Retrofit:** Add confidence self-assessment step to Scaffolder, Dark Mode, Content agents. Initial thresholds set conservatively (0.5) and tuned after eval data available.
**Security:** Confidence scores logged in audit trail. Never exposed to end-users (internal routing metric only).
**Verify:** Agent returns confidence score. Blueprint routes low-confidence outputs to human review node. Confidence correlates with actual QA pass rate (validated via eval data).

### ~~7.4 Template-Aware Component Context~~ DONE
**What:** When an agent works on a template that uses components from the component library, automatically load that component's metadata (version, dark mode variant, known quirks, compatibility notes) into the agent's context.
**Why:** Scaffolder pulls in a `hero` component but doesn't know it has a known Outlook 2016 rendering issue. Dark Mode agent doesn't know the component already has a dark mode variant. This context prevents redundant work and avoids breaking working components.
**Implementation:** Template parser identifies component references → queries `app/components/` for metadata → injects as structured context in agent prompt. Leverages existing component versioning and the progressive disclosure pattern (only loads components actually used).
**Retrofit:** Existing agents automatically benefit once the component context loader is wired into the blueprint engine — no per-agent changes needed.
**Security:** Component metadata is project-scoped (existing RLS). No additional access surface.
**Verify:** Agent working on template with `hero` component receives component metadata in context. Agent output references component-specific constraints. Token usage stays within progressive disclosure budget.

### ~~7.5 Hub Agent Memory System (PRD 4.9.3-4.9.6)~~ DONE
**Plan ref:** PRD Section 4.9.3-4.9.6 (Agent Memory Entries, Temporal Decay, Cross-Agent Sharing), `.agents/plans/dcg-agent-memory.md`
**What:** Full `app/memory/` VSA module with pgvector-backed semantic memory for AI agents. Persistent, project-scoped memory entries with vector embeddings for similarity search, temporal decay, and a DCG note promotion bridge (4.9.7).
**Implementation:** `MemoryEntry` model with `Vector(1024)` embedding, HNSW index, 3 memory types (procedural/episodic/semantic), temporal decay via `POWER(2, -age/half_life)`, 5 REST endpoints (`POST /memory`, `POST /memory/search`, `GET /memory/{id}`, `DELETE /memory/{id}`, `POST /memory/promote`), `MemoryCompactionPoller` background task, `MemoryConfig` in settings. Alembic migration `f1a2b3c4d5e6`. 19 unit tests (repository: 6, service: 6, routes: 7).
**Verify:** Store, recall, promote all tested. Auth on all endpoints (admin/developer). Viewer role blocked (403). 404 on missing entries. Lint, mypy, pyright all clean.

### ~~7.6 DCG-Based Lightweight Cross-Agent Memory~~ DONE
**Plan ref:** PRD Section 4.9.7 (DCG Agent Memory), `destructive_command_guard/docs/prd-agent-memory-sharing.md`
**What:** Add 2 MCP tools (`store_note`, `recall_notes`) to the existing dcg MCP server, enabling agents to share project-scoped observations via append-only JSONL files. Zero new dependencies, ~150 lines of Rust.
**Why:** dcg already sits in the critical path of every agent's command execution and auto-detects which agent is calling. The history DB already stores per-agent evaluation data. Exposing a lightweight key/value note layer via MCP gives agents cross-agent memory with no infrastructure cost — complementing the Hub's full pgvector memory system (7.5) at the shell/tool layer.
**Dependencies:** None. Uses existing dcg MCP server, agent detection, and JSONL I/O.
**Implementation:**

#### Phase 1 — Core (MVP) DONE
- [x] Add `AgentNote` struct to `destructive_command_guard/src/notes.rs` (timestamp, agent, key, value, project)
- [x] Implement `store_note()` — append to `.dcg/{project}_notes.jsonl` with auto-detected agent identity
- [x] Implement `recall_notes()` — read + filter from JSONL (by key, agent, project; limit 50)
- [x] Register both tools in `handle_list_tools_request` and `handle_call_tool_request`
- [x] Enforce size limits (1024 char value, 500 notes max per project, 128 char key)
- [x] Key namespace convention: `project.*`, `safety.*`, `workflow.*`, `config.*`
- [x] 13 unit tests for store/recall round-trip, isolation, limits, sanitization
- [x] 1 MCP integration test (store from "agent A", recall from "agent B")

**Security:** Notes are project-local (no cross-project leakage). Agent identity auto-detected (not self-reported). `.dcg/` gitignored.
**Verify:** Agent A stores a note. Agent B recalls it via MCP. Store/recall latency < 5ms.

---

## Phase 8 — Knowledge Graph Integration (Cognee)

**Plan ref:** Section 5.6 (Smart Agent Memory), new Section 5.8 (Knowledge Graph Integration)
**What:** Replace flat RAG chunk retrieval with graph-structured knowledge using [Cognee](https://github.com/topoteretes/cognee) — an open-source AI memory platform that builds persistent knowledge graphs from raw data. This transforms the Hub's agent memory from "similar text chunks" to "structured entity relationships," making agents more precise and less error-prone.
**Why:** The current RAG pipeline (`app/knowledge/`) retrieves similar text, not related concepts. Agents asked about "Outlook dark mode" get 5 similar paragraphs — but not the structured chain: *Outlook 2019 -> does_not_support -> CSS variables -> fallback -> MSO conditional VML*. Knowledge graphs capture these relationships explicitly.
**Dependencies:** Phase 7 infrastructure (handoff schemas, confidence scoring, component context) should be in place first. Phase 5.4-5.8 eval execution provides baseline metrics to measure improvement.

### Execution Order

**Step 1 — Cognee Integration Layer (8.1)**
Add Cognee as a dependency. Create `app/knowledge/graph/` adapter that wraps Cognee's `add()` + `cognify()` + `search()` behind the existing knowledge service interface. This runs alongside existing RAG — additive, not replacement.

**Step 2 — Seed Knowledge Graph (8.2)**
Feed existing knowledge base documents (Can I Email data, email dev guides, client quirks) through Cognee's ECL pipeline. Extracts entities (email clients, CSS properties, rendering engines, components) and relationships automatically.

**Step 3 — Graph Context Provider for Agents (8.3)**
Add a graph search context provider that blueprint nodes query before generation. Agents receive structured relationships alongside existing RAG chunks. Highest impact for Scaffolder and Dark Mode agents where compatibility chains matter most.

**Step 4 — Outcome Logging (8.4)**
Feed completed blueprint run outcomes (QA verdicts, recovery paths, what worked/failed) back into Cognee. Over time, builds institutional memory of which patterns succeed.

**Step 5 — Agent SKILL.md Domain Files (8.5)**
Create per-agent SKILL.md files with domain-specific knowledge, grounded by the knowledge graph. Each agent gets a skill file covering its Four Discipline sections (Prompt Craft, Context Engineering, Intent Engineering, Specification Engineering) with domain-specific rules pulled from graph entities.

**Step 6 — Ontology Definition (8.6)**
Define an email development OWL ontology (email clients, CSS properties, rendering engines, component types, ESP platforms). Cognee uses this to ground entity extraction against known domain concepts rather than relying on LLM training data.

### 8.1 Cognee Integration Layer
**What:** Add `cognee` as a Python dependency. Create `app/knowledge/graph/` module with `GraphKnowledgeProvider` that wraps Cognee's async API (`add`, `cognify`, `search`) behind a Protocol interface consistent with existing knowledge architecture.
**Why:** Keeps Cognee isolated behind an interface — can swap graph backends later without touching agent code. Runs alongside existing vector+fulltext search, not replacing it.
**Deployment model (DECIDED):** Background worker pattern — graph search queries run in-process (Kuzu is sub-millisecond for traversals), heavy operations (`cognify()`, outcome logging from 8.4) run via existing `DataPoller` background task system with Redis queue. This matches the existing pattern for memory compaction (Section 5.6 Layer 5). Migration path to sidecar container available if needed later.
**Graph DB (DECIDED):** Kuzu (file-based). Zero extra infrastructure. Sub-millisecond traversals for read-heavy agent queries. Stored in `DATA_ROOT_DIRECTORY` alongside other file-based data. Migration path to PostgreSQL available via Cognee's adapter layer if cross-database joins are needed later.
**Implementation:**
- `app/knowledge/graph/__init__.py`
- `app/knowledge/graph/provider.py` — `GraphKnowledgeProvider` Protocol + Cognee implementation
- `app/knowledge/graph/config.py` — Cognee config (graph DB: Kuzu file-based, data in `DATA_ROOT_DIRECTORY`)
- `app/knowledge/graph/tasks.py` — Background task wrappers for `cognify()` and outcome ingestion via `DataPoller`
- Wire into `KnowledgeService` as an optional search mode alongside existing hybrid search
**Security:** Cognee databases stored in project-scoped directories. No cross-tenant access. Graph queries logged to audit trail. Background tasks inherit existing Redis leader election for single-writer safety.
**Verify:** `KnowledgeService.search()` can return graph-structured results alongside existing chunk results. Background `cognify()` completes without blocking API server. Unit tests for provider interface.

### ~~8.2 Knowledge Graph Seeding~~ DONE (2026-03-10)
**What:** Run existing knowledge base documents through Cognee's ECL pipeline (`add()` -> `cognify()`) to extract entities and relationships into a knowledge graph.
**Why:** Transforms static document chunks into interconnected knowledge. "Gmail clips at 102KB" becomes a queryable entity linked to "file_size_check" and "Gmail" with relationship "clips_above_threshold."
**Implementation:**
- Extend `make seed-knowledge` to also run Cognee pipeline after existing chunking/embedding
- Seed manifest (`app/knowledge/data/seed_manifest.py`) unchanged — same source documents, additional processing path
- Initial entity types: EmailClient, CSSProperty, RenderingEngine, Component, Workaround, Limitation
**Security:** Same documents, additional index. No new data surface.
**Verify:** After seeding, graph contains extracted entities from Can I Email data. Query "What does Outlook 2019 not support?" returns structured graph traversal results.

### ~~8.3 Graph Context Provider for Blueprint Nodes~~ DONE (2026-03-10)
**What:** Add graph-aware context retrieval to the blueprint engine's `_build_node_context()`. Before an agent generates output, query Cognee for structured relationships relevant to the task.
**Why:** This is the highest-impact integration. Instead of "here are 5 similar chunks about dark mode," agents get: *"Apple Mail supports prefers-color-scheme -> use media query. Outlook ignores it -> use MSO conditional fallback. Gmail Android partially supports -> test with persona."*
**Implementation:**
- New context source in `app/ai/blueprints/engine.py::_build_node_context()`
- Uses Cognee's `GRAPH_COMPLETION` or `TRIPLET_COMPLETION` search types
- Progressive disclosure: only fetch graph context when the task involves email client compatibility, CSS support, or component interactions
- Results formatted as structured triplets injected into agent system prompt
**Security:** Graph queries scoped to project. Query content logged. No PII in graph (email dev knowledge only).
**Verify:** Scaffolder agent generating a 3-column layout receives structured compatibility data for target email clients. Dark Mode agent receives known workarounds for components in the template.

### ~~8.4 Blueprint Outcome Logging~~ DONE (2026-03-10)
**What:** After a blueprint run completes, feed the outcome (which agents ran, what they produced, QA results, recovery actions taken) back into Cognee via `cognee.add()`.
**Why:** Builds institutional memory. After 50 blueprint runs, agents can query: "What fixes have worked when QA fails for VML backgrounds in Outlook?" — answered from real outcomes, not LLM guessing.
**Implementation:**
- Post-run hook in `BlueprintEngine` that serialises `BlueprintRun` outcome to text
- Feeds through Cognee pipeline to extract patterns (successful fixes, common failure modes, recovery paths)
- Tagged with project scope and agent types involved
**Security:** Outcomes contain generated HTML patterns, not client content. Project-scoped. Temporal decay applies (Section 5.6 Layer 5).
**Verify:** After 10+ blueprint runs, querying "common Scaffolder failures" returns aggregated patterns from actual runs.

### ~~8.5 Per-Agent Domain SKILL.md Files~~ DONE (2026-03-10)
**What:** Create a SKILL.md file for each of the 9 agents following the Four Discipline structure (Section 5.4). Each skill file contains domain-specific rules, examples, anti-patterns, and context requirements grounded by the knowledge graph. Skills start as manually authored baselines and grow over time as agents accumulate knowledge.
**Why:** Currently agent prompts are static strings in `prompt.py` constants. SKILL.md files make agent expertise versionable, updatable without code changes, and benchmarkable via the eval system. Combined with the knowledge graph, skills reference verified entities rather than relying on LLM memory.
**Implementation:**
- `app/ai/agents/{agent_name}/SKILL.md` for each agent
- **Prompt Craft**: Best system prompts with success metrics, failure examples, output format specs
- **Context Engineering**: Required data sources, graph queries that improve output, progressive disclosure rules
- **Intent Engineering**: Trade-off hierarchies, escalation boundaries, decision frameworks
- **Specification Engineering**: Output schemas, acceptance criteria, eval test cases
- Skill loader reads SKILL.md at runtime and injects into agent context (existing pattern from Section 5.4)
- Graph-grounded: skill files reference entity types from the ontology (8.6) for precise constraints

**Skill Growth Lifecycle:**
1. **Manual baseline** — Devs author initial SKILL.md with proven patterns, known anti-patterns, output specs
2. **Passive accumulation** — Knowledge graph captures agent run outcomes (8.4). After 50+ runs, patterns emerge
3. **Growth proposals** — Periodic `DataPoller` job analyses graph for patterns not yet in SKILL.md. Generates diff suggestions (new procedural knowledge, updated success metrics, new anti-patterns). Proposed as review items — never auto-applied
4. **Dev review + merge** — Dev reviews proposed skill additions, approves or rejects. Versioned in git like any code change
5. **Size management** — SKILL.md files have a token budget (progressive disclosure). When skill grows beyond budget, entries ranked by impact (graph outcome data), low-impact entries archived to knowledge graph (still retrievable via graph search, just not in default agent context)

**Security:** SKILL.md files contain no client data. Versioned in git. Growth proposals logged with source data references. Changes auditable.
**Verify:** Agent loaded with SKILL.md produces measurably better output on eval suite vs static prompt. Skill updates don't require code deployment. Growth proposals reference specific graph entities and outcome data.

### ~~8.6 Email Development Ontology (Full Granularity)~~ DONE (2026-03-10)
**What:** Define a comprehensive OWL ontology for the email development domain. Full coverage of every email client version, every CSS property from Can I Email, all rendering engines, HTML elements relevant to email, ESP platforms, and template patterns.
**Why:** Without an ontology, Cognee's LLM-based entity extraction invents entity types inconsistently ("Outlook" vs "Microsoft Outlook" vs "Outlook 2019"). The ontology grounds extraction against canonical domain concepts, ensuring the knowledge graph is consistent and queryable. Full granularity means agents can reason at the version level ("Outlook 2016 on Windows" vs "Outlook 365 on Mac" have different rendering engines).
**Implementation:**
- `app/knowledge/graph/ontology/email_development.owl`
- Configure Cognee's `ONTOLOGY_RESOLVER=rdflib` + `MATCHING_STRATEGY=fuzzy` (80% similarity threshold)
- **Entity types and scope:**
  - `EmailClient` — Every client+version from Can I Email database (Apple Mail 10-18, Gmail Web/Android/iOS, Outlook 2007-365/Windows/Mac, Yahoo, AOL, Samsung Mail, Thunderbird, etc.) with version ranges
  - `CSSProperty` — Full Can I Email CSS property database (300+ properties with support status per client)
  - `RenderingEngine` — WebKit, Blink, Gecko, Word (MSO), Presto, with client→engine mappings
  - `HTMLElement` — Email-relevant elements with support status (semantic elements, `<picture>`, `<video>`, AMP elements)
  - `Component` — Maps to `app/components/` taxonomy (header, CTA, hero, product card, footer, etc.) with dark mode variant relationships
  - `Workaround` — Named patterns (MSO conditional comments, VML backgrounds, `mso-` properties, `<!--[if mso]>` blocks)
  - `Limitation` — Named constraints (Gmail 102KB clip, Outlook DPI scaling, Yahoo `!important` stripping)
  - `ESPPlatform` — Braze, SFMC, Adobe Campaign, Taxi, with template language relationships (Liquid, AMPscript, Handlebars)
  - `TemplatePattern` — Layout archetypes (single column, 2-col, 3-col, hybrid, fluid) with client compatibility profiles
  - `InteractiveFeature` — AMP components, CSS animations, kinetic techniques, with feasibility per client
- **Relationships:** `supports`, `does_not_support`, `partially_supports`, `fallback_for`, `renders_with`, `requires`, `conflicts_with`, `variant_of`, `degrades_to`
- **Data source:** Primary data scraped/imported from Can I Email API + database. Supplemented by Good Email Code patterns and team's tribal knowledge
- Updated as new email clients or CSS properties emerge. Can I Email data refresh on `make seed-knowledge`
**Security:** Ontology is public domain knowledge (email client names, CSS specs, Can I Email data). No sensitive data.
**Verify:** After seeding with ontology, entity extraction produces canonical names. "Outlook 2019" and "Microsoft Outlook 2019" resolve to the same entity. Graph contains 300+ CSS property nodes with per-client support status. Query "what does Gmail Android not support?" returns comprehensive, version-specific results.

## Phase 9 — Graph-Driven Intelligence Layer

**Plan ref:** Section 5.8 (Knowledge Graph Integration), Section 5.6 (Smart Agent Memory), Section 12.6 (Compound Innovation Effect)
**What:** Extensions that leverage the knowledge graph (Phase 8) across the entire Hub — connecting personas, components, blueprints, competitive intelligence, and skill evolution into a self-improving system.
**Dependencies:** Phase 8 core (8.1-8.6) must be operational. Phase 5 evals providing baseline data.

### ~~9.1 Graph-Powered Client Audience Profiles~~ DONE
**What:** Connect the Test Persona Engine (`app/personas/`) to the knowledge graph. When a persona specifies "iPhone 15 + Apple Mail 18 + Dark Mode," the graph surfaces: which CSS properties are safe, which components have tested dark mode variants, which workarounds are needed — all pre-filtered for that specific audience profile.
**Why:** Currently agents generate first, then discover breakage during QA. With graph-powered personas, agents receive pre-filtered compatibility context before generation. Eliminates the "generate → QA fail → retry" loop for known compatibility issues.
**Implementation:**
- Extend `app/personas/service.py` to query graph when a persona is selected
- Persona selection triggers graph traversal: persona.email_client → `supports`/`does_not_support` → CSS properties + components + workarounds
- Results cached per persona (compatibility data changes infrequently)
- Blueprint engine injects persona graph context into `NodeContext` alongside existing persona data
- Progressive disclosure: only load graph context for the persona's email client chain, not the entire graph
**Security:** Persona data is project-scoped (existing RLS). Graph queries read-only. Cached results invalidated on graph update.
**Verify:** Selecting "Outlook 2019 + Windows + Dark Mode" persona injects structured compatibility constraints into agent context. Agent output avoids known unsupported CSS properties without needing QA to catch them. Measurable reduction in QA retry loops vs Phase 8 baseline.

### ~~9.2 Can I Email Live Sync~~ DONE
**What:** Periodic sync job that pulls fresh data from the Can I Email API/database, diffs against existing graph entities, and updates the knowledge graph and ontology automatically.
**Why:** Knowledge base is currently seeded once via `make seed-knowledge`. Can I Email updates regularly (new client versions, updated support data). Stale compatibility data means agents give wrong advice. Live sync ensures agents always work with current data.
**Implementation:**
- `app/knowledge/graph/sync/caniemail.py` — sync job that fetches Can I Email data
- Diff engine compares fetched data against existing graph entities
- New/changed entities fed through Cognee's `add()` + `cognify()` pipeline (background worker, 8.1 pattern)
- Ontology auto-extended when new email clients or CSS properties appear (new entity nodes, not OWL schema changes)
- Configurable sync interval (weekly default, daily optional)
- Runs via existing `DataPoller` background task system
- Sync report logged: N new entities, N updated relationships, N deprecated
**Security:** Can I Email is public data. Sync job runs with read-only external access. Graph writes scoped to knowledge domain (no user data).
**Verify:** After sync, new email client version appears in graph. Agents querying that client get updated compatibility data. Sync report shows meaningful diffs.

### ~~9.3 Component-to-Graph Bidirectional Linking~~ DONE
**What:** When a component is created, updated, or tested in `app/components/`, automatically create/update its entity in the knowledge graph with: supported email clients (from QA test results), known quirks (from QA failures), dark mode variant status, and rendering engine compatibility. Reverse direction: graph insights surface as component metadata in the component browser UI.
**Why:** Component metadata is currently static (version, description). The graph can enrich this with real test data — "this CTA component passed QA in 18/20 clients, fails in Outlook 2016 VML and Samsung Mail 14." Agents using components get real compatibility data, not just static descriptions.
**Implementation:**
- `app/components/qa_bridge.py` — `extract_compatibility()` maps HTML CSS issues to per-client levels (full/partial/none) via ontology; `run_component_qa()` runs full QA gate + stores `ComponentQAResult` join model
- `app/components/graph_export.py` — `export_component_documents()` generates Cognee ECL-friendly docs with compatibility profiles and CSS issue details
- `ComponentQAResult` join model links `ComponentVersion` → `QAResult` with denormalised compatibility JSON; cascade delete on both FKs
- `POST /api/v1/components/{id}/versions/{v}/qa` (developer, 10/min) triggers QA + compatibility extraction
- `GET /api/v1/components/{id}/compatibility` (authenticated, 30/min) returns per-client support breakdown
- `ComponentResponse.compatibility_badge` (full/partial/issues) populated from latest QA data
- `CanIEmailSyncPoller._refresh_graph()` re-exports component documents after ontology sync
- Alembic migration `a1b2c3d4e5f6` for `component_qa_results` table
- 20 new tests (qa_bridge: 5, graph_export: 5, compatibility: 10); 747 total backend tests
**Security:** Both new endpoints have auth + rate limiting. Error responses use `AppError` hierarchy (auto-sanitized). Component data is project-scoped. Graph entities inherit project scope.
**Verify:** Creating a component and running QA creates a graph entity with test results. Component browser shows compatibility badge. Agent using the component receives graph-derived quirk warnings.

### ~~9.4 Failure Pattern Propagation Across Agents~~ DONE
**What:** When any agent discovers a failure pattern (e.g., Dark Mode agent finds "Samsung Mail strips `color-scheme` meta tag"), this is stored as a graph relationship — not just an agent memory entry. Every agent that subsequently touches Samsung Mail compatibility automatically gets this knowledge through graph context.
**Why:** Section 5.6 Layer 6 describes cross-agent memory sharing via project-scoped memory pools. Graph relationships are more powerful — they're structured, queryable, and don't require explicit sharing logic. The graph's structure means propagation is inherent in the data model.
**Implementation:**
- Extend outcome logging (8.4) to extract failure patterns as typed graph relationships
- Pattern format: `Entity → failure_type → Description` (e.g., `Samsung_Mail_14 → strips → color-scheme_meta`)
- Failure patterns tagged with: discovery date, agent type that discovered it, number of times observed, confidence level
- All agents' graph context queries automatically include relevant failure patterns (no per-agent wiring needed)
- High-frequency patterns automatically promoted to SKILL.md growth proposals (8.5 lifecycle)
**Security:** Failure patterns contain technical details only (CSS properties, email clients). No user/client data. Project-scoped when client-specific, org-scoped when universal.
**Verify:** Dark Mode agent discovers Samsung Mail failure. Scaffolder agent working on a Samsung Mail-targeting template receives the failure pattern in context without explicit configuration. Pattern appears in SKILL.md growth proposals after threshold observations.

### ~~9.5 Client-Specific Subgraphs for Project Onboarding~~ DONE
**What:** When a new project is created for a client, auto-generate a project-specific subgraph: the client's target email clients (from persona data) → their supported CSS properties → known workarounds → recommended components → historical failure patterns. This becomes the project's "compatibility brief."
**Why:** New developers on a project currently have no structured context about which email clients matter for that client, what works, and what doesn't. The subgraph gives instant onboarding context. Agents working on the project start with pre-loaded domain knowledge instead of discovering constraints through trial and error.
**Implementation:**
- Post-create hook on `Project` model → generates subgraph from persona selections
- Subgraph query: project personas → email clients → CSS support matrix → compatible components → known workarounds → historical outcomes from similar projects
- Subgraph materialised as a cached view (regenerated when personas change or graph updates)
- Accessible via: API endpoint (`GET /api/v1/projects/{id}/compatibility-brief`), agent context (injected into all blueprint runs for the project), UI page (project settings → compatibility overview)
- Knowledge Agent can answer questions scoped to the project subgraph: "What CSS properties should I avoid for this project?"
**Security:** Subgraph inherits project scope (RLS). Contains only email dev knowledge filtered for the project's target audience. No cross-project data.
**Verify:** Creating a project with Outlook 2019 + Apple Mail personas generates a subgraph with compatibility constraints for those clients. Agent working on the project receives subgraph context. New developer querying the Knowledge Agent gets project-specific answers.

### ~~9.6 Graph-Informed Blueprint Route Selection~~ DONE
**What:** Blueprint engine dynamically adjusts node sequence based on graph data about the target audience and template content. Skip unnecessary nodes, add required ones, reorder for efficiency.
**Why:** Currently blueprints follow a fixed sequence (scaffolder → dark_mode → QA → export). But if the target audience is 100% Apple Mail (internal corporate comms), the Outlook Fixer node is wasted work. If the template uses AMP components, an AMP validation node should be added. Graph-informed routing makes blueprints adaptive.
**Implementation:**
- `app/ai/blueprints/route_advisor.py` — `RoutingPlan` with `build_routing_plan()` analysing audience profile + content keywords to recommend skip/add/reorder
- `app/ai/blueprints/engine.py` — pre-execution routing plan, `skip_nodes` set consulted before each node, `routing_decisions` logged on run, `_skip_summary()` helper
- `app/ai/blueprints/schemas.py` — `RoutingDecisionResponse` in `BlueprintRunResponse`
- Rules: skip Outlook Fixer for non-Microsoft audiences, skip Dark Mode for non-dark-mode clients, add AMP validation for AMP content, audience-based prioritisation
- Developer can force full pipeline (overrides routing plan)
- 563 lines test coverage (`test_route_advisor.py`) + 161 lines engine integration tests (`test_engine_routing.py`)
**Security:** Route decisions based on project-scoped graph data. No new access surface. Audit trail captures routing rationale.
**Verify:** Blueprint for Apple Mail-only project skips Outlook nodes. Blueprint for template with AMP adds AMP validation. Routing decisions visible in blueprint run log with graph-backed reasoning.

### ~~9.7 Competitive Intelligence Graph~~ DONE
**What:** Extend the ontology to include competitor capabilities (Stripo, Parcel, Chamaileon, Dyspatch, Knak — from Plan Section 15.4). When the Innovation Agent evaluates new techniques, it checks the graph for feasibility and competitive landscape.
**Why:** Section 15.4 maps competitor features. This data in the graph lets the Innovation Agent answer: "Is this technique feasible for the client's audience AND do competitors support it?" Powers the capability reports mentioned in Section 12.2 with structured data instead of manual research.
**Implementation:**
- `app/knowledge/ontology/competitive_feasibility.py` — `compute_audience_coverage()` cross-references capability CSS deps with ontology support matrix, `build_competitive_report()` generates full audience-scoped report, `format_feasibility_context()` for agent prompt injection
- `app/knowledge/ontology/schemas.py` + `routes.py` — `GET /api/v1/ontology/competitive-report` (JSON) + `/text` (formatted), auth + rate limited
- Engine LAYER 10 enhanced: uses audience-aware feasibility when `audience_client_ids` available (from LAYER 7), falls back to standard competitive context
- `app/ai/blueprints/competitor_context.py` — added `build_audience_competitive_context()` convenience wrapper
- 5 competitors (Stripo, Parcel, Chamaileon, Dyspatch, Knak), 24 capabilities, 55+ Hub capabilities with agent mappings
- 17 feasibility tests + 5 route tests + 3 audience-aware context tests (35 total new)
**Security:** Competitor data is public knowledge (pricing pages, feature lists). No proprietary intelligence. All endpoints auth + rate limited.
**Verify:** Innovation Agent asked "what techniques can we offer that Stripo can't?" returns graph-backed answer with audience feasibility. Capability report includes competitive positioning data.

### ~~9.8 SKILL.md A/B Testing via Eval System~~ DONE
**What:** When the skill growth system (8.5) proposes a SKILL.md update, automatically A/B test it against the current version using the eval suite. Only merge if the updated skill performs equal or better.
**Why:** Skill growth proposals are currently review-only (dev reads the diff and decides). A/B testing adds empirical evidence: run the eval suite with current SKILL.md, then with proposed update, compare pass rates. This closes the loop: knowledge graph → skill proposal → eval validation → merge.
**Implementation:**
- `app/ai/agents/skill_override.py` — Runtime SKILL.md override registry (in-process, no disk writes)
- `app/ai/agents/evals/skill_ab.py` — A/B test runner CLI (`compare_variants`, `build_ab_report`, `run_ab_test`)
- `app/ai/agents/evals/schemas.py` — `SkillABCriterionDelta`, `SkillABResult`, `SkillABReport` dataclasses
- All 9 agent `prompt.py` files refactored to check `get_override()` before file-loaded SKILL.md
- Runs eval suite twice (current vs proposed) on same synthetic test data
- Computes per-criterion pass rate delta, overall improvement, minimum 10 cases per dimension
- Output: JSON comparison report with recommendation (merge / reject / needs_more_data)
- `make eval-skill-test AGENT=scaffolder PROPOSED=path/to/SKILL.md` CLI command
- Proposed updates that degrade any criterion by >5% auto-rejected with explanation
- 17 unit tests (override registry, comparison logic, report builder, edge cases)
**Security:** A/B tests run on synthetic test data (no client data). Results logged for audit. Rejected proposals archived with reasoning.
**Verify:** Proposed SKILL.md update runs through A/B test. Report shows per-criterion comparison. Update that improves 3 criteria and degrades none is recommended for merge. Update that degrades 1 criterion by >5% is auto-rejected.

---

## Phase 10 — Full-Stack Agent Workflow (Frontend Integration)

**What:** Wire all Phase 8-9 backend intelligence into the frontend so email developers can run the full AI-powered workflow from the UI — from project setup with priority clients, through blueprint-orchestrated multi-agent pipelines, to graph-informed QA and export. Currently ~50% of backend capabilities are invisible from the frontend.
**Design principle:** QA always checks against ALL 25 email clients. "Priority clients" mark which clients get prominent display in QA results, drive failure pattern urgency, and influence agent retry priority — but never exclude non-priority clients from validation. No campaign-level client selector needed; campaigns inherit project priorities.
**Dependencies:** Phase 8 (knowledge graph) + Phase 9 (graph intelligence) backend complete. Phase 0-3 frontend foundation in place.

### ~~10.1 Project Priority Clients Selector~~ DONE
**What:** Add a multi-select "Priority Email Clients" field to project creation and project settings forms. Populated from the ontology's 25 email clients. Persists to the existing `target_clients` JSON column on `Project`. Shows client icons, engine type (WebKit/Blink/Word), and market share from ontology data. QA always validates against ALL 25 clients; priority clients get prominent display, higher urgency in failure patterns, and influence agent retry priority.
**Why:** `target_clients` (priority clients) drives audience profiles (9.1), onboarding subgraphs (9.5), failure pattern urgency (9.4), and blueprint route selection (9.6). Empty = all clients treated equally. Non-priority clients are still fully checked — priority only affects display emphasis and agent attention.
**Implementation:**
- New component: `target-clients-selector.tsx` — searchable multi-select with client metadata (icon, engine, share %)
- Add to `create-project-dialog.tsx` as optional step (defaults to empty = all clients equal priority)
- Add to project settings page for editing after creation
- New API hook: `useEmailClients()` fetching from ontology endpoint (or static list from SDK)
- `ProjectCreateRequest` / `ProjectUpdateRequest` schemas already support `target_clients`
- SDK regeneration to include `target_clients` in `ProjectResponse`
- No campaign-level client selector — campaigns inherit project priorities
**Security:** Client list is public ontology data. Project-scoped via existing RLS. Input validated against known client IDs.
**Verify:** Create project with "Outlook 2019 + Gmail" as priority. Project detail shows priority clients. QA results show ALL 25 clients but priority clients are visually emphasised. Empty priority = all clients shown equally. Blueprint runs receive audience context for priority clients.

### ~~10.2 Onboarding Compatibility Brief UI~~ DONE
**What:** Add a "Compatibility Brief" tab/section to the project workspace that displays the auto-generated onboarding subgraph (9.5). Shows: executive summary, per-client CSS constraint profiles, cross-client risk matrix, and a "Regenerate" button that calls `POST /projects/{id}/onboarding-brief`.
**Why:** The backend generates rich compatibility briefs per project but there's no way to see them. Email developers need this as a reference while building — "what CSS is safe across all clients, and where do my priority clients have constraints?"
**Implementation:**
- New page/tab: `project-compatibility-brief.tsx` in workspace or project settings
- Sections: Summary card (client count, total risky properties, dark mode warning), per-client accordion (unsupported CSS list, fallbacks, engine info), risk matrix table (properties × clients heat map)
- "Regenerate Brief" button → `POST /api/v1/projects/{id}/onboarding-brief`
- Auto-generate on first visit if brief doesn't exist
- New API hook: `useOnboardingBrief(projectId)` with SWR caching
- SDK types: `OnboardingBriefResponse` (message, dataset_name, document_count, client_count)
**Security:** Brief data is project-scoped. Read-only for viewer role. Regenerate requires developer+ role.
**Verify:** Navigate to project compatibility tab. Brief displays with per-client profiles (all 25 clients, priority clients highlighted). "Regenerate" updates the content. Brief reflects project's priority clients with emphasis.

### ~~10.3 Blueprint Run Trigger & Pipeline Visualisation~~ DONE
**What:** Add a "Generate with Blueprint" button in the workspace that triggers a full multi-agent blueprint run (not just a single agent call). Show real-time pipeline progress: which agent is running, QA gate status, self-correction loops, handoff chain, and final result with confidence score.
**Why:** The chat sidebar currently calls individual agent endpoints, bypassing the blueprint engine entirely. The engine is where all the intelligence layers (audience context, failure patterns, component injection, handoff memory, self-correction) converge. Without a UI trigger, the most powerful feature in the hub is CLI-only.
**Implementation:**
- New component: `blueprint-run-dialog.tsx` — select blueprint template (campaign, dark-mode-fix, accessibility-audit, etc.), input brief text, optional HTML input, shows project's priority clients
- Pipeline visualisation: `blueprint-pipeline-view.tsx` — vertical node list showing: agent name + status (pending/running/complete/failed), QA gate results per node, self-correction attempt count, handoff decisions and warnings, confidence score per agent
- WebSocket or SSE streaming for real-time updates (blueprint engine already emits events)
- New API hooks: `useBlueprintRun(runId)` for status polling, `useBlueprintTemplates()` for available blueprints
- "Apply Result" button to insert generated HTML into Monaco editor
- "View Handoff History" expandable panel showing cross-agent decisions
- SDK types: `BlueprintRunResponse`, `BlueprintNodeStatus`, `HandoffSummary`
**Security:** Blueprint runs consume AI quota (existing rate limits apply). Run status scoped to project. Only project members can trigger runs.
**Verify:** Click "Generate with Blueprint" → select campaign → enter brief → pipeline shows agents executing in sequence → QA gate results appear → final HTML available with "Apply" button. Self-correction visible when QA fails.

### ~~10.4 Blueprint Run History & Outcomes~~ DONE
**What:** Add a "Runs" tab in the workspace showing all blueprint runs for the project — status, agents involved, QA pass/fail, duration, token usage. Click into a run to see full handoff history, agent decisions, failure patterns discovered, and the generated output.
**Why:** Blueprint outcome logging (8.4) captures rich data but it's only in the database/graph. Developers need to review past runs to understand what agents did, why QA failed, and what patterns were discovered. Essential for debugging and iterating on email quality.
**Implementation:**
- New page: `blueprint-runs-list.tsx` — table with columns: run ID, blueprint name, status (badge), agents involved, QA result, duration, created_at
- Run detail view: `blueprint-run-detail.tsx` — timeline of node executions, expandable handoff cards, QA check breakdown, failure patterns extracted, generated HTML diff
- Filter/sort: by status, date range, blueprint type
- New API hooks: `useBlueprintRuns(projectId)` with pagination, `useBlueprintRun(runId)` for detail
- Link from pipeline visualisation (10.3) to run detail after completion
- New backend endpoints needed: `GET /api/v1/blueprints/runs?project_id=X` (list), `GET /api/v1/blueprints/runs/{id}` (detail)
**Security:** Run history scoped to project (RLS). Viewer role can read but not trigger new runs. Token usage visible to developer+ only.
**Verify:** Run a blueprint → appears in runs list with correct status → click into detail → see full handoff history and QA breakdown. Filter by "failed" shows only failed runs.

### ~~10.5 Component Compatibility Badges & Matrix~~ DONE
**What:** Display per-client compatibility badges on component cards in the component browser. Add a compatibility matrix view showing which components work in which clients. Add a "Run QA" button on component detail to trigger `POST /components/{id}/versions/{v}/qa`.
**Why:** Component-to-graph linking (9.3) generates compatibility data but the frontend never shows it. Email developers choosing components need to know "will this CTA button work in Outlook?" before inserting it into their template.
**Implementation:**
- Update `ComponentResponse` SDK type to include `compatibility_badge` (full/partial/issues/untested)
- Badge component: coloured dot/icon on component cards (green=full, yellow=partial, red=issues, grey=untested)
- Component detail: compatibility section showing per-client support status (full/partial/none per client)
- "Run QA" button on component version detail → `POST /api/v1/components/{id}/versions/{v}/qa`
- Compatibility matrix page: `components-compatibility-matrix.tsx` — grid of components × clients with support indicators
- Filter component browser by "compatible with [client]" using project's priority clients as default filter (all clients still visible)
- New API hook: `useComponentCompatibility(componentId)`
**Security:** QA trigger rate-limited (10/min). Compatibility data is read-only for viewers. Component data project-scoped.
**Verify:** Component card shows green badge (all clients pass). Click component → see per-client breakdown. "Run QA" updates badge. Filter by "Outlook compatible" hides incompatible components.

### ~~10.6 Graph-Powered Knowledge Search~~ DONE
**What:** Upgrade the `/knowledge` page to support graph search mode alongside existing RAG search. Add a toggle: "Text Search" (current) vs "Graph Search" (Cognee). Graph search returns entities and relationships with visual presentation — entity cards with relationship links between them.
**Why:** The flat RAG search on `/knowledge` returns text chunks. The graph search (Phase 8.1) returns structured entities (email clients, CSS properties) with relationships (supports, fallback_for, incompatible_with). This is far more useful for understanding compatibility.
**Implementation:**
- Search mode toggle: "Text" | "Graph" (graph disabled with tooltip if `COGNEE__ENABLED=false`)
- Graph results component: `graph-search-results.tsx` — entity cards showing name, type, properties, related entities
- Relationship visualisation: simple list view with "→ supports →", "→ fallback_for →" relationship labels (not full graph viz)
- Search modes map to: Text → `POST /api/v1/knowledge/search`, Graph → `POST /api/v1/knowledge/graph/search`
- Graph search supports `dataset_name` filter (email_ontology, email_components, project_onboarding_X)
- Optional: "Ask" mode using graph completion (`mode: "completion"`) for natural language Q&A
- New API hook: `useGraphSearch()` calling `/api/v1/knowledge/graph/search`
- SDK types: `GraphSearchRequest`, `GraphSearchResponse`, `GraphEntity`, `GraphRelationship`
**Security:** Graph search has same auth + rate limits as text search. Dataset names validated server-side. No graph write access from frontend.
**Verify:** Toggle to Graph Search → search "Outlook dark mode" → see entity cards for Outlook + dark mode CSS properties with support relationships. Toggle back to Text → same query returns text chunks.

### ~~10.7 Failure Pattern Dashboard~~ DONE
**What:** Add a "Failure Patterns" section to the intelligence dashboard showing extracted patterns across blueprint runs — which agents fail on which checks for which clients, how patterns trend over time, and which patterns have been resolved.
**Why:** Failure pattern propagation (9.4) collects rich data about cross-agent failures but there's no visibility. Email developers and leads need to see: "Outlook dark mode fails 40% of the time" → "we need to update the SKILL.md" or "this client needs a workaround documented."
**Implementation:**
- "Failure Patterns" tab on `/renderings` page (merged from standalone `/failure-patterns` route)
- Pattern list: agent name, QA check, affected clients, frequency, first/last seen, status (active/resolved)
- Trend chart: failure frequency over time per agent/check (simple line chart)
- Filter by: agent, QA check, email client, date range
- Pattern detail: shows the description, workaround hint, associated blueprint runs
- New backend endpoint needed: `GET /api/v1/blueprints/failure-patterns?project_id=X` (paginated list with filters)
- Link from QA results panel → "View related failure patterns"
**Security:** Pattern data project-scoped. Contains only technical details (CSS properties, email clients), no user data. Read-only for all roles.
**Verify:** After several blueprint runs with QA failures, dashboard shows patterns. Filter by "Outlook" shows Outlook-specific failures. Trend chart shows pattern frequency. Click pattern → see detail with workaround.

### ~~10.8 Agent Confidence & Handoff Visibility~~ DONE
**What:** Display agent confidence scores in the chat sidebar and blueprint pipeline view. Show a "needs review" badge when confidence < 0.5. Display handoff decisions (what the agent decided and warned about) in an expandable panel below agent responses.
**Why:** Agents already emit confidence scores (7.3) and structured handoffs (7.1) but the frontend doesn't show them. Developers need to know when an agent is unsure and what decisions were made during generation.
**Implementation:**
- Confidence indicator: coloured bar/badge on agent responses (green ≥0.7, yellow 0.5-0.7, red <0.5)
- "Needs Review" badge on responses with confidence < 0.5
- Handoff panel: expandable section below response showing: decisions made (list), warnings (list), component references (links), skills loaded (list)
- Blueprint pipeline view (10.3): confidence score per node, handoff arrows between nodes showing decisions
- Update chat API response parsing to extract `confidence` and handoff metadata from agent responses
- SDK types: agent response schemas already include `confidence` + `skills_loaded`
**Security:** Confidence scores and handoff data are informational. No new access surface.
**Verify:** Agent responds with 0.45 confidence → "Needs Review" badge appears. Expand handoff → see decisions and warnings. Blueprint pipeline shows confidence per step.

### ~~10.9 Workspace Agent Context Panel~~ DONE
**What:** Add a collapsible "Agent Context" panel in the workspace that shows what intelligence layers are active for the current project — audience profile summary, active failure patterns, loaded SKILL.md version, component context, and onboarding brief status.
**Why:** All intelligence layers inject silently into agent prompts. Developers have no visibility into what context agents are working with. This panel makes the invisible visible — "the scaffolder knows about 3 failure patterns for Outlook and has 12 component references loaded."
**Implementation:**
- New component: `agent-context-panel.tsx` — collapsible sidebar section or drawer
- Sections: Audience Profile (target clients, constraints summary), Active Failure Patterns (count + top patterns), SKILL.md Status (loaded version, last A/B test result), Component Context (detected components in current template), Onboarding Brief (generated/not generated, last refresh)
- Data sources: project target_clients, memory recall for failure patterns, agent response metadata for skills_loaded
- Refresh button to re-fetch context state
- Link each section to its detail view (compatibility brief, failure dashboard, etc.)
- New backend endpoint: `GET /api/v1/projects/{id}/agent-context-summary` (aggregates all context layers)
**Security:** Context summary is read-only, project-scoped. No sensitive data — only agent configuration state.
**Verify:** Open workspace for project with target clients set → context panel shows audience profile, failure pattern count, SKILL.md status. Change template to include a component → component context section updates.

### ~~10.10 SDK Regeneration & Type Coverage~~ DONE
**What:** Regenerate the TypeScript SDK to include all Phase 8-10 response types and endpoints. Add missing types: `BlueprintRunResponse`, `BlueprintNodeStatus`, `HandoffSummary`, `GraphSearchRequest/Response`, `GraphEntity`, `GraphRelationship`, `FailurePatternResponse`, `OnboardingBriefResponse`, `ComponentCompatibilityResponse`, `AgentContextSummary`.
**Why:** The SDK is the contract between backend and frontend. Missing types mean frontend components use `any` or manual type definitions, which defeats the type-safety principle. All new endpoints from Phase 8-10 need SDK coverage.
**Implementation:**
- Run `make sdk` (or equivalent generation command) against updated backend OpenAPI spec
- Verify all new endpoints appear in generated types
- Add new React hooks in `cms/apps/web/src/hooks/`: `useBlueprintRun()`, `useBlueprintRuns()`, `useBlueprintTemplates()`, `useGraphSearch()`, `useOnboardingBrief()`, `useComponentCompatibility()`, `useFailurePatterns()`, `useAgentContextSummary()`, `useEmailClients()`
- Update existing hooks where response types changed (e.g., `useComponents()` now includes `compatibility_badge`)
- Ensure all hooks use `authFetch` with proper error handling and SWR caching
**Security:** SDK generation is automated from OpenAPI spec — no manual type definitions that could diverge. All hooks use authenticated fetch.
**Verify:** `make check-fe` passes. All new components use typed SDK hooks — zero `any` types. New endpoints callable from frontend with full type safety.

### ~~10.11 Blueprint-Aware Chat Mode~~ DONE
**What:** Add a "Blueprint Mode" toggle to the AI chat sidebar. When enabled, chat messages trigger blueprint runs instead of single-agent calls. The user selects agents to include, and the chat orchestrates a full pipeline with QA gating and self-correction, streaming progress updates into the chat panel.
**Why:** Some developers prefer the chat interface over a separate blueprint dialog. Blueprint mode in chat means they can type "create a responsive email for Outlook and Gmail with dark mode" and get a full pipeline run inline — with the same audience context, failure patterns, and self-correction as the standalone blueprint trigger (10.3).
**Implementation:**
- Toggle button in chat header: "Single Agent" | "Blueprint Mode"
- Blueprint mode: chat input triggers `POST /api/v1/blueprints/run` instead of individual agent endpoints
- Progress messages streamed into chat: "Scaffolder generating... → QA gate running... → Dark Mode agent fixing... → Complete (confidence: 0.82)"
- Blueprint selects agents automatically based on brief content (or user can pin specific agents)
- Final result appears as a chat message with "Apply to Editor" button
- Handoff history shown as collapsible thread under the result
- Falls back to single agent mode if blueprint service is unavailable
**Security:** Same rate limits and quota as standalone blueprint runs. Chat history project-scoped.
**Verify:** Toggle Blueprint Mode → type brief → see pipeline progress in chat → result appears with confidence score and "Apply" button → handoff history expandable. Switch back to Single Agent → normal agent behaviour.

### ~~10.12 Intelligence Dashboard Enhancements~~ DONE
**What:** Extend the existing intelligence dashboard (`/intelligence`) with Phase 8-9 data: graph entity counts, knowledge freshness (last Can I Email sync), blueprint success rates over time, top failure patterns, agent performance by confidence distribution, and component compatibility coverage.
**Why:** The intelligence dashboard currently shows QA trends and support matrices. Phase 8-9 generates much richer data that should surface here — graph health, sync status, agent quality trends, and failure pattern analysis.
**Implementation:**
- New dashboard cards: Graph Health (entity count, last sync, dataset sizes), Blueprint Success Rate (chart: pass/fail/self-corrected over time), Agent Performance (confidence distribution per agent, mean/median), Failure Patterns (top 5 most frequent, trend arrows), Component Coverage (% of components with QA data, average compatibility score)
- Can I Email sync status: last sync timestamp, changes applied, next scheduled sync
- Data from existing backend endpoints + new aggregation endpoint: `GET /api/v1/intelligence/summary`
- Export enhanced: PDF/CSV now includes graph metrics and blueprint stats
**Security:** Dashboard read-only. Aggregated data only — no individual run details without clicking through. Developer+ role required.
**Verify:** Dashboard shows graph entity count, last sync date, blueprint success rate chart, top failure patterns. Data updates after running blueprints and syncing knowledge.

---

## Phase 11 — QA Engine Hardening & Agent Quality Improvements

**What:** Upgrade QA checks from shallow string matching to production-grade DOM-parsed validation, expand coverage with new checks, and fix the highest-failure agent skills. Current QA checks detect ~60% of real email issues; target is 95%+. Agent eval pass rate is 16.7% overall — targeted fixes on worst-performing dimensions should lift to 60%+.
**Dependencies:** Phase 5 (eval framework operational), Phase 8-9 (ontology + graph available for enriched checks). All 10 QA checks exist and run end-to-end.
**Design principle:** Every check upgrade must be backward-compatible (same `QACheckResult` schema). New checks added to `ALL_CHECKS` list. Agent fixes validated via `make eval-run` before/after comparison.

### ~~11.1 QA Check Configuration System~~ DONE
**What:** Replace hardcoded thresholds and trigger lists with a per-check configuration model. Currently values like `MAX_SIZE_KB=102`, spam triggers (10 words), and pass thresholds are baked into check implementations. Add `QACheckConfig` that supports per-project overrides and per-client tuning.
**Why:** Every check below needs configurable thresholds. Without this, improvements require code changes instead of config. Client-specific QA rules (e.g., stricter accessibility for healthcare) are impossible.
**Implementation:**
- ~~Create `app/qa_engine/check_config.py` — `QACheckConfig` Pydantic model with `enabled: bool`, `severity: str`, `threshold: float`, `params: dict[str, Any]`~~
- ~~Add `QAProfileConfig` model mapping check names → `QACheckConfig` instances~~
- ~~Default profile loaded from `app/qa_engine/defaults.yaml` (new file)~~
- ~~Per-project override via `qa_profile` JSON column on `Project` model~~
- ~~Service layer merges default + project overrides at runtime~~
- ~~Each check's `run()` method receives optional config parameter~~
**Security:** Config is project-scoped, validated by Pydantic. No raw user input reaches check logic.
**Verify:** ~~Create two projects with different QA profiles. Same HTML produces different scores based on project config. `make test` passes.~~ 72/72 tests pass, mypy + pyright clean.

### ~~11.2 HTML Validation — DOM Parser Upgrade~~ DONE
**What:** Replace string matching (`"<!DOCTYPE" in html`) with proper DOM parsing using `html.parser` or `lxml`. Current check only verifies DOCTYPE and `<html>` tag presence — misses malformed structure, missing `<head>`/`<body>`, invalid nesting, missing charset meta.
**Why:** Real emails with syntax errors pass the current check. Malformed HTML causes unpredictable rendering across clients. This is the foundation check — if HTML structure is broken, all other checks are unreliable.
**Implementation:**
- Replace string checks in `app/qa_engine/checks/html_validation.py` with `lxml.html` parser
- Validate: DOCTYPE is HTML5 (`<!DOCTYPE html>`), `<html>` contains `<head>` + `<body>`, `<head>` has `<meta charset="utf-8">`, no unclosed block-level tags, proper nesting order
- Return specific failure details: "Missing `<body>` tag", "Unclosed `<div>` at approximate position"
- Scoring: 1.0 = all structural checks pass, deduct 0.15 per structural issue, minimum 0.0
- Add `lxml` to dependencies (if not already present)
**Security:** Parser input is the HTML string already validated by Pydantic schema (1-500K chars). No external fetches.
**Verify:** Test with: valid HTML (1.0), missing DOCTYPE (0.85), missing body (0.85), multiple issues (cumulative deductions), malformed nesting (caught). Existing tests still pass.

### 11.3 Accessibility Check — WCAG AA Coverage
**What:** Expand from 3 checks (lang, alt, role) to comprehensive WCAG AA validation. Current eval data shows 70% alt text pass rate and 70% screen reader compatibility — the check is too lenient. Add: heading hierarchy, link text quality, color contrast estimation, alt text quality scoring, table semantics.
**Why:** Accessibility is the highest eval failure category across agents. The check should catch issues before agents attempt fixes, reducing retry loops. Healthcare/finance clients require strict WCAG compliance.
**Implementation:**
- Rewrite `app/qa_engine/checks/accessibility.py` using HTML parser (not regex)
- **Alt text quality**: Check ALL images (not just first). Validate: present, 5-125 chars for content images, `alt=""` for decorative images, not generic ("image", "photo", "picture", "logo")
- **Heading hierarchy**: Validate h1-h6 in order, no skipped levels, at most one `<h1>`
- **Link text quality**: Flag "click here", "read more", "learn more" — require descriptive text
- **Color contrast**: Extract foreground/background color pairs from inline styles, estimate contrast ratio (4.5:1 normal text, 3:1 large text per WCAG AA)
- **Table semantics**: Layout tables need `role="presentation"`, data tables need `<caption>`, `scope` attributes on `<th>`
- **Screen reader**: Check for `aria-label` on interactive elements, `aria-describedby` where appropriate
- Scoring: weight by severity (missing alt = -0.2, heading skip = -0.1, contrast fail = -0.15, etc.)
**Security:** Read-only HTML analysis. No DOM manipulation.
**Verify:** Test matrix: fully accessible HTML (1.0), missing alts (deducted), broken heading hierarchy (deducted), poor link text (deducted), low contrast (deducted). Test that decorative images with `alt=""` are not penalised.

### 11.4 Fallback Check — MSO Conditional Parser
**What:** Replace presence-only detection (`"<!--[if mso" in html`) with a proper MSO conditional parser that validates syntax correctness, balanced pairs, VML nesting, and namespace declarations. Eval data shows **50% MSO conditional correctness failure** — the single worst failure cluster.
**Why:** Outlook rendering breaks silently when MSO conditionals are malformed. Current check passes HTML that will render incorrectly in Outlook (the largest email client by enterprise adoption). This is the highest-impact single check fix.
**Implementation:**
- Rewrite `app/qa_engine/checks/fallback.py` with MSO-specific parser
- **Balanced pair validation**: Count `<!--[if` openers == `<![endif]-->` closers. Report unbalanced pairs with approximate position
- **VML nesting**: Verify all `<v:*>` and `<o:*>` elements are inside `<!--[if mso]>` blocks. Flag VML orphans
- **Namespace validation**: If VML present, verify `xmlns:v="urn:schemas-microsoft-com:vml"` and `xmlns:o="urn:schemas-microsoft-com:office:office"` on `<html>` tag
- **Ghost table structure**: Detect multi-column layouts and verify MSO ghost tables have proper `width` attributes
- **Conditional targeting**: Validate version targeting syntax (`<!--[if gte mso 12]>`, `<!--[if !mso]><!--> ... <!--<![endif]-->`)
- Extract reusable `validate_mso_conditionals(html) -> list[MSOIssue]` function for agents to call
- Scoring: -0.25 per unbalanced pair, -0.2 per VML orphan, -0.15 per missing namespace, -0.1 per ghost table issue
**Security:** Read-only parsing. No code execution.
**Verify:** Test: valid MSO HTML (1.0), unbalanced conditional (0.75), VML outside conditional (0.8), missing namespaces (0.85), complex nested conditionals (validates correctly). Eval re-run shows fallback check now catches issues that agents fail on.

### 11.5 Dark Mode Check — Semantic Validation
**What:** Upgrade from presence-only checks to semantic validation of dark mode implementation. Current check accepts empty `@media (prefers-color-scheme: dark)` blocks and HTML with `color-scheme` meta but no actual color remapping. Eval shows **50% meta tag failure rate**.
**Why:** Dark mode is the #1 rendering complaint from email clients. Passing the check with a broken dark mode implementation gives false confidence. The check should validate that dark mode actually works, not just that the syntax exists.
**Implementation:**
- Rewrite `app/qa_engine/checks/dark_mode.py` with CSS parser
- **Meta tag validation**: Both `<meta name="color-scheme" content="light dark">` AND `<meta name="supported-color-schemes" content="light dark">` must be in `<head>` (not body, not malformed)
- **Media query validation**: `@media (prefers-color-scheme: dark)` block must contain at least one CSS rule with a color property (`color`, `background-color`, `background`, `border-color`)
- **Outlook selector validation**: `[data-ogsc]` and `[data-ogsb]` selectors must contain actual color declarations (not empty)
- **Color coherence**: Extract light mode colors and dark mode remapped colors. Flag obvious issues: white-on-white, black-on-black, text disappearing
- **Apple Mail**: Check for `[data-apple-mail-background]` pattern (common Apple Mail dark mode fix)
- Scoring: meta tags present (0.3), media query with rules (0.3), Outlook selectors with rules (0.2), color coherence (0.2)
**Security:** CSS parsing is read-only. Color extraction uses regex on style attributes.
**Verify:** Test: complete dark mode (1.0), meta tags only (0.3), empty media query (0.3), Outlook selectors without rules (0.5), color coherence failure (flagged). Regression: existing passing HTML still passes.

### 11.6 Spam Score Check — Production Trigger Database
**What:** Expand from 10 hardcoded trigger phrases to 50+ weighted triggers with case-insensitive word-boundary matching. Add formatting heuristics (excessive punctuation, all-caps words, obfuscation patterns). Current implementation misses most real spam patterns.
**Why:** Emails that pass current check may hit spam filters in Gmail, Outlook, Yahoo. SpamAssassin uses 100+ content rules. A flagged email wastes the entire campaign investment.
**Implementation:**
- Rewrite `app/qa_engine/checks/spam_score.py`
- **Trigger database**: Move triggers to `app/qa_engine/data/spam_triggers.yaml` — 50+ phrases with weights (0.05-0.30) and categories (urgency, money, action, clickbait)
- **Case-insensitive word boundary matching**: Use `re.compile(rf"\b{trigger}\b", re.IGNORECASE)` — no more false positives from substrings
- **Formatting heuristics**: Detect excessive punctuation (3+ `!` or `?`), all-caps words (>3 consecutive), mixed case obfuscation ("fR33", "d1scount")
- **Subject line awareness**: If HTML contains `<title>` or known subject line meta, score it separately (subject is 3x more spam-prone)
- **Weighted scoring**: `score = 1.0 - sum(trigger_weights)`, pass if score ≥ configurable threshold (default 0.5)
- **Detail reporting**: List every matched trigger with weight and category for user transparency
**Security:** Trigger database is static YAML, not user-modifiable. Regex patterns are pre-compiled at module load.
**Verify:** Test: clean copy (1.0), "Buy Now" (deducted), "FREE SHIPPING!!!" (multiple deductions), obfuscated "FR33" (caught), edge case "guarantee" in legitimate context (low weight). Load test: 50 triggers on 100KB HTML completes in <50ms.

### 11.7 Link Validation — HTML Parser + URL Format Check
**What:** Replace fragile regex extraction with proper HTML parser link extraction. Add URL format validation, ESP template variable syntax checking, and empty href detection.
**Why:** Current regex breaks on complex href syntax (mixed quotes, newlines, encoded characters). Malformed links cause broken emails that look unprofessional. ESP template variables like `{{ url }}` need syntax validation.
**Implementation:**
- Rewrite `app/qa_engine/checks/link_validation.py` using HTML parser
- **Proper extraction**: Parse all `<a>` tags, extract `href` attribute value properly (handles quotes, encoding)
- **URL format validation**: Use `urllib.parse.urlparse()` — verify scheme, netloc, path are well-formed
- **ESP template validation**: Detect `{{ }}` (Liquid), `%%[ ]%%` (AMPscript), `<%= %>` (JSSP). Validate balanced delimiters
- **Empty href detection**: Flag `href=""`, `href="#"` (except intentional anchors), `href="javascript:"`
- **URL encoding**: Flag unencoded spaces, special characters that will break in email clients
- **Tracking pixel whitelist**: Don't flag known tracking pixel patterns (1x1 images, `open.gif` etc.)
- Scoring: -0.15 per broken link, -0.10 per HTTP link, -0.05 per empty/suspicious href
**Security:** No HTTP requests to validate links (avoid SSRF). Validation is syntax-only.
**Verify:** Test: all valid HTTPS links (1.0), HTTP link (deducted), malformed URL (deducted), empty href (deducted), valid Liquid template var (not flagged), unbalanced `{{ url }` (flagged).

### 11.8 File Size Check — Multi-Client Thresholds
**What:** Extend beyond Gmail-only 102KB threshold to include client-specific limits from the ontology. Add content breakdown analysis (markup vs styles vs images).
**Why:** Emails may pass Gmail's threshold but clip in Yahoo (75KB) or hit issues in other clients. Without breakdown analysis, developers don't know what to trim.
**Implementation:**
- Update `app/qa_engine/checks/file_size.py`
- **Client-specific thresholds**: Load from ontology or config: Gmail (102KB), Yahoo (~75KB), Outlook.com (~100KB). Report per-client pass/fail
- **Content breakdown**: Calculate size of: inline styles, HTML markup (minus styles), embedded images (base64), total. Report as percentages
- **Gzip estimate**: Calculate gzip compressed size as secondary metric (actual transfer size)
- **Actionable guidance**: If over threshold, identify largest contributors: "Inline styles: 45KB (44%) — consider external stylesheet or removing unused rules"
- Scoring: 1.0 if under all client thresholds, deduct based on most impacted client's overage
**Security:** Read-only size calculation. No file system access.
**Verify:** Test: small HTML (1.0), 80KB HTML (passes Gmail, flags Yahoo), 110KB HTML (fails multiple), breakdown percentages are accurate.

### 11.9 Image Optimization — Comprehensive Validation
**What:** Upgrade from first-image-only dimension check to all-image validation with format analysis, dimension value validation, and tracking pixel detection.
**Why:** Current check only catches the first missing dimension and only flags BMP format. WebP has limited email client support. Invalid dimension values (`width="auto"`, `width="0"`) cause layout breaks.
**Implementation:**
- Rewrite `app/qa_engine/checks/image_optimization.py` using HTML parser
- **All images**: Check every `<img>` tag, not just the first. Report per-image results
- **Dimension validation**: Verify `width` and `height` are positive integers, < 5000px, realistic aspect ratios. Flag `auto`, `100%`, negative values
- **Format support**: Flag formats with limited email support — WebP (poor), SVG (partial), BMP (never), AVIF (none). Recommend JPEG/PNG/GIF
- **Tracking pixels**: Detect 1x1 images — don't flag for missing dimensions (legitimate pattern)
- **Retina detection**: If `width` attribute differs significantly from intrinsic width hint, note potential retina image
- Scoring: -0.15 per image missing dimensions, -0.10 per unsupported format, cap at 0.0
**Security:** No image fetching (avoid SSRF). Attribute analysis only.
**Verify:** Test: all images with dimensions (1.0), missing dimensions on 3 images (deducted), WebP format (flagged), 1x1 tracking pixel without dimensions (not flagged), `width="auto"` (flagged).

### 11.10 CSS Support Check — Syntax Validation & Vendor Prefixes
**What:** Add CSS syntax validation and vendor prefix detection to the existing ontology-powered check. Current check scans for unsupported properties but doesn't catch malformed CSS or vendor prefixes that may not work.
**Why:** Malformed CSS rules silently fail in email clients. Vendor prefixes (`-webkit-`, `-moz-`) have inconsistent email client support but aren't in the ontology. Full issue list truncation at 10 hides real problems.
**Implementation:**
- Extend `app/qa_engine/checks/css_support.py`
- **CSS syntax validation**: Parse CSS blocks with `cssutils` or regex-based validator. Flag malformed rules (unclosed braces, missing semicolons, invalid property names)
- **Vendor prefix detection**: Flag `-webkit-`, `-moz-`, `-ms-`, `-o-` prefixes. Cross-reference with ontology for actual support data
- **Full issue reporting**: Remove 10-issue truncation. Return all issues in `details` field. Frontend can paginate
- **External stylesheet detection**: If `<link rel="stylesheet">` found, flag it (most email clients strip external CSS)
- Scoring: existing ontology scoring + deductions for syntax errors (-0.1 each) and unsupported vendor prefixes (-0.05 each)
**Security:** CSS parsing is read-only. No external fetches for linked stylesheets.
**Verify:** Test: valid CSS with supported properties (1.0), unsupported `display: flex` (deducted per ontology), malformed CSS `color: ` with no value (flagged), vendor prefix `-webkit-transform` (flagged), external stylesheet (flagged).

### 11.11 Brand Compliance Check — Per-Project Rules Engine
**What:** Replace the always-pass placeholder with a configurable brand rules engine. Validate colors, typography, logo presence, and footer requirements against per-project brand guidelines.
**Why:** Brand compliance is currently zero-enforced. Off-brand emails reaching clients damages credibility. This is the only check that's completely non-functional.
**Implementation:**
- Rewrite `app/qa_engine/checks/brand_compliance.py`
- Create `BrandRules` Pydantic model: `allowed_colors: list[str]`, `required_fonts: list[str]`, `required_elements: list[str]` (e.g., "footer", "logo"), `forbidden_patterns: list[str]`
- Load brand rules from project config (new `brand_rules` JSON column on `Project` model, or separate `BrandProfile` model)
- **Color validation**: Extract all CSS colors (hex, rgb, rgba, named), validate against brand palette. Flag off-brand colors with severity
- **Typography validation**: Extract font-family declarations, validate against brand-approved fonts
- **Required elements**: Check for required sections (footer with legal text, logo image, unsubscribe link)
- **If no brand rules configured**: Return `passed=True` with "No brand rules configured — set up brand profile for enforcement" (backward-compatible)
- Scoring: -0.2 per off-brand color, -0.15 per wrong font, -0.25 per missing required element
**Security:** Brand rules are project-scoped, validated by Pydantic. No code execution.
**Verify:** Test: HTML matching brand rules (1.0), off-brand color (deducted), wrong font (deducted), missing footer (deducted), no brand rules configured (1.0 with info message). Existing tests unchanged.

### 11.12 New Check — Personalisation Syntax Validation (Check #11)
**What:** Add an 11th QA check that validates ESP-specific template syntax: Liquid (Braze), AMPscript (SFMC), JSSP (Adobe Campaign). No existing check covers personalisation correctness. Agent eval shows **58% logic match failure** for Personalisation agent.
**Why:** Broken template syntax causes runtime errors in ESPs — variables don't render, conditionals break, fallbacks fail. This is invisible until the email is sent to real subscribers. Catching syntax errors in QA prevents broken personalisation in production.
**Implementation:**
- Create `app/qa_engine/checks/personalisation_syntax.py`
- Add to `ALL_CHECKS` list in service
- **Auto-detect platform**: Scan for `{{ }}` (Liquid), `%%[ ]%%` (AMPscript), `<%= %>` (JSSP). If none found, return `passed=True` ("No personalisation detected")
- **Liquid validation**: Balanced `{% if %}...{% endif %}`, `{% for %}...{% endfor %}`, valid `{{ var | filter }}` syntax, `{% unless %}...{% endunless %}`
- **AMPscript validation**: Balanced `%%[...]%%` blocks, valid function syntax (`Lookup()`, `Set @var`), `IF...ENDIF` balance
- **JSSP validation**: Balanced `<%= %>` blocks, proper escaping
- **Fallback detection**: For each dynamic variable, check if a default/fallback is provided (e.g., `{{ name | default: "there" }}`)
- **Cross-platform conflict**: Flag if multiple ESP syntaxes detected in same HTML (likely error)
- Scoring: -0.2 per unbalanced tag pair, -0.15 per missing fallback, -0.1 per syntax error
**Security:** Pure syntax parsing, no template execution. No variable interpolation.
**Verify:** Test: valid Liquid with fallbacks (1.0), unbalanced `{% if %}` (deducted), missing fallback on `{{ first_name }}` (deducted), valid AMPscript (1.0), mixed Liquid+AMPscript (flagged). `make test` passes.

### 11.13 Outlook Fixer Agent — MSO Diagnostic Validator
**What:** Add deterministic MSO validation to the Outlook Fixer agent service. Before returning HTML, programmatically verify MSO conditional balance and VML nesting. Reuse the `validate_mso_conditionals()` function from 11.4. Current eval: **50% MSO conditional correctness failure**.
**Why:** LLMs consistently struggle with MSO conditional syntax — they see `<!--[if mso]>` as incomplete comments and "fix" them. A post-generation validator catches these errors before the agent returns output, converting a 50% failure to near-zero.
**Implementation:**
- Import `validate_mso_conditionals()` from `app/qa_engine/checks/fallback.py` into `app/ai/agents/outlook_fixer/service.py`
- After LLM generates HTML, call validator. If issues found:
  - Attempt programmatic fix: re-balance conditionals, inject missing namespaces
  - If programmatic fix insufficient, retry LLM with explicit error context: "Your output has 2 unbalanced MSO conditionals at positions X, Y. Fix these specific issues."
  - Max 1 programmatic retry to avoid infinite loops
- Update Outlook Fixer SKILL.md `mso_conditionals.md` with explicit pair-balance rules and common LLM mistakes
- Emit validator results in `AgentHandoff.warnings` for downstream agents
**Security:** Validator is read-only analysis. Programmatic fixes are limited to injecting closing tags and namespace attributes.
**Verify:** `make eval-run --agent outlook_fixer` shows MSO conditional pass rate improvement from 50% to 85%+. Manual test: intentionally unbalanced MSO HTML → agent fixes it. Existing tests pass.

### 11.14 Dark Mode Agent — Deterministic Meta Tag Injector
**What:** Add deterministic meta tag injection to the Dark Mode agent service. Before returning HTML, check `<head>` for both required meta tags and inject if missing. Current eval: **50% meta tag failure**.
**Why:** The agent forgets one of the two required meta tags ~50% of the time. A simple programmatic check + inject eliminates this failure mode entirely without relying on the LLM.
**Implementation:**
- In `app/ai/agents/dark_mode/service.py`, after LLM generation:
  - Parse HTML, find `<head>` section
  - Check for `<meta name="color-scheme" content="light dark">` — inject if missing
  - Check for `<meta name="supported-color-schemes" content="light dark">` — inject if missing
  - Inject at end of `<head>` (before `</head>`) to avoid disrupting existing content
- Update Dark Mode SKILL.md with explicit meta tag checklist
- Add color coherence validation: extract light/dark color pairs, flag white-on-white or black-on-black combinations
**Security:** Meta tag injection is adding standard HTML tags to `<head>`. No script injection possible.
**Verify:** `make eval-run --agent dark_mode` shows meta tag pass rate improvement from 50% to 95%+. Test: HTML without meta tags → agent adds them. HTML with both tags → no change.

### 11.15 Scaffolder Agent — MSO-First Generation
**What:** Update Scaffolder SKILL.md and service to generate MSO-correct HTML from the first attempt. Load Outlook Fixer's MSO patterns as reference context. Current eval: **58% MSO conditional failure** — the scaffolder should never generate broken MSO.
**Why:** If the scaffolder generates correct MSO from the start, the entire blueprint pipeline avoids one retry loop. MSO fixes are the most common recovery router destination. Prevention > correction.
**Implementation:**
- Update `app/ai/agents/scaffolder/SKILL.md` with mandatory MSO section:
  - Every template MUST include MSO centering table wrapper
  - MUST include `xmlns:v` and `xmlns:o` on `<html>` when VML used
  - MUST balance all conditional comments
  - Reference Outlook Fixer's `mso_conditionals.md` patterns
- In `app/ai/agents/scaffolder/service.py`, load Outlook Fixer's L3 SKILL files into system prompt context (top 15 MSO patterns)
- Add same `validate_mso_conditionals()` post-generation check as 11.13
- Emit MSO validation status in `AgentHandoff.decisions` so downstream agents know MSO is verified
**Security:** Cross-agent SKILL file loading is read-only from local filesystem.
**Verify:** `make eval-run --agent scaffolder` shows MSO conditional pass rate improvement from 58% to 85%+. Blueprint pipeline test: scaffolder output passes fallback QA check on first attempt.

### 11.16 Personalisation Agent — Per-Platform Syntax Validator
**What:** Add deterministic per-platform template syntax validation to the Personalisation agent service. Before returning HTML, validate balanced tags and fallback presence. Current eval: **58% logic match failure**.
**Why:** LLMs generate plausible-looking but syntactically broken template code. Liquid `{% if %}` without `{% endif %}`, AMPscript `%%[` without `]%%`. A programmatic validator catches these mechanical errors.
**Implementation:**
- Create `app/ai/agents/personalisation/validators.py`:
  - `validate_liquid(html) -> list[str]`: balanced if/endif, for/endfor, unless/endunless, valid filter syntax
  - `validate_ampscript(html) -> list[str]`: balanced blocks, valid function calls, IF/ENDIF pairs
  - `validate_jssp(html) -> list[str]`: balanced expression tags, proper escaping
- In service, after LLM generation: detect platform, run validator
  - If issues found: retry LLM with specific errors ("Unbalanced `{% if %}` at line 45 — add `{% endif %}`")
  - Max 1 retry
- Reuse validators in QA check 11.12 (shared logic, different integration point)
- Update Personalisation SKILL.md with balanced-tag rules per platform
**Security:** Syntax validation only. No template rendering or variable interpolation.
**Verify:** `make eval-run --agent personalisation` shows logic match pass rate improvement from 58% to 80%+. Test: Liquid with missing endif → agent fixes it.

### 11.17 Code Reviewer Agent — Actionability Framework
**What:** Update Code Reviewer SKILL.md to require "change X to Y" format for every suggestion. Current eval: **67% suggestion actionability** — suggestions are too vague.
**Why:** Vague suggestions like "simplify CSS" don't help agents or developers. Actionable suggestions like "Replace `display: flex` with `<table>` layout (unsupported in Outlook 2019)" can be auto-applied.
**Implementation:**
- Update `app/ai/agents/code_reviewer/SKILL.md`:
  - Every suggestion MUST include: property/element name, current value, recommended replacement, affected clients
  - Format: `ISSUE: {property} on line {N} | CURRENT: {value} | FIX: {replacement} | CLIENTS: {list}`
  - Reference ontology data in suggestions (link CSS property to client support matrix)
- Expand "email allowlist" in SKILL.md: add `mso-` prefixes, `[data-ogsc]` selectors, MSO conditionals, VML elements as known-good patterns
- In service, validate output format: if suggestions don't match actionable format, retry with format correction prompt
- Add 75%+ coverage completeness target: reviewer should flag issues in at least 75% of categories (CSS, HTML structure, accessibility, performance)
**Security:** Output format validation is string matching. No code execution.
**Verify:** `make eval-run --agent code_reviewer` shows suggestion actionability improvement from 67% to 85%+. Manual review: every suggestion has concrete before/after values.

### 11.18 Accessibility Agent — Alt Text Quality Framework
**What:** Update Accessibility Auditor SKILL.md with structured alt text generation rules. Current eval: **70% alt text quality, 70% screen reader compatibility**.
**Why:** Generic alt text ("image", "photo") is worse than no alt text — it clutters screen readers without conveying information. The agent needs clear rules for decorative vs informative images and quality criteria.
**Implementation:**
- Update `app/ai/agents/accessibility/SKILL.md` with alt text framework:
  - **Decorative images** (borders, spacers, backgrounds): `alt=""`
  - **Content images** (product shots, photos): 5-15 words, describe what's shown, not the file name
  - **Functional images** (buttons, icons, CTAs): describe the action ("Submit form", "Download PDF"), not appearance
  - **Logo images**: company name only ("Acme Corp"), not "Acme Corp logo image"
  - **Complex images** (charts, infographics): `aria-describedby` pointing to text description
- Add WCAG AA contrast ratio rules to SKILL.md: 4.5:1 for normal text, 3:1 for large text (≥18pt or ≥14pt bold)
- Update service to validate alt text quality before returning: reject single-word alts, reject generic terms, verify length bounds
- Add screen reader landmark recommendations: `role="banner"`, `role="main"`, `role="contentinfo"` for email structure
**Security:** Alt text generation from image context. No image fetching or processing.
**Verify:** `make eval-run --agent accessibility` shows alt text quality improvement from 70% to 85%+. Test: image with no context → descriptive alt generated. Decorative spacer → `alt=""`.

### 11.19 Content Agent — Length Guardrails
**What:** Add token/character limits per operation type to the Content agent. Current eval: **71% length appropriate** — expand operations overshoot, shorten operations remove critical info.
**Why:** Email copy has strict length constraints. Subject lines (50 chars ideal), preheaders (85-100 chars), CTAs (2-5 words). Without guardrails, the LLM generates copy that doesn't fit.
**Implementation:**
- Update `app/ai/agents/content/SKILL.md` with length rules per operation:
  - Subject line: 30-60 chars (50 ideal), no truncation in mobile preview
  - Preheader: 85-100 chars (fills preview pane, prevents body text leak)
  - CTA text: 2-5 words, action verb first ("Get Started", "Download Now")
  - Body copy: respect original length ±20% for tone/rewrite operations
  - Expand: max 150% of original length
  - Shorten: min 50% of original, preserve all key information points
- In service, post-generation length validation:
  - If subject > 60 chars, retry with explicit "shorten to under 60 characters" instruction
  - If CTA > 5 words, retry with word count constraint
  - Max 1 retry per length violation
- Add excessive punctuation detection: strip `!!!`, `???`, `...` patterns from generated copy
**Security:** Length validation is character counting. No content injection.
**Verify:** `make eval-run --agent content` shows length appropriate improvement from 71% to 85%+. Test: "expand this paragraph" → output ≤ 150% original length. Subject line generation → ≤ 60 chars.

### 11.20 Recovery Router — Enriched Failure Context
**What:** Upgrade recovery router to pass detailed, structured failure information to fixer agents instead of generic check names. Currently sends `"fallback: failed"` — should send `"fallback: 2 unbalanced MSO conditionals at lines 45, 89; VML orphan at line 112"`.
**Why:** Agents with specific error context fix issues 3x faster than agents with generic "this check failed" messages. Reduces retry loops from 2-3 to 1. This amplifies every individual check improvement.
**Implementation:**
- Update `app/ai/blueprints/nodes/recovery_router_node.py`
- QA check results already contain `details: str` — pass the full details string (not just check name) to recovery context
- Structure failure context as: `{check_name: str, score: float, details: str, suggested_agent: str, priority: int}`
- Order failures by priority (MSO > accessibility > dark mode > spam > links > images > size)
- Inject into `NodeContext.metadata["qa_failure_details"]` — list of structured failure objects
- Recovery router selects agent based on highest-priority failure, but passes ALL failure details so agent can fix multiple issues in one pass
- Add cycle detection enhancement: if same check failed with same details twice, escalate to scaffolder (full regeneration) instead of same fixer
- **Scoped retry constraints:** On retry, constrain what each agent can modify to prevent cascading failures. Scaffolder: HTML structure only (no new CSS frameworks). Dark mode: CSS only (`<style>` + inline styles, no HTML restructuring). Content: text nodes + attributes only (`alt`, `title`, `aria-label`). Outlook fixer: add MSO/VML only (no HTML removal). Enforce via prompt constraints on retry + output diff validation (reject changes outside allowed scope).
**Security:** Failure details are derived from QA check output (already sanitised). No user input injection.
**Verify:** Blueprint test: intentionally broken HTML with 3 QA failures → recovery router passes all 3 with details → fixer agent receives structured context. Fewer retry loops than current generic routing. Retry output diff stays within allowed scope per agent.

### 11.21 Deterministic Micro-Judges — Codify Judge Criteria into QA Checks
**What:** Extract the subset of eval judge criteria that can be validated deterministically and add them as enhanced QA checks. ~60% of judge criteria across all 9 agents map to codifiable rules (e.g., "uses nested tables with 600px max-width" from ScaffolderJudge, "balanced MSO conditionals" from OutlookFixerJudge). This gives judge-quality detection at QA-gate speed (0 tokens, <50ms per check).
**Why:** Items 11.2–11.12 already upgrade individual QA checks. This task explicitly maps each judge criterion to its deterministic equivalent, ensuring QA checks cover what judges catch. After this, the QA gate catches ~90% of what LLM judges would flag, making inline judges (11.23) only necessary for the remaining ~10% that requires LLM reasoning (brief fidelity, tone accuracy, copy quality).
**Implementation:**
- Create `app/qa_engine/judge_criteria_map.py` — mapping of `{agent: {criterion: qa_check_name | None}}`:
  - ScaffolderJudge: `email_layout_patterns` → html_validation (11.2), `mso_conditionals` → fallback (11.4), `dark_mode_readiness` → dark_mode (11.5), `accessibility_baseline` → accessibility (11.3), `brief_fidelity` → None (requires LLM)
  - DarkModeJudge: `html_preservation` → html_validation, `outlook_selector_completeness` → fallback, `meta_and_media_query` → dark_mode, `contrast_preservation` → accessibility, `color_coherence` → None (requires LLM)
  - ContentJudge: `spam_avoidance` → spam_score (11.6), `operation_compliance` → None, `copy_quality` → None, `tone_accuracy` → None, `security_and_pii` → brand_compliance (11.11)
  - (Map remaining 6 agents similarly)
- For each mapped criterion, verify the upgraded QA check (11.2–11.12) covers the judge's specific validation logic. Add sub-checks where gaps exist.
- Add `make eval-qa-coverage` command: runs all judges + QA checks on same test set, reports criterion-vs-check agreement rate. Target: >85% agreement on mapped criteria.
- Update recovery router (11.20) — use criteria map to route QA failures to the correct fixer agent with judge-criterion-level specificity
**Security:** No new attack surface — extends existing deterministic checks only.
**Verify:** Run `make eval-qa-coverage` on all 9 agents' synthetic data. For each mapped criterion, QA check agrees with judge verdict >85% of the time. Unmapped criteria (brief_fidelity, tone_accuracy, etc.) documented as "LLM-only" — these are what 11.23 inline judges cover.

### 11.22 Template-First Hybrid Architecture — From 16.7% to 99%+ Structural Pass Rate

**What:** Replace LLM-generates-everything architecture with a hybrid model where deterministic code generates all structural HTML and the LLM makes content/design decisions only. The LLM never writes a `<table>` tag, `<!--[if mso]>` conditional, or `<meta>` tag — it selects templates, fills content slots, and chooses design tokens. Deterministic Python assembles the final HTML from tested, pre-validated building blocks.

**Why:** Current 16.7% pass rate (36 traces via claude-sonnet-4) fails because the LLM is asked to generate the hardest HTML that exists — table layouts, MSO conditionals, VML, 25-client compatibility. Even frontier models struggle (Sonnet: 0% on MSO conditionals, 8% on accessibility, 10% on html_preservation). The insight: **if deterministic code generates every structural element, QA checks are validating code we wrote and tested, not LLM output.** This eliminates entire failure categories by construction rather than correction. No model changes needed — this extracts maximum value from Claude Sonnet/Opus by giving the LLM the job it's actually good at (creative content decisions) and taking away the job it's bad at (syntax-precise structural HTML). Local/weaker models are not viable — email HTML generation is one of the hardest LLM tasks; substituting models would degrade quality further.

**Target ceiling:** 99%+ on structural QA checks (deterministic guarantees), ~95% on semantic quality (brief fidelity, tone), **93-97% overall**. The irreducible ~3-5% gap comes from subjective criteria (tone accuracy, copy quality, novel layout requests) that require LLM judgment.

**Dependencies:** 11.1–11.21 (upgraded QA checks + deterministic micro-judges provide better feedback signals). Phase 8-9 (ontology for client compatibility data). Phase 7 (SKILL.md, BaseAgentService). Phase 2 (component library for golden template building blocks).

#### 11.22.1 Golden Template Library — Pre-Validated Email Skeletons
**What:** Build 15-20 battle-tested email HTML templates covering ~95% of real campaign briefs. Each template passes all 10 QA checks at 100% out of the box. Templates contain named content slots (`<!-- SLOT:hero -->`, `<!-- SLOT:body -->`) that the LLM fills — the LLM never generates structural HTML.
**Why:** This is the single highest-impact change. MSO conditionals go from 0% to ~99% because they're pre-written and tested. Dark mode goes from ~50% to ~99% because meta tags, media queries, and Outlook selectors are pre-wired. The LLM's job shrinks from "generate a complete email" to "pick a template and fill in the blanks."
**Implementation:**
- Create `app/ai/templates/` directory — golden template library:
  - `app/ai/templates/library.py` — `TemplateLibrary` class: `list_templates() -> list[TemplateMeta]`, `get_template(id) -> GoldenTemplate`, `match_template(brief: str) -> list[TemplateMeta]` (brief-to-template matching via keyword analysis)
  - `app/ai/templates/models.py` — `GoldenTemplate` dataclass: `id`, `name`, `description`, `category` (promotional/transactional/newsletter/notification), `layout_type` (single_col/two_col/hero_cards/sidebar/hybrid), `slot_definitions: list[SlotDef]`, `html_skeleton: str`, `supported_clients: list[str]`, `qa_scores: dict[str, float]`
  - `app/ai/templates/slots.py` — `SlotDef` dataclass: `name`, `slot_type` (text/image/cta/repeatable/conditional), `constraints` (max_chars, allowed_tags, required_fields), `default_content: str`
  - `app/ai/templates/assembler.py` — `assemble(template: GoldenTemplate, slot_fills: dict[str, SlotFill]) -> str` — replaces slot markers with filled content, validates constraints, returns complete HTML
- Build 15 initial templates covering core layout categories:
  - **Single column** (3 variants): simple announcement, long-form article, transactional receipt
  - **Two column** (3 variants): product comparison, feature highlight, content + sidebar
  - **Hero + cards** (3 variants): promotional splash, event invitation, product launch
  - **Newsletter** (2 variants): multi-story digest, curated links
  - **Transactional** (2 variants): order confirmation, account notification
  - **Hybrid** (2 variants): hero + 2-col + CTA stack, progressive disclosure (expandable)
- Each template must:
  - Pass all 10 QA checks at 1.0 score (verified by automated test)
  - Have balanced MSO conditionals (validated by `validate_mso_conditionals()`)
  - Include complete dark mode (meta tags + media query + Outlook selectors + color remapping for 5 base color slots)
  - Include WCAG AA accessibility (lang, alt placeholders with guidance, heading hierarchy, table roles, link text slots with constraints)
  - Include VML namespaces on `<html>` tag
  - Support all 25 email clients in the ontology
  - Use fluid hybrid layout pattern (600px max-width, responsive to 320px)
- Template QA regression test: `tests/test_golden_templates.py` — runs all 10 QA checks on all 15 templates, fails CI if any score < 1.0
**Security:** Templates are static files in the repo. No user input in template structure. Slot fills are validated by `SlotDef.constraints` before assembly.
**Verify:** `python -m pytest tests/test_golden_templates.py` — all 15 templates pass all 10 QA checks at 1.0. Manual review: templates render correctly in Litmus across 25 clients.

#### 11.22.2 Structured Output Schema — LLM Returns JSON, Not HTML
**What:** Replace the current "generate full HTML" prompt with a structured output schema where the LLM returns a JSON object containing template selection, slot content, and design token choices. Deterministic code assembles this into HTML. The LLM never writes HTML tags.
**Why:** Structured output is dramatically more reliable than freeform generation. The LLM excels at content decisions (copy, layout choice, color selection) but fails at syntax-precise structural HTML. JSON output is parseable, validatable, and retryable at the field level — a malformed subject line doesn't require regenerating the entire email.
**Implementation:**
- Create `app/ai/templates/schemas.py` — structured output models:
  ```python
  class TemplateSelection(BaseModel):
      template_id: str                          # Which golden template to use
      reasoning: str                            # Why this template fits the brief

  class SlotFill(BaseModel):
      slot_name: str                            # Matches SlotDef.name
      content_type: Literal["text", "image", "cta", "repeatable"]
      heading: str | None = None                # For sections with headings
      body_text: str                            # Main content
      image_alt: str | None = None              # Alt text for images in this slot
      cta_text: str | None = None               # CTA button text (2-5 words)
      cta_url_variable: str | None = None       # ESP variable for CTA href
      items: list[SlotFill] | None = None       # For repeatable slots (card grids)

  class DesignTokens(BaseModel):
      primary_color: str                        # Hex, used for headers/CTAs
      secondary_color: str                      # Hex, used for accents
      background_color: str                     # Hex, email body background
      text_color: str                           # Hex, body text
      dark_primary: str                         # Hex, dark mode remap of primary
      dark_secondary: str                       # Hex, dark mode remap of secondary
      dark_background: str                      # Hex, dark mode background
      dark_text: str                            # Hex, dark mode text
      heading_font: str                         # Font stack
      body_font: str                            # Font stack

  class PersonalisationConfig(BaseModel):
      esp_platform: Literal["liquid", "ampscript", "jssp", "none"]
      variables: list[PersonalisationVariable]   # Name, fallback, location

  class EmailBuildPlan(BaseModel):
      template_selection: TemplateSelection
      slot_fills: list[SlotFill]
      design_tokens: DesignTokens
      personalisation: PersonalisationConfig
      subject_line: str                         # 30-60 chars
      preheader: str                            # 85-100 chars
  ```
- Update Scaffolder agent to return `EmailBuildPlan` JSON instead of HTML:
  - System prompt instructs: "You are an email architect. Analyse the brief and return a structured build plan. Do NOT generate HTML."
  - Use Claude's tool_use / structured output mode to enforce schema compliance
  - If JSON validation fails, retry with specific field-level error (not full regeneration)
- Update `app/ai/templates/assembler.py` to consume `EmailBuildPlan`:
  - `assemble_from_plan(plan: EmailBuildPlan, library: TemplateLibrary) -> str`
  - Fetches golden template by `plan.template_selection.template_id`
  - Fills slots using `plan.slot_fills` with constraint validation
  - Injects `plan.design_tokens` into CSS variables and dark mode block
  - Injects `plan.personalisation` variables at marked positions
  - Returns complete, QA-ready HTML
**Security:** JSON schema enforced by Pydantic — no injection via slot content. HTML content in slot fills is escaped by the assembler. Design token hex values validated by regex. ESP variables validated against known patterns per platform.
**Verify:** Test with 10 diverse briefs: LLM returns valid `EmailBuildPlan` JSON ≥95% of the time. Assembled HTML passes all 10 QA checks at 1.0 for every valid plan. Invalid JSON triggers field-level retry (not full regen). Token usage: measure ~60% reduction vs current full-HTML generation.

#### 11.22.3 Multi-Pass Generation Pipeline — Decompose for Reliability
**What:** Replace the single LLM call with 3 focused passes, each with a narrow scope and independent validation. Errors in one pass don't cascade — a bad CTA doesn't require regenerating the layout decision.
**Why:** Compound reliability: if each pass has 95% accuracy, a single pass = 95% overall, but the current single-call approach asks for 10+ correct decisions simultaneously (95%^10 = 60%). Three focused passes with 3-4 decisions each: (95%^4)^3 = 70% worst case, but with per-field retry the effective rate approaches 99%.
**Implementation:**
- Create `app/ai/agents/pipeline.py` — `MultiPassPipeline` orchestrator:
  - **Pass 1 — Layout Analysis** (cheap, Haiku-tier model via `_get_model_tier("lightweight")`):
    - Input: campaign brief
    - Output: `TemplateSelection` — which golden template, reasoning
    - Validation: template_id exists in library, layout matches brief intent
    - Retry: if invalid template_id, retry with available template list
    - Cost: ~500-1,000 tokens
  - **Pass 2 — Content Generation** (quality, Sonnet-tier model via `_get_model_tier("standard")`):
    - Input: brief + selected template's `SlotDef` list (tells LLM exactly what content is needed)
    - Output: `list[SlotFill]` + `subject_line` + `preheader`
    - Validation: all required slots filled, content within `SlotDef.constraints` (char limits, required fields)
    - Retry: per-slot — only regenerate slots that failed validation
    - Cost: ~2,000-4,000 tokens
    - **Parallelisable**: if template has independent slots, generate them in parallel
  - **Pass 3 — Design & Personalisation** (cheap, Haiku-tier):
    - Input: brief + template + filled slots summary
    - Output: `DesignTokens` + `PersonalisationConfig`
    - Validation: hex colors valid, contrast ratio ≥ 4.5:1 (computed deterministically), font stacks valid, ESP variables syntactically correct
    - Retry: if contrast fails, retry with "ensure dark_text on dark_background has ≥4.5:1 contrast ratio"
    - Cost: ~500-1,000 tokens
  - **Assembly** (deterministic, 0 tokens):
    - `assemble_from_plan()` combines all three pass outputs into final HTML
    - Run all 10 QA checks
    - If QA fails: identify which pass produced the failing element, retry ONLY that pass with QA feedback
- Wire into `BaseAgentService` — `MultiPassPipeline` replaces single `_call_llm()` for generation agents
- Existing single-call path preserved behind feature flag `AGENT__USE_MULTI_PASS` (default `True`, set `False` for A/B comparison)
**Security:** Each pass receives only the context it needs (principle of least privilege for LLM context). Pass outputs validated by Pydantic before assembly. No pass has access to credentials or system internals.
**Verify:** Run all 36 eval synthetic cases through multi-pass pipeline. Measure per-pass success rate (target: ≥95% per pass). Measure overall first-attempt QA pass rate (target: ≥85%). Measure token usage (target: ≤ 5,000 tokens total vs ~8,000-15,000 for current single-call). Measure latency (target: ≤ 8s wall time with parallel slots).

#### 11.22.4 Cascading Auto-Repair Pipeline — Belt-and-Suspenders Post-Processing
**What:** Multi-stage deterministic repair pipeline that runs between assembly and QA gate. Each stage targets a specific failure category, and each stage's output feeds the next. The pipeline guarantees structural correctness — if the assembler produced valid HTML (which it should from golden templates), repair is a no-op. If the LLM snuck malformed content into a slot, repair catches it.
**Why:** Defense in depth. Golden templates + structured output + multi-pass should yield ~95% QA pass rate. The repair pipeline catches the remaining ~4-5% of structural issues (malformed slot content, edge cases in personalisation variable injection, unexpected LLM output in slot fills). This is the difference between 95% and 99%+.
**Implementation:**
- Create `app/ai/agents/repair_pipeline.py` — `RepairPipeline` with ordered stages:
  - **Stage 1: Structure validator** — `lxml` parse, verify DOCTYPE/html/head/body present and well-formed. If broken, rebuild from golden template skeleton (content preserved).
  - **Stage 2: MSO balancer** — count `<!--[if` vs `<![endif]-->`, inject missing closers at correct nesting depth. Verify VML inside conditionals. Add missing namespaces. (Reuses `validate_mso_conditionals()` from 11.4)
  - **Stage 3: Dark mode completeness** — verify meta tags in `<head>`, media query non-empty, Outlook selectors present with color declarations. If media query empty, populate from `DesignTokens` dark colors. If meta tags missing, inject.
  - **Stage 4: Accessibility enforcer** — verify all `<img>` have `alt`, heading hierarchy valid, tables have `role`, links have descriptive text. Add `alt=""` to images missing alt. Add `role="presentation"` to layout tables.
  - **Stage 5: Personalisation syntax validator** — verify balanced Liquid `{% %}` / `{{ }}`, AMPscript `%%[ ]%%`, JSSP `<%= %>`. Report unbalanced but don't auto-fix (semantic — flag for LLM retry of personalisation pass).
  - **Stage 6: Size optimizer** — if assembled HTML > 102KB (Gmail clipping), remove redundant whitespace, inline duplicate CSS, warn if still over threshold.
  - **Stage 7: Link sanitizer** — verify all `href` values well-formed, no empty hrefs, no `javascript:` protocols, ESP template variables syntactically valid.
- Each stage returns `RepairResult(html: str, fixes: list[str], warnings: list[str])`
- Pipeline logs all fixes applied: `agent.repair_pipeline.stage_{n}.fixes_applied`
- If total fixes > 5, flag for human review (too much repair suggests a deeper issue)
- Wire into `BaseAgentService` — runs after assembly, before QA gate
**Security:** All repair operations are deterministic HTML manipulation via `lxml`. No external fetches. No LLM calls. Slot content is escaped during assembly — repair doesn't re-introduce injection vectors.
**Verify:** Feed all 36 eval synthetic cases (original LLM output, before any pipeline changes) through repair pipeline alone. Measure: how many QA failures does repair fix without any upstream changes? Target: ≥50% of current failures fixable by repair alone. Combined with golden templates + structured output: 99%+ QA pass rate on structural checks.

#### 11.22.5 SKILL.md Rewrite — Architect Prompts, Not Generator Prompts
**What:** Rewrite all 9 agent SKILL.md files to match the new template-first architecture. Agents are no longer "HTML generators" — they are "email architects" that make content and design decisions. Prompts must instruct the LLM to return structured decisions, not raw HTML.
**Why:** Current SKILL.md files instruct agents to generate complete HTML, which is the root cause of structural failures. The prompt must match the architecture — telling the LLM "return JSON with your decisions" produces fundamentally different (better) output than "generate an HTML email."
**Implementation:**
- **Scaffolder SKILL.md**: Rewrite from "generate Maizzle HTML" to "analyse brief → select golden template → fill content slots → choose design tokens." Include the `EmailBuildPlan` schema in L1. Add template selection heuristics in L2. Few-shot examples of brief → JSON plan in L3.
- **Dark Mode SKILL.md**: Rewrite from "inject dark mode CSS" to "analyse existing colors → generate dark mode color remapping." LLM returns `DesignTokens.dark_*` fields only. Deterministic code handles meta tags, media queries, Outlook selectors.
- **Content SKILL.md**: Rewrite from "generate copy" to "fill content slots with constraints." Include `SlotDef.constraints` (char limits, required fields) as hard rules. Per-operation limits: subject 30-60 chars, preheader 85-100 chars, CTA 2-5 words.
- **Outlook Fixer SKILL.md**: Rewrite from "fix MSO conditionals" to "diagnose structural issues in build plan." If using golden templates, this agent's scope shrinks to edge cases where slot content breaks MSO structure — provide specific diagnostic patterns.
- **Accessibility SKILL.md**: Rewrite from "audit accessibility" to "fill alt text slots and validate heading hierarchy." LLM returns structured accessibility decisions (`{image_id: alt_text, table_id: role}`), code applies them.
- **Personalisation SKILL.md**: Rewrite from "add Liquid/AMPscript" to "specify variable placements." LLM returns `PersonalisationConfig`, code injects syntax-correct ESP variables.
- **Code Reviewer SKILL.md**: Rewrite to focus on build plan review (template choice appropriateness, slot content quality, design token contrast) rather than raw HTML review.
- **Knowledge SKILL.md**: Unchanged (RAG Q&A doesn't generate HTML).
- **Innovation SKILL.md**: Rewrite to prototype new golden template variants and slot types rather than freeform HTML generation.
- Add negative examples to all generation agents: "Do NOT return raw HTML. Return the structured JSON plan. The assembler handles HTML generation."
- Use `make eval-skill-test` for each SKILL.md rewrite to validate improvement
**Security:** No change to security surface — SKILL.md files are prompt content only.
**Verify:** `make eval-run` per agent before/after rewrite. Target: each agent's structured output compliance ≥95% (LLM returns valid JSON matching schema). Combined with template library: overall QA pass rate ≥90%.

#### 11.22.6 Context Assembly Optimisation — Token Budget Enforcement
**What:** Optimise what context each agent receives per pass. Multi-pass architecture enables pass-specific context — Pass 1 (layout) needs only the brief, Pass 2 (content) needs brief + slot definitions, Pass 3 (design) needs brief + template palette. No pass needs full SKILL.md + handoff history + failure warnings.
**Implementation:**
- Create `app/ai/agents/context_budget.py`:
  - `ContextBudget` dataclass: `max_tokens: int`, `sections: dict[str, int]` (per-section budgets)
  - `measure_context(prompt: str) -> ContextMetrics` — token counts per section
  - `enforce_budget(context: dict, budget: ContextBudget) -> dict` — trim lowest-priority sections to fit budget
- Per-pass budgets:
  - Pass 1 (layout): 2,000 tokens max (brief + template list summaries)
  - Pass 2 (content): 4,000 tokens max (brief + slot definitions + 2 few-shot examples)
  - Pass 3 (design): 1,500 tokens max (brief + brand guidelines + current template palette)
- **Selective SKILL.md loading**: Load only the L1 section for the current pass. L2/L3 loaded only if Pass fails and retries.
- **Handoff summarisation**: For multi-node blueprint chains, summarise handoffs >2 nodes back to a single paragraph.
- **Failure warning pruning**: Only inject warnings relevant to the current pass (e.g., MSO warnings only in Pass 1 layout selection, not in Pass 2 content generation).
**Security:** No new attack surface. Context trimming is deterministic.
**Verify:** Measure prompt token counts per pass. Target: total across 3 passes ≤ 8,000 tokens (vs current single-call ~10,000-15,000). Per-pass accuracy should not decrease from trimming (same or better signal-to-noise).

#### 11.22.7 Novel Layout Fallback — Graceful Degradation for Edge Cases
**What:** Handle the ~5% of briefs that don't match any golden template. Instead of falling back to unreliable full-HTML generation, compose new layouts by combining tested building blocks (sections from golden templates). This is the difference between 95% and 97-99%.
**Why:** Golden templates cover common layouts, but clients occasionally request unusual combinations (e.g., 3-column on mobile, accordion sections, gamification elements). Without a fallback, these briefs either fail or revert to the old unreliable pipeline.
**Implementation:**
- Create `app/ai/templates/composer.py` — `TemplateComposer`:
  - `decompose_templates() -> list[SectionBlock]` — break golden templates into reusable section blocks (hero, text_block, two_col, card_grid, cta, footer, spacer, divider)
  - `SectionBlock` dataclass: `block_type`, `html_skeleton`, `slot_definitions`, `mso_wrapper: bool`, `dark_mode_vars: list[str]`
  - `compose(blocks: list[str], order: list[str]) -> GoldenTemplate` — assemble a new template from section blocks, auto-generate MSO wrappers between adjacent blocks, merge dark mode variables
  - `validate_composition(template: GoldenTemplate) -> list[QACheckResult]` — run QA checks on composed template before use
- Update Scaffolder Pass 1 to support composition:
  - If no golden template matches brief (confidence < 0.7), return `CompositionPlan` instead of `TemplateSelection`
  - `CompositionPlan`: ordered list of `SectionBlock` IDs + per-block slot overrides
  - Assembler builds from `CompositionPlan` using `TemplateComposer.compose()`
- Composed templates validated by QA before slot filling — if composition fails QA, fall back to closest matching golden template with a warning
- Track composition frequency in `traces/` — if >10% of briefs require composition, build new golden templates for the common compositions
**Security:** Section blocks are derived from golden templates (pre-validated). Composition is deterministic concatenation + MSO wrapper generation. No LLM involvement in structural composition.
**Verify:** Create 5 "unusual" briefs that don't match any golden template. Verify: composer produces valid compositions, assembled HTML passes QA, fallback to closest template works when composition fails. Measure: composition QA pass rate ≥90%.

#### 11.22.8 Agent Role Redefinition — Tighten Specialisation
**What:** Redefine agent responsibilities to eliminate overlap and match the template-first architecture. Several agents become simpler or unnecessary when templates handle structure.
**Why:** Current agent overlap causes conflicting fixes — Scaffolder generates dark mode, then Dark Mode agent overwrites it. Template-first architecture means each agent owns a specific slice of the `EmailBuildPlan`, with no structural HTML generation.
**Implementation:**
- **Scaffolder**: Template selection + content slot filling only. No HTML generation. Owns Pass 1 + Pass 2.
- **Dark Mode**: Color remapping decisions only. Returns `DesignTokens.dark_*` values. Deterministic code handles all CSS/meta/Outlook injection. Owns Pass 3 color subset.
- **Content**: Subject line, preheader, CTA text, body copy editing. Operates on `SlotFill.body_text` fields only. Separate from Scaffolder (can run independently for copy-only tasks).
- **Outlook Fixer**: Reduced scope — only activated when repair pipeline detects MSO issues that golden templates shouldn't have (indicates template bug or unusual composition). Primarily a diagnostic agent that reports issues rather than generating HTML fixes.
- **Accessibility**: Alt text generation + heading hierarchy validation. Returns structured `{image_id: alt_text}` decisions. Code applies them. Does NOT generate or modify HTML.
- **Personalisation**: ESP variable placement decisions. Returns `PersonalisationConfig`. Code injects syntax-correct variables. Does NOT write Liquid/AMPscript directly.
- **Code Reviewer**: Reviews `EmailBuildPlan` for appropriateness (template choice, slot content quality, design token contrast, personalisation completeness). Does NOT review raw HTML.
- **Knowledge**: Unchanged — RAG Q&A.
- **Innovation**: Prototypes new `SectionBlock` types and `GoldenTemplate` compositions. Tests via `TemplateComposer.validate_composition()`. Does NOT generate freeform HTML.
- Update `app/ai/blueprints/definitions/` — blueprint node sequences reflect new agent scopes. Scaffolder node produces `EmailBuildPlan`, downstream agents modify specific plan fields, final assembly node is deterministic.
**Security:** No change — agents produce structured data, code handles HTML. Attack surface reduced (less raw HTML in LLM output).
**Verify:** Blueprint end-to-end test: brief → Scaffolder (plan) → Content (refine slots) → Dark Mode (dark tokens) → Personalisation (variables) → Assembly (deterministic) → QA → Export. Each agent's output is valid JSON matching its schema. No agent produces raw HTML.

#### 11.22.9 Eval-Driven Iteration Loop — Milestone Tracking to 99%
**What:** Establish the measurement framework for tracking progress from 16.7% to 99%+. Every change in 11.22.1–11.22.8 must be validated by the eval system before merging. Regression detection prevents backsliding.
**Implementation:**
- Define baseline: current `traces/baseline.json` (16.7% overall, per-agent and per-criterion breakpoints)
- After each 11.24.x subtask, run `make eval-run` + `make eval-analysis` + `make eval-regression`
- Use `make eval-skill-test` for every SKILL.md rewrite (A/B comparison)
- Track progress in `traces/improvement_log.jsonl` — append `{date, change_description, agent, criterion, before_rate, after_rate}`
- **Milestone targets:**
  - M1 (after 11.22.1 golden templates + 11.22.2 structured output): 70% overall — structural failures eliminated for template-covered briefs
  - M2 (after 11.22.3 multi-pass): 85% overall — per-field retry catches content generation errors
  - M3 (after 11.22.4 repair pipeline): 95% overall — cascading repair catches remaining structural edge cases
  - M4 (after 11.22.5 SKILL.md rewrites): 97% overall — LLM produces better structured decisions
  - M5 (after 11.22.6 context optimisation + 11.22.7 novel layout fallback): 99%+ structural, ~95% semantic, **97%+ overall**
  - M6 (after 11.22.8 agent redefinition): sustained 97%+ with reduced token cost and latency
- If a change decreases any agent's pass rate by >3 percentage points, revert and investigate
- **Autonomous eval loop:** Implement modify→run→measure→keep/revert cycle for prompt optimization. After each prompt/SKILL.md change: run agents against the same briefs, score via QA gate (deterministic) + LLM judge (subjective), record in `traces/improvement_log.jsonl`. Keep changes that improve pass rate, auto-revert those that don't. Can run overnight as unattended sweeps.
- **CI golden test cases:** Small set of email templates with known-correct QA outcomes that must pass in CI (`make eval-golden`). Catches regressions on model/prompt/check changes without running full eval suite. Golden cases derived from highest-confidence eval traces.
- **New eval dimensions for template-first**: add eval criteria for template selection accuracy (did LLM pick the right template?), slot fill quality (content appropriate for slot constraints?), design token coherence (colors accessible, on-brand?)
- Update synthetic test data: add 10 cases specifically testing template selection edge cases (ambiguous briefs, multi-intent briefs, novel layout requests)
**Verify:** After completing all 11.24.x subtasks:
- `make eval-analysis` shows ≥97% overall pass rate
- Per-agent minimums: no agent below 90%
- `mso_conditionals` ≥99% (from 0% — guaranteed by golden templates)
- `accessibility` ≥95% (from 8% — alt text + heading decisions are structured)
- `html_preservation` ≥99% (from 10% — assembler preserves template structure)
- Token usage per blueprint run: ≤ 8,000 tokens (from ~15,000-30,000 with self-correction loops)
- Latency per blueprint run: ≤ 10s (from ~30-60s with retry loops)

### 11.23 Inline Eval Judges — Selective LLM Judge on Recovery Retries
**What:** Wire eval judges (`JUDGE_REGISTRY`) into the blueprint engine as an inline quality signal, but ONLY on self-correction retries (`iteration > 0`). First-attempt agents rely on the fast QA gate (0 tokens, <200ms). When an agent has already failed QA and is retrying, invoke the LLM judge for that agent to get a nuanced verdict before deciding whether to retry again or escalate to human review.
**Why:** The 10-point QA gate catches structural issues but misses semantic quality (brief fidelity, tone accuracy, colour coherence). Eval judges check 5 nuanced criteria per agent but cost ~3,200 tokens per call. Running judges on every handoff is cost-prohibitive (+67% per run). Running them only on retries bounds the cost (max 2 retries × 1 judge = 6,400 extra tokens) and targets the moment where the signal is most valuable — the agent already failed once and extra context prevents wasted retry loops. After 11.22 (template-first), retries are rare (~5% of runs), making the cost negligible.
**Implementation:**
- Create `app/ai/blueprints/inline_judge.py` — adapter between `JUDGE_REGISTRY` judges and `NodeContext`. Builds `JudgeInput` from live context (brief, HTML output, QA failures, handoff history). Calls judge via provider registry with `temperature=0.0` and `AI__MODEL_LIGHTWEIGHT` tier.
- Update `app/ai/blueprints/engine.py` — after agentic node execution when `iteration > 0` and `self._judge_enabled`, call `run_inline_judge()`. If `verdict.overall_pass` is False, set `run.status = "needs_review"` and break (don't retry again). If True, proceed to QA gate normally.
- Add `judge_verdict: JudgeVerdict | None` field to `BlueprintRun` dataclass in `protocols.py`
- Expose `judge_verdict` in `BlueprintRunResponse` schema (criterion results + reasoning visible in API)
- Engine config: `judge_on_retry: bool` (default `False`, opt-in per blueprint definition)
- Use lightweight model to keep cost low (~1,500 tokens with Haiku-tier vs ~3,200 with Sonnet)
**Security:** Judge prompts contain only generated HTML + brief (already in agent context). No new user input paths. Judge response parsed as structured JSON, validated against `JudgeVerdict` schema.
**Verify:** Blueprint test with intentionally flawed HTML: first attempt → QA fail → recovery → fixer retry triggers judge → judge verdict surfaces in API response. Compare: run with judge enabled escalates bad retries faster (fewer wasted loops) vs run without judge retries blindly. Cost delta measurable via `run.model_usage`.

### 11.24 Production Trace Sampling for Offline Judge Feedback Loop
**What:** Sample a configurable percentage of successful production blueprint runs and judge them asynchronously in a background worker. Results feed back into `traces/analysis.json`, which `failure_warnings.py` reads to inject updated failure patterns into agent system prompts. This closes the eval feedback loop — agents continuously learn from production data, not just synthetic test cases.
**Why:** Current eval data is synthetic (12-14 cases per agent). Real production briefs have different distributions of complexity, client requirements, and edge cases. Without production sampling, `failure_warnings.py` only reflects synthetic test failures. With sampling, agents get warnings based on actual production quality — the feedback loop becomes self-improving.
**Implementation:**
- Create `app/ai/agents/evals/production_sampler.py`:
  - `enqueue_for_judging(trace: BlueprintTrace, sample_rate: float)` — probabilistic Redis enqueue
  - `ProductionJudgeWorker` — pulls from Redis queue, runs agent-specific judge, appends verdict to `traces/production_verdicts.jsonl`
  - `refresh_analysis()` — merges production verdicts with synthetic verdicts, regenerates `traces/analysis.json`
- Update `app/ai/blueprints/engine.py` — on successful blueprint completion, call `enqueue_for_judging()` with configured sample rate
- Add config: `EVAL__PRODUCTION_SAMPLE_RATE` (default `0.0` — disabled until opted in), `EVAL__PRODUCTION_QUEUE_KEY` (Redis key)
- Update `app/ai/agents/evals/failure_warnings.py` — read from merged analysis (production + synthetic)
- Add `make eval-refresh` command to manually trigger analysis refresh from production verdicts
- Worker runs via `DataPoller` pattern (same as `MemoryCompactionPoller`, `CanIEmailSyncPoller`)
**Security:** Production traces contain generated HTML + briefs (no raw user credentials). Sampling rate configurable to control LLM cost. Redis queue uses same auth as existing Redis config. Verdicts stored locally in `traces/` (not exposed via API).
**Verify:** Set sample rate to 1.0 (100%) in test. Run 5 blueprints → verify 5 traces enqueued → worker processes all 5 → `production_verdicts.jsonl` has 5 entries → `refresh_analysis()` produces updated `analysis.json` with production data merged. Agent prompt includes warnings derived from production failures.

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

---

## Phase 12 — Design-to-Email Import Pipeline

**What:** Pull actual design files from Figma, convert them to editable Maizzle email templates via AI-assisted conversion, extract components, and import images — all through the Hub UI. Extends the existing `design_sync` module beyond token extraction.
**Approach:** AI-assisted conversion — extract layout structure + images from Figma, generate a structured brief, feed to the Scaffolder agent to produce Maizzle HTML. User can review/edit the brief before conversion.
**Scope:** Figma only (real API). Sketch/Canva stubs remain unchanged.
**Dependencies:** Phase 2 (Scaffolder agent), Phase 4.3 (design_sync module), Phase 0.3 (SDK).

### 12.1 Extend Protocol & Figma API Integration
**What:** Add 3 new methods to `DesignSyncProvider` protocol + implement in Figma provider. New dataclasses: `DesignNode`, `DesignFileStructure`, `DesignComponent`, `ExportedImage`.
**Files:** `app/design_sync/protocol.py`, `app/design_sync/figma/service.py`, `app/design_sync/sketch/service.py`, `app/design_sync/canva/service.py`
**Implementation:**
- `get_file_structure(file_ref, access_token)` → parse Figma `GET /v1/files/{key}` into `DesignNode` tree
- `list_components(file_ref, access_token)` → `GET /v1/files/{key}/components` → `list[DesignComponent]`
- `export_images(file_ref, access_token, node_ids, format, scale)` → `GET /v1/images/{key}` → `list[ExportedImage]` (batch max 100 IDs)
- Sketch/Canva: stub implementations returning empty results
**Security:** Uses existing Fernet-encrypted PAT storage. No new credential handling.
**Verify:** Unit test Figma JSON parsing. Stub providers return empty defaults.
- [ ] 12.1 Protocol extension + Figma API integration

### 12.2 Asset Storage Pipeline
**What:** Download images from Figma's temporary URLs (expire ~14 days), store locally, serve via authenticated endpoint.
**Files:** New `app/design_sync/assets.py`. Modify `app/core/config.py`, `app/design_sync/routes.py`.
**Implementation:**
- `DesignAssetService`: download via httpx, store at `data/design-assets/{connection_id}/{node_id}.{format}`
- Resize if >600px wide (standard email max), optional Pillow compression
- `GET /api/v1/design-sync/assets/{connection_id}/{filename}` — serve with BOLA check
- Path traversal prevention in `get_stored_path()`
- `asset_storage_path` config in `DesignSyncConfig`
**Security:** BOLA check on connection access. Path traversal guard. No directory listing.
**Verify:** Download mock URL → file stored → serve via endpoint returns correct bytes.
- [ ] 12.2 Asset storage pipeline

### 12.3 Design Import Models & Migration
**What:** Track import jobs (`DesignImport`) and their exported assets (`DesignImportAsset`).
**Files:** `app/design_sync/models.py`, `alembic/versions/`, `app/design_sync/repository.py`, `app/design_sync/schemas.py`
**Implementation:**
- `DesignImport`: id, connection_id, project_id, status (pending|extracting|converting|completed|failed), selected_node_ids (JSON), structure_json, generated_brief, template_id (FK), error_message, created_by_id
- `DesignImportAsset`: id, import_id (CASCADE), node_id, node_name, file_path, width, height, format, usage (hero|logo|icon|background|content)
- Alembic migration for both tables with indexes
- Repository CRUD: create_import, get_import, update_import_status, create_import_asset, list_import_assets
- Request/response Pydantic schemas for all new models
**Security:** FKs enforce referential integrity. BOLA via project_id.
**Verify:** Migration up/down clean. Repository CRUD unit tests pass.
- [ ] 12.3 Design import models & migration

### 12.4 Layout Analyzer & Brief Generator
**What:** Convert Figma document structure into a Scaffolder-compatible campaign brief.
**Files:** New `app/design_sync/figma/layout_analyzer.py`, `app/design_sync/brief_generator.py`
**Implementation:**
- `LayoutAnalyzer`: pure function, no I/O. Input: `DesignFileStructure` (selected nodes). Detect email sections (header, hero, content, CTA, footer) by name conventions + position. Detect column layouts from sibling frames. Extract text from TEXT nodes. Identify image placeholders. Output: `DesignLayoutDescription` with typed `EmailSection` list.
- `BriefGenerator`: transform layout + images into structured markdown brief. Image refs point to local asset URLs. Includes design token summary. User can edit before conversion.
**Security:** Pure computation. No I/O, no user input in SQL or templates.
**Verify:** Mock Figma JSON → expected section detection. Layout with 2 columns → correct brief format.
- [ ] 12.4 Layout analyzer & brief generator

### 12.5 AI-Assisted Conversion Pipeline
**What:** Wire Figma import → Scaffolder agent → Template creation. Full orchestration service.
**Files:** New `app/design_sync/import_service.py`. Modify `app/design_sync/routes.py`, `app/design_sync/schemas.py`, `app/ai/agents/scaffolder/schemas.py`, `app/ai/agents/scaffolder/prompt.py`, `app/ai/agents/scaffolder/service.py`
**Implementation:**
- `DesignImportService` orchestrator: fetch structure → export images → analyze layout → generate brief → call Scaffolder → create Template + TemplateVersion → update import status
- Status polling: frontend polls `GET /imports/{id}` until completed/failed
- `DesignContext` schema for Scaffolder: image_urls, design_tokens, source
- Scaffolder prompt enhancement: when design_context present, use image URLs as `<img src>`, apply design tokens as inline styles
- 6 new API endpoints: GET structure, GET components, POST export-images, POST imports, GET import status, PATCH import brief
**Security:** BOLA on all endpoints. Rate limit imports. Scaffolder sanitises output via nh3.
**Verify:** Mock Figma API + mock Scaffolder → import completes with template. Brief edit → re-conversion works.
- [ ] 12.5 AI-assisted conversion pipeline

### 12.6 Component Extraction
**What:** Extract Figma components → Hub `Component` + `ComponentVersion` with auto-generated HTML.
**Files:** New `app/design_sync/component_extractor.py`. Modify `app/design_sync/routes.py`, `app/design_sync/schemas.py`
**Implementation:**
- `ComponentExtractor`: list components from Figma, export PNG previews, detect category (button→cta, header→header, footer→footer, hero→hero, card→content, default→general), generate mini-brief per component → Scaffolder → create Component + ComponentVersion
- Store Figma origin reference in ComponentVersion metadata JSON
- `POST /api/v1/design-sync/connections/{id}/extract-components` endpoint
**Security:** BOLA check. Component HTML sanitised via nh3.
**Verify:** Mock Figma components → Hub components created with correct categories and HTML.
- [ ] 12.6 Component extraction

### 12.7 Frontend: File Browser & Import Dialog
**What:** Tree view of Figma file structure + multi-step import wizard in the UI.
**Files:** New `design-file-browser.tsx`, `design-import-dialog.tsx`, `design-components-panel.tsx`. Modify `design-connection-card.tsx`, design-sync page, hooks, types, i18n.
**Implementation:**
- File browser: pages → frames → components tree, thumbnails, checkbox selection, node type icons
- Import dialog wizard: Select Frames → Review Brief (editable textarea) → Converting (progress) → Result (preview + "Open in Workspace")
- Component extraction panel: thumbnail previews, batch checkbox selection, progress, results link to Hub components
- Connection card: "Import Design" and "Extract Components" buttons
- Hooks: useDesignFileStructure, useDesignComponents, useExportImages, useCreateDesignImport, useDesignImport (polling), useUpdateImportBrief, useExtractComponents
- Types: DesignNode, DesignFileStructure, DesignComponent, ExportedImage, DesignImport, DesignImportAsset
- i18n keys for all new UI text
**Security:** authFetch for all API calls. No dangerouslySetInnerHTML.
**Verify:** File browser renders mock tree. Import wizard completes all steps. Component extraction shows progress.
- [ ] 12.7 Frontend file browser & import dialog

### 12.8 Design Reference in Workspace
**What:** "Design Reference" tab in workspace bottom panel showing the original Figma design alongside the editor.
**Files:** New `design-reference-panel.tsx`. Modify workspace bottom panel registration.
**Implementation:**
- Show exported Figma frame image alongside editor
- Display design tokens (colors, typography, spacing) for quick reference
- Click-to-copy hex values and font specs
- Link back to Figma file
**Security:** Images served via authenticated asset endpoint.
**Verify:** Panel shows design image + tokens. Copy-to-clipboard works.
- [ ] 12.8 Design reference in workspace

### 12.9 SDK Regeneration & Tests
**What:** Regenerate SDK for all new endpoints. Backend tests for all new modules.
**Files:** `app/design_sync/tests/` (extend + new files)
**Implementation:**
- Layout analyzer unit tests (mock Figma JSON → expected sections)
- Brief generator unit tests (structured layout → expected brief text)
- Asset service tests (download, store, serve)
- Import orchestrator tests (mock Figma API + mock scaffolder)
- Component extractor tests
- New endpoint route tests
- `make sdk` to cover all new endpoints
- Update frontend type imports
**Verify:** `make test` — all design_sync tests pass. `make types` — clean. `make lint` — clean. `make check-fe` — clean.
- [ ] 12.9 SDK regeneration & tests

---

## Phase 13 — ESP Bidirectional Sync & Mock Servers

**What:** Transform the Hub's 4 ESP connectors (Braze, SFMC, Adobe Campaign, Taxi) from export-only mock stubs into fully bidirectional sync with real API surface. Adds local mock ESP servers with pre-loaded realistic email templates, encrypted credential management, and pull/push template workflows.
**Why:** Currently connectors only export via fake IDs — no template browsing, no round-trip editing, no credential validation. This phase makes the connector pipeline usable end-to-end for demos and development.
**Dependencies:** Phase 0-3 foundation (auth, projects, templates, connectors export). Reuses Fernet encryption from `app/design_sync/crypto.py`, connection model pattern from `app/design_sync/models.py`, BOLA pattern from `app/projects/service.py`.

### 13.1 Mock ESP Server — Core Infrastructure
**What:** Create `services/mock-esp/` — a standalone FastAPI app (port 3002) with SQLite persistence, auto-seeding on startup, and per-ESP auth patterns (Bearer for Braze/Taxi, OAuth token exchange for SFMC/Adobe).
**Why:** Real ESP APIs require paid accounts and complex setup. A local mock server lets developers test the full sync workflow offline with realistic data.
**Implementation:**
- `services/mock-esp/main.py` — FastAPI app with lifespan (init DB + seed)
- `services/mock-esp/database.py` — aiosqlite manager, DDL for 4 ESP tables
- `services/mock-esp/auth.py` — per-ESP auth dependencies (Bearer validation, OAuth token issuance)
- `services/mock-esp/seed.py` — loads JSON seed data into SQLite on startup
- `services/mock-esp/Dockerfile` — python:3.12-slim, port 3002
- `services/mock-esp/requirements.txt` — fastapi, uvicorn, pydantic, aiosqlite
- `GET /health` endpoint for Docker healthcheck
**Security:** Mock server is dev-only. Auth accepts any non-empty token (Braze/Taxi) or issues mock OAuth tokens (SFMC/Adobe). No real credentials stored.
**Verify:** `uvicorn main:app --port 3002` starts clean. `GET /health` returns `{"status": "healthy"}`.

### 13.2 Mock ESP — Braze Content Blocks API
**What:** Braze API routes at `/braze/content_blocks/` — create, list, info, update, delete. Auth via Bearer token.
**Implementation:**
- `services/mock-esp/braze/routes.py` — 5 endpoints matching Braze REST API surface
- `services/mock-esp/braze/schemas.py` — ContentBlockCreate, ContentBlockResponse, etc.
**Verify:** `curl -H "Authorization: Bearer test" http://localhost:3002/braze/content_blocks/list` returns seeded templates.

### 13.3 Mock ESP — SFMC Content Builder API
**What:** SFMC API routes — OAuth token exchange at `/sfmc/v2/token`, CRUD at `/sfmc/asset/v1/content/assets`. Auth via client_credentials flow.
**Implementation:**
- `services/mock-esp/sfmc/routes.py` — token endpoint + 5 CRUD endpoints
- `services/mock-esp/sfmc/schemas.py` — TokenRequest, AssetResponse, etc.
**Verify:** Token exchange returns access_token. CRUD with Bearer works.

### 13.4 Mock ESP — Adobe Campaign Delivery API
**What:** Adobe API routes — IMS token at `/adobe/ims/token/v3`, CRUD at `/adobe/profileAndServicesExt/delivery`. Auth via IMS OAuth.
**Implementation:**
- `services/mock-esp/adobe/routes.py` — IMS token + 5 CRUD endpoints
- `services/mock-esp/adobe/schemas.py` — IMSTokenRequest, DeliveryResponse, etc.
**Verify:** IMS token exchange works. Delivery CRUD with Bearer works.

### 13.5 Mock ESP — Taxi for Email API
**What:** Taxi API routes at `/taxi/api/v1/templates` — standard REST CRUD. Auth via `X-API-Key` header.
**Implementation:**
- `services/mock-esp/taxi/routes.py` — 5 REST endpoints
- `services/mock-esp/taxi/schemas.py` — TemplateCreate, TemplateResponse, etc.
**Verify:** `curl -H "X-API-Key: test" http://localhost:3002/taxi/api/v1/templates` returns seeded templates.

### 13.6 Mock ESP — Seed Data (44 Templates)
**What:** Pre-loaded realistic email templates with ESP-specific personalization tags — 12 Braze (Liquid), 12 SFMC (AMPscript), 10 Adobe (expressions), 10 Taxi (Taxi Syntax). Full HTML with DOCTYPE, dark mode, MSO conditionals, fluid hybrid 600px layout.
**Implementation:**
- `services/mock-esp/seed/braze.json` — 12 templates with `{{first_name}}`, `{% if %}`, `{{content_blocks.${}}}` etc.
- `services/mock-esp/seed/sfmc.json` — 12 templates with `%%=v(@firstName)=%%`, `%%[SET ...]%%` etc.
- `services/mock-esp/seed/adobe.json` — 10 templates with `<%= recipient.firstName %>` etc.
- `services/mock-esp/seed/taxi.json` — 10 templates with `<!-- taxi:editable -->` regions
**Verify:** After startup, each ESP table has its full seed data. Templates render correctly in a browser.

### 13.7 Backend — ESP Sync Protocol, Model & Migration
**What:** New `ESPSyncProvider` Protocol, `ESPConnection` model, Pydantic schemas, repository, and Alembic migration for the `esp_connections` table. Reuses Fernet encryption from design_sync and BOLA pattern from projects.
**Implementation:**
- `app/connectors/sync_protocol.py` — `ESPSyncProvider` Protocol (runtime_checkable) with 6 methods: validate_credentials, list/get/create/update/delete templates
- `app/connectors/sync_schemas.py` — `ESPTemplate`, `ESPTemplateList`, `ESPConnectionCreate`, `ESPConnectionResponse`, `ESPImportRequest`, `ESPPushRequest`
- `app/connectors/sync_models.py` — `ESPConnection(Base, TimestampMixin)` with encrypted_credentials, project FK, status tracking
- `app/connectors/sync_repository.py` — `ESPSyncRepository` with BOLA-safe list (user-owned + accessible projects)
- `app/connectors/sync_config.py` — `ESPSyncConfig` with per-ESP base URLs (default to mock-esp:3002)
- `app/connectors/exceptions.py` — add `ESPConnectionNotFoundError`, `ESPSyncFailedError`, `InvalidESPCredentialsError`
- `app/core/config.py` — add `esp_sync: ESPSyncConfig` to Settings
- `alembic/versions/d8e9f0a1b2c3_add_esp_connections.py` — migration
- `alembic/env.py` — import sync_models
**Security:** Credentials encrypted at rest via Fernet (same PBKDF2 key as design_sync). Only `credentials_hint` (last 4 chars) exposed in responses. BOLA via `verify_project_access()`.
**Verify:** `make db-migrate` applies cleanly. `ESPConnection` CRUD works in tests. Protocol type-checks with mypy.

### 13.8 Backend — Per-ESP Sync Providers
**What:** Four sync provider implementations — one per ESP — each using `httpx.AsyncClient` to call the mock (or real) ESP API. Implements `ESPSyncProvider` Protocol.
**Implementation:**
- `app/connectors/braze/sync_provider.py` — `BrazeSyncProvider` (Bearer auth, Content Blocks API)
- `app/connectors/sfmc/sync_provider.py` — `SFMCSyncProvider` (OAuth token exchange + Asset API)
- `app/connectors/adobe/sync_provider.py` — `AdobeSyncProvider` (IMS OAuth + Delivery API)
- `app/connectors/taxi/sync_provider.py` — `TaxiSyncProvider` (X-API-Key + Templates API)
- Provider registry dict in sync service (Step 13.9)
**Security:** Credentials decrypted in-memory only for API calls, never logged. httpx timeout enforced (10-30s).
**Verify:** Each provider conforms to `ESPSyncProvider` Protocol (isinstance check). Integration test with mock-esp server.

### 13.9 Backend — Sync Service & Routes
**What:** `ConnectorSyncService` orchestrating connections and template operations, plus REST API routes at `/api/v1/connectors/sync/`.
**Implementation:**
- `app/connectors/sync_service.py` — `ConnectorSyncService(db)` with:
  - `create_connection()` — validate via provider, encrypt creds, save
  - `list_connections()` — BOLA-scoped via accessible project IDs
  - `delete_connection()` — BOLA check
  - `list_remote_templates()` / `get_remote_template()` — decrypt creds, call provider
  - `import_template()` — pull from ESP, create local template via `TemplateService`
  - `push_template()` — read local template, push to ESP via provider
- `app/connectors/sync_routes.py` — Router at `/api/v1/connectors/sync` with 8 endpoints:
  - `POST /connections` (developer, 10/min) — create connection
  - `GET /connections` (viewer, 30/min) — list connections
  - `GET /connections/{id}` (viewer, 30/min) — get connection
  - `DELETE /connections/{id}` (developer, 10/min) — delete connection
  - `GET /connections/{id}/templates` (developer, 20/min) — list remote templates
  - `GET /connections/{id}/templates/{template_id}` (developer, 20/min) — get remote template
  - `POST /connections/{id}/import` (developer, 10/min) — import remote → local
  - `POST /connections/{id}/push` (developer, 10/min) — push local → remote
- `app/main.py` — register sync_routes router
**Security:** All endpoints authenticated + role-checked. BOLA on every operation. Rate limited. Credentials never in responses.
**Verify:** Full connection lifecycle: create → list → browse remote → import → push. BOLA denies cross-project access.

### 13.10 Frontend — ESP Sync UI
**What:** Frontend components for managing ESP connections, browsing remote templates, and import/push workflows. Adds tabs to the existing connectors page.
**Implementation:**
- `cms/apps/web/src/hooks/use-esp-connections.ts` — SWR hooks for connection CRUD
- `cms/apps/web/src/hooks/use-esp-templates.ts` — SWR hooks for remote template list/get
- `cms/apps/web/src/components/connectors/esp-connection-card.tsx` — status, provider icon, last synced
- `cms/apps/web/src/components/connectors/create-esp-connection-dialog.tsx` — provider-specific credential fields
- `cms/apps/web/src/components/connectors/esp-template-browser.tsx` — template list with search, import button
- `cms/apps/web/src/components/connectors/esp-template-preview-dialog.tsx` — HTML preview + import/push
- Modify `connectors/page.tsx` — add 3 tabs: Export History | ESP Connections | Remote Templates
- `cms/apps/web/messages/en.json` — i18n keys for espSync namespace
**Security:** All API calls via `authFetch`. No credentials displayed beyond hint. Token stored server-side only.
**Verify:** Create connection → browse remote templates → import one → verify in local templates. Push local template back → verify in mock ESP.

### 13.11 Tests, SDK & Docker Integration
**What:** Backend tests, SDK regeneration, Docker compose integration, and Makefile target.
**Implementation:**
- `app/connectors/tests/test_sync_service.py` — connection CRUD, encryption, template ops, BOLA, errors
- `app/connectors/tests/test_sync_protocol.py` — Protocol conformance for all 4 providers
- `app/connectors/tests/test_sync_routes.py` — route-level tests with auth/rate-limit
- `docker-compose.yml` — add `mock-esp` service (port 3002, healthcheck, resource limits)
- `Makefile` — add `dev-mock-esp` target
- SDK regeneration (`make sdk`) to include new sync endpoints
**Verify:** `make check` passes (lint + types + tests + security). `docker compose up` starts mock-esp healthy. SDK includes sync types.
