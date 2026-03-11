# Frontend Prime — Load Full Frontend Context

## Step 0: Index & Discover (jCodeMunch)
1. Run `index_folder({ "path": "<project_root>" })` if not already indexed
2. Run `get_repo_outline` to understand overall project structure
3. Run `get_file_tree` to map the `cms/` directory layout
4. Run `get_file_outline` on key files below to understand their exports before reading full content

## Step 1: Load Core Files

**Code files** — Read in full (need complete content for patterns):
1. Read `/cms/apps/web/src/app/layout.tsx` for provider hierarchy
2. Read `/cms/apps/web/auth.ts` for authentication setup
3. Read `/cms/apps/web/middleware.ts` for RBAC route protection
4. Read `/cms/apps/web/src/lib/auth-fetch.ts` for API fetching patterns
5. Read `/cms/apps/web/src/lib/sdk.ts` for SDK client setup

**Documentation** — Use jDocMunch (repo: `local/merkle-email-hub`) for targeted section reads:
6. `CLAUDE.md` — `get_section` on `::project-overview#2`, `::core-principles#2`, `::project-structure#3`, `::frontend-features-for-fe-prime#3`
7. `TODO.md` — `get_document_outline` to list phases, then `get_section` on frontend-relevant phases only

If jDocMunch index is stale, fall back to full `Read`.

After reading, summarize what you've loaded.

## Step 2: Assess Task Status
Use jDocMunch `get_section` on each frontend-relevant phase in `TODO.md` (by section ID) instead of reading the full file. Use jCodeMunch `search_symbols` to check if implementations exist in the codebase. Report status (done/not started):

**Phase 0 — Foundation Blockers:**
- 0.2 Initialize shadcn/ui component library in `cms/apps/web/`
- 0.3 Generate OpenAPI TypeScript SDK from backend
- 0.4 Authenticated API client layer (token refresh, error handling, React hooks)

**Phase 1 — Sprint 1: Editor + Build Pipeline:**
- 1.1 Project dashboard page (`/(dashboard)/page.tsx`)
- 1.2 Project workspace layout (3-pane: editor, preview, AI chat)
- 1.3 Monaco editor (HTML/CSS/Liquid, Can I Email autocomplete)
- 1.4 Maizzle live preview (compile-on-save, viewport toggles, dark mode)
- 1.5 Test persona engine UI (persona selector, device/client context)
- 1.6 Template CRUD + persistence UI (versioning, restore)

**Phase 2 — Sprint 2: Intelligence + Export:**
- 2.5 AI chat sidebar UI (agent selection, streaming, accept/reject)
- 2.7 Component library browser UI (`/components`)
- 2.8 10-point QA gate system UI (run, results, override flow)
- 2.9 Raw HTML export + Braze connector UI

**Phase 3 — Sprint 3: Client Handoff + Polish:**
- 3.1 Client approval portal UI (viewer login, read-only preview, feedback)
- 3.2 Rendering intelligence dashboard (QA trends, support matrices)
- 3.3 Dashboard homepage enhancement (real data, activity feed)
- 3.4 Error handling, loading states, UI polish (skeletons, toasts, error pages)

**Phase 4 — V2:**
- 4.3 Figma design sync (REST API, token extraction, webhooks)
- 4.5 Advanced features (collaborative editing, visual Liquid builder)

Confirm you're ready for frontend work.
