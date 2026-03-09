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

### ~~4.3 Figma Design Sync (Frontend Demo)~~ DONE
**Plan ref:** Section 4 (Design Tool Integration), `.agents/plans/figma-design-sync.md`
**What:** Dedicated `/figma` page for managing Figma file connections and extracting design tokens. Connection card grid with status badges (connected/syncing/error/disconnected), sync and delete actions, design token preview (colors grid, typography list, spacing bars). Connect Figma dialog with name, file URL, access token, and project selector. Optional Figma URL field added to Create Project dialog with auto-connection on submit. Full demo mode data layer (3 connections, 1 token set with 10 colors, 7 typography styles, 7 spacing values).
**Frontend:** `/figma` page with `FigmaConnectionCard`, `FigmaStatusBadge`, `FigmaDesignTokensView`, `ConnectFigmaDialog` components; 6 SWR hooks in `use-figma.ts`; `types/figma.ts` local types; demo data in `lib/demo/data/figma.ts`; demo resolver + mutation-resolver routes; Figma sidebar nav icon; middleware RBAC (all roles); ~45 i18n keys in `figma` namespace; optional Figma URL field in `CreateProjectDialog`; loading skeleton; all semantic Tailwind tokens.
**Remaining:** Real Figma REST API integration, change webhook handling, plugin ecosystem (Emailify, Email Love, MigmaAI) — deferred to backend implementation phase.
**Verify:** `/figma` page loads with 3 demo connections. Connect dialog creates new connection. Clicking connected card shows design tokens. Sync/delete actions work. Create Project dialog has optional Figma URL field. `pnpm build` passes.

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

**Step 3 — Cognee Integration + Ontology + Seeding (8.1 + 8.6 + 8.2)**
Install Cognee, define the full email ontology, seed the knowledge graph. This runs in parallel with Step 2 (independent work streams).

**Step 4 — Graph Context Provider + SKILL.md Files (8.3 + 8.5)**
Wire graph search into blueprint nodes. ~~Author initial SKILL.md files for the 3 existing agents.~~ DONE for Scaffolder + Dark Mode (Step 2.6). Content agent SKILL.md pending. Re-run evals to measure improvement vs Step 0 baseline.

~~**Step 5 — Build Remaining 6 Agents WITH Phase 7+8 Patterns (Task 4.1)**~~ DONE (Outlook Fixer, Accessibility Auditor, Personalisation, Code Reviewer, Knowledge, Innovation — all complete)
Each new agent inherits handoff/confidence/context/graph/SKILL.md infrastructure from day one. No retrofitting needed.

**Step 6 — Outcome Logging + Eval-Informed Prompts (8.4 + 7.2)**
Requires real runs and real failure data. Feed blueprint outcomes into graph. Generate prompt fragments from failure clusters. Close the learning loop.

### ~~7.1 Structured Inter-Agent Handoff Schemas~~ DONE (extended 2026-03-09)
**What:** Define typed handoff contracts between agents in blueprint pipelines. Currently agents chain via raw HTML output. Instead, each agent should emit a structured handoff object containing: the output artifact, metadata about decisions made (e.g., "used 2-column layout", "applied VML fallback for hero"), warnings/caveats, and context the next agent needs.
**Why:** Dark Mode agent receiving raw HTML from Scaffolder doesn't know which design patterns were used, which components were pulled in, or what trade-offs were made. Structured handoffs eliminate "undoing each other's work."
**Implementation:** `AgentHandoff` frozen dataclass in `app/ai/blueprints/protocols.py` with `artifact`, `decisions`, `warnings`, `component_refs`, `confidence` fields. Blueprint engine passes handoff objects between nodes. **Extended:** Full handoff history accumulates in `BlueprintRun._handoff_history` — all nodes see every prior node's decisions via `context.metadata["handoff_history"]`. Auto-persisted to episodic memory via `handoff_memory.py` bridge (`on_handoff` callback). API response includes `handoff_history: list[HandoffSummary]`.
**Retrofit:** Updated Scaffolder, Dark Mode to emit `AgentHandoff`. RecoveryRouterNode reads upstream warnings.
**Security:** Handoff objects scoped to blueprint session. No cross-project leakage. Decisions logged to audit trail. Memory persistence failure-safe (callback errors logged, never crash pipeline).
**Verify:** Blueprint pipeline passes structured handoff between scaffolder → dark_mode nodes. Full history available to all downstream nodes. Handoffs auto-persisted to memory. 8 unit tests (4 original + 4 history/callback tests).

