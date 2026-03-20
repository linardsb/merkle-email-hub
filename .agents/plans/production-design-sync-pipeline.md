# Plan: Production Design Sync Pipeline — Remove Demo Mode, Real Figma Integration

## Overview

Remove all demo mode mocking. Connect the frontend directly to the real FastAPI backend for all operations. Make the Figma-to-email pipeline production-ready: real Figma API calls, real design token extraction, AI-powered component mapping, and Scaffolder agent assembly using the existing HTML component library.

### How the Pipeline Works

```
Figma Design File
  │
  ├─ Connect: Validate PAT, extract file_key from URL
  ├─ Browse: Real file structure (pages, frames, components)
  ├─ Tokens: Extract colors, typography, spacing from Figma styles
  │
  ▼ User selects frames → generates brief
  │
  ├─ Layout Analysis: Detect email sections from frame structure
  ├─ Asset Download: Export frame images to local storage
  │
  ▼ Scaffolder Agent (3-pass pipeline)
  │
  │  Pass 1 — Layout (LLM): Selects GoldenTemplate + components
  │           from existing HTML component library based on
  │           Figma structure (e.g., hero-block for hero frame,
  │           column-layout-2 for 2-col content)
  │
  │  Pass 2 — Content (LLM): Fills [data-slot] markers with
  │           content from brief (headlines, body text, CTAs)
  │
  │  Pass 3 — Design (deterministic): Applies Figma design tokens
  │           to template (color replacement, font swap, spacing)
  │
  ▼ TemplateAssembler (zero LLM, 12 deterministic steps)
  │
  │  1. Fill slots with content
  │  2. Replace default palette with Figma/brand colors
  │  3. Component palette replacement
  │  4. Font replacement
  │  5. Logo enforcement
  │  6. Social link injection
  │  7. Dark mode color generation
  │  8. Brand color sweep (nearest-match safety net)
  │  9. Section visibility decisions
  │  10. Preheader text
  │  11. Builder annotations
  │  12. Progressive enhancement (MSO conditionals)
  │
  ▼ Final HTML (production-ready email)
  │
  ├─ Stored as TemplateVersion.html_source
  ├─ Loaded into workspace code editor
  ├─ Preview panel renders compiled output
  └─ QA engine validates (11 checks)
```

### HTML Components Stay As-Is

The 16 components in `email-templates/components/` are the structural building blocks:
- `email-shell.html` — Root wrapper with dark mode, VML namespaces
- `header.html`, `logo-header.html`, `navigation-bar.html` — Header variants
- `hero-block.html` — Full-width hero with VML background for Outlook
- `column-layout-2/3/4.html` — Responsive multi-column with MSO ghost tables
- `reverse-column.html` — RTL-trick for image-right on desktop
- `full-width-image.html`, `image-grid.html` — Image layouts
- `article-card.html`, `product-card.html` — Content cards
- `cta-button.html` — CTA with VML roundrect Outlook fallback
- `footer.html`, `preheader.html` — Standard sections

The Scaffolder maps Figma frames → these components. No new HTML generation from scratch.

---

## Stage 1: Fix Empty Editor Bug (Yjs Race Condition)

**Priority: Critical — affects both demo and production**

### Problem
When a template loads in the workspace, the code editor is empty because:
1. `useCollaboration` creates a Y.Doc synchronously but loads `awareness` asynchronously
2. When `awareness` resolves, CodeMirror switches from controlled mode to collaborative mode
3. The Yjs document was never populated with the HTML content

### Files to Modify
- `cms/apps/web/src/app/projects/[id]/workspace/page.tsx`

### Changes

**1a. Populate Yjs document when version loads (line ~198)**

In the `useEffect` that syncs editor content:

```typescript
useEffect(() => {
  if (latestVersion?.html_source) {
    setEditorContent(latestVersion.html_source);
    setSavedContent(latestVersion.html_source);
    setSaveStatus("idle");

    // Populate Yjs document so collaborative editor shows the content
    if (collabDoc) {
      const yText = collabDoc.getText("content");
      if (yText.length === 0) {
        yText.insert(0, latestVersion.html_source);
      }
    }

    // Auto-compile so preview is populated
    if (!demoCompiledRef.current) {
      demoCompiledRef.current = true;
      const sanitized = sanitizeHtml(stripAnnotations(latestVersion.html_source));
      triggerPreview({ source_html: sanitized })
        .then((r) => {
          if (r) {
            setCompiledHtml(r.compiled_html);
            setBuildTimeMs(r.build_time_ms);
          }
        })
        .catch(() => {});
    }
  }
}, [latestVersion?.html_source, triggerPreview, collabDoc]);
```

