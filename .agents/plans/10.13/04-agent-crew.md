# 10.13 / Phase 4 — Agent Crew rail

> Make the 9 agents first-class citizens. A left rail of agent cards with live status driven by `useAgUiStream`. Replaces the dropdown-based selection with click-to-focus chat. **Agents appear in the human collaborator avatar stack** (§12 S2).

**Spine:** §4 Phase 4, §12 S1 (selection bus), §12 S2 (agents-as-collaborators), §10 D7 (Context for selection bus).

| | |
|---|---|
| Calendar | 1 week |
| LOC budget | ~900 |
| Dependencies | Phase 3 V1–V14 green (`useAgUiStream` works); `lib/agents/registry.ts` from Phase 0.4; SelectionContext skeleton from Phase 0 |
| Outputs consumed by | Phase 5 (crew rail mounts in left zone of new workspace grid; selection bus is wired in) |
| Locked by spine | 9-agent registry stays canonical (D2: no BE endpoint); semantic colors per N3; cards subscribe to selection bus per S1 |

---

## 1 · Inputs

### Local code

| What | File / Path | Why |
|---|---|---|
| Agent registry stub | `cms/apps/web/src/lib/agents/registry.ts` | From Phase 0.4 — extend with full per-agent metadata |
| `useAgUiStream` hook | `cms/apps/web/src/lib/ag-ui/use-ag-ui-stream.ts` | Phase 3 source of live events |
| EventStore | `cms/apps/web/src/lib/ag-ui/event-store.ts` | For typed event slicing |
| Selection context skeleton | `cms/apps/web/src/lib/selection/SelectionContext.tsx` | Phase 0 stub; Provider lands in Phase 5; we consume via `useSelection()` |
| Existing agent skill metadata | `cms/apps/web/src/hooks/use-agent-skills.ts` | For per-agent skill file count, last calibration |
| Existing chat panel | `cms/apps/web/src/components/workspace/chat-panel.tsx` | Click-to-focus integration target |
| Existing top bar avatar stack | `cms/apps/web/src/app/(dashboard)/layout.tsx` | Where agent avatars join human ones |
| Existing UI primitives | `cms/packages/ui/src/components/ui/{tooltip, badge, avatar}.tsx` | Wrappers, never replace |

---

## 2 · Tasks

### 4.1 — Extend agent registry (~2 h)

**Goal:** flesh out the 9-agent constants file from Phase 0.4 with full metadata used by the crew rail.

**File:** `cms/apps/web/src/lib/agents/registry.ts`

**Extend `AgentDef` shape:**

```typescript
export type AgentDef = {
  id: string;                            // "scaffolder"
  name: string;                          // "Scaffolder"
  short: string;                         // "SC" — 2-letter avatar
  color: SemanticColorToken;             // "primary" | "info" | "warning" | "success" | "secondary"
  role: string;                          // 1-line role description
  defaultLevel: 0 | 1 | 2 | 3;           // pipeline level
  optIn: boolean;                        // false except Innovation
  judgeId?: string;                      // links to judge config
  skillFiles?: number;                   // populated at runtime via `useAgentSkills`
  docHref?: string;                      // link to internal docs
};

export type SemanticColorToken =
  | "primary" | "info" | "warning" | "success" | "secondary" | "danger";

export const AGENTS: readonly AgentDef[] = [
  { id: "scaffolder",      name: "Scaffolder",      short: "SC", color: "primary",   role: "Build email layout from component manifest",          defaultLevel: 1, optIn: false, judgeId: "scaffolder-judge",      docHref: "/docs/agents/scaffolder" },
  { id: "dark-mode",       name: "Dark Mode",       short: "DM", color: "info",      role: "Generate dark variant",                                defaultLevel: 2, optIn: false, judgeId: "dark-mode-judge",        docHref: "/docs/agents/dark-mode" },
  { id: "content",         name: "Content",         short: "CN", color: "warning",   role: "Draft and refine copy",                                defaultLevel: 2, optIn: false, judgeId: "content-judge",          docHref: "/docs/agents/content" },
  { id: "outlook-fixer",   name: "Outlook Fixer",   short: "OF", color: "secondary", role: "MSO ghost-table sweep + Outlook quirks",                defaultLevel: 3, optIn: false, judgeId: "outlook-fixer-judge",    docHref: "/docs/agents/outlook-fixer" },
  { id: "accessibility",   name: "Accessibility",   short: "AX", color: "success",   role: "Alt-text, contrast, WCAG sweep",                       defaultLevel: 3, optIn: false, judgeId: "accessibility-judge",    docHref: "/docs/agents/accessibility" },
  { id: "personalisation", name: "Personalisation", short: "PR", color: "success",   role: "Liquid blocks + fallback chains",                      defaultLevel: 1, optIn: false, judgeId: "personalisation-judge",  docHref: "/docs/agents/personalisation" },
  { id: "code-reviewer",   name: "Code Reviewer",   short: "CR", color: "primary",   role: "Token drift, brand compliance, HITL gate",             defaultLevel: 2, optIn: false, judgeId: "code-reviewer-judge",    docHref: "/docs/agents/code-reviewer" },
  { id: "knowledge",       name: "Knowledge",       short: "KN", color: "info",      role: "Inject proactive warnings from past failures",         defaultLevel: 0, optIn: false, judgeId: "knowledge-judge",        docHref: "/docs/agents/knowledge" },
  { id: "innovation",      name: "Innovation",      short: "IN", color: "secondary", role: "Suggest novel layouts (opt-in)",                       defaultLevel: 0, optIn: true,  judgeId: "innovation-judge",       docHref: "/docs/agents/innovation" },
] as const;
```