### 7.2 Eval-Informed Agent Prompts ⏳ (unblocked — real failure data available)
**What:** Feed common failure patterns from eval error analysis (`make eval-analysis`) back into agent system prompts automatically. When eval clusters show recurring failures (e.g., "Scaffolder consistently misses MSO conditionals for 3-column layouts"), inject those as explicit warnings in the agent's prompt.
**Why:** Eval system already captures failure clusters in `error_analysis.py`. Currently this data sits in JSONL files — it should actively improve agent performance in a feedback loop.
**Prerequisite:** ~~Requires real eval traces from Phase 5.4-5.8 live execution.~~ DONE — baseline established 2026-03-09 with real failure patterns available in `traces/analysis.json`.
**Implementation:** `failure_warnings.py` in `app/ai/agents/evals/` that reads latest error analysis, extracts top-N failure patterns per agent, and generates prompt fragments. Agent system prompts load these at runtime via the existing skill/context loading pattern.
**Security:** Failure patterns contain no user data (only aggregated error categories). Prompt fragments reviewed before deployment.
**Verify:** After running `make eval-analysis`, agent prompt includes failure-specific warnings. Re-running evals shows improved pass rate on previously-failing dimensions.

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

### 7.6 DCG-Based Lightweight Cross-Agent Memory (Research — 2026-03-06)
**Plan ref:** PRD Section 4.9.7 (DCG Agent Memory), `destructive_command_guard/docs/prd-agent-memory-sharing.md`
**What:** Add 2 MCP tools (`store_note`, `recall_notes`) to the existing dcg MCP server, enabling agents to share project-scoped observations via append-only JSONL files. Zero new dependencies, ~150 lines of Rust.
**Why:** dcg already sits in the critical path of every agent's command execution and auto-detects which agent is calling. The history DB already stores per-agent evaluation data. Exposing a lightweight key/value note layer via MCP gives agents cross-agent memory with no infrastructure cost — complementing the Hub's full pgvector memory system (7.5) at the shell/tool layer.
**Dependencies:** None. Uses existing dcg MCP server, agent detection, and JSONL I/O.
**Implementation:**

#### Phase 1 — Core (MVP, ~2-3 hours)
- [ ] Add `AgentNote` struct to `destructive_command_guard/src/mcp.rs` (timestamp, agent, key, value, project)
- [ ] Implement `store_note()` — append to `.dcg/agent_notes.jsonl` with auto-detected agent identity
- [ ] Implement `recall_notes()` — read + filter from JSONL (by key, agent, project; limit 50)
- [ ] Register both tools in `handle_list_tools_request` and `handle_call_tool_request`
- [ ] Enforce size limits (1024 char value, 500 notes max per project, 128 char key)
- [ ] Key namespace convention: `project.*`, `safety.*`, `workflow.*`, `config.*`
- [ ] Unit tests for store/recall round-trip
- [ ] MCP integration test (store from "agent A", recall from "agent B")

#### Phase 2 — CLI
- [ ] Add `dcg memory list` subcommand (pretty + JSON output)
- [ ] Add `dcg memory clear` subcommand (with `--older-than`, `--agent`, `--key` filters)
- [ ] Document in dcg `docs/agents.md`

