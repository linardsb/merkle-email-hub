# Product Requirements Document (PRD)

## Email Innovation Hub

**Classification:** Internal / Confidential
**Version:** 4.36
**Date:** 2026-03-16
**Status:** V1 Complete — Sprint 3 done (3.1-3.5); V2 tasks 4.1-4.5, 4.8-4.13 done; ALL 10 AI agents built (eval-first + skills workflow); Phase 5.1-5.8 eval system complete; Phase 6 OWASP complete; Phase 7 complete; Phase 8 Knowledge Graph COMPLETE; Phase 9 Graph-Driven Intelligence COMPLETE; Phase 10 Frontend Integration COMPLETE (10.1-10.12); Phase 11 QA Engine Hardening COMPLETE (11.1-11.25 all done — template-first architecture, inline judges, production trace sampling, eval-driven iteration, client design system & brand pipeline); Phase 12 Design-to-Email Import COMPLETE (12.1-12.9 — protocol extension, asset storage, import models, layout analyzer, AI conversion, component extraction, frontend file browser, design reference panel, SDK + tests); Phase 13 ESP Bidirectional Sync COMPLETE (13.1-13.11 — mock ESP server with 4 API surfaces, sync protocol + providers, encrypted credential management, 8 REST endpoints, frontend sync UI, 93 backend tests, SDK regen); Phase 14 Blueprint Checkpoint & Recovery COMPLETE (14.1-14.7 — checkpoint storage layer, engine save integration, resume from checkpoint, multi-pass pipeline checkpoints, cleanup & observability, frontend resume UI, 47 tests, ADR-006); Phase 15 COMPLETE (15.1-15.5 all done — typed handoff schemas + phase-aware memory decay + adaptive model tier routing + auto-surfacing prompt amendments + bidirectional knowledge graph pre-query); Phase 16 COMPLETE (16.1-16.6 all done — query router intent classification, structured compatibility queries, code-aware HTML chunking, template/component retrieval, CRAG validation loop, multi-representation indexing); Phase 17 COMPLETE (17.1-17.6 all done — Playwright CLI screenshot service with 5 client profiles, ODiff visual regression baseline system with 3 new endpoints, VLM Visual Analysis Agent — 10th AI agent with multimodal defect detection + ontology cross-referencing, auto-fix pipeline integration with LLM correction + re-render verification, frontend Visual QA Dashboard with 6 components + 3-tab dialog + 4 SWR hooks, 28 route tests + 12 judge tests + SDK regeneration; 2639 total backend tests). Next: Phase 18 (Rendering Resilience & Property-Based Testing)

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