**Acceptance:** all 9 agents present; semantic-color-only (§12 N3); types check.

---

### 4.2 — `useAgentRuntime(runId)` hook (~5 h)

**Goal:** derive per-agent live status from `useAgUiStream` events.

**File:** `cms/apps/web/src/hooks/use-agent-runtime.ts`

**Output shape:**

```typescript
export type AgentStatus = {
  agentId: string;
  state: "idle" | "queued" | "running" | "paused" | "succeeded" | "failed";
  level: 0 | 1 | 2 | 3;
  confidence: number | null;             // 0–1, populated on TOOL_CALL_RESULT
  lastAction: string | null;             // human-readable, e.g. "Inverting 4 hero/footer color pairs"
  lastUpdated: string;                   // ISO timestamp
  elapsedMs: number;                     // since start, while running
  proposalsCount: number;                // count of A2UI cards generated this run
  errorMessage: string | null;
};

export function useAgentRuntime(runId: string | null): {
  agents: Record<string, AgentStatus>;   // keyed by agentId
  activeIds: string[];                   // agents currently running or paused
};
```

**Derivation logic:**

| Event seen | Status update |
|---|---|
| `RUN_STARTED` | All agents → `idle`; mark all "queued for level X" based on `defaultLevel` |
| `STEP_STARTED stepName="level-{n}"` | Agents at this level → `running` |
| `STEP_FINISHED stepName="level-{n}"` | Running agents at this level → `succeeded` (unless overridden) |
| `TOOL_CALL_START toolCallName=agentId` | agent → `running`; clear lastAction |
| `TOOL_CALL_CHUNK toolCallName=agentId delta=…` | append to lastAction |
| `TOOL_CALL_END toolCallId` | mark elapsed (now − start) |
| `TOOL_CALL_RESULT content=decision` | parse confidence from decision; agent → `succeeded` |
| `CUSTOM hitl.requested value.agentId` | agent → `paused`; lastAction = pause reason |
| `CUSTOM hitl.resolved` | agent → `running` (if was paused) |
| `RUN_ERROR` | currently-running agent → `failed`; errorMessage = message |
| `RUN_FINISHED` | all `running` → `succeeded` |

**Memoization:** keyed on `events.length` to avoid re-deriving on every render.

**Acceptance:** unit-tested against blueprint stream fixture; produces correct per-agent state at every checkpoint; idle agents stay idle.

---

### 4.3 — `<AgentCrewPanel />` (~6 h)

**Goal:** the left-rail panel containing the 9 agent cards + pipeline header.

**File:** `cms/apps/web/src/components/workspace/agent-crew/AgentCrewPanel.tsx`

**Anatomy:**

```
┌──────────────────────────────────────────┐
│ AGENT CREW                  [Pipeline ▾] │
│ 9 agents · 4 active · pipeline full-build│
├──────────────────────────────────────────┤
│ Run #bp_412 · iter 2/3                   │
│ Stage Level 2/4 — content + design       │
│ Tokens 14,820 / 60k · $0.18              │
│ ███░░░░░░░ 42%                           │
├──────────────────────────────────────────┤
│ ┌────────────────────────────────────┐  │
│ │ [SC] Scaffolder  v0.4.2     ✓     │  │
│ │ Built layout from 7 components ... │  │
│ │ ████████░░ conf 0.94 · 3.4s · L1   │  │
│ └────────────────────────────────────┘  │
│ ┌────────────────────────────────────┐  │
│ │ [DM] Dark Mode   v0.3.1 [running]  │  │
│ │ Inverting 4 hero/footer pairs ...  │  │
│ │ ████░░░░░░ conf 0.62 · L2 · 1.8s   │  │
│ └────────────────────────────────────┘  │
│ ... (7 more) ...                         │
└──────────────────────────────────────────┘
```

