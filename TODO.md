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
**Plan ref:** Section 9.2 (Dashboard), MVP #1
**What:** Dashboard page at `/[locale]/(dashboard)/page.tsx`. Project overview grid, recent activity feed, QA status summary, quick-start template selection. Data from `GET /api/v1/projects` and `GET /api/v1/orgs`.
**Security:**
- Only show projects the authenticated user has access to (RBAC-filtered on backend)
- No client org data leakage across user sessions
**Verify:** Dashboard loads. Shows only user's assigned projects. Empty state for new users.

### 1.2 Project Workspace Layout
**Plan ref:** Section 9.2 (Project Workspace), MVP #2
**What:** Split-pane workspace at `/projects/[id]/workspace`. Three resizable panels: editor (left), preview (center/right), AI chat (bottom, collapsible). Use a resizable pane library compatible with React 19.
**Security:**
- Route guard: verify user has access to project before rendering
- Project ID validated server-side (no client-side trust)
**Verify:** Three-pane layout renders. Panels resize. Collapses gracefully on mobile.

### 1.3 Monaco Editor Integration
**Plan ref:** Section 9.2 (Monaco Editor), MVP #2
**What:** Embed Monaco Editor with HTML/CSS/Liquid syntax highlighting. Add Can I Email CSS autocomplete (flag unsupported properties inline). Bracket matching, code folding, minimap, search/replace. Editor state persists per template.
**Security:**
- Editor content sanitised before sending to backend (strip script injections)
- Content-Security-Policy headers prevent execution of editor content in host page
- Editor runs in sandboxed context (no access to parent window APIs)
**Verify:** Editor loads with syntax highlighting. Can I Email warnings appear for unsupported CSS. Content persists on save.

### 1.4 Maizzle Live Preview
**Plan ref:** Section 6.3 (Build Pipeline), 9.2 (Live Preview), MVP #3
**What:** Compile-on-save via `POST /api/v1/email/preview`. Render compiled HTML in sandboxed iframe. Desktop/tablet/mobile viewport toggles. Dark mode preview toggle. Zoom controls.
**Security:**
- Preview iframe uses `sandbox="allow-same-origin"` — NO `allow-scripts`
- Preview iframe loaded via blob URL or srcdoc, never from external URL
- PostMessage communication between editor and preview must validate origin
- No user-generated content executes JavaScript in preview context
**Verify:** Type HTML in editor → compiled preview updates within 2 seconds. Viewport toggles resize iframe. Dark mode toggle works.

### 1.5 Test Persona Engine UI
**Plan ref:** Section MVP #10, 16.4
**What:** Persona selector dropdown in preview panel. Load personas from `GET /api/v1/personas`. One-click preview as: "Gmail Desktop", "iPhone Dark Mode", "Outlook 2016", etc. Visual context switching (device frame, email client chrome).
**Security:**
- Personas scoped to project (no cross-project persona leakage)
- Persona data is non-PII (device config, not subscriber data)
**Verify:** Persona selector loads presets. Preview updates to show selected device/client context.

### 1.6 Template CRUD + Persistence
**Plan ref:** Section 2.3 (Projects module), MVP #1
**What:** Save/load templates within projects. Template versioning (each save creates a version). Version history sidebar. Restore previous version capability.
**Security:**
- Template content stored encrypted at rest (PostgreSQL column encryption or transparent data encryption)
- Version history includes author + timestamp for audit
- Template access scoped to project members only
**Verify:** Create template → edit → save → reload shows saved content. Version history shows all saves. Restore works.

---

## Phase 2 — Sprint 2: Intelligence + Export (Plan: 2-3 weeks)

> **Sprint 2 Deliverable (Plan Section 16.4):** "Functional AI-assisted email development with automated QA and CMS export."

### 2.1 Wire AI Provider to LLM
**Plan ref:** Section 5.5 (AI Model Selection), 5.1 (Agent Architecture)
**What:** Register Claude (via Anthropic SDK) or OpenAI-compatible provider in `app/ai/registry.py`. Add `AI__PROVIDER`, `AI__MODEL`, `AI__API_KEY` to config. Implement model routing logic: Opus for complex, Sonnet for standard, Haiku for lightweight tasks. Verify streaming works via WebSocket.
**Security:**
- API keys stored as environment variables, NEVER in code or database
- AI request/response bodies logged WITHOUT the actual content (log token counts + model + latency only)
- Rate limit AI endpoints separately: 20 req/min per user for chat, 5 req/min for generation
- Input sanitisation: strip any PII patterns from prompts before sending to external API
- AI responses go through output validation before returning to client
**Verify:** `POST /v1/chat/completions` returns streamed response. Model routing selects correct tier. API key is not exposed in logs or errors.

