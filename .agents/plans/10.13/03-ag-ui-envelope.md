# 10.13 / Phase 3 — AG-UI envelope over existing endpoints

> Wrap the existing progress/blueprint/chat polling in a unified, canonical AG-UI event stream. Frontend-only — backend untouched. **Use the canonical 17-event vocabulary verbatim** (spine §13). Polling at 1s via `useSmartPolling`; future phase swaps transport without consumer code changes.

**Spine:** §4 Phase 3, §13 References (R2), §12 S5/S8 (live ripple cues, no fire-and-forget), §10 D6 (polling interval).

| | |
|---|---|
| Calendar | 1 week |
| LOC budget | ~1100 |
| Dependencies | Phase 0 V1–V8 green; Phase 1 chip shipped (chrome pattern reuse); Phase 2 parser + EMAIL_HUB_CATALOG available (TOOL_CALL_RESULT can carry A2UI specs) |
| Outputs consumed by | Phase 4 (`useAgentRuntime` derives per-agent status from events), Phase 5 (event ripple cues, HITL pause card, stream tab in chat panel) |
| Locked by spine | Canonical event names only (§13 R2); polling 1s/5s (D6); no SSE in v1 (deferred to 11a) |

---

## 1 · Inputs

### Local code

| What | File / Path | Why |
|---|---|---|
| Skeleton | `cms/apps/web/src/lib/ag-ui/{envelope.ts, index.ts}` | Stub from Phase 0.4 |
| Smart polling | `cms/apps/web/src/hooks/use-smart-polling.ts` | Visibility-aware refresh; this is our transport |
| Progress hook | `cms/apps/web/src/hooks/use-progress.ts` | Wraps `/api/v1/progress/{id}` |
| Blueprint run hook | `cms/apps/web/src/hooks/use-blueprint-run.ts` | Streams blueprint chunks |
| Chat hook | `cms/apps/web/src/hooks/use-chat.ts` | Existing message stream |
| Progress fixture | `cms/apps/web/src/lib/a2ui/__fixtures__/progress-{mid,done}.json` | Captured Phase 0.1 |
| Blueprint stream fixture | `cms/apps/web/src/lib/a2ui/__fixtures__/blueprint-stream-chunks.jsonl` | Captured Phase 0.1 |
| HITL fixture | `cms/apps/web/src/lib/a2ui/__fixtures__/hitl-pause.json` | Captured Phase 0.1 |
| Approval / override endpoints | existing connectors | HITL resume routes through existing approve/override flows |
| A2UI parser (Phase 2) | `cms/apps/web/src/lib/a2ui/parser.ts` | TOOL_CALL_RESULT may carry A2UI JSONL |

### External primary sources