**Width:** 312 px (matches mockup).
**Scroll:** vertical; pipeline header sticky on top.
**Empty state (no run):** "No active run. Press ⌘⇧G to generate." (§12 N4).

**Pipeline header:**

```typescript
type PipelineHeaderProps = {
  runId: string | null;
  totalLevels: number;        // 4 for full-build
  currentLevel: number;
  tokensUsed: number;
  tokenBudget: number;
  costUsd: number;
  progress: number;           // 0..1
};
```

Subcomponent: `<PipelineHeader />` in `agent-crew/PipelineHeader.tsx`.

**Selection wiring (S1):**

When user selects a section on canvas (Phase 5), `useSelection().selection.agentIds` lists agents owning that section. The crew rail highlights those cards with a gold ring (`outline-2 outline-warning` or equivalent semantic token).

```tsx
const { selection } = useSelection();
const isHighlighted = selection.agentIds.includes(agent.id);
return <AgentCrewCard agent={agent} status={status} highlighted={isHighlighted} />;
```

**Acceptance:** rail renders, scroll works, empty state present, selection highlight responds within 1 frame.

---

### 4.4 — `<AgentCrewCard />` (~5 h)

**Goal:** single agent card. Compact, expandable. Action surface on click.

**File:** `cms/apps/web/src/components/workspace/agent-crew/AgentCrewCard.tsx`

**Props:**

```typescript
type Props = {
  agent: AgentDef;
  status: AgentStatus;
  highlighted: boolean;            // gold ring per S1
  onFocus: (agentId: string) => void;   // click → chat focus
};
```

**States:**

| state | visual cue |
|---|---|
| idle | muted text, gray status dot |
| queued | "queued" badge in info color |
| running | warning-color "running" badge + pulsing dot, current lastAction visible |
| paused | tertiary-accent "review" badge (pause icon), full reason visible |
| succeeded | success-color check + last conf bar + elapsed |
| failed | danger-color X + errorMessage truncated to 1 line |

**Expand-on-click:** card grows to show:
- recent proposals count + link to chat-filtered-by-agent
- last 3 events from `EventStore.byTool(agentId)`
- "Open in chat" button (S2 — focus chat to this agent)
- "View doc" link (uses `agent.docHref`)

**Avatar:** circle, `agent.short` text, semantic color (never hex). Status dot bottom-right.

**A11y:**

- Keyboard: focusable, Enter expands, Tab navigates
- Screen reader: `aria-label="Scaffolder agent — running, confidence 0.94, level 1"`
- Status changes announced via `aria-live="polite"` region (optional, debounced)

**Acceptance:** all 6 states render in storybook, both themes; click → focus works; expanded view loads agent's last 3 events.

---

### 4.5 — Click-to-focus chat (~3 h)

**Goal:** clicking an agent card prefills the chat input with `@AgentName` and filters chat history to that agent's lineage.

**Files:**

- `cms/apps/web/src/components/workspace/chat/chat-panel.tsx` (extend, additive)
- `cms/apps/web/src/components/workspace/chat-panel.tsx` (selector dropdown stays as keyboard fallback)

**Flow:**

1. User clicks `<AgentCrewCard />`
2. `onFocus(agentId)` → updates `useChat`'s `agent` state to `agentId`
3. Chat input prefills with `@${agent.name}: ` (cursor after colon)
4. Optional: chat history view filters to that agent's messages (toggle)

**Spine §12 S2 emphasis:** the click should feel like *selecting a teammate*, not *changing a setting*. UX cue: chat input briefly pulses on focus (200 ms, respects reduced-motion).

**Acceptance:** clicking each of the 9 cards focuses chat correctly; existing dropdown still works for keyboard users; pulse respects `prefers-reduced-motion`.

---

### 4.6 — Agents in the human collaborator avatar stack (~3 h)

**Goal:** §12 S2 — agents that are currently `running` or `paused` appear in the top-bar avatar stack alongside human collaborators.

**Files:**

- `cms/apps/web/src/components/collaboration/PresenceStack.tsx` (modify)
- `cms/apps/web/src/components/collaboration/AgentPresenceAvatar.tsx` (new)

**Visual distinction:**

- Agent avatars use `agent.short` initials with `bg-color-{agent.color}`
- A small "AI" sparkle glyph (Lucide `Sparkles` icon) overlays the avatar bottom-right
- Tooltip: "Scaffolder · running · level 1"

**Source of truth:** `useAgentRuntime(runId)` → `activeIds` → render an `AgentPresenceAvatar` for each.

**Order:** humans first (existing order), then agents. Cap stack at 6 visible; "+N" overflow chip.