### 2.2 Scaffolder Agent
**Plan ref:** Section 5.1 (Scaffolder), MVP #5
**What:** First AI agent — generates Maizzle email HTML from natural language campaign briefs. System prompt defines email constraints (table layouts, inline CSS, MSO conditionals, responsive stacking). Outputs complete Maizzle template source.
**Security:**
- Agent output goes through QA validation before being offered to user
- System prompt includes instruction to never include external URLs or script tags
- Generated HTML sanitised for XSS before rendering in preview
**Verify:** Provide brief "Create a 2-column product showcase email with dark mode support" → get valid Maizzle HTML. Preview renders correctly.

### 2.3 Dark Mode Agent
**Plan ref:** Section 5.1 (Dark Mode Agent), MVP #5
**What:** Analyses existing HTML and injects `@media (prefers-color-scheme: dark)` rules, `[data-ogsc]`/`[data-ogsb]` selectors for Outlook, transparent PNG suggestions, colour token remapping. Uses Knowledge Base for client-specific dark mode quirks.
**Security:**
- Agent only modifies CSS/style blocks, never injects script content
- Output diff shown to developer before applying (human-in-the-loop)
**Verify:** Provide email HTML without dark mode → agent returns enhanced version with dark mode CSS. Preview confirms dark mode toggle works.

