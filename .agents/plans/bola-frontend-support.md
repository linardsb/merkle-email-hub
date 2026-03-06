# Plan: Frontend Support for BOLA Fixes (6.1.1–6.1.9)

## Context

Backend BOLA fixes will add `verify_project_access()` checks to 9 endpoints. These will return **403 Forbidden** where previously any authenticated user could access any resource. The frontend currently has **zero 403-specific handling** — all API errors produce generic toasts.

The frontend changes are minimal:
1. **Thread `project_id`** into AI chat requests (currently missing — blocks backend BOLA enforcement)
2. **No special 403 UX** — keep generic error handling (per user decision)
3. **Knowledge stays global** — no project scoping needed

## Files to Modify

1. `cms/apps/web/src/hooks/use-chat.ts` — Accept `projectId`, include in request bodies
2. `cms/apps/web/src/components/workspace/chat-panel.tsx` — Pass `projectId` to `useChat()`
3. `cms/apps/web/src/types/chat.ts` — Update `UseChatReturn` and `sendMessage` signatures

## Implementation Steps

### Step 1: Update `useChat` to accept and forward `projectId`

**File:** `cms/apps/web/src/hooks/use-chat.ts`

1. Change `useChat()` signature to accept `projectId`:
   ```typescript
   export function useChat(projectId?: string): UseChatReturn {
   ```

2. Update `buildBody` to include `project_id` in both request types:
   ```typescript
   function buildBody(
     content: string,
     agent: AgentMode,
     history: ChatMessage[],
     projectId?: string,
   ): string {
     if (agent === "scaffolder") {
       return JSON.stringify({
         brief: content,
         stream: true,
         ...(projectId && { project_id: Number(projectId) }),
       });
     }

     const recent = history
       .filter((m) => !m.isStreaming)
       .slice(-19)
       .map((m) => ({ role: m.role, content: m.content }));

     recent.push({ role: "user" as const, content });

     return JSON.stringify({
       messages: recent,
       stream: true,
       ...(projectId && { project_id: Number(projectId) }),
     });
   }
   ```

3. Update the `sendMessage` callback to pass `projectId` through:
   ```typescript
   const body = buildBody(content, agent, messages, projectId);
   ```

### Step 2: Pass `projectId` from `ChatPanel` to `useChat`

**File:** `cms/apps/web/src/components/workspace/chat-panel.tsx`

Change line ~62 from:
```typescript
} = useChat();
```
to:
```typescript
} = useChat(projectId);
```

No other changes needed — `ChatPanel` already receives `projectId` as a prop from the workspace page (`chat-panel.tsx:50,55`).

### Step 3: Update types (if needed)

**File:** `cms/apps/web/src/types/chat.ts`

Only if the `UseChatReturn` type constrains the hook signature. Check if the type needs updating — likely no change since the hook's return type doesn't change, only its input parameter.

## What This Plan Does NOT Cover (Backend-Only)

These BOLA fixes are entirely backend and need no frontend changes:

| Task | Why No Frontend Change |
|------|----------------------|
| 6.1.1 `PATCH /projects/{id}` | Frontend already sends project_id in URL path |
| 6.1.2 `POST /approvals/{id}/decide` | Frontend already sends approval_id; backend resolves project |
| 6.1.3 `POST /connectors/export` | Frontend already sends `project_id` in request body |
| 6.1.4 `POST /qa/results/{id}/override` | Backend resolves project from QA result ID |
| 6.1.5 `GET/POST /approvals/{id}/*` | Frontend already sends `project_id` query param |
| 6.1.6 `POST /rendering/compare` | Backend resolves project from test IDs |
| 6.1.7 `GET /knowledge/documents/{id}/download` | Knowledge stays global (no project scoping) |
| 6.1.8 WebSocket `/ws/stream` | Backend-side tenant isolation on connection |
| **6.1.9 AI agent endpoints** | **This plan handles it** — adding project_id to chat requests |

## Verification

- [ ] `pnpm build` passes (from `cms/`)
- [ ] AI chat sends `project_id` in request body (check Network tab)
- [ ] Scaffolder agent sends `project_id` in request body
- [ ] Existing chat functionality works unchanged when no projectId provided
- [ ] No TypeScript errors