**1b. Reset compile flag on template switch**

```typescript
useEffect(() => {
  demoCompiledRef.current = false;
}, [activeTemplateId]);
```

### Verification
- [ ] Open workspace with any template → HTML appears in code editor
- [ ] Switch templates → editor updates correctly
- [ ] Preview panel shows rendered email

---

## Stage 2: Remove Demo Mode Interception Layer

**Priority: High — required before any real backend work**

### Goal
Remove the demo mode fetcher interception so ALL API calls go to the real backend. Keep the demo data files initially (can delete later) — just disconnect them.

### Files to Modify

**2a. `cms/apps/web/src/lib/swr-fetcher.ts` — Remove GET interception**

Remove the `IS_DEMO` check and dynamic `resolveDemo` import. Keep only the `authFetch` path:

```typescript
export async function fetcher<T>(url: string): Promise<T> {
  const res = await authFetch(url);
  if (!res.ok) {
    // ... existing error handling ...
  }
  return res.json();
}
```

**2b. `cms/apps/web/src/lib/mutation-fetcher.ts` — Remove POST interception**

Remove `tryDemoMutation()` entirely. Remove demo calls from `mutationFetcher()` and `longMutationFetcher()`:

```typescript
export async function mutationFetcher<T>(
  url: string,
  { arg }: { arg: unknown }
): Promise<T> {
  const res = await authFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(arg),
  });
  // ... existing error handling ...
}

export async function longMutationFetcher<T>(
  url: string,
  { arg }: { arg: unknown }
): Promise<T> {
  const res = await authFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(arg),
    timeout: 120_000,
  });
  // ... existing error handling ...
}
```

**2c. `cms/apps/web/auth.ts` — Remove demo credentials**

Remove the `if (process.env.NEXT_PUBLIC_DEMO_MODE === "true")` block (~lines 79-95). Keep the real backend login flow that calls `POST /api/v1/auth/login`.

**2d. `cms/apps/web/.env.example` — Remove demo env vars**

Remove `NEXT_PUBLIC_DEMO_MODE`, `DEMO_USERNAME`, `DEMO_PASSWORD`. Add:
```env
BACKEND_URL=http://localhost:8891
```

**2e. `cms/apps/web/Dockerfile` — Remove demo build arg**

Remove:
```dockerfile
ARG NEXT_PUBLIC_DEMO_MODE=true
ENV NEXT_PUBLIC_DEMO_MODE=$NEXT_PUBLIC_DEMO_MODE
```

### Verification
- [ ] `make dev` starts backend + frontend
- [ ] Login page authenticates against real backend
- [ ] API calls visible in backend logs (not intercepted)

---

## Stage 3: Remove Demo Mode from Individual Hooks

**Priority: High — hooks that bypass real APIs**

### Files to Modify (remove IS_DEMO checks)

**3a. `cms/apps/web/src/hooks/use-chat.ts`**
- Remove `IS_DEMO` constant and demo streaming logic
- Keep real SSE streaming to `/api/v1/ai/chat/stream`

**3b. `cms/apps/web/src/hooks/use-collaboration.ts`**
- Remove the `if (IS_DEMO)` branch that creates in-memory Yjs doc with fake collaborator
- Keep the production WebSocket provider path (`createHubProvider`)
- The collab WebSocket connects to backend at `/ws/collab/{roomName}`
- If WebSocket server isn't running, gracefully degrade (status: "disconnected")

**3c. `cms/apps/web/src/hooks/use-blueprint-run.ts`**
- Remove demo simulation (fake 2-3s delay with mock response)
- Keep real POST to `/api/v1/blueprints/run`

**3d. `cms/apps/web/src/components/builder/import-dialog.tsx`**
- Remove `IS_DEMO` check for HTML annotation

**3e. `cms/apps/web/src/hooks/use-chat-history.ts`**
- Remove demo chat history seeding

**3f. `cms/apps/web/src/hooks/use-export-history.ts`**
- Remove `IS_DEMO` check

**3g. `cms/apps/web/src/app/projects/[id]/workspace/page.tsx`**
- Remove `IS_DEMO` check in auto-compile effect (already handled in Stage 1)

### Verification
- [ ] Chat sends real messages to backend
- [ ] Collaboration connects via WebSocket (or gracefully degrades)
- [ ] Blueprint runs execute on real backend
- [ ] No console errors about demo mode

---

## Stage 4: Backend Infrastructure Setup

**Priority: High — backend must be running for frontend to work**

### Requirements