| Ref | Source | Time |
|---|---|---|
| R2 | AG-UI events doc — `https://docs.ag-ui.com/concepts/events` | 30 min — re-read; binding |
| R2b | AG-UI repo TS types — `https://github.com/ag-ui-protocol/ag-ui` | 20 min — crib type shapes (don't depend on it) |
| R2c | Master 17 events blog — `https://www.copilotkit.ai/blog/master-the-17-ag-ui-event-types-for-building-agents-the-right-way` | 15 min — plain-English category overview |

---

## 2 · Tasks

### 3.1 — Envelope types (~3 h)

**Goal:** discriminated union typing every canonical event. **Use the names from spine §13 verbatim.**

**File:** `cms/apps/web/src/lib/ag-ui/envelope.ts`

**Sketch:**

```typescript
// Base envelope — every event has these
export type AgUiEventBase = {
  type: AgUiEventType;
  timestamp: string;          // ISO-8601
  rawEvent?: unknown;         // optional pass-through of source payload
};

export type AgUiEventType =
  // Lifecycle (5)
  | "RUN_STARTED" | "RUN_FINISHED" | "RUN_ERROR"
  | "STEP_STARTED" | "STEP_FINISHED"
  // Text Message (4)
  | "TEXT_MESSAGE_START" | "TEXT_MESSAGE_CONTENT" | "TEXT_MESSAGE_END" | "TEXT_MESSAGE_CHUNK"
  // Tool Call (5)
  | "TOOL_CALL_START" | "TOOL_CALL_ARGS" | "TOOL_CALL_END" | "TOOL_CALL_RESULT" | "TOOL_CALL_CHUNK"
  // State (3)
  | "STATE_SNAPSHOT" | "STATE_DELTA" | "MESSAGES_SNAPSHOT"
  // Special (2)
  | "RAW" | "CUSTOM";

// === Lifecycle ===
export type RunStarted   = AgUiEventBase & { type: "RUN_STARTED";  threadId: string; runId: string };
export type RunFinished  = AgUiEventBase & { type: "RUN_FINISHED"; threadId: string; runId: string };
export type RunError     = AgUiEventBase & { type: "RUN_ERROR";    message: string; runId?: string };
export type StepStarted  = AgUiEventBase & { type: "STEP_STARTED"; stepName: string };
export type StepFinished = AgUiEventBase & { type: "STEP_FINISHED";stepName: string };

// === Text Message ===
export type TextMessageStart   = AgUiEventBase & { type: "TEXT_MESSAGE_START";   messageId: string; role: "user" | "assistant" | "system" };
export type TextMessageContent = AgUiEventBase & { type: "TEXT_MESSAGE_CONTENT"; messageId: string; delta: string };
export type TextMessageEnd     = AgUiEventBase & { type: "TEXT_MESSAGE_END";     messageId: string };
export type TextMessageChunk   = AgUiEventBase & { type: "TEXT_MESSAGE_CHUNK";   delta: string };

// === Tool Call ===
export type ToolCallStart  = AgUiEventBase & { type: "TOOL_CALL_START";  toolCallId: string; toolCallName: string };
export type ToolCallArgs   = AgUiEventBase & { type: "TOOL_CALL_ARGS";   toolCallId: string; delta: string };
export type ToolCallEnd    = AgUiEventBase & { type: "TOOL_CALL_END";    toolCallId: string };
export type ToolCallResult = AgUiEventBase & { type: "TOOL_CALL_RESULT"; messageId: string; toolCallId: string; content: string | unknown };
export type ToolCallChunk  = AgUiEventBase & { type: "TOOL_CALL_CHUNK";  toolCallId: string; toolCallName: string; delta: string };

// === State ===
export type StateSnapshot    = AgUiEventBase & { type: "STATE_SNAPSHOT";    snapshot: unknown };
export type StateDelta       = AgUiEventBase & { type: "STATE_DELTA";       delta: unknown };           // JSON Patch
export type MessagesSnapshot = AgUiEventBase & { type: "MESSAGES_SNAPSHOT"; messages: unknown[] };

// === Special ===
export type RawEvent    = AgUiEventBase & { type: "RAW";    event: unknown; source?: string };
export type CustomEvent = AgUiEventBase & { type: "CUSTOM"; name: AgUiCustomName; value: unknown };

// === Email-Hub-specific CUSTOM event names (binding from spine §13) ===
export type AgUiCustomName =
  | "contract.validated"
  | "contract.failed"
  | "hitl.requested"
  | "hitl.resolved"
  | "eval.verdict"
  | "knowledge.warnings"
  | "artifact.stored"
  | "calibration.delta";

export type AgUiEvent =
  | RunStarted | RunFinished | RunError | StepStarted | StepFinished
  | TextMessageStart | TextMessageContent | TextMessageEnd | TextMessageChunk
  | ToolCallStart | ToolCallArgs | ToolCallEnd | ToolCallResult | ToolCallChunk
  | StateSnapshot | StateDelta | MessagesSnapshot
  | RawEvent | CustomEvent;

export function isToolCallResult(e: AgUiEvent): e is ToolCallResult {
  return e.type === "TOOL_CALL_RESULT";
}
// ... narrowing helpers per event type
```

**Acceptance:** `pnpm tsc --noEmit` clean; types parse blueprint stream fixture correctly.

---

### 3.2 — `useAgUiStream(runId)` hook (~5 h)

**Goal:** the consumer-facing API. Subscribers get `{ events, status, latest, send }`.

**File:** `cms/apps/web/src/lib/ag-ui/use-ag-ui-stream.ts`

**Sketch:**

```typescript
import { useMemo } from "react";
import { useSmartPolling } from "@/hooks/use-smart-polling";
import { useProgress } from "@/hooks/use-progress";
import { useBlueprintRun } from "@/hooks/use-blueprint-run";
import { progressToEvents } from "./adapters/progress";
import { blueprintToEvents } from "./adapters/blueprint";
import type { AgUiEvent } from "./envelope";
import { EventStore } from "./event-store";

export type StreamStatus = "idle" | "running" | "paused" | "completed" | "errored";

export function useAgUiStream(runId: string | null): {
  events: AgUiEvent[];
  status: StreamStatus;
  latest: AgUiEvent | null;
  send: (action: { kind: "resume" | "abort" | "approve"; payload?: unknown }) => Promise<void>;
} {
  const { data: progress } = useProgress(runId, {
    refreshInterval: useSmartPolling({ visible: 1000, blurred: 5000 }),
  });
  const { data: blueprintChunks } = useBlueprintRun(runId);

  const events = useMemo(() => {
    const store = new EventStore({ maxSize: 200 });
    if (progress) for (const e of progressToEvents(progress, runId!)) store.append(e);
    if (blueprintChunks) for (const e of blueprintToEvents(blueprintChunks, runId!)) store.append(e);
    return store.snapshot();
  }, [progress, blueprintChunks, runId]);

  const status = deriveStatus(events);
  const latest = events.at(-1) ?? null;

  const send = useCallback(async (action) => {
    // Routes through existing endpoints — see 3.8
    if (action.kind === "resume") return resumeBlueprint(runId!, action.payload);
    if (action.kind === "approve") return approveProposal(runId!, action.payload);
    if (action.kind === "abort")   return abortBlueprint(runId!);
  }, [runId]);

  return { events, status, latest, send };
}
```

**Acceptance:** unit-tested with progress + blueprint fixtures; status derivation correct (RUN_STARTED → "running", RUN_FINISHED → "completed", RUN_ERROR → "errored", `hitl.requested` CUSTOM → "paused").

---

### 3.3 — Progress adapter (~3 h)

**Goal:** translate `ProgressEntry` (existing) into AG-UI events.

**File:** `cms/apps/web/src/lib/ag-ui/adapters/progress.ts`

**Mapping:**

| `ProgressEntry` field | AG-UI event |
|---|---|
| `status === "started"` | `RUN_STARTED` (threadId = `progress.thread`, runId) |
| `status === "completed"` | `RUN_FINISHED` |
| `status === "failed"` | `RUN_ERROR` (message = error reason) |
| `current_step` change | `STEP_STARTED` for the new step, `STEP_FINISHED` for the previous |
| `metadata.proactive_warnings` | `CUSTOM` (`name: "knowledge.warnings"`, `value`) |

**Sketch:**

```typescript
export function progressToEvents(p: ProgressEntry, runId: string): AgUiEvent[] {
  const out: AgUiEvent[] = [];
  if (p.status === "started")  out.push({ type: "RUN_STARTED", threadId: p.thread ?? p.id, runId, timestamp: p.started_at });
  if (p.status === "completed")out.push({ type: "RUN_FINISHED", threadId: p.thread ?? p.id, runId, timestamp: p.ended_at ?? new Date().toISOString() });
  if (p.status === "failed")   out.push({ type: "RUN_ERROR", message: p.error ?? "unknown", runId, timestamp: p.ended_at ?? new Date().toISOString() });
  for (const step of p.steps ?? []) {
    out.push({ type: step.ended ? "STEP_FINISHED" : "STEP_STARTED", stepName: step.name, timestamp: step.started_at });
  }
  if (p.metadata?.proactive_warnings)
    out.push({ type: "CUSTOM", name: "knowledge.warnings", value: p.metadata.proactive_warnings, timestamp: p.updated_at });
  return out;
}
```

**Idempotency:** repeated polls return the same events; the EventStore dedupes by `(type, timestamp, key)`.

**Acceptance:** fixture-driven test produces the expected event sequence.

---

### 3.4 — Blueprint stream adapter (~4 h)

**Goal:** translate blueprint stream chunks into AG-UI events. This is the richest source — agents, tool calls, contract validations, HITL.

**File:** `cms/apps/web/src/lib/ag-ui/adapters/blueprint.ts`

**Mapping (binding):**

| Blueprint event (existing) | AG-UI event |
|---|---|
| `level.entered` | `STEP_STARTED` (`stepName: "level-{n}"`) |
| `level.exited` | `STEP_FINISHED` |
| `agent.started(agent_id)` | `TOOL_CALL_START` (`toolCallName: agent_id`, `toolCallId`) |
| `agent.streaming.text(delta)` | `TOOL_CALL_CHUNK` (`delta`, `toolCallName: agent_id`) |
| `agent.completed(decision_json)` | `TOOL_CALL_END` + `TOOL_CALL_RESULT` (`content: decision_json`) |
| `agent.errored(message)` | `RUN_ERROR` (`message`) |
| `contract.validated(result)` | `CUSTOM` (`name: "contract.validated"`, `value: result`) |
| `contract.failed(result)` | `CUSTOM` (`name: "contract.failed"`, `value: result`) |
| `hitl.paused(payload)` | `CUSTOM` (`name: "hitl.requested"`, `value: payload`) |
| `hitl.resumed` | `CUSTOM` (`name: "hitl.resolved"`) |
| `evaluator.verdict(verdict)` | `CUSTOM` (`name: "eval.verdict"`, `value`) |
| `artifact.stored(artifact)` | `CUSTOM` (`name: "artifact.stored"`, `value`) |

**Special: A2UI in `TOOL_CALL_RESULT.content`.** When an agent's decision JSON is convertible to an A2UI spec (via Phase 2 adapters), the adapter MAY synthesize the spec inline:

```typescript
if (decision.kind === "build_summary") {
  const a2uiSpec = decisionsToA2UI(decision);          // from Phase 2
  out.push({
    type: "TOOL_CALL_RESULT",
    toolCallId,
    messageId,
    content: a2uiSpec,   // array of A2UIMessage
    timestamp: now,
  });
}
```

This is the bridge: agents emit decisions → adapter wraps as TOOL_CALL_RESULT carrying A2UI → consumers (Phase 5 chat) feed to `<A2UIRenderer />`.

**Acceptance:** fixture `blueprint-stream-chunks.jsonl` produces an event sequence with at least: 1× RUN_STARTED, 2× STEP_STARTED, 4× TOOL_CALL_START/END pairs, 1× TOOL_CALL_RESULT carrying A2UI, 1× RUN_FINISHED.

---

### 3.5 — Chat stream adapter (~2 h)

**Goal:** translate chat-only flows (agent responses outside a blueprint run) into AG-UI events.

**File:** `cms/apps/web/src/lib/ag-ui/adapters/chat.ts`

**Mapping:**

| Chat event | AG-UI event |
|---|---|
| user message | `TEXT_MESSAGE_START` (role=user) + `TEXT_MESSAGE_CONTENT` + `TEXT_MESSAGE_END` |
| assistant streaming chunk | `TEXT_MESSAGE_CHUNK` |
| assistant final + structured payload | `TOOL_CALL_RESULT` carrying A2UI if convertible |

**Acceptance:** chat fixtures from Phase 0.1 (Scaffolder, Dark Mode, Content, Outlook Fixer) all map to coherent event sequences.

---

### 3.6 — Event store (~3 h)

**Goal:** bounded buffer with dedupe, ordering, replay.

**File:** `cms/apps/web/src/lib/ag-ui/event-store.ts`

**API:**

```typescript
export class EventStore {
  constructor(opts?: { maxSize?: number });
  append(event: AgUiEvent): boolean;     // returns false if duplicate
  snapshot(): readonly AgUiEvent[];
  clear(): void;
  byType<T extends AgUiEvent["type"]>(type: T): readonly Extract<AgUiEvent, { type: T }>[];
  byCustomName(name: AgUiCustomName): readonly CustomEvent[];
}
```

**Dedupe key:** `${type}:${timestamp}:${primaryId}` where `primaryId` is `runId` / `messageId` / `toolCallId` / `stepName` depending on type.

**Bounded buffer:** when exceeding `maxSize` (default 200), evict oldest. Emit a "history-truncated" warning to console once per run.

**Acceptance:** 1000-event torture test runs without leak; dedup works; ordering preserved by timestamp.

---

### 3.7 — `<StreamLog />` component (~5 h)

**Goal:** terminal-style live event log. Sticky scroll. Filterable. Color-coded.

**File:** `cms/apps/web/src/lib/ag-ui/StreamLog.tsx`

**Anatomy (user-visible text per spine §1.6 — no protocol names):**

```
┌────────────────────────────────────────────────────┐
│ Pipeline activity · #bp_412               ● live   │
├────────────────────────────────────────────────────┤
│ 09:42:01 Knowledge   ▸ Warnings recalled (×4)      │
│ 09:42:02 Pipeline    ▸ Step 1 started              │
│ 09:42:05 Scaffolder  ▸ Completed · conf 0.94       │
│ 09:42:09 Code Review ▸ Brand check failed          │
│ ...                                                │
├────────────────────────────────────────────────────┤
│ Filter: [ All ] [ Pipeline ] [ Agents ] [ Issues ] │
└────────────────────────────────────────────────────┘
```

**Translation layer:** the internal event types (`RUN_STARTED`, `TOOL_CALL_END`, `CUSTOM { name: "contract.failed" }`) are mapped to human-readable lines via a `formatEventForDisplay()` pure function in `lib/ag-ui/format.ts`. The raw event JSON is available via the **admin-only** "Inspect" pill (Phase 2.8), gated behind admin role + `?inspector=1`.

**Filter labels:** "Pipeline" (lifecycle events), "Agents" (tool calls), "Issues" (errors + failed checks), "All". Never expose category names like "Lifecycle / Tool Call / State Management" to users.

**Features:**

- Fixed-row height for virtualization (use `react-virtuoso` if dep already there, else manual windowing)
- Sticky-scroll: stays at bottom if user is at bottom; pauses auto-scroll if user scrolls up
- Filter chips: by category (Lifecycle/Text/Tool/State/Custom) and by source (`agentId`)
- Click event row → expand to show raw payload (Shiki)
- Status colors per spine §12 N3 (success/warn/danger/info)
- Reduced-motion: no animation on row enter

**Acceptance:** renders 200-event fixture; filter works; sticky scroll behavior tested; no memory leak.

---

### 3.8 — HITL integration (~4 h)

**Goal:** when `hitl.requested` arrives, render an `<HitlPauseCard />` (from Phase 2 catalog) inline. User actions (Resume / Override / Ask agent) route to existing endpoints.

**File:** `cms/apps/web/src/lib/ag-ui/use-hitl.ts`

**Flow:**

1. `useAgUiStream` emits `CUSTOM { name: "hitl.requested", value: pausePayload }`
2. Phase 5 chat panel renders an A2UI message containing `<HitlPauseCard />` populated from `pausePayload`
3. User clicks "Resume" → `useAgUiStream.send({ kind: "resume", payload: choice })`
4. `send` calls existing `POST /api/v1/blueprints/{runId}/resume` (already exists for HITL gates)
5. Backend resumes pipeline; next poll surfaces `CUSTOM { name: "hitl.resolved" }`

**Routes used (existing, not new):**

- `POST /api/v1/blueprints/{runId}/resume` — resume with decision
- `POST /api/v1/qa/{templateId}/override` — for QA-failure HITL
- `POST /api/v1/approvals/{id}/decide` — for approval HITL

**Acceptance:** HITL fixture from Phase 0.1 triggers card render; "Resume" submits to the right endpoint; `hitl.resolved` arrives within ≤ 1.5s.

---

### 3.9 — Stream tab in chat panel (~2 h)

**Goal:** add an "Event Log" tab to the existing chat panel. Existing tabs (Conversation, History) stay.

**File:** `cms/apps/web/src/components/workspace/chat-panel.tsx` (extend, additive)

**Tabs after change:** `Conversation` | `Event Log` | `Eval Trace` (Phase 6) | `History`. Active run gets a small live-dot on the Event Log tab.

**Toggle behavior:** ⌘. opens contract inspector (Phase 2); separate shortcut **⌘L** opens the Event Log tab.

**Acceptance:** existing chat unchanged; new tab renders `<StreamLog />`; live dot updates on new events.

---

## 3 · Verification gates

| # | Check | How |
|---|---|---|
| V1 | Envelope types parse v0.8 example sequence without `as any` | unit |
| V2 | Polling at 1s visible / 5s blurred | observe in DevTools network tab |
| V3 | Progress adapter: fixture → expected event sequence | unit |
| V4 | Blueprint adapter: fixture → expected event sequence including A2UI in TOOL_CALL_RESULT | unit |
| V5 | Chat adapter: fixture → coherent text-message + tool-call mix | unit |
| V6 | EventStore: dedup, ordering, eviction work | unit + torture test |
| V7 | StreamLog renders 200 events without lag (60 fps scroll) | manual + Lighthouse |
| V8 | HITL flow end-to-end: paused → user clicks Resume → resumed | e2e |
| V9 | Status derivation: idle/running/paused/completed/errored | unit |
| V10 | No new BE endpoints called | network audit during e2e |
| V11 | A11y: StreamLog keyboard-navigable, screen-reader-friendly | axe |
| V12 | Reduced-motion respected (no row-enter animation) | manual with system pref |
| V13 | Bundle size delta ≤ 18 KB gz on workspace route | `pnpm analyze` |
| V14 | `pnpm tsc && pnpm test` clean | CI |

---

## 4 · Decisions to lock in this phase

| ID | Question | Default |
|---|---|---|
| D3.1 | Polling interval visible | **1000 ms** (D6) |
| D3.2 | Polling interval blurred | **5000 ms** (D6) |
| D3.3 | EventStore size | **200** events; emit warning on truncation |
| D3.4 | Status mapping for paused state | **`hitl.requested` CUSTOM event → "paused"** |
| D3.5 | StreamLog row virtualization | **manual windowing** if react-virtuoso not in deps; else use it |
| D3.6 | Tool call boundary for agents | **one `TOOL_CALL_*` group per agent invocation** |
| D3.7 | A2UI surface id convention | `bp-{runId}-step-{n}-{agentId}` |
| D3.8 | RAW event handling | preserve in store; render in StreamLog as italic muted row |

Record in `docs/decisions/D-006-ag-ui-locks.md`.

---

## 5 · Pitfalls

- **Don't invent event names.** §13 R2 is binding. Email-Hub specifics live under `CUSTOM` with allowed names from the union (§3.1 above).
- **Don't poll while tab is hidden.** `useSmartPolling` already handles this — confirm visible/blurred branches both trigger.
- **Don't accumulate events forever.** EventStore caps at 200. Long runs lose history; if needed, persist to IndexedDB in Phase 11a.
- **Don't double-count events.** A run can be observed via both progress and blueprint streams. Dedup key must reconcile.
- **Don't tightly couple StreamLog to a specific run.** It takes events as a prop; future phases may show pre-run history or multiple runs.
- **Don't bypass A2UI parser for TOOL_CALL_RESULT.** When `content` is JSONL, feed to `parseA2UIJsonl`; when it's plain JSON, treat as the decision payload directly. Store both — the parser may not exhaust all formats in v1.
- **Don't fire-and-forget HITL resumes.** Optimistic UI per §12 S6: show "resuming…" toast, roll back on error.
- **Don't expose RawEvent payloads to non-admins.** They may contain stack traces. Gate `RAW` rendering by user role (existing role check via `useAuth`).

---

## 6 · Hand-off to Phase 4

Phase 4 (Agent Crew rail) consumes:

- `useAgUiStream` — to derive per-agent status from `TOOL_CALL_*` events (`toolCallName === agentId`)
- The custom event vocabulary — to know when an agent is "paused waiting for HITL"
- `EventStore.byType("TOOL_CALL_RESULT")` and `byCustomName("contract.failed")` — for confidence/error counts on the crew cards

When Phase 3 closes, the next agent reads:

1. Spine §13 (event mapping)
2. Phase 3 V1–V14 verification table
3. `10.13/04-agent-crew.md`
4. Phase 0 fixtures + the EventStore unit tests

**End-state of Phase 3:** `useAgUiStream(runId)` returns a live event list within ≤ 1.5s of backend changes; HITL pause card actionable end-to-end; bundle delta ≤ 18 KB; backend untouched.
