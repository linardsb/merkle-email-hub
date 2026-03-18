# [REDACTED] Email Innovation Hub — Implementation Roadmap

> Derived from `[REDACTED]_Email_Innovation_Hub_Plan.md` Sections 2-16
> Architecture: Security-first, development-pattern-adjustable, GDPR-compliant
> Pattern: Each task = one planning + implementation session

---

> **Completed phases (0–23):** See [docs/TODO-completed.md](docs/TODO-completed.md)
>
> Summary: Phases 0-10 (core platform, auth, projects, email engine, components, QA engine, connectors, approval, knowledge graph, full-stack integration). Phase 11 (QA hardening — 38 tasks, template-first architecture, inline judges, production trace sampling, design system pipeline). Phase 12 (Figma-to-email import — 9 tasks). Phase 13 (ESP bidirectional sync — 11 tasks, 4 providers). Phase 14 (blueprint checkpoint & recovery — 7 tasks). Phase 15 (agent communication — typed handoffs, phase-aware memory, adaptive routing, prompt amendments, knowledge prefetch). Phase 16 (domain-specific RAG — query router, structured ontology queries, HTML chunking, component retrieval, CRAG validation, multi-rep indexing). Phase 17 (visual regression agent & VLM-powered QA — Playwright rendering, ODiff baselines, VLM analysis agent #10, auto-fix pipeline, visual QA dashboard). Phase 18 (rendering resilience & property-based testing — chaos engine with 8 profiles, Hypothesis-based property testing with 10 invariants, resilience score integration, knowledge feedback loop). Phase 19 (Outlook transition advisor & email CSS compiler — Word-engine dependency analyzer, audience-aware migration planner, Lightning CSS 7-stage compiler with ontology-driven conversions). Phase 20 (Gmail AI intelligence & deliverability — Gemini summary predictor, schema.org auto-injection, deliverability scoring, BIMI readiness check). Phase 21 (real-time ontology sync & competitive intelligence — caniemail auto-sync, rendering change detector with 25 feature templates, competitive intelligence dashboard). Phase 22 (AI evolution infrastructure — capability registry, prompt template store, token budget manager, fallback chains, cost governor, cross-module integration tests + ADR-009). Phase 23 (multimodal protocol & MCP agent interface — 7 subtasks: content block protocol, adapter serialization, agent integration, MCP tool server with 17 tools, voice brief pipeline, frontend multimodal UI, tests & ADR-010; 197 tests).

---

## Phase 24 — Real-Time Collaboration & Visual Builder

**What:** Google Docs-style simultaneous editing with CRDT conflict resolution for the code editor, real-time cursor and presence awareness, plus a drag-and-drop visual email builder for non-technical users alongside the code editor. Changes in either view sync bidirectionally via AST-level mapping.
**Why:** The pitch identifies these as key "Future Vision" features that separate a platform from a tool. Real-time collaboration enables team workflows — developer and copywriter editing simultaneously without merge conflicts. The visual builder opens the Hub to the largest untapped user base: marketers and designers who can't write HTML but need to build emails daily. Combined, they make the Hub the only email platform where technical and non-technical users share a single workspace.
**Dependencies:** Phase 11 (component library for builder blocks), Phase 12 (Figma import for design-to-builder), Phase 23 (multimodal protocol for design reference images), all frontend phases.
**Design principle:** Yjs CRDT provides conflict-free merging — no operational transform complexity. The visual builder operates on the same component/section model as the code editor — it's a different view, not a different system. WebSocket connections are authenticated and tenant-isolated. Offline edits reconcile automatically on reconnect.

### 24.1 WebSocket Infrastructure & Authentication `[Backend]`
**What:** WebSocket server infrastructure for real-time communication. Handles connection management, authentication, room-based message routing (one room per template/document), heartbeat/keepalive, and graceful reconnection. Built on FastAPI's WebSocket support with Redis pub/sub for multi-instance scaling.
**Why:** Real-time collaboration requires persistent bidirectional connections — HTTP polling can't deliver sub-100ms latency for cursor movements and keystroke propagation. Redis pub/sub ensures WebSocket messages reach all instances in a multi-server deployment. Room-based routing isolates template editing sessions.
**Implementation:**
- Create `app/streaming/websocket/` package:
  - `manager.py` — `WebSocketManager`:
    - `ConnectionPool` — tracks active WebSocket connections per room: `dict[str, set[WebSocket]]`
    - `async connect(websocket: WebSocket, room_id: str, user_id: int) -> None` — authenticate, join room, notify peers
    - `async disconnect(websocket: WebSocket, room_id: str) -> None` — leave room, notify peers, cleanup
    - `async broadcast(room_id: str, message: bytes, exclude: WebSocket | None = None) -> None` — send to all connections in room except sender
    - `async send_to_user(room_id: str, user_id: int, message: bytes) -> None` — targeted message delivery
    - Heartbeat: server sends ping every 30s, client must pong within 10s or connection dropped
    - Connection metadata: `ConnectionInfo(user_id: int, room_id: str, connected_at: datetime, last_activity: datetime, client_info: str)`
  - `auth.py` — `WebSocketAuthenticator`:
    - `async authenticate(websocket: WebSocket) -> User` — extract JWT from query param `?token=` (WebSocket doesn't support headers in browser)
    - Token validation reuses existing `decode_access_token()` from `app/auth/`
    - Role-based access: viewer can observe but not edit, developer/admin can edit
    - BOLA protection: verify user has access to the project owning the template being edited
  - `redis_pubsub.py` — `RedisPubSubBridge`:
    - `async publish(room_id: str, message: bytes) -> None` — publish to Redis channel `ws:room:{room_id}`
    - `async subscribe(room_id: str, callback: Callable) -> None` — subscribe to room channel
    - Enables multi-instance WebSocket: message published on instance A → delivered to connections on instance B
    - Graceful fallback: if Redis unavailable, single-instance broadcast only (logged warning)
  - `routes.py` — WebSocket endpoint:
    - `@app.websocket("/ws/collab/{room_id}")` — main collaboration WebSocket
    - Protocol: binary messages (Yjs update encoding) for document sync, JSON messages for awareness (cursors, presence)
    - Connection lifecycle: authenticate → join room → sync document state → enter edit loop → disconnect
- Modify `app/main.py` — register WebSocket route, initialize `WebSocketManager`
- Config: `STREAMING__WS_ENABLED: bool = False`, `STREAMING__WS_MAX_CONNECTIONS_PER_ROOM: int = 20`, `STREAMING__WS_HEARTBEAT_INTERVAL_S: int = 30`, `STREAMING__WS_AUTH_TIMEOUT_S: int = 10`
**Security:** JWT authentication required before any message exchange. Token passed via query parameter (standard WebSocket auth pattern) — HTTPS encrypts in transit. Room isolation: users can only join rooms for templates in their project. Message size limit: 1MB per WebSocket message (prevents memory abuse). Connection count limited per room and per user. Redis pub/sub channels use room ID only — no user data in channel names. WebSocket upgrade restricted to `websocket` protocol only (no HTTP hijacking).
**Verify:** Two browser tabs connect to same room → both authenticated → messages broadcast between them. Invalid JWT → connection rejected. User without project access → connection rejected. Redis pub/sub: message sent from instance A → received on instance B (docker-compose test). Connection drops → peer notified → reconnection re-syncs state. Max connections reached → new connection rejected with 429. `make test` passes.
- [x] ~~24.1 WebSocket infrastructure & authentication~~ DONE

### 24.2 Yjs CRDT Document Engine `[Backend + Frontend]`
**What:** Integrate Yjs CRDT library for conflict-free collaborative editing of email HTML. Server-side Yjs document persistence, client-side binding to CodeMirror editor, and WebSocket sync provider. Multiple users can edit the same template simultaneously with automatic conflict resolution — no merge dialogs, no lost changes.
**Why:** CRDT (Conflict-free Replicated Data Type) is the modern approach to collaborative editing — used by Figma, Linear, and Notion. Unlike Operational Transform (Google Docs), CRDTs guarantee convergence without a central server ordering operations. Yjs is the most mature JavaScript CRDT library (2M+ weekly npm downloads), with ready-made bindings for CodeMirror, Monaco, and ProseMirror.
**Implementation:**
- Backend — `app/streaming/crdt/` package:
  - `document_store.py` — `YjsDocumentStore`:
    - `async get_or_create(room_id: str) -> bytes` — load Yjs document state from PostgreSQL, or create empty document
    - `async save(room_id: str, update: bytes) -> None` — persist incremental Yjs update
    - `async get_snapshot(room_id: str) -> bytes` — full document state for new connections
    - Storage: `CollaborativeDocument` SQLAlchemy model with `room_id` (unique), `state_vector` (LargeBinary), `updates` (LargeBinary — compacted Yjs updates), `last_modified`, `participant_count`
    - Compaction: merge accumulated updates into single state every 100 updates or 5 minutes (prevents unbounded update log growth)
  - `sync_handler.py` — `YjsSyncHandler`:
    - Implements Yjs sync protocol (y-protocols/sync):
      - Step 1: new client sends `SyncStep1` (state vector) → server responds with `SyncStep2` (missing updates)
      - Step 2: client sends `SyncStep2` (its missing updates to server)
      - Ongoing: each edit → `Update` message broadcast to all peers
    - `async handle_message(room_id: str, client_id: str, message: bytes) -> list[tuple[str, bytes]]` — process incoming sync message, return messages to send
    - Server-side merge: Yjs `Y.applyUpdate()` via `ypy` (Python Yjs bindings) — server maintains authoritative document state
  - Alembic migration for `collaborative_documents` table
- Frontend — `cms/apps/web/src/lib/collaboration/`:
  - `yjs-provider.ts` — `HubWebSocketProvider`:
    - Extends `y-websocket` provider with Hub authentication (JWT in query param)
    - Automatic reconnection with exponential backoff (1s, 2s, 4s, 8s, max 30s)
    - Offline queue: edits made while disconnected stored locally, replayed on reconnect
    - Connection status events: `connected`, `disconnected`, `synced`, `error`
  - `editor-binding.ts` — `YjsCodeMirrorBinding`:
    - Binds `Y.Text` to CodeMirror 6 editor via `y-codemirror.next`
    - Preserves existing CodeMirror extensions (syntax highlighting, linting, `highlightField` from 12.8)
    - Undo/redo manager: `Y.UndoManager` replaces CodeMirror's built-in undo (collaborative undo tracks per-user operations)
  - `awareness.ts` — collaborative awareness (cursors, selection, presence):
    - Each user's cursor position + selection range shared via Yjs Awareness protocol
    - User metadata: `{name: string, color: string, role: string}` — color assigned from palette, consistent per session
- Install: `yjs`, `y-websocket`, `y-codemirror.next`, `y-protocols` (frontend), `ypy-websocket`, `y-py` (backend)
- Config: `STREAMING__CRDT_ENABLED: bool = False`, `STREAMING__CRDT_COMPACTION_INTERVAL_S: int = 300`, `STREAMING__CRDT_COMPACTION_THRESHOLD: int = 100`, `STREAMING__CRDT_MAX_DOCUMENT_SIZE_MB: int = 5`
**Security:** Document state encrypted at rest (existing PostgreSQL encryption). Yjs updates are binary-encoded operations — no executable content. Document size capped at 5MB (prevents memory abuse via large pastes). Per-room access control enforced at WebSocket connection (24.1). Yjs Awareness protocol shares only cursor position + user display name — no sensitive data. Offline queue stored in browser `IndexedDB` — cleared on logout.
**Verify:** Two users open same template → both see each other's edits in real-time (<100ms latency on LAN). User A types in line 5, User B types in line 20 → no conflicts, both changes merge. User disconnects → reconnects → missed edits sync automatically. Server restart → document state restored from PostgreSQL. Compaction: 200 updates → compacted to single state → new client syncs quickly. `make test` passes. `make check-fe` passes.
- [x] ~~24.2 Yjs CRDT document engine~~ DONE

### 24.3 Collaborative Cursor & Presence Awareness `[Frontend]`
**What:** Visual indicators for real-time collaboration: colored cursors showing each user's position, selection highlights, user presence list (who's currently editing), and activity indicators (typing, idle, viewing). Integrated into the CodeMirror editor and workspace sidebar.
**Why:** Collaboration without presence awareness is confusing — users need to see where others are editing to avoid stepping on each other's work. Google Docs proved that colored cursors + user avatars are the minimum viable UX for real-time editing. The presence list adds team context — "Sarah from copy is editing the CTA section."
**Implementation:**
- Create `cms/apps/web/src/components/collaboration/` package:
  - `RemoteCursors.tsx` — CodeMirror decoration plugin:
    - Renders colored cursor lines at each remote user's position via CodeMirror `Decoration.widget`
    - Cursor label: small tooltip showing user name on hover, auto-hides after 3s of inactivity
    - Selection highlight: remote user's text selection shown as semi-transparent colored background
    - Color palette: 8 distinct colors assigned round-robin per session, consistent across reconnects
    - Smooth cursor animation: CSS transitions for position changes (avoids jarring jumps)
  - `PresencePanel.tsx` — sidebar panel showing connected collaborators:
    - User list: avatar/initials + name + role badge (developer/viewer) + activity indicator
    - Activity states: `editing` (green pulse), `idle` (gray, >60s no activity), `viewing` (blue, read-only mode)
    - "Follow" mode: click a user → editor scrolls to their cursor position in real-time
    - Collapsed view: avatar stack in toolbar (click to expand panel)
  - `CollaborationBanner.tsx` — top bar notification:
    - "3 people editing" indicator with avatar stack
    - Connection status: green dot (connected), yellow (reconnecting), red (disconnected)
    - "View-only mode" indicator when user has viewer role
  - `ConflictResolver.tsx` — edge case handler:
    - When CRDT merges produce unexpected HTML (e.g., broken tags from simultaneous edits in same element), show inline warning with "Accept" / "Revert to mine" options
    - Runs QA HTML validation on merged output — if invalid, highlight the merge point
- Modify `cms/apps/web/src/components/workspace/code-editor.tsx`:
  - Integrate `RemoteCursors` CodeMirror extension
  - Pass Yjs awareness state to cursor renderer
  - Add presence panel toggle to editor toolbar
- Add i18n keys across 6 locales — ~30 keys for presence, cursors, collaboration status
**Security:** User display names sourced from authenticated session only (not from Yjs awareness — verified server-side). "Follow" mode transmits only cursor position — no editor content. Viewer role enforced: read-only users see cursors but their edits are rejected by server.
**Verify:** 3 users in same document → 3 colored cursors visible to each user. User selects text → selection visible to peers. User goes idle (60s) → status changes to idle for peers. "Follow" mode → editor scrolls to followed user's position. Viewer opens document → sees cursors but cannot edit. `make check-fe` passes.
- [x] ~~24.3 Collaborative cursor & presence awareness~~ DONE

### 24.4 Visual Email Builder — Component Palette & Canvas `[Frontend]`
**What:** A drag-and-drop visual email builder where users construct emails by dragging section components from a palette onto a canvas. The canvas renders a live preview of the email using the same component library that the code editor uses. Sections snap to email-width constraints (600px max), stack vertically, and show placeholder content that's editable inline.
**Why:** 70% of email creation at agencies is done by non-developers who rely on drag-and-drop tools (Mailchimp, Klaviyo builder, Stripo). The Hub currently requires HTML knowledge. A visual builder using the existing component library means every component built for the code editor is automatically available in the visual builder — no duplicate work. This is the single biggest user-base expansion feature.
**Implementation:**
- Create `cms/apps/web/src/components/builder/` package:
  - `BuilderCanvas.tsx` — main canvas area:
    - Rendered email preview in constrained 600px-wide iframe (sandboxed, same origin)
    - Drop zones between sections — highlighted on drag-over with insertion indicator
    - Section ordering via drag handle (grip icon on left edge)
    - Click section → select → show property panel (24.5)
    - Double-click text content → inline editing (contenteditable with sanitization)
    - Canvas background: email client preview frame (inbox chrome around the email body)
    - Zoom controls: 50%, 75%, 100%, 125% — CSS transform on canvas container
    - Undo/redo: integrated with Yjs undo manager (if collaboration enabled) or local history stack
  - `ComponentPalette.tsx` — left sidebar component library:
    - Categories: Header, Hero, Content, Product, CTA, Social, Footer, Divider, Custom
    - Each component shown as thumbnail preview with name
    - Drag from palette → drop on canvas → inserts section with default content
    - Search/filter by component name or category
    - "Custom" category: user-uploaded components from the component library (Phase 11)
    - Component data sourced from `ComponentVersion` via `GET /api/v1/components` with latest version
  - `SectionWrapper.tsx` — wrapper for each section on canvas:
    - Selection state: click → blue border + drag handle + delete button + duplicate button
    - Hover state: subtle highlight border
    - Drag handle: reorder sections via drag-and-drop (using `@dnd-kit/core` for accessible DnD)
    - Section label: component name shown above section on hover
    - Responsive indicator: icon showing if section has responsive variants
  - `BuilderPreview.tsx` — sandboxed iframe rendering:
    - Takes section list → assembles HTML via client-side template assembly
    - Uses `srcdoc` attribute for iframe content (no server round-trip for preview)
    - CSS reset inside iframe to match email rendering (no inherited page styles)
    - Auto-refreshes on any section change (debounced 200ms)
  - `DragDropContext.tsx` — DnD infrastructure:
    - `@dnd-kit/core` with `@dnd-kit/sortable` for section reordering
    - Custom `DragOverlay` showing component preview during drag
    - Accessibility: keyboard DnD support (arrow keys + space to grab/drop)
    - Drop validation: prevent invalid nesting (e.g., no header inside footer)
- Create `cms/apps/web/src/hooks/use-builder.ts`:
  - `useBuilderState()` — manages section list, selection, undo history
  - `useSectionOperations()` — add, remove, duplicate, reorder section operations
  - `useBuilderPreview()` — debounced HTML assembly from section list
  - `useComponentLibrary()` — fetches available components with caching
- Install: `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`
- Add i18n keys across 6 locales — ~45 keys for builder labels, tooltips, section types
**Security:** Builder canvas uses sandboxed iframe (`sandbox="allow-same-origin"`) — no script execution in preview. Inline text editing sanitized via DOMPurify before committing to section data. Component HTML from API is pre-sanitized (existing pipeline). Drag-and-drop uses library with built-in XSS prevention (no innerHTML). User-uploaded components validated through existing component ingestion pipeline.
**Verify:** Drag hero component from palette → drops on canvas → preview shows hero section. Reorder sections via drag → preview updates. Click section → property panel opens (24.5). Delete section → removed from canvas. Undo → section restored. Inline text edit → preview reflects change. 10 sections on canvas → smooth drag performance. Keyboard DnD works. `make check-fe` passes.
- [x] ~~24.4 Visual email builder — component palette & canvas~~ DONE

### 24.5 Visual Builder — Property Panels & Section Configuration `[Frontend]`
**What:** Right sidebar property panels that appear when a section is selected in the visual builder. Each panel exposes section-specific configuration: content editing (text, images, links), style controls (colors from design system palette, spacing, alignment), responsive behavior toggles, and slot configuration (for template slots from 11.25). Non-technical users configure sections visually — no CSS knowledge required.
**Why:** Drag-and-drop gets sections onto the canvas, but property panels make them useful. Every visual email builder (Mailchimp, Stripo, Chamaileon) has property panels — they're table stakes. The Hub's advantage: property panels are driven by `slot_definitions` and `default_tokens` from `ComponentVersion` (11.25.2), so they automatically reflect the component's configuration surface without manual panel building.
**Implementation:**
- Create `cms/apps/web/src/components/builder/panels/` package:
  - `PropertyPanel.tsx` — main panel container:
    - Appears on section selection (right sidebar, 320px wide)
    - Tab structure: Content | Style | Responsive | Advanced
    - Panel content dynamically generated from `slot_definitions` of selected component
    - "Apply" button with live preview (changes reflected in canvas immediately)
  - `ContentTab.tsx` — content editing controls:
    - Text slots: rich text editor (bold, italic, link, list) — Tiptap or Plate.js embedded
    - Image slots: image picker (upload, URL, or asset library from design sync)
    - Link slots: URL input with "Open in new tab" toggle
    - CTA slots: button text + URL + button style selector
    - Dynamic slots: auto-generated from `slot_definitions` JSON — `{name, type, label, placeholder, validation}`
  - `StyleTab.tsx` — visual style controls:
    - Color picker: limited to design system palette (11.25.1) — shows brand colors as swatches, prevents off-brand choices
    - Spacing: margin/padding controls with visual box model diagram
    - Alignment: left/center/right buttons for text and images
    - Font: dropdown limited to design system typography (font family, size, weight)
    - Background: color or image with opacity slider
    - All values map to design tokens — output uses CSS custom properties or inline styles per component
  - `ResponsiveTab.tsx` — responsive behavior:
    - Toggle: "Stack on mobile" (multi-column → single column below 480px)
    - Image behavior: "Full width on mobile" toggle
    - Font size: mobile override (e.g., 14px body on mobile vs 16px desktop)
    - Preview: inline mobile/desktop toggle showing how section responds
    - Values stored as responsive tokens in section configuration
  - `AdvancedTab.tsx` — power user controls:
    - Custom CSS class input (validated against design system classes)
    - MSO conditional toggle: "Include Outlook fallback" checkbox (adds `<!--[if mso]>` wrapper)
    - Dark mode: explicit dark mode color overrides per element
    - HTML attribute editor: key-value pairs for custom attributes
    - "View Source" button: shows section HTML in read-only code viewer
  - `SlotEditor.tsx` — generic slot editor component:
    - Renders appropriate input control based on `slot_definitions` type: `text`, `rich_text`, `image`, `url`, `color`, `select`, `number`, `boolean`
    - Validation rules from slot definition (required, min/max length, pattern)
    - Default value from `default_tokens`
- Modify `cms/apps/web/src/components/builder/BuilderCanvas.tsx` — emit `onSectionSelect(sectionId)` → triggers property panel render
- Add i18n keys across 6 locales — ~60 keys for property panel labels, tab names, input placeholders
**Security:** Color picker restricted to design system palette — prevents arbitrary CSS injection via color values. Custom CSS class input validated against allowlist of design system classes. HTML attribute editor: `on*` event handlers blocked, `href` validated (no `javascript:` URIs), `style` attribute goes through sanitization. Rich text editor output sanitized via DOMPurify.
**Verify:** Select hero section → property panel shows Content tab with text + image + CTA slots. Edit text → canvas preview updates live. Change color from design system palette → section color updates. Responsive toggle → mobile preview shows stacked layout. Advanced: add MSO conditional → section HTML includes `<!--[if mso]>`. Slot types match `slot_definitions` from component. `make check-fe` passes.
- [x] ~~24.5 Visual builder — property panels & section configuration~~ DONE

### 24.6 Builder ↔ Code Bidirectional Sync `[Full-Stack]`
**What:** Changes in the visual builder reflect in the code editor and vice versa. AST-level mapping between builder section model and HTML source. Editing HTML directly updates the builder canvas; dragging a section in the builder inserts corresponding HTML at the correct position. A single source of truth (Yjs document or local state) drives both views.
**Why:** Professional email developers use both views — visual for layout, code for fine-tuning. Unidirectional sync (builder → code only) forces a choice. Bidirectional sync means a developer can drag sections in the builder, then switch to code to tweak MSO conditionals, then switch back — everything stays consistent. This is what Webflow does for web development; no email platform achieves it.
**Implementation:**
- Create `cms/apps/web/src/lib/builder-sync/` package:
  - `ast-mapper.ts` — `BuilderASTMapper`:
    - `htmlToSections(html: string) -> SectionNode[]` — parse HTML into section tree:
      - Identifies section boundaries via `data-section-id` attributes (added by TemplateAssembler)
      - Falls back to heuristic detection: `<table>` with `role="presentation"` as section wrapper, `<!--section:type-->` comments
      - Each `SectionNode`: `{id, componentId, slotValues, styleOverrides, responsiveConfig, htmlFragment}`
    - `sectionsToHtml(sections: SectionNode[], template: string) -> string` — serialize section tree back to HTML:
      - Preserves non-section HTML (head, doctype, wrapper table)
      - Inserts section HTML in order with `data-section-id` attributes
      - Merges slot values into component template HTML
    - `diffSections(prev: SectionNode[], next: SectionNode[]) -> SectionDiff[]` — minimal diff for incremental updates
    - Error recovery: if HTML parse fails (user broke structure in code editor), show warning banner with "Revert to last valid state" option instead of crashing builder
  - `sync-engine.ts` — `BuilderSyncEngine`:
    - Maintains single source of truth: `Y.Map` (if CRDT enabled) or React state
    - `onCodeChange(html: string)` — code editor changed → parse → update builder sections
    - `onBuilderChange(sections: SectionNode[])` — builder changed → serialize → update code editor
    - Debounced sync: code → builder syncs on 500ms idle (parsing is expensive), builder → code syncs on 200ms idle
    - Conflict detection: if both views change simultaneously, builder change wins (last-write-wins with user notification)
    - Parse error mode: if HTML is unparseable, builder shows "Code has unsupported structure" overlay — code editor remains functional
  - `section-markers.ts` — HTML annotation utilities:
    - `annotateHtml(html: string) -> string` — add `data-section-id`, `data-slot-name` attributes for roundtrip fidelity
    - `stripAnnotations(html: string) -> string` — remove builder annotations for export/render
    - Annotations are invisible in rendered output (data attributes don't affect rendering)
- Modify `app/ai/agents/scaffolder/` — `TemplateAssembler`:
  - Add `data-section-id="{section.id}"` attributes to assembled HTML output
  - Add `data-slot-name="{slot.name}"` on slot content containers
  - Attributes preserved through QA pipeline and repair pipeline
- Modify `cms/apps/web/src/components/workspace/` — workspace layout:
  - View switcher: "Code" | "Visual" | "Split" toggle in toolbar
  - Split view: code editor left (50%), builder canvas right (50%), synced
  - View state persisted in localStorage per template
- Create `cms/apps/web/src/hooks/use-builder-sync.ts`:
  - `useBuilderSync(editorRef, builderState)` — manages bidirectional sync lifecycle
  - `useSyncStatus()` — returns sync state: `synced`, `syncing`, `parse_error`, `conflict`
**Security:** HTML parsing uses DOMParser (browser built-in, safe) — no eval. `data-*` attributes cannot execute code. Section annotations stripped before export to prevent data leakage. Conflict resolution does not silently discard changes — user always notified.
**Verify:** Type HTML in code editor → builder canvas updates to show sections. Drag section in builder → code editor shows corresponding HTML insertion. Edit text in builder → code editor text updates. Edit same text in code editor → builder preview updates. Break HTML structure in code editor → builder shows parse error overlay, code editor still functional. Split view: changes in either side reflected in the other. Export: `data-section-id` attributes stripped from output. `make check-fe` passes.
- [x] ~~24.6 Builder ↔ code bidirectional sync~~ DONE

### 24.7 Frontend Builder Integration & Workspace `[Frontend]`
**What:** Integrate the visual builder, collaboration features, and property panels into the existing workspace layout. Add builder-specific toolbar actions (preview modes, device simulation, export), onboarding flow for non-technical users, and builder keyboard shortcuts. Ensure all workspace features (QA panel, AI agents, design reference) work in both code and builder views.
**Why:** The builder must feel native to the workspace — not a separate app. QA checks should run on builder output the same way they run on code editor output. AI agent suggestions should appear in both views. The onboarding flow is critical: non-technical users need guidance on their first builder session.
**Implementation:**
- Modify `cms/apps/web/src/components/workspace/` — workspace enhancements:
  - `BuilderToolbar.tsx` — builder-specific toolbar actions:
    - Device preview: Desktop (600px), Tablet (480px), Mobile (375px) — resizes canvas
    - Client preview: "View as Gmail" / "View as Outlook" — applies rendering profiles from chaos engine (18.1)
    - "Run QA" button — runs QA checks on assembled builder HTML (same pipeline as code editor)
    - "AI Suggest" button — feeds current builder structure to Scaffolder for content suggestions
    - Export: "Copy HTML", "Download .html", "Push to ESP" (Phase 13 integration)
  - `ViewSwitcher.tsx` — code/visual/split toggle:
    - Animated transition between views (fade/slide, 200ms)
    - Last view preference saved to localStorage per template
    - Keyboard shortcut: `Ctrl+Shift+V` toggles between code and visual
  - `BuilderOnboarding.tsx` — first-time user guide:
    - Step 1: "Drag a section from the palette" — highlight palette with pulsing border
    - Step 2: "Click to configure" — highlight section after first drop
    - Step 3: "Preview your email" — highlight device preview buttons
    - Step 4: "Run quality checks" — highlight QA button
    - 4 steps total, skippable, completion saved to user preferences
    - Only shown when user.role !== "developer" (developers likely don't need it)
- Modify `cms/apps/web/src/components/workspace/qa-results-panel.tsx`:
  - QA panel works identically in builder view — HTML assembled from sections → sent to QA endpoint
  - QA issues linkable to specific sections: click issue → section highlighted in builder canvas
- Modify `cms/apps/web/src/components/workspace/toolbar.tsx`:
  - Conditionally render builder-specific or code-specific actions based on active view
  - Voice brief (23.6) and design reference (23.6) buttons visible in both views
- Builder keyboard shortcuts:
  - `Delete` / `Backspace` — delete selected section
  - `Ctrl+D` — duplicate selected section
  - `Ctrl+Z` / `Ctrl+Shift+Z` — undo/redo
  - `Ctrl+Shift+V` — toggle code/visual view
  - `Arrow Up/Down` — move section up/down in order
  - `Escape` — deselect section
- Add i18n keys across 6 locales — ~40 keys for toolbar, onboarding, keyboard shortcuts
**Security:** Builder-assembled HTML passes through same `sanitize_html_xss()` pipeline as code editor output. Export actions validate HTML before sending to ESP. Client preview rendering uses same sandboxed Playwright approach as Phase 17.
**Verify:** Full builder workflow: open template → switch to visual view → drag 5 sections → configure via property panels → preview on mobile → run QA → all checks pass → export HTML. Split view: edit in code → see change in builder → edit in builder → see change in code. Onboarding: new viewer user → onboarding flow appears → complete 4 steps → not shown again. Keyboard shortcuts work in builder view. QA issue click → corresponding section highlighted. `make check-fe` passes.
- [ ] 24.7 Frontend builder integration & workspace

### 24.8 Tests & Documentation `[Full-Stack]`
**What:** Comprehensive test suite for WebSocket infrastructure (connection, auth, broadcast, Redis pub/sub), CRDT engine (merge correctness, compaction, persistence), collaboration UI (cursors, presence, follow mode), visual builder (DnD, property panels, section operations), bidirectional sync (code→builder, builder→code, parse errors), and workspace integration. ADR-011 documenting real-time collaboration architecture.
**Implementation:**
- Create `app/streaming/tests/test_websocket.py` — 20+ tests:
  - Connection lifecycle (connect, authenticate, join room, disconnect)
  - Auth rejection (invalid JWT, expired token, wrong project)
  - Room broadcast (message reaches all peers, not sender)
  - Redis pub/sub bridge (cross-instance message delivery)
  - Connection limits (max per room, max per user)
  - Heartbeat timeout (connection dropped after missed pongs)
- Create `app/streaming/tests/test_crdt.py` — 15+ tests:
  - Document create, load, save round-trip
  - Concurrent update merge (two updates applied, both preserved)
  - Update compaction (100 updates → single state)
  - Document size limit enforcement
  - State vector sync protocol (SyncStep1 → SyncStep2)
- Frontend tests (Vitest + Testing Library):
  - `builder-canvas.test.tsx` — section drag-and-drop, selection, inline editing
  - `property-panel.test.tsx` — slot rendering, value changes, design system constraints
  - `builder-sync.test.tsx` — HTML parse, section serialize, bidirectional sync
  - `collaboration.test.tsx` — cursor rendering, presence panel, follow mode
- Route tests for WebSocket endpoint (auth, message handling)
- ADR-011 in `docs/ARCHITECTURE.md` — Real-Time Collaboration & Visual Builder
- SDK regeneration for collaboration + builder types
- Target: 80+ tests
**Verify:** `make test` passes. `make check-fe` passes. `make check` all green. No regression in existing test suite.
- [ ] 24.8 Tests & documentation

### 24.9 AI-Powered HTML Import & Section Annotation `[Full-Stack]`
**What:** AI agent that takes arbitrary email HTML (imported from any ESP — Braze, SFMC, Klaviyo, Mailchimp, HubSpot, Adobe Campaign, Iterable) and automatically annotates it with `data-section-id` attributes, making it fully editable in the visual builder. Combines structural analysis with the Scaffolder agent's email layout understanding and the Personalisation agent's ESP token knowledge. User refinement UI (merge/split/group) lets developers fix what the AI got wrong. Once annotated, Strategy 1 (data-section-id) provides perfect roundtrip sync.
**Why:** No existing email builder can import arbitrary client HTML and make it fully editable without manual annotation (Stripo requires `esd-*` classes, Mailchimp requires `mc:edit` attributes, Mosaico requires `data-ko-*` attributes, Beefree's HTML→JSON import strips merge tags). AI-powered auto-annotation is the key differentiator: the annotation step that competitors require manually, Hub automates. Email developers keep full granular HTML access via the code editor — annotations are just `data-*` attributes, nothing is abstracted or locked behind a schema.
**Implementation:**
- Create `app/ai/agents/import_annotator/` — new AI agent `[Backend]`:
  - `prompt.py` — system prompt leveraging Scaffolder's email structure knowledge:
    - Input: raw email HTML (any structure — table-based, div-based, hybrid, column layouts)
    - Output: same HTML with `data-section-id` attributes on each logical section boundary
    - Rules: identify header, hero, content blocks, column groups, CTA sections, footer
    - Preserve ALL existing attributes, classes, IDs, inline styles — only ADD `data-section-id`
    - Preserve ALL ESP tokens (Liquid `{% %}`, Handlebars `{{ }}`, AMPscript `%% %%`, ERB `<% %>`) — treat as opaque text, never parse or modify
    - Detect column layouts and annotate the parent as a single section (not each column separately)
    - Add `data-section-layout="columns"` on column group sections
    - Add `data-component-name` with inferred name (Hero, Header, Footer, Content, CTA, Columns, Divider)
  - `schemas.py` — structured output:
    - `AnnotationDecision`: section_id, component_name, element_selector (CSS path to the element), layout_type (single/columns)
    - `ImportAnnotationResult`: list of `AnnotationDecision`, warnings (ambiguous sections, nested layouts)
  - `service.py` — `ImportAnnotatorService.annotate(html: str) -> str`:
    - Calls AI to get `ImportAnnotationResult`
    - Applies annotations to HTML via CSS selectors (no regex on arbitrary HTML)
    - Returns annotated HTML — same content, just `data-section-id` attributes added
    - Fallback: if AI fails, return original HTML unchanged (user can still use code editor)
  - `SKILL.md` — progressive disclosure skill file:
    - L1: email section anatomy (header/hero/content/cta/footer patterns)
    - L2: column layout detection (2-col, 3-col, 4-col, hybrid)
    - L3 files: `table_layouts.md` (nested table patterns), `div_layouts.md` (CSS-based layouts), `esp_tokens.md` (7 ESP syntaxes to preserve), `column_patterns.md` (Fab Four, calc-based, media query columns)
- Create `app/ai/agents/import_annotator/evals/` — eval-first development `[Backend]`:
  - `synthetic_data_import.py` — 15+ test cases:
    - Classic table layout (bodyTable/emailContainer)
    - Modern div-based layout
    - 2/3/4 column layouts (table-based and CSS-based)
    - Deeply nested tables (SFMC-style)
    - Hybrid layout (tables + divs)
    - Email with Liquid conditionals wrapping sections
    - Email with AMPscript blocks
    - Email with Handlebars partials
    - Email with MSO conditionals
    - Email with inline CSS + embedded `<style>`
    - Minimal email (single-section)
    - Complex email (10+ sections, mixed layouts)
    - Already-annotated email (should not double-annotate)
  - `judges/import_judge.py` — 5 evaluation criteria:
    - Section boundary accuracy (did AI find the right boundaries?)
    - Annotation completeness (every visual section has an ID?)
    - HTML preservation (no content, attributes, or tokens modified?)
    - ESP token integrity (all `{{ }}`, `{% %}`, `%% %%` tokens survive?)
    - Column detection (column groups annotated as single section?)
- Add API route `POST /api/v1/email/import-annotate` `[Backend]`:
  - Input: `{ html: string, esp_platform?: string }`
  - Output: `{ annotated_html: string, sections: AnnotationDecision[], warnings: string[] }`
  - Auth: `Depends(get_current_user)`, rate limited
  - The `esp_platform` hint helps the AI understand which token syntax to expect
- Create builder import UI `[Frontend]`:
  - `ImportDialog.tsx` — modal triggered from workspace toolbar:
    - Paste HTML or upload .html file
    - Optional: select ESP platform (Braze, SFMC, Klaviyo, etc.) for better token handling
    - "Import" button calls `/api/v1/email/import-annotate`
    - Shows progress: "Analyzing structure..." → "Annotating sections..." → "Done"
    - Preview: shows detected sections highlighted before accepting
    - "Accept" loads annotated HTML into code editor → builder renders sections
  - `SectionRefinementToolbar.tsx` — builder toolbar for user refinement:
    - **Merge**: select 2+ adjacent sections → combine into one section (removes inner `data-section-id`)
    - **Split**: click inside a section → inserts a section boundary at that point (adds new `data-section-id`)
    - **Group**: select multiple elements within a section → wrap in new sub-section
    - **Unwrap**: remove a section boundary → children merge into parent section
    - **Rename**: click section name → edit inline
    - All operations modify `data-section-id` attributes in the HTML — no separate data model
  - Section highlighting in builder canvas:
    - Hover over section → subtle border highlight
    - Click section → selection UI with merge/split/group/unwrap buttons
    - Section name badge shown on hover (from `data-component-name`)
- Integrate with ESP connectors `[Full-Stack]`:
  - `app/connectors/service.py` — add `import_and_annotate()` method:
    - Pull template HTML from ESP API (existing connector flow)
    - Pass through import annotator agent
    - Return annotated HTML ready for builder
  - Workspace "Import from ESP" button:
    - Select connected ESP → browse templates → select → auto-import + annotate
    - ESP tokens preserved throughout (Liquid, AMPscript, etc.)
- ESP token passthrough architecture `[Full-Stack]`:
  - Tokens stay as-is in the HTML — no extraction/placeholder dance
  - The AI annotates the HTML structure; it does not parse or modify content inside elements
  - `stripAnnotations()` only removes `data-section-id`/`data-component-name` — ESP tokens untouched
  - Export to ESP: same HTML minus annotations, all tokens intact
  - Round-trip guarantee: import from Braze → edit in builder → export back to Braze → tokens identical
**Security:** Import endpoint validates HTML size (<2MB). AI agent receives HTML as input but does not execute it. Annotations are `data-*` attributes only — cannot execute code. `stripAnnotations()` removes all builder metadata before export. ESP tokens treated as opaque strings — never evaluated, never modified. Import API rate-limited (10 req/min per user). Uploaded HTML files scanned for embedded scripts (rejected if found).
**Verify:** Import classic Braze email with Liquid tokens → sections detected → tokens preserved → edit in builder → export → Liquid tokens identical to original. Import SFMC email with AMPscript → same flow. Import 4-column layout → detected as single "Columns" section. Import complex 10-section email → all sections detected with correct names. Merge two sections → `data-section-id` removed from inner boundary. Split a section → new `data-section-id` added. Import already-annotated email → no double annotations. `make check` passes. `make eval-golden` passes.
- [ ] 24.9 AI-powered HTML import & section annotation

---

## Phase 24B — Email Client Rendering Accuracy & Liquid Validation

**What:** Upgrade the email client rendering pipeline from static YAML-maintained CSS support data to an auto-synced industry data source, restructure targeting around rendering engines instead of individual clients, add Liquid template dry-run validation, replace crude Playwright simulation profiles with accurate client sanitizer emulation, and adopt progressive enhancement HTML generation (engine-tier assembly) instead of generate-then-fix.
**Why:** The current ontology-based approach is architecturally sound but has three weaknesses: (1) the 95KB `support_matrix.yaml` drifts as clients update CSS support 2-3× per year, (2) local rendering profiles (strip `<style>` for Gmail, inject `display:block` for Outlook) give false confidence — they don't replicate actual client behavior, (3) the pipeline generates HTML then checks if clients support it, when it should generate correct HTML per engine tier from the start. Liquid template validation catches broken conditionals and undefined variables that the current regex-only `personalisation_syntax` check misses entirely.
**Dependencies:** Phase 24 (visual builder uses assembled HTML), Phase 11.25 (design system), QA engine (checks pipeline).
**Design principle:** Engine-first targeting. Five rendering engines (Word/VML, WebKit, Blink, Gmail sanitizer, Outlook.com sanitizer) replace 25+ individual client entries. Progressive enhancement generates correct HTML per tier rather than patching unsupported CSS after the fact. Can I Email data syncs replace manual YAML maintenance. Liquid dry-run catches logic errors without needing a full sandbox.

### 24B.1 Can I Email Data Sync `[Backend]`
**What:** Replace hand-maintained `support_matrix.yaml` with automated sync from Can I Email's open dataset. Keep the ontology query interface (`onto.clients_not_supporting()`) unchanged — only the data source changes.
**Why:** 365+ CSS properties × 25+ clients = 9,125 entries that rot without updates. Can I Email is community-maintained, updated when clients change, and the data is open on GitHub. Syncing eliminates manual maintenance and improves accuracy.
**Implementation:**
- Create `app/knowledge/ontology/sync/caniemail.py` — sync adapter:
  - Fetch Can I Email data from GitHub repo (JSON/YAML format)
  - Map their feature IDs to our `CSSProperty` IDs (build mapping table)
  - Map their client IDs to our `EmailClient` IDs
  - Convert their support levels (y/n/a/u) to our `SupportLevel` enum (full/partial/none/unknown)
  - Extract fallback recommendations where available
  - Write to `support_matrix.yaml` or a parallel `support_matrix_caniemail.yaml`
- Create `scripts/sync-caniemail.sh` — CLI command for manual sync
- Add `make sync-caniemail` target
- Merge strategy: Can I Email data is primary, custom overrides in `support_matrix_overrides.yaml` for any corrections or additions not in their dataset
- Add sync freshness check: warn if data is >90 days old
- Keep existing `support_matrix.yaml` as fallback if sync fails
**Security:** Sync fetches from a known GitHub repo only. No user input involved. Override file is developer-maintained.
**Verify:** Sync runs successfully. `onto.clients_not_supporting("display_flex")` returns same or better results. QA checks produce equivalent or improved results on existing test emails. `make test` passes.
- [ ] 24B.1 Can I Email data sync

### 24B.2 Rendering Engine Taxonomy `[Backend]`
**What:** Restructure client targeting around 5 rendering engines instead of 25+ individual clients. Each client maps to an engine; CSS support queries can target engine-level or client-level.
**Why:** Outlook 2016 and Outlook 2019 on Windows both use the Word engine — they have nearly identical CSS support. Tracking them separately creates redundant entries. Engine-level targeting reduces the matrix ~5× and is more accurate (a new Outlook version on Word still behaves like Word).
**Implementation:**
- Add `RenderingEngine` enum to `app/knowledge/ontology/types.py`:
  - `WORD` — Outlook 2013–2021, 365 Windows
  - `WEBKIT` — Apple Mail, Outlook Mac, iOS Mail
  - `BLINK` — Gmail Android, Samsung Mail, Outlook Android
  - `GMAIL_SANITIZER` — Gmail web, Gmail app, Google Workspace (strips `<style>`, rewrites classes)
  - `OUTLOOK_COM_SANITIZER` — Outlook.com, O365 web (`[data-ogsc]`/`[data-ogsb]` dark mode)
- Add `engine` field to `EmailClient` in `clients.yaml`
- Add engine-level query: `onto.engine_support(engine, property_id) -> SupportLevel`
  - Returns the **worst** support level across all clients in that engine
- Update `css_support.py` check to report engine-level issues alongside client-level
- Market share aggregated per engine for severity weighting
**Verify:** `onto.engine_support(WORD, "display_flex")` returns `NONE`. Engine-level CSS check produces cleaner, grouped output. `make test` passes.
- [ ] 24B.2 Rendering engine taxonomy

### 24B.3 Progressive Enhancement Assembly `[Backend]`
**What:** Modify `TemplateAssembler` to generate HTML in engine tiers with graceful degradation, instead of generating one HTML and then checking/fixing client support issues.
**Why:** Current flow: generate HTML → QA flags unsupported CSS → Outlook Fixer agent patches it → re-check. This is reactive. Progressive enhancement is proactive: the assembler generates correct HTML for each engine tier from the start, wrapped in MSO conditionals and media queries.
**Implementation:**
- Add engine tier strategy to `app/ai/agents/scaffolder/assembler.py`:
  - **Base tier (Word-safe)**: Table-based layout, inline styles only, VML for backgrounds, no CSS3. This is the MSO conditional path — already partially generated.
  - **Enhanced tier (WebKit/Blink)**: CSS Grid/Flexbox where templates use it, `<style>` block, media queries. This is the `<!--[if !mso]><!--` path.
  - Assembler decides per-section: if template uses only table layout, no tier split needed. If template uses modern CSS, generate both tiers with MSO conditional wrapping.
- Add `TierStrategy` to `EmailBuildPlan`:
  - `UNIVERSAL` — template is table-based, works everywhere (no tier split)
  - `PROGRESSIVE` — template uses modern CSS, needs Word fallback tier
  - Auto-detected from template structure during layout pass
- Modify brand color sweep to run per-tier (dark mode tier may have different colors)
- Existing Outlook Fixer agent becomes a **validation** agent rather than a **repair** agent — it checks that the Word tier is correct, not that it needs to be created
**Verify:** Template with Flexbox layout → assembler generates MSO conditional with table fallback + non-MSO block with Flexbox. Template with table-only layout → single universal output (no unnecessary conditionals). QA `css_support` check passes without needing Outlook Fixer repair loop. `make test` passes. `make eval-golden` passes.
- [ ] 24B.3 Progressive enhancement assembly

### 24B.4 Gmail & Outlook.com Sanitizer Emulation `[Backend]`
**What:** Build accurate sanitizer emulators for Gmail and Outlook.com webmail — the two most impactful webmail rendering environments. Replace the current crude Playwright profiles (`strip_style_tags=True` for Gmail) with emulators that replicate actual client behavior.
**Why:** Gmail doesn't just strip `<style>` — it rewrites class names, strips `<svg>`, removes `position`, has a specific attribute blocklist, and mangles certain selectors. The current `strip_style_tags=True` profile misses all of this. Gmail and Outlook.com together cover ~30% of email opens — accurate emulation here gives 60% of real-client-testing value at 10% of the cost.
**Implementation:**
- Create `app/rendering/emulators/gmail.py` — Gmail sanitizer emulator:
  - Strip `<style>` and `<link>` tags (existing behavior)
  - Rewrite class names with `m_` prefix (Gmail behavior)
  - Strip forbidden attributes: `id`, `class` (after inlining), `position`, `float`
  - Strip forbidden elements: `<svg>`, `<math>`, `<form>`, `<input>`
  - Convert `margin: 0 auto` to supported centering (Gmail quirk)
  - Supported CSS properties allowlist (Gmail publishes this)
  - Strip unsupported CSS properties from inline styles
- Create `app/rendering/emulators/outlook_com.py` — Outlook.com sanitizer emulator:
  - Inject `[data-ogsc]` attribute wrappers for dark mode
  - Inject `[data-ogsb]` for background overrides
  - Strip forbidden CSS properties
  - Rewrite certain selectors
- Create `app/rendering/emulators/base.py` — shared emulator interface:
  - `emulate(html: str) -> EmulationResult` with `html`, `warnings`, `stripped_properties`
- Update `app/rendering/local/profiles.py`:
  - Gmail profile uses `gmail.py` emulator instead of `strip_style_tags`
  - Outlook.com profile uses `outlook_com.py` emulator
  - Word profile remains Playwright-based (Word engine can't be emulated in browser)
  - WebKit/Blink profiles remain Playwright-based (close enough)
- Add `make render-emulate` command for standalone emulation testing
**Security:** Emulators process HTML strings only. No network access, no code execution. Input size capped at 2MB.
**Verify:** Send known Gmail-breaking email through emulator → same issues flagged as real Gmail rendering. Send email with `<style>` block → classes rewritten, styles inlined or stripped. Outlook.com dark mode email → `[data-ogsc]` attributes applied. Compare emulator output to real Gmail screenshots for 5 reference emails. `make test` passes.
- [ ] 24B.4 Gmail & Outlook.com sanitizer emulation

### 24B.5 Liquid Template Dry-Run Validation `[Backend]`
**What:** Execute Liquid templates with synthetic test data to validate personalization logic before accepting agent output. Catches broken conditionals, undefined variables, and type errors that the current regex-only `personalisation_syntax` check misses.
**Why:** The `personalisation_syntax` QA check validates syntax (matching `{% %}` / `{{ }}` delimiters) but not logic. An agent can generate `{% if subscriber.teir == "premium" %}` — valid syntax, misspelled variable, silent failure in production. Dry-run catches this class of error. No user PII is involved — Hub works with Liquid templates and synthetic placeholder data only.
**Implementation:**
- Create `app/qa_engine/checks/liquid_dryrun.py` — new QA check (check #12):
  - Uses `liquidpy` or `python-liquid` library to parse and execute Liquid templates
  - Synthetic test context: `{ subscriber: { first_name: "Alex", last_name: "Test", email: "alex@example.com", tier: "premium" }, company: { name: "Acme Corp" }, ... }`
  - Configurable per-project: custom variable schemas via `PersonalisationConfig` on project
  - Catches: `UndefinedVariable`, `LiquidSyntaxError`, `TypeError`, infinite loop (timeout 500ms)
  - Returns: `QACheckResult` with specific variable names and line numbers
  - Does NOT catch Handlebars/AMPscript/ERB — only Liquid (most common in Braze, Shopify, Jekyll)
- Add Handlebars support as a follow-up (separate library, same pattern)
- Add synthetic context builder: `app/qa_engine/checks/liquid_context.py`
  - Default context covers common ESP variables (subscriber, company, content, urls)
  - Project-level overrides for custom variable schemas
  - Context is synthetic only — never contains real subscriber data
- Register as check #12 in QA pipeline
- Add to `personalisation_syntax` check as complementary (syntax check + dry-run = full coverage)
**Security:** Liquid execution runs with timeout (500ms), no file system access, no network access. Synthetic data only — no user PII. Library sandboxed via `liquidpy` restricted mode if available.
**Verify:** Template with `{{ subscriber.first_name }}` → passes. Template with `{{ subscriber.frist_name }}` → warning: undefined variable. Template with unclosed `{% if %}` → error: syntax. Template with `{% for i in (1..99999) %}` → timeout. `make test` passes. Existing `personalisation_syntax` check still runs (complementary).
- [ ] 24B.5 Liquid template dry-run validation

### 24B.6 Per-Agent nh3 Allowlists `[Backend]`
**What:** Narrow the nh3 sanitization allowlist per agent role. Currently all agents share the same 70-tag allowlist. A Dark Mode agent should never produce `<a>` or `<img>` tags — its allowlist should be tighter.
**Why:** Defense-in-depth via capability restriction. If an agent is compromised or hallucinates, the narrower allowlist limits the damage. Zero performance cost — just different nh3 config dicts.
**Implementation:**
- Create `app/ai/agents/sanitization.py` — per-agent allowlist configs:
  - `SCAFFOLDER_ALLOWLIST` — full allowlist (it generates complete emails)
  - `DARK_MODE_ALLOWLIST` — `<style>`, `<meta>`, CSS-only tags (no structural HTML)
  - `ACCESSIBILITY_ALLOWLIST` — text content tags, ARIA attributes, `<img>` (for alt text)
  - `CONTENT_ALLOWLIST` — text/inline tags only (no tables, no structural)
  - `OUTLOOK_FIXER_ALLOWLIST` — full allowlist + VML tags (it fixes structure)
  - `PERSONALISATION_ALLOWLIST` — text tags + ESP token passthrough
- Modify `BaseAgentService._post_process()` to use agent-specific allowlist
- Structured decision mode agents (returning JSON) get the strictest allowlist (they shouldn't produce HTML at all — catch any leakage)
**Verify:** Dark Mode agent output with injected `<script>` tag → stripped. Dark Mode agent output with `<a>` tag → stripped (shouldn't be producing links). Scaffolder output with full HTML → preserved. `make test` passes.
- [ ] 24B.6 Per-agent nh3 allowlists

### 24B.7 Tests & Integration `[Full-Stack]`
**What:** Test suite for all 24B subtasks. Integration tests verifying the upgraded rendering pipeline end-to-end.
**Implementation:**
- `app/knowledge/ontology/sync/tests/test_caniemail.py` — sync adapter tests (10+)
- `app/knowledge/ontology/tests/test_engine_taxonomy.py` — engine query tests (10+)
- `app/ai/agents/scaffolder/tests/test_progressive_assembly.py` — tier generation tests (15+)
- `app/rendering/emulators/tests/test_gmail.py` — Gmail emulator accuracy tests (15+)
- `app/rendering/emulators/tests/test_outlook_com.py` — Outlook.com emulator tests (10+)
- `app/qa_engine/checks/tests/test_liquid_dryrun.py` — Liquid validation tests (15+)
- `app/ai/agents/tests/test_per_agent_sanitization.py` — allowlist restriction tests (10+)
- Integration test: brief → pipeline → progressive assembly → emulator check → QA pass (5+)
- Target: 90+ tests
**Verify:** `make test` passes. `make check` all green. `make eval-golden` passes (no regression in existing golden cases).
- [ ] 24B.7 Tests & integration

---

## Phase 25 — Platform Ecosystem & Advanced Integrations

**What:** Plugin architecture for community-contributed components, Tolgee integration for multilingual campaigns, Kestra workflow orchestration replacing ad-hoc blueprint scheduling, Penpot as a self-hosted Figma alternative, and Typst for programmatic QA report generation. Each integration compounds with existing capabilities — Tolgee + Maizzle enables per-locale builds, Kestra replaces ad-hoc pipeline orchestration, Penpot offers FOSS design import.
**Why:** These extend the Hub from a tool into a platform. A plugin architecture means the community can add QA checks, agent skills, export connectors, and component packages without core changes. Tolgee solves the "same email in 12 languages" problem that enterprises face daily. Kestra provides production-grade workflow orchestration (retry, parallelism, scheduling, audit) that the blueprint engine lacks. Penpot is the self-hosted alternative to Figma (no per-seat licensing). Typst generates beautiful PDF reports from QA data in <100ms.
**Dependencies:** All previous phases — plugins extend every subsystem, Tolgee hooks into Maizzle, Kestra wraps the blueprint engine, Penpot reuses the design sync protocol (Phase 12), Typst consumes QA engine data.
**Design principle:** Plugins are sandboxed — they can read Hub data and contribute capabilities but cannot modify core behavior. External integrations are protocol-based — swap Tolgee for another TMS, swap Kestra for Temporal, swap Penpot for any design tool that speaks the protocol. Every integration ships behind a feature flag.

### 25.1 Plugin Architecture — Manifest, Discovery & Registry `[Backend]`
**What:** Define the plugin manifest format, discovery mechanism, and central registry. Plugins declare their type (QA check, agent skill, export connector, component package, theme), required Hub API version, permissions, and entry points. The registry discovers plugins from a configurable directory, validates manifests, and registers capabilities with the appropriate subsystem.
**Why:** Without a formal plugin architecture, every new capability requires core code changes. A plugin system lets the community contribute: custom QA checks for specific industries (finance compliance, healthcare HIPAA), agent skills for niche use cases (AMP email generation, interactive email), ESP connectors for less common providers (Mailtrap, Postmark), and component packages (holiday themes, industry-specific templates).
**Implementation:**
- Create `app/plugins/` package:
  - `manifest.py` — `PluginManifest` Pydantic model:
    - `name: str` — unique plugin identifier (reverse domain: `com.example.my-plugin`)
    - `version: str` — semver (validated)
    - `hub_api_version: str` — minimum Hub API version required (e.g., `">=1.0"`)
    - `plugin_type: PluginType` — enum: `qa_check`, `agent_skill`, `export_connector`, `component_package`, `theme`, `workflow_step`
    - `entry_point: str` — Python module path for plugin entry (e.g., `my_plugin.main`)
    - `permissions: list[PluginPermission]` — enum: `read_templates`, `read_components`, `read_qa_results`, `write_qa_results`, `call_llm`, `network_access`, `file_read`
    - `config_schema: dict | None` — JSON Schema for plugin-specific configuration
    - `metadata: PluginMetadata` — `author`, `description`, `homepage`, `license`, `tags`
    - Loaded from `plugin.yaml` or `plugin.json` in plugin directory
  - `discovery.py` — `PluginDiscovery`:
    - `discover(plugin_dir: Path) -> list[PluginManifest]` — scans directory for plugin manifests
    - Plugin directory structure: `plugins/{plugin-name}/plugin.yaml` + Python package
    - Validation: manifest schema check, version compatibility check, dependency resolution
    - Hot reload support: `watch(plugin_dir)` using `watchdog` — detects new/modified plugins without restart
    - Conflict detection: two plugins registering same QA check name → error logged, second rejected
  - `registry.py` — `PluginRegistry` singleton:
    - `register(manifest: PluginManifest, module: ModuleType) -> None` — registers plugin with appropriate subsystem:
      - `qa_check` → registers with `QAEngineService` as additional check
      - `agent_skill` → registers with `SkillOverrideManager` as SKILL.md override
      - `export_connector` → registers with `ConnectorSyncService` as new provider
      - `component_package` → bulk imports components via `ComponentService`
      - `theme` → registers design system theme with `DesignSystemService`
      - `workflow_step` → registers with Kestra workflow (25.5) as custom step
    - `unregister(plugin_name: str) -> None` — cleanly removes plugin
    - `list_plugins() -> list[PluginInfo]` — returns all registered plugins with status
    - `get_plugin(name: str) -> PluginInstance` — returns loaded plugin instance
    - `PluginInfo(manifest: PluginManifest, status: str, loaded_at: datetime, error: str | None)`
  - `loader.py` — `PluginLoader`:
    - `load(manifest: PluginManifest) -> ModuleType` — `importlib` dynamic import of entry point module
    - Plugin entry point must export `setup(hub: HubPluginAPI) -> None` function
    - Module loaded in isolated namespace (no access to `app.core` internals)
    - Import timeout: 10s (prevents hanging plugins from blocking startup)
- Create `app/plugins/api.py` — `HubPluginAPI`:
  - Sandboxed API surface exposed to plugins:
    - `api.qa.register_check(name, check_fn)` — register QA check
    - `api.knowledge.search(query)` — read-only knowledge search
    - `api.components.list(category)` — list components
    - `api.templates.get(template_id)` — get template HTML
    - `api.llm.complete(messages, model_tier)` — call LLM (only if `call_llm` permission)
    - `api.config.get(key)` — read plugin-specific config
  - Permission enforcement: each API method checks `manifest.permissions` before executing
- Modify `app/main.py` — on startup: discover plugins → validate → load → register
- Modify `app/plugins/routes.py` — admin endpoints:
  - `GET /api/v1/plugins` — list all plugins with status
  - `POST /api/v1/plugins/{name}/enable` — enable a discovered plugin
  - `POST /api/v1/plugins/{name}/disable` — disable without removing
  - `DELETE /api/v1/plugins/{name}` — unregister and remove
  - `GET /api/v1/plugins/{name}/config` — get plugin config
  - `PUT /api/v1/plugins/{name}/config` — update plugin config
- Config: `PLUGINS__ENABLED: bool = False`, `PLUGINS__DIRECTORY: str = "plugins/"`, `PLUGINS__HOT_RELOAD: bool = False`, `PLUGINS__MAX_LOAD_TIME_S: int = 10`
**Security:** Plugins run in-process but with a restricted API surface — no direct database access, no file system writes, no network access (unless `network_access` permission granted). Plugin code is not sandboxed at the OS level (Python limitation) — this is a trust-based system suitable for enterprise self-hosted deployments where plugins are vetted. Admin-only plugin management endpoints. Plugin errors are caught and logged — a crashing plugin never takes down the Hub. Plugin config stored in database — not in plugin directory (prevents tampering).
**Verify:** Create sample QA check plugin (`plugin.yaml` + Python module) → place in plugins directory → Hub discovers on startup → plugin appears in `GET /plugins` → run QA → custom check included in results. Disable plugin → QA runs without it. Plugin requesting `call_llm` without permission → API call rejected. Hot reload: add new plugin to directory → registered without restart (when enabled). `make test` passes.
- [ ] 25.1 Plugin architecture — manifest, discovery & registry

### 25.2 Plugin Sandboxed Execution & Lifecycle `[Backend]`
**What:** Execution sandbox for plugins with resource limits, error isolation, and lifecycle hooks. Plugins get CPU/memory budgets, structured logging, health checks, and graceful shutdown. The sandbox ensures a misbehaving plugin cannot degrade Hub performance or crash the service.
**Why:** Plugins run third-party code in the Hub process. Without resource controls, a single plugin with an infinite loop or memory leak brings down the entire platform. Enterprise deployments need guarantees that plugin failures are isolated. Lifecycle hooks (startup, shutdown, health check) enable monitoring and graceful degradation.
**Implementation:**
- Create `app/plugins/sandbox.py` — `PluginSandbox`:
  - `execute(plugin: PluginInstance, fn: str, *args, timeout_s: float = 30) -> Any` — run plugin function with:
    - Timeout: `asyncio.wait_for()` with configurable per-plugin timeout
    - Error isolation: all exceptions caught, logged with plugin context, returned as `PluginError`
    - Resource tracking: wall-clock time measured, logged in structured format
  - `PluginExecutionContext` — passed to every plugin function:
    - `context.logger` — structured logger prefixed with plugin name
    - `context.config` — plugin-specific configuration (read-only)
    - `context.metrics` — counter/gauge registration for plugin metrics
  - `async health_check(plugin: PluginInstance) -> PluginHealth` — calls plugin's `health()` function if defined, times out after 5s
  - `PluginHealth(status: str, message: str | None, latency_ms: float)` — status: `healthy`, `degraded`, `unhealthy`
- Create `app/plugins/lifecycle.py` — `PluginLifecycleManager`:
  - `async startup(plugin: PluginInstance) -> None` — calls plugin `setup()`, validates return, marks as active
  - `async shutdown(plugin: PluginInstance) -> None` — calls plugin `teardown()` if defined, waits up to 10s, marks as inactive
  - `async restart(plugin: PluginInstance) -> None` — shutdown → load → startup (for hot reload)
  - Periodic health checks: every 60s, check all active plugins, disable unhealthy plugins after 3 consecutive failures
  - Startup ordering: plugins loaded in dependency order (if plugin A depends on plugin B, B loads first)
- Modify `app/plugins/registry.py` — integrate sandbox execution:
  - QA check plugins: `sandbox.execute(plugin, "run_check", html, config)` with 30s timeout
  - Agent skill plugins: `sandbox.execute(plugin, "process", request)` with 60s timeout
  - Export connector plugins: `sandbox.execute(plugin, "push", template, connection)` with 120s timeout
- Modify `app/plugins/routes.py` — add:
  - `GET /api/v1/plugins/{name}/health` — plugin health status
  - `POST /api/v1/plugins/{name}/restart` — restart plugin (admin only)
  - `GET /api/v1/plugins/health` — all plugins health summary
- Config: `PLUGINS__DEFAULT_TIMEOUT_S: int = 30`, `PLUGINS__HEALTH_CHECK_INTERVAL_S: int = 60`, `PLUGINS__MAX_CONSECUTIVE_FAILURES: int = 3`
**Security:** Timeout enforcement prevents infinite loops. Error isolation prevents plugin exceptions from propagating to request handlers. Plugin functions cannot catch `asyncio.CancelledError` (timeout is non-negotiable). Structured logging with plugin name prefix enables security audit of plugin actions. Health checks run with minimal permissions.
**Verify:** Plugin with `time.sleep(60)` → timeout after 30s → error logged → Hub continues serving. Plugin raising exception → caught, logged, result indicates error → Hub unaffected. Health check on healthy plugin → `healthy` status. Plugin failing health check 3 times → auto-disabled. Restart disabled plugin → re-enabled if health check passes. `make test` passes.
- [ ] 25.2 Plugin sandboxed execution & lifecycle

### 25.3 Tolgee Multilingual Campaign Support `[Backend]`
**What:** Integrate Tolgee (self-hosted translation management system) for multilingual email campaigns. Sync email content keys to Tolgee for translation, pull translations back, and trigger per-locale Maizzle builds. Supports ICU message format for pluralization and gender-aware content. Translation memory and machine translation suggestions speed up the translation workflow.
**Why:** Enterprise email campaigns routinely deploy in 5-20 languages. Currently, translations are managed in spreadsheets or external TMS with manual copy-paste into templates. Tolgee integration automates the full loop: extract translatable strings → translate → build per-locale email → QA each locale. The Hub's Maizzle sidecar already supports per-locale builds — Tolgee provides the translation data.
**Implementation:**
- Create `app/connectors/tolgee/` package:
  - `client.py` — `TolgeeClient(httpx.AsyncClient)`:
    - `async list_projects() -> list[TolgeeProject]` — list Tolgee projects
    - `async get_translations(project_id: int, language: str, namespace: str | None) -> dict[str, str]` — fetch translations for a language
    - `async push_keys(project_id: int, keys: list[TranslationKey]) -> PushResult` — create/update translation keys with source text
    - `async get_languages(project_id: int) -> list[TolgeeLanguage]` — list project languages
    - `async import_translations(project_id: int, format: str, data: bytes) -> ImportResult` — bulk import translations
    - `async export_translations(project_id: int, format: str, languages: list[str]) -> bytes` — bulk export
    - Authentication: Tolgee PAT (Personal Access Token) stored encrypted in `ESPConnection` model (reusing connector infrastructure)
    - Base URL: configurable for self-hosted instances
  - `extractor.py` — `TranslationKeyExtractor`:
    - `extract_keys(html: str, template_id: int) -> list[TranslationKey]` — scan email HTML for translatable content:
      - Text content in `<td>`, `<p>`, `<h1>`-`<h6>`, `<a>`, `<span>` elements
      - `alt` attributes on `<img>` elements
      - `title` attributes
      - Subject line and preview text (from template metadata)
    - `TranslationKey(key: str, source_text: str, context: str | None, namespace: str)` — key format: `template_{id}.section_{name}.{element}` (e.g., `template_42.hero.heading`)
    - ICU format detection: content with `{count, plural, ...}` or `{gender, select, ...}` preserved as-is
    - Skips non-translatable content: URLs, email addresses, code snippets, tracking parameters
  - `builder.py` — `LocaleEmailBuilder`:
    - `async build_locale(template_html: str, translations: dict[str, str], locale: str) -> str` — inject translations into template:
      - Replace source text with translations at each key location
      - Adjust RTL/LTR direction for Arabic, Hebrew, Farsi, Urdu locales
      - Handle text expansion: German/Finnish text is ~30% longer than English — validate no Gmail clipping after translation
    - `async build_all_locales(template_id: int, locales: list[str]) -> dict[str, str]` — parallel build for all target locales
    - Integration with Maizzle sidecar: `POST /build` with `locale` parameter for locale-specific Tailwind config
  - `schemas.py` — `TolgeeConnectionRequest`, `TranslationSyncRequest`, `LocaleBuildRequest`, `LocaleBuildResponse`, `TranslationKeySchema`
- Modify `app/connectors/routes.py` — add endpoints:
  - `POST /api/v1/connectors/tolgee/connect` — create Tolgee connection (encrypted credentials)
  - `POST /api/v1/connectors/tolgee/sync-keys` — push translatable keys to Tolgee with auth + `5/minute`
  - `POST /api/v1/connectors/tolgee/pull` — pull translations from Tolgee with auth + `10/minute`
  - `POST /api/v1/connectors/tolgee/build-locales` — build email in multiple locales with auth + `3/minute`
  - `GET /api/v1/connectors/tolgee/languages` — list available languages
- Config: `TOLGEE__ENABLED: bool = False`, `TOLGEE__BASE_URL: str = "http://localhost:25432"`, `TOLGEE__DEFAULT_LOCALE: str = "en"`, `TOLGEE__MAX_LOCALES_PER_BUILD: int = 20`
**Security:** Tolgee PAT stored encrypted (Fernet) in `ESPConnection` — same security model as ESP credentials (Phase 13). Translation content is text-only — no HTML injection possible (translations injected as text nodes, not raw HTML). RTL direction changes applied via `dir` attribute only — no CSS injection. Tolgee API calls use HTTPS. Rate limited to prevent API abuse.
**Verify:** Connect to Tolgee → extract 15 keys from template → push to Tolgee → verify keys appear in Tolgee UI. Add German translations in Tolgee → pull → build German locale → German text present in output. RTL locale (Arabic) → `dir="rtl"` applied. Long German text → Gmail clipping warning. ICU pluralization → preserved in translation. `make test` passes.
- [ ] 25.3 Tolgee multilingual campaign support

### 25.4 Tolgee Frontend & Per-Locale Maizzle Builds `[Frontend]`
**What:** Frontend UI for Tolgee integration: translation key viewer/editor, locale build dashboard with per-locale QA results, side-by-side locale preview, and in-context translation overlay. Non-translators can see which text is translatable and what the email looks like in each language.
**Why:** Translation workflows fail when the translator can't see the email context. Tolgee's in-context translation pattern lets translators click on text in the email preview and translate it directly — no switching between spreadsheet and email. Per-locale QA results catch locale-specific issues (text overflow in German, RTL layout breaks in Arabic) that english-only QA misses.
**Implementation:**
- Create `cms/apps/web/src/components/tolgee/` package:
  - `TranslationPanel.tsx` — main translation management panel:
    - Key list with source text, translation status per locale (translated, untranslated, machine-translated)
    - Inline translation editing for quick fixes
    - "Sync to Tolgee" button to push local edits
    - Translation progress bar per locale
    - Filter: by status (untranslated first), by section, by key
  - `LocalePreview.tsx` — side-by-side locale comparison:
    - Locale selector dropdown (flags + language names)
    - Split view: source locale left, target locale right
    - Rendered email preview per locale (using iframe)
    - "Build All" button → triggers per-locale Maizzle builds
  - `LocaleQAResults.tsx` — per-locale QA summary:
    - Matrix view: locales × QA checks with pass/fail indicators
    - Locale-specific issues highlighted (e.g., "German: Gmail clipping threshold exceeded by 3KB")
    - "Run QA for All Locales" batch action
  - `InContextOverlay.tsx` — translation overlay on email preview:
    - Hover over text in preview → tooltip showing translation key + current translation
    - Click → inline edit field → save → preview updates
    - Highlight untranslated strings with yellow background
    - Toggle overlay on/off via toolbar button
  - `TolgeeConnectionDialog.tsx` — connection setup dialog:
    - Tolgee URL input + PAT input
    - Test connection button
    - Project selector after successful connection
    - Language configuration (which locales to enable)
- Create `cms/apps/web/src/hooks/use-tolgee.ts` — SWR hooks:
  - `useTolgeeConnection()` — connection status
  - `useTranslationKeys(templateId)` — translatable keys for template
  - `useTranslations(templateId, locale)` — translations for a locale
  - `useLocaleBuild(templateId, locales)` — trigger locale builds
  - `useLocaleQA(templateId, locale)` — QA results for locale
- Add i18n keys across 6 locales — ~50 keys for translation UI labels
- SDK regeneration for Tolgee endpoints
**Security:** Tolgee PAT displayed as masked value in connection dialog. Translation edits go through text sanitization. In-context overlay is read-only unless user has developer/admin role. Locale preview iframe sandboxed.
**Verify:** Connect to Tolgee → translation keys extracted → view in panel → translate German → preview shows German text → QA checks pass. In-context overlay: hover → key shown → edit → translation saved. Side-by-side: English left, German right, layout intact. `make check-fe` passes.
- [ ] 25.4 Tolgee frontend & per-locale Maizzle builds

### 25.5 Kestra Workflow Orchestration `[Backend]`
**What:** Integrate Kestra (open-source workflow orchestration engine) to replace the blueprint engine's ad-hoc pipeline scheduling with declarative YAML workflows. Each email build becomes a Kestra flow with typed inputs, conditional branching (skip Visual QA if no screenshots enabled), parallel task execution (run QA checks concurrently), automatic retry with backoff, and a full audit trail. Blueprint engine remains the node execution logic; Kestra handles scheduling, retries, and cross-workflow coordination.
**Why:** The blueprint engine (Phase 14) handles single-run orchestration well, but lacks: (1) scheduled recurring builds (weekly newsletter pipeline), (2) cross-workflow dependencies (design import → build → QA → approve → push to ESP), (3) production-grade retry with dead-letter queues, (4) workflow versioning and rollback. Kestra provides all of these as a self-hosted service with a web UI. The Hub becomes a set of Kestra tasks that Kestra orchestrates — separation of concerns.
**Implementation:**
- Create `app/workflows/` package:
  - `kestra_client.py` — `KestraClient(httpx.AsyncClient)`:
    - `async create_flow(namespace: str, flow_id: str, definition: dict) -> Flow` — register a workflow
    - `async trigger_execution(namespace: str, flow_id: str, inputs: dict) -> Execution` — start workflow execution
    - `async get_execution(execution_id: str) -> Execution` — poll execution status
    - `async list_executions(namespace: str, flow_id: str) -> list[Execution]` — execution history
    - `async get_logs(execution_id: str) -> list[LogEntry]` — execution logs
    - `Execution(id: str, status: str, started: datetime, ended: datetime | None, inputs: dict, outputs: dict, task_runs: list[TaskRun])`
    - Authentication: Kestra API token stored in settings (not per-user)
  - `tasks/` — Hub-specific Kestra task definitions:
    - `blueprint_run.py` — `BlueprintRunTask` — wraps `BlueprintService.create_run()` as Kestra task:
      - Input: brief text, project_id, template preferences
      - Output: blueprint run ID, generated HTML, QA score
      - Retry policy: 3 attempts with 30s backoff on LLM timeout/rate-limit
    - `qa_check.py` — `QACheckTask` — wraps `QAEngineService.run_checks()`:
      - Input: HTML, config overrides
      - Output: QA results, pass/fail, score
      - Conditional: skip if HTML is None (previous task failed)
    - `chaos_test.py` — `ChaosTestTask` — wraps chaos engine:
      - Input: HTML, profiles
      - Output: resilience score, failures
    - `esp_push.py` — `ESPPushTask` — wraps ESP sync:
      - Input: HTML, connection_id, template_name
      - Output: push result, remote template ID
    - `locale_build.py` — `LocaleBuildTask` — wraps Tolgee locale builder (25.3):
      - Input: template_id, locales
      - Output: per-locale HTML map
    - `approval_gate.py` — `ApprovalGateTask` — creates approval request and waits:
      - Input: template_id, approver_role
      - Output: approval status (blocks workflow until approved/rejected)
      - Implements Kestra's `pause` task type for human-in-the-loop
  - `flow_templates/` — pre-built YAML workflow templates:
    - `email_build_and_qa.yaml` — standard flow: blueprint run → QA → chaos test (parallel) → visual QA → result
    - `multilingual_campaign.yaml` — extract keys → await translations → parallel locale builds → per-locale QA → approval gate → ESP push per locale
    - `weekly_newsletter.yaml` — scheduled trigger (cron) → content pull → blueprint run → QA → approval → ESP push
    - `design_import_pipeline.yaml` — design sync → layout analysis → brief generation → blueprint run → visual comparison → approval
  - `schemas.py` — `WorkflowTriggerRequest`, `WorkflowStatusResponse`, `WorkflowListResponse`
- Modify `app/workflows/routes.py` — workflow endpoints:
  - `GET /api/v1/workflows` — list available workflow templates + custom workflows
  - `POST /api/v1/workflows/trigger` — trigger workflow execution with inputs, auth + `5/minute`
  - `GET /api/v1/workflows/{execution_id}` — execution status + task run details
  - `GET /api/v1/workflows/{execution_id}/logs` — execution logs
  - `POST /api/v1/workflows/flows` — create custom workflow from YAML (admin only)
  - `GET /api/v1/workflows/flows/{flow_id}` — get workflow definition
- Modify `app/main.py` — register Kestra task definitions on startup, sync flow templates to Kestra
- Config: `KESTRA__ENABLED: bool = False`, `KESTRA__API_URL: str = "http://localhost:8080"`, `KESTRA__API_TOKEN: str = ""`, `KESTRA__NAMESPACE: str = "merkle-email-hub"`, `KESTRA__DEFAULT_RETRY_ATTEMPTS: int = 3`, `KESTRA__DEFAULT_RETRY_BACKOFF_S: int = 30`
**Security:** Kestra API token stored in settings (not in database — single instance token). Workflow inputs validated via Pydantic schemas before passing to Kestra. Custom workflow YAML validated against allowlist of Hub task types — no arbitrary script execution. Approval gate tasks enforce RBAC. Kestra runs as a separate Docker service — network-isolated from public internet (accessible only from Hub backend). Workflow logs may contain template content — same data classification as blueprint run logs.
**Verify:** Trigger `email_build_and_qa` flow → blueprint runs → QA checks run → results returned via status endpoint. Flow with LLM timeout → retries 3 times → succeeds on retry 2. `multilingual_campaign` flow → locale builds run in parallel → per-locale QA → approval gate pauses workflow → approve → ESP push completes. Scheduled `weekly_newsletter` → executes on cron schedule. Custom workflow YAML with invalid task type → rejected. `make test` passes.
- [ ] 25.5 Kestra workflow orchestration

### 25.6 Penpot Design-to-Email Pipeline `[Backend]`
**What:** Self-hosted, API-driven design-to-email pipeline using Penpot's CSS-native design primitives. Replaces or supplements Figma import (Phase 12) with a zero-cost, self-hosted alternative. Uses Penpot's API to extract components, layouts, typography, and colors — converting them to Hub components and design system tokens. Leverages Penpot's native CSS output (unlike Figma which requires translation from proprietary format).
**Why:** Figma charges per-editor ($15-75/month/seat) and restricts API access on lower tiers. Penpot is open-source, self-hosted, and outputs native CSS — making the design-to-email conversion more accurate (no Figma-to-CSS translation layer). For enterprises already using Penpot (growing in EU due to GDPR/data sovereignty), this is the natural design import path. The Hub's existing design sync protocol (Phase 12) provides the abstraction layer — Penpot becomes a second implementation alongside Figma.
**Implementation:**
- Create `app/design_sync/penpot/` package:
  - `client.py` — `PenpotClient(httpx.AsyncClient)`:
    - `async list_projects() -> list[PenpotProject]` — list Penpot projects via API
    - `async get_file(file_id: str) -> PenpotFile` — get file with pages, components, colors
    - `async get_components(file_id: str) -> list[PenpotComponent]` — extract component library
    - `async export_svg(file_id: str, object_id: str) -> bytes` — export node as SVG
    - `async export_css(file_id: str, object_id: str) -> str` — get CSS for a design element (Penpot native feature)
    - `async get_colors(file_id: str) -> list[PenpotColor]` — shared color library
    - `async get_typography(file_id: str) -> list[PenpotTypography]` — typography styles
    - Authentication: Penpot access token stored encrypted in `DesignConnection` (reusing Phase 12 model)
    - Base URL: configurable for self-hosted instances
  - `converter.py` — `PenpotToEmailConverter`:
    - `convert_component(component: PenpotComponent) -> ComponentVersion` — convert Penpot component to Hub component:
      - Extract CSS from Penpot's native CSS output (no Figma translation needed)
      - Convert CSS layout to email-safe HTML: flexbox → table (using CSS compiler from 19.3), grid → table
      - Map Penpot layers to HTML elements: frame → `<table>`, text → `<td>`, image → `<img>`, rectangle → `<div>` with background
      - Preserve Penpot component variants as Hub `ComponentVersion` compatibility configurations
    - `convert_colors(colors: list[PenpotColor]) -> BrandPalette` — map to design system colors (11.25.1)
    - `convert_typography(typography: list[PenpotTypography]) -> Typography` — map to design system fonts
    - `convert_layout(page: PenpotPage) -> LayoutAnalysis` — reuse layout analyzer (12.4) with Penpot-specific section detection
  - `sync_provider.py` — `PenpotSyncProvider` implementing `DesignSyncProtocol` (Phase 12 protocol):
    - `async list_files(connection_id: int) -> list[DesignFile]` — Penpot files as `DesignFile`
    - `async import_design(file_id: str, connection_id: int) -> DesignImport` — full import pipeline
    - `async extract_components(file_id: str, connection_id: int) -> list[Component]` — component extraction
    - Reuses existing `DesignImportService` workflow (create import → analyze layout → generate brief → convert)
  - `schemas.py` — Penpot-specific request/response schemas
- Modify `app/design_sync/routes.py` — add Penpot connection type:
  - `POST /api/v1/design-sync/connections` — already supports `provider` field, add `"penpot"` option
  - Penpot connections use same endpoints as Figma: file browser, import, component extraction
- Modify `app/design_sync/service.py` — register `PenpotSyncProvider` alongside `FigmaSyncProvider`
- Config: `DESIGN_SYNC__PENPOT_ENABLED: bool = False`, `DESIGN_SYNC__PENPOT_BASE_URL: str = "http://localhost:9001"`
**Security:** Penpot access token stored encrypted (Fernet). Penpot API calls use HTTPS (or internal network for self-hosted). CSS output from Penpot validated and sanitized before use in email HTML. SVG exports validated (no scripts, no external references — same validation as BIMI SVG in 20.4). BOLA protection on design connections.
**Verify:** Connect to self-hosted Penpot → list projects → browse files → import design → layout analyzed → brief generated → Scaffolder produces email matching design. Component extraction: Penpot components → Hub components with valid HTML. Color extraction: Penpot shared colors → design system palette. Typography: Penpot text styles → design system fonts. CSS conversion: Penpot flexbox → email table layout. `make test` passes.
- [ ] 25.6 Penpot design-to-email pipeline

### 25.7 Typst QA Report Generator `[Backend]`
**What:** Programmatic PDF generation for QA reports and client approval packages using Typst (Rust-based typesetting system, <100ms per document). Auto-generates branded PDF reports from Hub QA results, including visual regression screenshots, chaos test summaries, deliverability scores, and agent decision traces. Output suitable for client presentations and compliance archives.
**Why:** Clients and compliance teams need PDF reports — not dashboard links. Currently, QA results exist only in the Hub UI. Typst replaces LaTeX/wkhtmltopdf with a modern, fast, programmable alternative. A single QA report PDF containing all check results, screenshots, and recommendations is the deliverable that justifies the Hub's value to stakeholders who never log into the platform.
**Implementation:**
- Create `app/reporting/` package:
  - `typst_renderer.py` — `TypstRenderer`:
    - `async render(template_name: str, data: dict) -> bytes` — compile Typst template with data to PDF
    - Uses `typst` CLI via subprocess: `typst compile input.typ output.pdf --font-path fonts/`
    - Template + data merged: Typst templates use `#import "data.json"` for dynamic content
    - Temporary files: write `.typ` + `data.json` to temp directory, compile, read PDF, cleanup
    - Font embedding: Hub brand fonts bundled in `app/reporting/fonts/` for consistent rendering
    - Compilation timeout: 10s (Typst compiles ~100 pages in <1s — 10s is generous safety margin)
  - `templates/` — Typst report templates:
    - `qa_report.typ` — full QA report:
      - Cover page: project name, template name, date, Hub logo
      - Executive summary: overall pass/fail, score, top 3 issues
      - Check-by-check results: table with check name, status, score, details
      - Visual regression section: screenshot comparison grid (if available)
      - Chaos test results: resilience score bar chart, per-profile breakdown
      - Deliverability section: score gauge, dimension breakdown
      - Agent decisions: which agents contributed, key decisions made
      - Recommendations: prioritized fix list with estimated effort
    - `approval_package.typ` — client approval document:
      - Email preview renders (desktop, mobile, Outlook)
      - QA summary (pass/fail only — no technical details)
      - Brand compliance confirmation
      - Signature/approval section
    - `regression_report.typ` — visual regression comparison:
      - Baseline vs current screenshots side-by-side
      - Diff highlights
      - Changed regions annotated
  - `report_builder.py` — `ReportBuilder`:
    - `async build_qa_report(qa_run_id: int) -> bytes` — fetch QA results, screenshots, chaos data → compile PDF
    - `async build_approval_package(template_id: int, qa_run_id: int) -> bytes` — fetch template + QA → compile PDF
    - `async build_regression_report(entity_type: str, entity_id: int) -> bytes` — fetch baselines + current → compile PDF
    - Data assembly: queries QA engine, rendering service, blueprint service for all report data
    - Image embedding: screenshots base64-decoded and embedded in Typst as inline images
  - `schemas.py` — `ReportRequest(report_type: str, qa_run_id: int | None, template_id: int | None)`, `ReportResponse(pdf_base64: str, filename: str, size_bytes: int, generated_at: datetime)`
- Create `app/reporting/routes.py` — report endpoints:
  - `POST /api/v1/reports/qa` — generate QA report PDF with auth + `5/minute`
  - `POST /api/v1/reports/approval` — generate approval package PDF with auth + `5/minute`
  - `POST /api/v1/reports/regression` — generate regression report PDF with auth + `5/minute`
  - `GET /api/v1/reports/{report_id}` — retrieve previously generated report (cached in Redis for 24h)
- Modify `app/main.py` — register reporting routes
- Config: `REPORTING__ENABLED: bool = False`, `REPORTING__TYPST_BINARY: str = "typst"`, `REPORTING__CACHE_TTL_H: int = 24`, `REPORTING__MAX_REPORT_SIZE_MB: int = 50`
**Security:** Typst CLI runs as subprocess with fixed arguments — no user input in command. Report data sourced from authenticated API calls — BOLA enforced on all data fetches. PDF output is a binary document — no executable content. Temporary files written to OS temp directory with restricted permissions, deleted after compilation. Report cache uses Redis with TTL — auto-expiry prevents stale data. Rate limited to prevent CPU abuse.
**Verify:** Generate QA report for a template with 11 checks → PDF output with all sections populated. Generate approval package → client-friendly PDF without technical jargon. Report with screenshots → images embedded correctly. Report with no visual regression data → section gracefully omitted. Typst compilation completes in <1s for standard report. Cached report retrieved without recompilation. `make test` passes.
- [ ] 25.7 Typst QA report generator

### 25.8 Frontend Ecosystem Dashboard `[Frontend]`
**What:** Unified frontend dashboard for plugin management, Tolgee translations, Kestra workflows, Penpot design sync, and report generation. Extends the workspace with ecosystem-level views that surface cross-cutting information: active workflow executions, translation progress, plugin health, and generated reports.
**Why:** Each integration (plugins, Tolgee, Kestra, Penpot, Typst) adds backend capabilities — the frontend must surface them in a unified experience. A fragmented UI with separate pages per integration creates cognitive overhead. The ecosystem dashboard provides a single view of "what's happening across all integrations" with drill-down into specifics.
**Implementation:**
- Create `cms/apps/web/src/components/ecosystem/` package:
  - `EcosystemDashboard.tsx` — main dashboard page:
    - Four-quadrant layout: Plugins (top-left), Workflows (top-right), Translations (bottom-left), Reports (bottom-right)
    - Each quadrant shows summary stats + 3 most recent items + "View All" link
    - Real-time updates via SWR polling (30s interval for workflows, 60s for others)
  - `PluginManagerPanel.tsx` — plugin administration:
    - Plugin list: name, type, status (active/disabled/error), version, health indicator
    - Enable/disable toggle per plugin
    - Plugin config editor (JSON form generated from `config_schema`)
    - "Install Plugin" dialog: upload plugin zip or enter Git URL
    - Health dashboard: per-plugin health history graph
    - Admin-only access
  - `WorkflowPanel.tsx` — Kestra workflow management:
    - Active executions: list with status, progress, elapsed time
    - Workflow templates: available flows with "Trigger" button
    - Execution detail: task run timeline (Gantt-style), logs viewer, input/output inspector
    - Scheduled workflows: cron expression display, next run time, enable/disable
  - `ReportPanel.tsx` — report generation and history:
    - "Generate Report" dialog: select report type, template, QA run
    - Report history: list with type, date, size, download button
    - PDF preview: embedded `<iframe>` with PDF viewer
    - Batch generation: "Generate reports for all templates in project"
  - `PenpotPanel.tsx` — Penpot connection management:
    - Connection status + project browser (reuses `DesignFileBrowser` from 12.7)
    - Quick import actions: "Import Design" → triggers design import pipeline
    - Component sync status: last sync time, component count
- Create SWR hooks: `use-plugins.ts`, `use-workflows.ts`, `use-reports.ts`, `use-penpot.ts`
- Add navigation: "Ecosystem" entry in main sidebar navigation (below existing entries)
- Add i18n keys across 6 locales — ~70 keys
- SDK regeneration for all new endpoints
**Security:** Plugin management requires admin role. Workflow triggers require developer/admin role. Report downloads validated for ownership (BOLA). PDF preview uses sandboxed iframe.
**Verify:** Ecosystem dashboard loads with all four quadrants populated. Plugin manager: install → enable → health check passes → disable. Workflow panel: trigger flow → execution appears → progress updates → completion. Report panel: generate QA report → PDF appears in history → download works → preview renders. Penpot panel: connect → browse files → import design. `make check-fe` passes.
- [ ] 25.8 Frontend ecosystem dashboard

### 25.9 Tests & Documentation `[Full-Stack]`
**What:** Comprehensive test suite for plugin architecture (manifest validation, discovery, sandbox execution, lifecycle, registry integration), Tolgee (client, key extraction, locale builds, RTL handling), Kestra (client, task execution, flow templates, retry logic), Penpot (client, CSS conversion, component extraction, design sync protocol compliance), Typst (template compilation, data assembly, report correctness), and ecosystem dashboard. ADR-012 documenting platform ecosystem architecture.
**Implementation:**
- Create `app/plugins/tests/` — 30+ tests:
  - `test_manifest.py` — manifest parsing, validation, version compatibility
  - `test_discovery.py` — directory scanning, conflict detection, hot reload
  - `test_registry.py` — plugin registration per type, unregister, list
  - `test_sandbox.py` — timeout enforcement, error isolation, resource tracking
  - `test_lifecycle.py` — startup ordering, health checks, auto-disable
  - `test_api.py` — permission enforcement, API surface correctness
  - Sample plugin: `tests/fixtures/sample_qa_plugin/` with `plugin.yaml` + Python module
- Create `app/connectors/tolgee/tests/` — 20+ tests:
  - `test_client.py` — API calls (mocked httpx), auth, error handling
  - `test_extractor.py` — key extraction from HTML, ICU format preservation, skip rules
  - `test_builder.py` — locale builds, RTL handling, text expansion detection
  - Route tests for all Tolgee endpoints
- Create `app/workflows/tests/` — 20+ tests:
  - `test_kestra_client.py` — API calls (mocked httpx), flow CRUD, execution polling
  - `test_tasks.py` — each task type with mocked service calls, retry logic
  - `test_flow_templates.py` — YAML validation, task type allowlist enforcement
  - Route tests for workflow endpoints
- Create `app/design_sync/penpot/tests/` — 15+ tests:
  - `test_client.py` — API calls, auth, file listing
  - `test_converter.py` — CSS conversion, component mapping, layout analysis
  - `test_sync_provider.py` — protocol compliance with `DesignSyncProtocol`
- Create `app/reporting/tests/` — 15+ tests:
  - `test_typst_renderer.py` — compilation, timeout, temp file cleanup
  - `test_report_builder.py` — data assembly, image embedding, section omission
  - Route tests for report endpoints
- Frontend tests (Vitest + Testing Library):
  - `ecosystem-dashboard.test.tsx`, `plugin-manager.test.tsx`, `workflow-panel.test.tsx`, `report-panel.test.tsx`
- ADR-012 in `docs/ARCHITECTURE.md` — Platform Ecosystem Architecture
- SDK regeneration with all new types
- Target: 110+ tests
**Verify:** `make test` passes with all new tests. `make check-fe` passes. `make check` all green. No regression in existing test suite. SDK types match API responses.
- [ ] 25.9 Tests & documentation

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

## Success Criteria (Updated)

| Metric | Phase 22 (Current) | Target (Phase 25) |
|--------|--------------------|--------------------|
| Campaign build time | Under 4 hours | Under 1 hour (Kestra parallel pipelines) |
| Cross-client rendering defects | Auto-fixed by VLM agent | Near-zero (property-tested + plugin checks) |
| Component reuse rate | 60%+ | 80%+ (plugin component packages) |
| AI agent count | 10 (Visual QA) | 12+ (plugin agents) |
| QA checks | 14 (resilience, deliverability, BIMI) | 16+ (plugin checks) |
| Ontology freshness | Auto-synced daily | Real-time change detection + plugin extensions |
| Outlook migration readiness | Automated advisor | Audience-aware phased plans |
| Gmail AI optimization | Summary prediction + schema.org | Full AI inbox optimization |
| Cloud AI API spend | Under £600/month (cost governor) | Under £600/month (budget caps + plugin cost tracking) |
| Email CSS output size | 15-25% smaller (CSS compiler) | Optimal per-client bundles |
| Knowledge base entries | 1000+ (auto-synced) | Self-growing (chaos findings + plugin contributions) |
| Multilingual campaigns | Manual per-locale builds | Automated via Tolgee (20+ locales) |
| Workflow orchestration | Single blueprint runs | Declarative YAML workflows (Kestra) |
| Design import sources | Figma only | Figma + Penpot (zero-cost self-hosted) |
| QA report delivery | Dashboard only | PDF reports (Typst, <100ms generation) |
| External tool integration | REST API only | MCP server (IDE-native, any MCP client) |
| Collaboration | Single-user editing | Real-time multi-user CRDT (visual + code) |
| Non-developer access | Code editor only | Visual drag-and-drop builder |