**4a. PostgreSQL + Redis**
```bash
make db          # Starts PostgreSQL (:5434) + Redis (:6380)
make db-migrate  # Run Alembic migrations
```

**4b. Seed component library**
The 21 HTML components need to be in the database:
```bash
# If seed command exists:
make seed
# Otherwise, POST each component via API or create a seed script
```

Check `app/components/data/seeds.py` — these 21 components (email-shell, header, footer, hero-block, column-layout-2/3/4, CTA, etc.) must be seeded into the `components` + `component_versions` tables.

**4c. Environment variables (`.env`)**
```env
ENVIRONMENT=development
DATABASE__URL=postgresql+asyncpg://postgres:postgres@localhost:5434/email_hub
REDIS__URL=redis://localhost:6380/0
AUTH__JWT_SECRET_KEY=<generate-with-openssl-rand-base64-32>

# AI Provider (required for Scaffolder)
AI__PROVIDER=anthropic
AI__API_KEY=sk-ant-...
AI__MODEL=claude-sonnet-4-20250514

# Embedding (optional, for knowledge/vector search)
EMBEDDING__PROVIDER=openai
EMBEDDING__API_KEY=sk-...

# Maizzle sidecar (for email compilation)
MAIZZLE_BUILDER_URL=http://localhost:3001
```

**4d. Start all services**
```bash
make dev  # Backend (:8891) + Frontend (:3000)
# In separate terminal:
cd services/maizzle-builder && npm start  # Maizzle (:3001)
```

### Verification
- [ ] `curl http://localhost:8891/health` returns 200
- [ ] `curl http://localhost:8891/api/v1/components/` returns seeded components
- [ ] Frontend login works with real credentials
- [ ] Projects list loads from database

---

## Stage 5: Figma Connection & Design Token Extraction

**Priority: High — core of the design sync feature**

### Already Implemented (Backend)

The backend Figma service (`app/design_sync/figma/service.py`) is production-ready:
- `validate_connection()` — validates PAT against Figma API
- `get_file_structure()` — fetches real page/frame/component tree
- `sync_tokens()` — extracts colors (RGBA→hex), typography (family/weight/size), spacing (auto-layout)
- `list_components()` — lists published Figma components
- `export_images()` — batch export nodes as PNG/SVG (groups of 100)

### Frontend Changes Needed

**5a. Connect Design Dialog needs real file browsing**

`cms/apps/web/src/components/design-sync/connect-design-dialog.tsx` already has a 3-step wizard:
1. Select provider + enter PAT
2. Browse files (calls `POST /api/v1/design-sync/browse-files`)
3. Configure name + project link

This should work out of the box once demo mode is removed. The `useBrowseDesignFiles` hook will hit the real backend, which calls `FigmaService.list_files()`.

**5b. File structure browser shows REAL Figma frames**

`cms/apps/web/src/components/design-sync/design-file-browser.tsx` calls `GET /api/v1/design-sync/connections/{id}/file-structure`. Once demo mode is removed, this returns the real Figma document tree with actual frame names, dimensions, and nesting.

**5c. Design tokens panel shows REAL extracted tokens**

`GET /api/v1/design-sync/connections/{id}/tokens` returns real colors, typography, and spacing extracted from Figma styles.

### User Flow (Production)
1. User enters Figma file URL + Personal Access Token
2. Backend validates PAT → fetches file metadata
3. File browser shows REAL frames from the Figma design
4. User selects frames to import
5. Tokens are extracted and displayed (colors, fonts, spacing)

### Verification
- [ ] Connect to real Figma file with PAT
- [ ] File structure shows actual Figma frames (not hardcoded 5)
- [ ] Design tokens show real colors/fonts from Figma styles
- [ ] Image export returns real Figma renders

---

## Stage 6: Design-to-Component Mapping Pipeline

**Priority: High — the core intelligence**

### How It Works

When the user imports selected Figma frames, the pipeline maps them to existing HTML components:

**6a. Layout Analysis** (`app/design_sync/service.py` → `analyze_layout()`)
- Analyzes selected Figma frames
- Detects email sections: header, hero, content, multi-column, CTA, footer
- Extracts text blocks, image areas, button elements
- Returns `LayoutAnalysisResponse` with section types

**6b. Brief Generation** (`generate_brief()`)
- Generates a Scaffolder-compatible markdown brief from:
  - Detected layout sections
  - Extracted text content from Figma
  - Design tokens (colors, fonts)
  - Image asset references

**6c. Scaffolder Agent Pipeline** (`app/ai/agents/scaffolder/pipeline.py`)