#### Phase 3 — Cross-Agent Intelligence (Future)
- [ ] Expose existing history DB via `query_history` MCP tool (agents query each other's past evaluations)
- [ ] Recommendation engine: "Agent X blocked N times on pattern Y" -> proactive warnings to other agents
- [ ] Bridge to Hub memory: dcg notes that exceed confidence/frequency thresholds auto-promoted to Hub's pgvector memory (4.9.3)

**Security:** Notes are project-local (no cross-project leakage). Agent identity auto-detected (not self-reported). `.dcg/` gitignored. `dcg memory clear` provides developer control.
**Verify:** Agent A stores a note. Agent B recalls it via MCP. `dcg memory list` shows the note. Store/recall latency < 5ms.

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

### 8.2 Knowledge Graph Seeding
**What:** Run existing knowledge base documents through Cognee's ECL pipeline (`add()` -> `cognify()`) to extract entities and relationships into a knowledge graph.
**Why:** Transforms static document chunks into interconnected knowledge. "Gmail clips at 102KB" becomes a queryable entity linked to "file_size_check" and "Gmail" with relationship "clips_above_threshold."
**Implementation:**
- Extend `make seed-knowledge` to also run Cognee pipeline after existing chunking/embedding
- Seed manifest (`app/knowledge/data/seed_manifest.py`) unchanged — same source documents, additional processing path
- Initial entity types: EmailClient, CSSProperty, RenderingEngine, Component, Workaround, Limitation
**Security:** Same documents, additional index. No new data surface.
**Verify:** After seeding, graph contains extracted entities from Can I Email data. Query "What does Outlook 2019 not support?" returns structured graph traversal results.

### 8.3 Graph Context Provider for Blueprint Nodes
**What:** Add graph-aware context retrieval to the blueprint engine's `_build_node_context()`. Before an agent generates output, query Cognee for structured relationships relevant to the task.
**Why:** This is the highest-impact integration. Instead of "here are 5 similar chunks about dark mode," agents get: *"Apple Mail supports prefers-color-scheme -> use media query. Outlook ignores it -> use MSO conditional fallback. Gmail Android partially supports -> test with persona."*
**Implementation:**
- New context source in `app/ai/blueprints/engine.py::_build_node_context()`
- Uses Cognee's `GRAPH_COMPLETION` or `TRIPLET_COMPLETION` search types
- Progressive disclosure: only fetch graph context when the task involves email client compatibility, CSS support, or component interactions
- Results formatted as structured triplets injected into agent system prompt
**Security:** Graph queries scoped to project. Query content logged. No PII in graph (email dev knowledge only).
**Verify:** Scaffolder agent generating a 3-column layout receives structured compatibility data for target email clients. Dark Mode agent receives known workarounds for components in the template.

### 8.4 Blueprint Outcome Logging
**What:** After a blueprint run completes, feed the outcome (which agents ran, what they produced, QA results, recovery actions taken) back into Cognee via `cognee.add()`.
**Why:** Builds institutional memory. After 50 blueprint runs, agents can query: "What fixes have worked when QA fails for VML backgrounds in Outlook?" — answered from real outcomes, not LLM guessing.
**Implementation:**
- Post-run hook in `BlueprintEngine` that serialises `BlueprintRun` outcome to text
- Feeds through Cognee pipeline to extract patterns (successful fixes, common failure modes, recovery paths)
- Tagged with project scope and agent types involved
**Security:** Outcomes contain generated HTML patterns, not client content. Project-scoped. Temporal decay applies (Section 5.6 Layer 5).
**Verify:** After 10+ blueprint runs, querying "common Scaffolder failures" returns aggregated patterns from actual runs.

### 8.5 Per-Agent Domain SKILL.md Files
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

### 8.6 Email Development Ontology (Full Granularity)
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

### 9.1 Graph-Powered Client Audience Profiles
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

### 9.2 Can I Email Live Sync
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

### 9.3 Component-to-Graph Bidirectional Linking
**What:** When a component is created, updated, or tested in `app/components/`, automatically create/update its entity in the knowledge graph with: supported email clients (from QA test results), known quirks (from QA failures), dark mode variant status, and rendering engine compatibility. Reverse direction: graph insights surface as component metadata in the component browser UI.
**Why:** Component metadata is currently static (version, description). The graph can enrich this with real test data — "this CTA component passed QA in 18/20 clients, fails in Outlook 2016 VML and Samsung Mail 14." Agents using components get real compatibility data, not just static descriptions.
**Implementation:**
- Post-save hook on `ComponentVersion` model → creates/updates graph entity via Cognee
- QA results from `app/qa_engine/` feed into component's graph node as test relationships
- Component browser UI (`/components`) shows graph-derived compatibility badge (green/amber/red per client)
- Graph query from component entity returns: tested clients, pass/fail status, known workarounds, dark mode variant availability
- Bidirectional: component detail page pulls live graph data; graph entity links back to component version
**Security:** Component data is project-scoped. Graph entities inherit project scope. QA results are non-sensitive.
**Verify:** Creating a component and running QA creates a graph entity with test results. Component browser shows compatibility badge. Agent using the component receives graph-derived quirk warnings.

### 9.4 Failure Pattern Propagation Across Agents
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

### 9.5 Client-Specific Subgraphs for Project Onboarding
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

### 9.6 Graph-Informed Blueprint Route Selection
**What:** Blueprint engine dynamically adjusts node sequence based on graph data about the target audience and template content. Skip unnecessary nodes, add required ones, reorder for efficiency.
**Why:** Currently blueprints follow a fixed sequence (scaffolder → dark_mode → QA → export). But if the target audience is 100% Apple Mail (internal corporate comms), the Outlook Fixer node is wasted work. If the template uses AMP components, an AMP validation node should be added. Graph-informed routing makes blueprints adaptive.
**Implementation:**
- `app/ai/blueprints/route_advisor.py` — analyses template content + project subgraph (9.5) to recommend node sequence
- Rules engine based on graph traversal:
  - Skip Outlook Fixer if no Microsoft clients in project personas
  - Skip Dark Mode node if no dark-mode-capable clients in audience
  - Add AMP validation node if template contains AMP components
  - Prioritise nodes based on audience coverage (most common client issues first)
- Route advisor runs before blueprint execution, proposes modified sequence
- Blueprint engine accepts or overrides (developer can force full pipeline)
- Routing decisions logged in audit trail with reasoning
**Security:** Route decisions based on project-scoped graph data. No new access surface. Audit trail captures routing rationale.
**Verify:** Blueprint for Apple Mail-only project skips Outlook nodes. Blueprint for template with AMP adds AMP validation. Routing decisions visible in blueprint run log with graph-backed reasoning.

### 9.7 Competitive Intelligence Graph
**What:** Extend the ontology to include competitor capabilities (Stripo, Parcel, Chamaileon, Dyspatch, Knak — from Plan Section 15.4). When the Innovation Agent evaluates new techniques, it checks the graph for feasibility and competitive landscape.
**Why:** Section 15.4 maps competitor features. This data in the graph lets the Innovation Agent answer: "Is this technique feasible for the client's audience AND do competitors support it?" Powers the capability reports mentioned in Section 12.2 with structured data instead of manual research.
**Implementation:**
- Extend ontology (8.6) with `Competitor` entity type and relationships: `supports_feature`, `pricing_tier`, `target_market`
- Competitor data seeded from Plan Section 15.4 table + periodic manual updates
- Relationships to email capabilities: `Stripo → supports → AMP_email`, `Parcel → supports → dark_mode_preview`
- Innovation Agent queries: "techniques the Hub supports that competitors don't" and "techniques competitors support that the Hub should add"
- Capability report generation: structured graph query → formatted report showing Hub vs competitor feature matrix with audience feasibility data
**Security:** Competitor data is public knowledge (pricing pages, feature lists). No proprietary intelligence. Clearly marked as external data in graph.
**Verify:** Innovation Agent asked "what techniques can we offer that Stripo can't?" returns graph-backed answer with audience feasibility. Capability report includes competitive positioning data.

### 9.8 SKILL.md A/B Testing via Eval System
**What:** When the skill growth system (8.5) proposes a SKILL.md update, automatically A/B test it against the current version using the eval suite. Only merge if the updated skill performs equal or better.
**Why:** Skill growth proposals are currently review-only (dev reads the diff and decides). A/B testing adds empirical evidence: run the eval suite with current SKILL.md, then with proposed update, compare pass rates. This closes the loop: knowledge graph → skill proposal → eval validation → merge.
**Implementation:**
- `app/ai/agents/evals/skill_ab.py` — A/B test runner
- Takes: current SKILL.md, proposed SKILL.md, agent name, eval suite
- Runs eval suite twice (current vs proposed) on same synthetic test data
- Computes per-criterion pass rate delta, overall improvement, and statistical significance (minimum 10 cases per dimension)
- Output: comparison report with recommendation (merge / reject / needs more data)
- Integrates with `make eval-skill-test` CLI command
- Proposed updates that degrade any criterion by >5% auto-rejected with explanation
**Security:** A/B tests run on synthetic test data (no client data). Results logged for audit. Rejected proposals archived with reasoning.
**Verify:** Proposed SKILL.md update runs through A/B test. Report shows per-criterion comparison. Update that improves 3 criteria and degrades none is recommended for merge. Update that degrades 1 criterion by >5% is auto-rejected.

---

## Autoresearch-Inspired Patterns

Techniques adapted from the autoresearch autonomous experiment framework. These patterns apply autoresearch's iterative modify→run→measure→keep/revert loop to agent and blueprint quality optimization.

> Source: autoresearch repo analysis (2026-03-09). Cross-referenced with merkle-email-hub architecture.

### Pattern 1: Autonomous Agent Eval Loop
- [ ] **Automated Eval Loop for Blueprint Pass Rate** — Implement autoresearch-style modify→run→measure→keep/revert cycle for agent prompt optimization. Use existing 36 eval traces + QA gate as the scoring mechanism. After each prompt/config change: run scaffolder/dark-mode/content agents against the same briefs, score via QA gate (deterministic) + LLM judge (subjective quality), record in `eval_results.tsv`. Collapse 10 QA checks into a single "QA pass rate" aggregate for the keep/revert decision. Keep changes that improve pass rate, revert those that don't. Target: move from 16.7% baseline pass rate upward through automated overnight sweeps.

### Pattern 4: Git-Based Experiment Tracking
- [ ] **Prompt Version Control + Eval Ledger** — Extract all agent prompts from per-agent Python files into version-controlled markdown (e.g., `prompts/scaffolder.md`, `prompts/dark_mode.md`, `prompts/content.md`). Each prompt tweak = a commit on an `experiments/<tag>` branch. Eval results appended to `eval_results.tsv` (columns: experiment_id, commit_hash, timestamp, qa_pass_rate, scaffolder_score, dark_mode_score, content_score, token_usage). Automated revert on regression. Gives reproducible prompt optimization history — currently no way to know what was tried before or why a prompt looks the way it does.

### Pattern 5: Per-Client Agent Steering Briefs
- [ ] **`program.md`-Style Client Briefs** — Create a human-editable `client_brief.md` per client/project that steers all 9 agents without code changes. Account managers (not developers) define constraints like: "this client requires dark backgrounds, never use white", "always include legal footer with unsubscribe link", "tone: corporate formal", "Outlook 2016 is primary target — table-based layouts only", "brand palette: #1B365D, #F2C94C, #FFFFFF only". Brief is injected into every agent's prompt via `NodeContext.metadata`. Changes take effect without deploys.

### Pattern 6: Constrained Modification Surface for Agent Retries
- [ ] **Scoped Self-Correction Constraints** — When agents retry after QA failure, constrain what they can modify (autoresearch only allows changes to `train.py`, not `prepare.py`). Scaffolder retry: can only modify HTML structure, not inject new CSS frameworks or dependencies. Dark mode retry: can only modify CSS (`<style>` blocks and inline styles), not restructure HTML layout. Content retry: can only change text nodes and attributes (`alt`, `title`, `aria-label`), not layout or styling. Outlook fixer retry: can only add MSO conditionals and VML, not remove existing HTML. Implement via prompt constraints injected on retry + output diff validation (reject changes outside allowed scope). Prevents cascading failures where a retry introduces new problems that trigger further QA failures.

---

## Infrastructure Best Practices (from LMCache Research)

Patterns identified from LMCache (distributed KV cache engine for LLM serving). These are infrastructure-level improvements that can be retrofitted without modifying existing agents or the blueprint engine.

> Source: LMCache repo analysis (2026-03-09). Cross-referenced with merkle-email-hub architecture.

### Quick Wins (Low Effort, High Impact)
- [ ] **Recoverable vs Irrecoverable Exception Hierarchy** — Add `IrrecoverableError` to exception hierarchy alongside existing `AIError`/`BlueprintError`. Use in WebSocket broadcaster, health monitors, and background services to distinguish "log and retry" from "shut down and alert." Blueprint engine already has bounded retries; this targets the infrastructure layer beneath it.

- [ ] **LRU Cache for QA Check Results** — Cache QA gate results keyed by content hash (LMCache uses pluggable LRU/LFU/MRU/FIFO policies via strategy pattern with `get_cache_policy()` factory). Same HTML re-checked during iterative editing produces identical scores. Avoids redundant 10-check QA runs when content hasn't changed. Also applicable to component metadata lookups.

- [ ] **SLF Ruff Enforcement** — Add `"SLF"` to ruff `select` rules in `pyproject.toml` to prevent private member access across module boundaries. Start with `app/ai/` where agent/blueprint encapsulation matters most. LMCache enforces this in distributed/multiprocess code to prevent tight coupling.

### Medium Effort
- [ ] **Background Task Registry** — Unified registry for long-running async tasks (WebSocket heartbeats, health checks, future document processing workers) with importance levels (CRITICAL/HIGH/MEDIUM/LOW). LMCache's `PeriodicThread` + `PeriodicThreadRegistry` tracks: total runs, failed runs, success rate, interruptible sleep. Expose through `/health` endpoint.

- [ ] **Event State Machine for Blueprint Tracking** — `EventManager` tracking async operations through `ONGOING → DONE` states with thread-safe futures. Blueprint executions are long-running multi-step workflows; currently tracked through state machine nodes but no unified "is build X still running? what step is it on?" query. Enables frontend polling without WebSocket.

- [ ] **Generator-Based QA Streaming** — Refactor blueprint node output to support yield-based flow through QA checks. LMCache uses `store_layer()` and `retrieve_layer()` generators for memory-efficient layerwise processing. Agent responses could stream through QA validation as they're generated rather than waiting for complete output.

- [ ] **CI Correctness Benchmarks** — Add golden test cases for each agent that must pass in CI. LMCache runs correctness benchmarks (MMLU) + K8s smoke tests post-deployment. A small set of email generation tasks with known-correct QA outcomes catches quality regressions on model/prompt changes. Complements the existing eval framework (Phase 5).

### Lower Priority
- [ ] **Deprecated Config Aliases** — Add `_DEPRECATED_CONFIGS` mapping to nested pydantic Settings for seamless env var migration when renaming. LMCache supports automatic migration paths (`_CONFIG_ALIASES`, `_DEPRECATED_CONFIGS`) so old env vars still work with deprecation warnings. Useful as the config surface grows (currently 40+ params across 11 config groups).

- [ ] **Batched API Variants** — Add batch endpoints for high-frequency operations (batch QA checks across email variants, batch component lookups). LMCache offers `batched_contains()`, `batched_submit_put_task()`, `batched_async_contains()` alongside single-item APIs.

- [ ] **Lazy Connection Pool Allocation** — Start with smaller pool sizes and expand under load. LMCache starts at 20% memory budget and expands on-demand with configurable ratios (`lazy_memory_initial_ratio: 0.2`, `expand_trigger_ratio: 0.5`, `step_ratio: 0.1`). Maizzle builder sidecar could also benefit from lazy worker scaling.

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
