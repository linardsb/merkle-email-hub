# Frontend Prime — Load Full Frontend Context

Load the complete frontend context for this project. Read the following files:

1. Read `/cms/apps/web/src/app/[locale]/layout.tsx` for provider hierarchy
2. Read `/cms/apps/web/auth.ts` for authentication setup
3. Read `/cms/apps/web/middleware.ts` for RBAC route protection
4. Read `/cms/apps/web/src/lib/auth-fetch.ts` for API fetching patterns
5. Read `/cms/apps/web/src/lib/sdk.ts` for SDK client setup

After reading, summarize what you've loaded.

Then read `/TODO.md` and extract only the **frontend-relevant tasks** below. Report their status (done/not started) based on what exists in the codebase:

**Phase 0 — Foundation Blockers:**
- 0.2 Initialize shadcn/ui component library in `cms/apps/web/`
- 0.3 Generate OpenAPI TypeScript SDK from backend
- 0.4 Authenticated API client layer (token refresh, error handling, React hooks)

**Phase 1 — Sprint 1: Editor + Build Pipeline:**
- 1.1 Project dashboard page (`/[locale]/(dashboard)/page.tsx`)
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

**Phase 4 — Post-MVP:**
- 4.3 Figma design sync (REST API, token extraction, webhooks)
- 4.5 Advanced features (collaborative editing, visual Liquid builder)

Confirm you're ready for frontend work.