Pass 1 — **Template Selection (LLM)**:
- Input: brief + available GoldenTemplates from registry
- LLM selects which template to use based on Figma structure
- Each GoldenTemplate is built from the HTML components
- Example: Figma has header + hero + 2-col + CTA + footer → Scaffolder picks a matching template that composes `header.html` + `hero-block.html` + `column-layout-2.html` + `cta-button.html` + `footer.html`

Pass 2 — **Slot Filling (LLM)**:
- Input: brief + template's `[data-slot]` markers
- LLM generates content for each slot:
  - `[data-slot="headline"]` → "Spring Sale — Up to 50% Off"
  - `[data-slot="hero_image"]` → URL from downloaded Figma assets
  - `[data-slot="cta_text"]` → "Shop Now"
  - `[data-slot="cta_url"]` → "#"

Pass 3 — **Design Tokens (Deterministic)**:
- Input: Figma design tokens + brief
- Maps Figma colors → template role colors (primary, secondary, accent, text, background)
- Maps Figma fonts → template font families
- Returns `DesignTokens` for the assembler

**6d. TemplateAssembler** (`app/ai/agents/scaffolder/assembler.py`)

12 deterministic steps (zero LLM calls):
1. Fill slots with Pass 2 content
2. Replace default palette colors with Figma/brand colors (hex → hex, role-based)
3. Component-level palette replacement
4. Font family replacement
5. Logo dimension enforcement
6. Social link injection
7. Dark mode color generation (inverted palette)
8. Brand color sweep safety net (Euclidean RGB nearest-match)
9. Section visibility from Pass 1 decisions
10. Preheader text
11. Builder section annotations (for round-trip editing)
12. Progressive enhancement (MSO conditionals for Outlook)

### Verification
- [ ] Import Figma frames → Scaffolder selects appropriate template
- [ ] Slot content reflects brief/design text
- [ ] Colors match Figma design tokens
- [ ] Fonts match Figma typography
- [ ] Images reference downloaded Figma assets
- [ ] Output is valid email HTML with MSO conditionals

---

## Stage 7: End-to-End Import Flow

**Priority: High — the complete user journey**

### Flow

1. User connects Figma file (Stage 5)
2. User clicks "Import Design" on connection card
3. Design Import Dialog opens:
   a. **Select Frames** — shows real Figma file tree, user picks frames
   b. **Review Brief** — AI-generated brief from Figma analysis, user can edit
   c. **Converting** — backend runs: layout analysis → asset download → Scaffolder pipeline
   d. **Result** — shows imported assets + "Open in Workspace" button