### 2.4 Content Agent
**Plan ref:** Section 5.1 (Content Agent), 15.4 (Competitive Feature — new capability #1)
**What:** Generates and refines email marketing copy: subject lines, preheaders, CTA text, body copy. Supports rewrite, shorten, expand, and tone adjustment. Brand voice constraints applied per client. Integrates into Monaco editor as context menu: select text → right-click → "Refine with AI."
**Security:**
- Brand voice constraints loaded from project settings, not hardcoded
- Content suggestions never include personal data patterns
- Generated copy flagged if it matches spam trigger patterns
**Verify:** Select text in editor → right-click → "Refine with AI" → get alternatives. Subject line generation produces 5 options.

### 2.5 AI Chat Sidebar UI
**Plan ref:** Section 9.2 (AI Orchestrator panel), MVP #5
**What:** Collapsible bottom panel in workspace. Agent selection toggles (Scaffolder, Dark Mode, Content). Natural language input with streaming response display. Code block rendering in responses. Accept/reject/merge controls to apply AI output to editor. Conversation history per session.
**Security:**
- WebSocket connection authenticated via JWT (validated on connect)
- Conversation history stored per-user, per-project (no cross-user visibility)
- AI conversation logs retained 90 days maximum (Plan Section 8.3)
- Merge operation creates a new template version (audit trail)
**Verify:** Open chat → select Scaffolder → provide brief → streamed response appears → click "Apply" → code merged into editor.

### 2.6 Component Library v1 — Backend
**Plan ref:** Section MVP #4, 2.3 (Component Library module)
**What:** Seed 5-10 pre-tested Maizzle email components: header, footer, CTA button, hero block, product card, spacer, social icons, image block, text block, divider. Each with dark mode variant, Outlook fallback, version metadata, and compatibility matrix stub.
**Security:**
- Component content validated on upload (no script injection in HTML components)
- Version immutability: published versions cannot be modified, only new versions created
- Component ownership tracked (author, last modifier)
**Verify:** `GET /api/v1/components` returns 5-10 components. Each has at least one version. Dark mode variant accessible.

### 2.7 Component Library Browser UI
**Plan ref:** Section 9.2 (Component Library), MVP #4
**What:** Page at `/components`. Grid view with component preview thumbnails. Search by name, type, client scope. Component detail view: rendered preview (light + dark mode), HTML source, version history, compatibility matrix table, usage documentation.
**Security:**
- Component previews rendered in sandboxed iframes (same as live preview)
- Components scoped: Global visible to all, Client-scoped visible to project members only
**Verify:** Browse components. Search filters work. Click component → see detail view with preview + source + versions.

### 2.8 10-Point QA Gate System UI
**Plan ref:** Section 7.2 (QA Pipeline), MVP #7
**What:** QA trigger button in workspace toolbar. Runs `POST /api/v1/qa/run` with current template HTML. Results displayed as pass/fail checklist with details per check. Gate enforcement: warn/block on export if checks fail. Senior override with documented justification.
**Security:**
- QA results stored with template version (audit: which version was tested)
- Override requires admin/developer role + written justification (logged)
- Override audit entry includes who, when, why, which checks bypassed
**Verify:** Click "Run QA" → 10 checks execute → results display inline. Failing checks show detail. Override flow works with audit logging.

### 2.9 Raw HTML Export + Braze Connector UI
**Plan ref:** Section 3.1 (Connector Architecture), MVP #6
**What:** Export console at `/export` or inline in workspace. Platform selector: Raw HTML download, Braze Content Blocks push. Export preview shows what will be sent. Braze connector: configure API key (encrypted), push as Content Block with Liquid packaging.
**Security:**
- Braze API key encrypted with AES-256 before storage. Never returned in API responses. Never logged.
- Credential scope validation: verify API key has minimum required permissions before storing
- Export creates audit entry (who exported, when, where, which template version)
- Export blocked if QA gate has failures (unless overridden with justification)
**Verify:** Configure Braze credentials → export template → Content Block appears in Braze sandbox. Raw HTML download produces valid file.

### 2.10 RAG Knowledge Base Seeding
**Plan ref:** Section MVP #8, 13.3 (Data Bootstrapping)
**What:** Seed knowledge base with: Can I Email CSS support data (automated crawl), email dev best practices (curated entries), email client rendering quirks (team knowledge capture). Verify hybrid search (vector + fulltext) returns relevant results for email development queries.
**Security:**
- Knowledge entries classified: public (Can I Email), internal (best practices), confidential (client quirks)
- Client-specific quirks tagged with client_org_id (access-controlled)
- Embedding model runs on infrastructure Merkle controls (no PII sent to external embedding APIs)
**Verify:** Search "Outlook dark mode background image" → get relevant Can I Email data + rendering quirk entries. Knowledge Agent uses RAG context in responses.

---

## Phase 3 — Sprint 3: Client Handoff + Polish (Plan: 1-2 weeks)

> **Sprint 3 Deliverable (Plan Section 16.4):** "Complete MVP that clients can log into for approvals, QA data is visible, and the team has a tool they want to use daily."

### 3.1 Client Approval Portal
**Plan ref:** Section MVP #9, 9.2 (QA Dashboard approval workflow)
**What:** Approval routes at `/approvals`. Viewer role login (scoped to assigned projects only). Live email preview (read-only, sandboxed iframe). Section-level feedback annotations (click to highlight, leave comment). Global feedback textarea. Approve/request changes buttons. Version comparison (diff between current and last-reviewed version). Email/Slack notification when review is ready. Time-stamped audit trail of all approvals, changes, feedback.
**Security:**
- Viewer role: READ ONLY. Cannot edit templates, run builds, export, or access other modules
- Approval URLs use signed tokens (not guessable IDs) — expire after 30 days
- Feedback content sanitised (no script injection via comments)
- Notification emails contain no template content (link back to portal only)
- Audit trail immutable: entries can be created, never modified or deleted
- Session timeout: 30 minutes inactivity for viewer role
**Verify:** Client logs in with viewer credentials → sees only their project's emails → leaves section feedback → approves → audit trail shows complete history.

### 3.2 Rendering Intelligence Dashboard
**Plan ref:** Section MVP #11, 12.6 (Compound Innovation Effect)
**What:** Dashboard at `/qa` or `/dashboard/intelligence`. Client support matrices (which innovations work in which email clients). Template quality scores (file size, code complexity, accessibility rating). QA results visualization (pass/fail trends over time). Visual regression tracking (before/after per change).
**Security:**
- Dashboard data aggregated — no individual subscriber data ever displayed
- Export dashboard as PDF requires developer+ role
- Analytics data retention: 12 months, then aggregated
**Verify:** Dashboard shows QA trends. Support matrix populates from accumulated QA results. Template quality scores calculate correctly.

### 3.3 Dashboard Homepage Enhancement
**Plan ref:** Section 9.2 (Dashboard)
**What:** Enhance Phase 1.1 dashboard with real data: project overview grid with status indicators, recent activity feed (builds, QA runs, exports, approvals), team workload summary, QA status at a glance (pass rate), quick-start template selection (from component library).
**Security:**
- Activity feed shows only actions on user's accessible projects
- No sensitive data in activity summaries (e.g., "Template exported to Braze" not "Template exported to Braze API key ending in ...xyz")
**Verify:** Dashboard shows real project data. Activity feed updates in near-realtime. Quick-start creates new template from component.

### 3.4 Error Handling, Loading States, UI Polish
**Plan ref:** Section 16.2 (Polish + Glue)
**What:** Skeleton loaders on all data-fetching pages. Toast notifications for async operations (build started, export completed, QA passed). Proper 404/403/500 error pages. Form validation with inline errors. Optimistic updates where safe. Offline detection.
**Security:**
- Error pages never expose stack traces, internal paths, or configuration
- 403 page: "You don't have access to this resource" — no detail about what the resource is
- API errors: structured error responses with error codes, not raw exception messages
- Client-side error boundary catches React crashes gracefully
**Verify:** Navigate to invalid URL → 404 page. Access forbidden resource → 403 page. Kill backend → graceful offline state. All forms validate before submit.

### 3.5 CMS + Nginx Docker Stack
**Plan ref:** Section 16.2 (Deployment), 10 (Infrastructure)
**What:** Get `cms` container building and healthy (pnpm install + next build + standalone output). Wire nginx reverse proxy: `/` → cms (port 3000), `/api/` → app (port 8891), `/ws` → app WebSocket. SSL termination ready (cert volume mount). Full `docker compose up` with all 7 services healthy.
**Security:**
- Nginx: rate limiting (100 req/s per IP), request body size limit (10MB), header hardening (X-Frame-Options DENY, X-Content-Type-Options nosniff, Strict-Transport-Security, Referrer-Policy strict-origin-when-cross-origin)
- Nginx: block access to `.env`, `.git`, `alembic/`, `__pycache__/` paths
- All containers: non-root user, `no-new-privileges`, `cap_drop: ALL`, minimal `cap_add`
- Redis: password-protected, not exposed to host in production
- PostgreSQL: not exposed to host in production (only via Docker network)
- Health check endpoints public; all other endpoints require auth
**Verify:** `docker compose up` → all 7 services healthy. `curl localhost:80` → CMS frontend. `curl localhost:80/api/v1/health` → backend health. `curl localhost:80/.env` → 403.

---

## Phase 4 — Post-MVP (Plan Section 16.1: Post-MVP Iterations)

### 4.1 Remaining 6 AI Agents
**Plan ref:** Section 5.1 (Agent Architecture)
- **Outlook Fixer**: MSO conditionals, VML backgrounds, table-based fallbacks
- **Accessibility Auditor**: WCAG AA checks, contrast ratios, alt text, touch targets, AI alt text generation
- **Personalisation Agent**: Liquid (Braze), AMPscript (SFMC), dynamic content logic
- **Code Reviewer**: Static analysis, redundant code, unsupported CSS, file size optimisation
- **Knowledge Agent**: RAG-powered Q&A from knowledge base
- **Innovation Agent**: Prototype new techniques, assess feasibility, generate fallback strategies

### 4.2 Additional CMS Connectors
**Plan ref:** Section 3.1 (~2-3 days each)
- SFMC connector (Content Builder + AMPscript, OAuth 2.0)
- Adobe Campaign connector (Deliveries + Content fragments, Adobe IMS OAuth)
- Taxi for Email connector (Taxi Syntax wrapping, Design System export)

### 4.3 Figma Design Sync
**Plan ref:** Section 4 (Design Tool Integration)
- Figma REST API integration
- Design token extraction (colours, typography, spacing)
- Component structure mapping
- Change webhook handling
- Plugin ecosystem (Emailify, Email Love, MigmaAI)

### 4.4 Litmus / Email on Acid API Integration
**Plan ref:** Section 7.2 (Cross-Client Render)
- API integration for 20+ client rendering screenshots
- Visual regression detection
- Rendering report generation

### 4.5 Advanced Features
- Real-time collaborative editing (CRDT/OT)
- Localisation engine (100+ locales)
- Per-client brand guardrails
- AI image generation (self-hosted Stable Diffusion XL)
- Visual Liquid builder UI
- Client brief system integration (Jira, Asana, Monday.com)

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