**Acceptance:** during a run, top-bar shows humans + active agents; avatars update reactively as agents start/finish.

---

### 4.7 — Storybook + tests (~3 h)

**Coverage:**

- `AgentCrewPanel/Default` — full 9-card list, no run
- `AgentCrewPanel/RunInProgress` — 4 active, 5 queued
- `AgentCrewPanel/Paused` — Code Reviewer in HITL
- `AgentCrewPanel/Errored` — Outlook Fixer failed
- `AgentCrewCard/Idle`, `Running`, `Paused`, `Succeeded`, `Failed`, `Highlighted`
- `PipelineHeader/Empty`, `Active`, `Completed`
- `AgentPresenceAvatar/Default`, `WithTooltip`

**Tests:**

- `useAgentRuntime` derivation against blueprint fixture
- Crew rail responds to selection bus highlight (mock SelectionContext)
- Click → chat focus integration test

**Acceptance:** chromatic shows both themes for every story; unit tests pass.

---

## 3 · Verification gates

| # | Check | How |
|---|---|---|
| V1 | All 9 agents render in rail | manual + snapshot |
| V2 | Per-agent state derivation correct against fixture | unit |
| V3 | Pipeline header reflects live token/cost/level | manual against running blueprint |
| V4 | Selection bus highlight responds within 1 frame | Playwright with timing |
| V5 | Click-card → chat focus works for all 9 | e2e |
| V6 | Top-bar avatar stack shows agents alongside humans during run | visual |
| V7 | Reduced-motion: no pulse animation | manual with system pref |
| V8 | A11y: keyboard navigation through rail; screen reader announcements | axe + manual |
| V9 | Empty state copy + CTA per N4 | snapshot |
| V10 | Dark + light parity | chromatic |
| V11 | Bundle delta ≤ 14 KB gz | `pnpm analyze` |
| V12 | Existing dropdown agent-selector still works as fallback | manual |
| V13 | Backend untouched | `git diff` |

---

## 4 · Decisions to lock in this phase

| ID | Question | Default |
|---|---|---|
| D4.1 | Crew rail width | **312 px** (matches mockup) |
| D4.2 | Card expand interaction | **click-to-toggle** (not hover); avoids accidental open during scroll |
| D4.3 | Status announcements (aria-live) | **debounced 1s**; only on state transition |
| D4.4 | Selection-bus highlight color | **`outline-warning` token** (gold) — never hex |
| D4.5 | Avatar stack cap before +N overflow | **6 visible** |
| D4.6 | Innovation agent default visibility | **shown but greyed** with "opt-in" pill |
| D4.7 | Recent events shown when expanded | **last 3** from `EventStore.byTool(agentId)` |

Record in `docs/decisions/D-007-agent-crew-locks.md`.

---

## 5 · Pitfalls

- **Don't hardcode agent colors as hex.** §12 N3. Always semantic tokens.
- **Don't poll backend for agent state.** Source of truth is `useAgUiStream` events, derived in `useAgentRuntime`. Adding a separate poll defeats the symbiotic-system goal.
- **Don't break the existing dropdown.** Keyboard users may rely on it. The crew rail is *additional* primary surface, not a replacement.
- **Don't render avatars for idle agents in the top stack.** Only `running` and `paused` agents qualify (§12 S2 — "active agents").
- **Don't tightly couple to runId === null.** Empty state must work with no run; rail should still show the 9 agents in idle state with helpful CTAs.
- **Don't trigger re-render storms.** `useAgentRuntime` returns memoized `Record<string, AgentStatus>`; cards check identity equality before re-rendering.
- **Don't leak the avatar stack across pages.** Only show on workspace route (where there's an active run); hide on Approvals/Renderings/etc.
- **Don't make selection highlight too visually loud.** Subtle gold ring; should not disturb scanning the list.

---

## 6 · Hand-off to Phase 5

Phase 5 (Workspace re-layout) consumes:

- `<AgentCrewPanel />` — mounts in left zone of new grid
- `useSelection` / `SelectionContext` — Phase 5 implements the Provider; Phase 4 cards already consume it
- `useAgentRuntime` — Phase 5 might surface per-agent attention indicators on canvas

When Phase 4 closes, the next agent reads:

1. Spine §12 (especially S1 — selection bus)
2. Phase 4 V1–V13 verification table
3. `10.13/05-workspace-layout.md`
4. Existing workspace page structure: `cms/apps/web/src/app/projects/[id]/workspace/page.tsx`

**End-state of Phase 4:** crew rail visible on workspace; agents update live during runs; selection bus highlights respond; agents show in collaborator stack; backend untouched; bundle delta ≤ 14 KB.