4. User clicks "Open in Workspace"
5. Workspace loads with:
   - Code editor: full email HTML from Scaffolder (Stage 1 fix ensures it's visible)
   - Preview: rendered email with Figma design tokens applied
   - Builder: visual representation with draggable sections

### Backend Pipeline (`app/design_sync/import_service.py`)

```
DesignImportService.run_conversion()
  ├─ Step 1: analyze_layout() → detect sections from Figma frames
  ├─ Step 2: download_assets() → export + store Figma images locally
  ├─ Step 3: build_design_context() → combine tokens + layout + image URLs
  ├─ Step 4: _call_scaffolder() → 3-pass AI pipeline
  │   ├─ Pass 1: Template selection (LLM picks from component library)
  │   ├─ Pass 2: Slot filling (LLM generates content)
  │   └─ Pass 3: Design tokens (deterministic color/font mapping)
  ├─ Step 5: _create_template() → Template + TemplateVersion in DB
  └─ Step 6: mark import as "completed" with result_template_id
```

### Frontend Polling

The import dialog polls `GET /api/v1/design-sync/imports/{id}` every 2 seconds. When status changes to "completed", it shows the result with assets and the "Open in Workspace" button.

### Verification
- [ ] Full flow: Figma connect → select frames → brief → convert → workspace
- [ ] HTML in editor matches Figma structure (correct sections)
- [ ] Colors/fonts from Figma design are applied
- [ ] Images from Figma are embedded
- [ ] QA checks pass on generated HTML

---

## Stage 8: Component Extraction from Figma

**Priority: Medium — parallel workflow for building component library**

### What It Does

Separate from the import-to-template flow, users can extract Figma components directly into the Hub's component library. This uses `POST /api/v1/design-sync/connections/{id}/extract-components`.

### Flow
1. User clicks "Extract Components" tab in the import dialog
2. Backend lists Figma components via `FigmaService.list_components()`
3. User selects components to extract
4. Backend runs background task:
   - Export each component as image
   - AI generates email-compatible HTML for each
   - Creates `Component` + `ComponentVersion` records in DB
   - Links back to Figma via `DesignOrigin` (provider, file_key, component_id)
5. Components appear in the Component Library

### Verification
- [ ] Figma components list loads from real API
- [ ] Extraction creates real components in DB
- [ ] Components have proper `design_origin` linking back to Figma
- [ ] Extracted components are usable in templates

---

## Stage 9: Collaboration & Real-Time Features

**Priority: Medium — can work without initially**

### WebSocket Collaboration

`use-collaboration.ts` production path connects to:
```
ws://localhost:8891/ws/collab/project-{projectId}-template-{templateId}
```

Requires:
- Backend WebSocket server running (configured in `app/streaming/websocket/`)
- Redis pub/sub bridge for multi-instance support
- CRDT document store (if `COLLAB_WS__CRDT_ENABLED=true`)

### Graceful Degradation

If WebSocket isn't available, collaboration status shows "disconnected" and the editor works in single-user mode (controlled CodeMirror, not Yjs). This is the safest initial approach.

### Changes
- In `use-collaboration.ts`, ensure the production path handles connection failures gracefully
- If WebSocket connection fails, return `doc: null, awareness: null`
- This makes `collaborative` prop `undefined` → CodeMirror uses controlled mode

### Verification
- [ ] Without WebSocket: editor works in single-user mode
- [ ] With WebSocket: real-time collaboration works
- [ ] No errors when WebSocket unavailable

---

## Stage 10: Cleanup & Production Hardening

**Priority: Low — after everything works**

### 10a. Delete demo data files

Remove entire directory:
```
cms/apps/web/src/lib/demo/  (32 files)
cms/apps/web/src/lib/collaboration/demo-provider.ts
```

### 10b. Remove all IS_DEMO references

Search and clean:
```bash
grep -r "IS_DEMO\|DEMO_MODE\|NEXT_PUBLIC_DEMO" cms/apps/web/src/
```

### 10c. Update imports

Remove any imports of demo data/resolvers that may have been left as dead code.

### 10d. Update tests

- `cms/apps/web/src/hooks/__tests__/use-complex-hooks.test.ts` — rewrite without demo mocks
- Any other tests referencing demo data

### 10e. Update Docker build

Ensure `Dockerfile` and `docker-compose.yml` don't reference demo mode.

### Verification
- [ ] `make check-fe` passes (TypeScript + tests)
- [ ] `make check` passes (full pipeline)
- [ ] No references to demo mode in codebase
- [ ] Docker build works without demo env var

---

## Environment Requirements Summary

### Backend (.env)
```env
ENVIRONMENT=development
DATABASE__URL=postgresql+asyncpg://postgres:postgres@localhost:5434/email_hub
REDIS__URL=redis://localhost:6380/0
AUTH__JWT_SECRET_KEY=<32+ chars>

# AI (required for Scaffolder)
AI__PROVIDER=anthropic
AI__API_KEY=sk-ant-...
AI__MODEL=claude-sonnet-4-20250514

# Maizzle sidecar
MAIZZLE_BUILDER_URL=http://localhost:3001
```

### Frontend (.env.local)
```env
BACKEND_URL=http://localhost:8891
AUTH_SECRET=<openssl rand -base64 32>
# NO NEXT_PUBLIC_DEMO_MODE
```

### Services to Run
```bash
make db           # PostgreSQL + Redis
make db-migrate   # Run migrations
make dev          # Backend (:8891) + Frontend (:3000)
# Maizzle sidecar:
cd services/maizzle-builder && npm start  # :3001
```

### Figma Requirements
- Figma Personal Access Token (PAT) — generated at https://www.figma.com/developers/api#access-tokens
- PAT needs read access to the target file

---

## Execution Order

| Stage | Description | Depends On | Effort |
|-------|-------------|------------|--------|
| 1 | Fix empty editor (Yjs) | None | Small |
| 2 | Remove fetcher interception | None | Small |
| 3 | Remove hook demo checks | Stage 2 | Medium |
| 4 | Backend infrastructure | None (parallel) | Medium |
| 5 | Figma connection (verify existing) | Stages 2-4 | Small |
| 6 | Component mapping (verify existing) | Stages 4-5 | Small |
| 7 | End-to-end import (verify + fix) | Stages 1-6 | Medium |
| 8 | Component extraction | Stage 5 | Small |
| 9 | Collaboration (optional initially) | Stage 3 | Medium |
| 10 | Cleanup & hardening | All above | Small |

Stages 1-3 (frontend) and Stage 4 (backend) can run in parallel.
Stages 5-7 are mainly verification — the backend code is already implemented.
