# 10.13 / Phase 0 — Pre-flight

> Capture the inputs, lock the architectural decisions, and stand up empty module skeletons that subsequent phases fill. **No user-visible behavior changes in this phase.**

**Spine:** see `.agents/plans/10.13-agentic-ui-frontend-adoption.md` §4 Phase 0, §12 (UX principles), §10 (decisions).

| | |
|---|---|
| Calendar | 1–2 working days |
| LOC budget | ~250 (mostly types + fixtures, almost no logic) |
| Dependencies | none — this is the entry phase |
| Outputs consumed by | Phase 1 (fixtures + skeleton), Phase 2 (decisions + spec stub), Phase 3 (envelope stub), Phase 5 (selection bus) |

---

## 1 · Inputs (read these first)

### Local code

| What | File | Why |
|---|---|---|
| Existing chat response shape | `cms/apps/web/src/types/chat.ts` | Source of `ChatMessage`, `AgentMode`, streaming chunk types |
| Blueprint run shape | `cms/apps/web/src/types/blueprint-runs.ts` | Source of `BlueprintRunResponse`, run lifecycle |
| QA result shape | `cms/apps/web/src/types/qa.ts` | Source of `QAResultResponse`, per-check schema |
| Agent skill metadata | `cms/apps/web/src/types/agent-skills.ts` | Source of `AgentSkillManifest` |
| Failure patterns | `cms/apps/web/src/types/failure-patterns.ts` | Source of `FailurePattern`, knowledge hits |
| Existing progress hook | `cms/apps/web/src/hooks/use-progress.ts` | Wraps `/api/v1/progress/{id}`; we'll wrap this in Phase 3 |
| Smart polling primitive | `cms/apps/web/src/hooks/use-smart-polling.ts` | Visibility-aware SWR refresh; AG-UI uses it as transport |
| Token system | `cms/packages/ui/src/tokens.css` | The "locked" 3-tier system; Phase 1 reads this at runtime |
| Tailwind config | `cms/packages/ui/src/globals.css` | Confirm `@theme` block emits CSS vars on `:root` |
| Backend decision schemas (read-only reference) | `app/ai/agents/schemas/*_decisions.py` | What agents emit today; fixtures need to match |

### External primary sources (≤ 2 h to scan all)

> **All cited in spine §13.** Read in this order before Task 0.3.

| # | Source | Time | Why |
|---|---|---|---|
| R1 | A2UI v0.8 spec — `https://a2ui.org/specification/v0.8-a2ui/` | 30 min | The canonical wire format. Phase 2 must be compatible with this OR consciously diverge with a recorded rationale. **Key facts to internalize: JSONL streaming with 4 message types (`surfaceUpdate`, `dataModelUpdate`, `beginRendering`, `deleteSurface`); adjacency-list components, not nested trees; standard catalog is primitives only (Text/Row/Column/Button/Card/Image/List); custom catalogs allowed; data binding via paths (`{path: "/data/x"}`) vs literals (`{literalString: "x"}`).** |
| R2 | AG-UI events — `https://docs.ag-ui.com/concepts/events` | 30 min | The 17 canonical events grouped into 5 categories. **Phase 3 must use these names verbatim** — no inventing `pipeline.start` etc. Mapping table is in spine §13 |
| R3 | CopilotKit "build with A2UI + AG-UI" blog — `https://www.copilotkit.ai/blog/build-with-googles-new-a2ui-spec-agent-user-interfaces-with-a2ui-ag-ui` | 20 min | Shows the integration pattern: agent emits A2UI JSONL → AG-UI ferries it → frontend renderer maps to React. Has package names |
| R4 | DESIGN.md spec — `https://github.com/google-labs-code/design.md/blob/main/docs/spec.md` | 20 min | Phase 1 mapping anchor. Token types, section order, lint rules |
| R5 | CopilotKit generative-ui examples — `https://github.com/CopilotKit/generative-ui` | 10 min | Skim a working A2UI renderer integration |
| R6 | AG-UI vs A2UI explainer — `https://www.copilotkit.ai/ag-ui-and-a2ui` | 10 min | Resolve any "which protocol does what" confusion |

---

## 2 · Tasks

### 0.1 — Capture real response fixtures (~1.5 h)

**Goal:** capture 5–7 representative JSON payloads from a real blueprint run for use as fixtures across Phase 1–5 tests. Synthesizing them = drift later. Capture once, reuse everywhere.

**Steps:**

1. Boot dev: `make dev` (backend :8891 + frontend :3000).
2. In the workspace, kick a blueprint run with the `editorial-with-hero` family on any project. Use Network tab to capture:
   - `POST /api/v1/blueprints/{project}/run` response → `fixtures/blueprint-run-response.json`
   - Streaming chunks (concat) → `fixtures/blueprint-stream-chunks.jsonl`
   - `GET /api/v1/progress/{id}` response (mid-run + post-run) → `fixtures/progress-mid.json`, `fixtures/progress-done.json`
   - `POST /api/v1/qa/run` response → `fixtures/qa-result.json`
3. Capture chat agent response per agent: send `@scaffolder build a hero` → save → `fixtures/chat-scaffolder.json`. Repeat for `@dark-mode`, `@content`, `@outlook-fixer` (4 agents minimum, 9 if time allows).
4. Capture an HITL pause payload: trigger a contract failure (apply an off-token color manually, run blueprint) → save the pause state → `fixtures/hitl-pause.json`.

**Drop fixtures into:**

```
cms/apps/web/src/lib/a2ui/__fixtures__/
├── README.md                       # what each fixture is, when captured, what changed
├── blueprint-run-response.json
├── blueprint-stream-chunks.jsonl
├── progress-mid.json
├── progress-done.json
├── qa-result.json
├── chat-scaffolder.json
├── chat-dark-mode.json
├── chat-content.json
├── chat-outlook-fixer.json
└── hitl-pause.json
```

**Acceptance:** 8+ fixtures committed, README explains capture date and any redactions (PII, tokens). Fixtures must be **un-edited** real responses — anything synthesized goes in a separate `synthetic/` subdir.

---

### 0.2 — Verify runtime token access (~30 min)

**Goal:** confirm the locked tokens.css emits CSS variables that Phase 1's `tokensToDesignMd()` can read.

**Steps:**

1. Run dev. Open any dashboard route in browser DevTools console.
2. Execute:
   ```js
   const r = getComputedStyle(document.documentElement);
   ['--color-foreground','--color-background','--color-primary','--color-success','--color-danger','--color-border']
     .map(k => [k, r.getPropertyValue(k).trim()]);
   ```
3. Repeat with `<html class="dark">` to confirm dark variant reads.
4. Snapshot the resolved values into `cms/apps/web/src/lib/design-md/__fixtures__/tokens-light.json` and `tokens-dark.json`.
5. Document the canonical token list (the names Phase 1 will map to DESIGN.md sections) in `lib/design-md/__fixtures__/README.md`.

**Acceptance:** both fixture files committed; light + dark differ by expected tokens (foreground, background, surface flips); raw oklch values present.

**Pitfall:** Tailwind 4 emits resolved colors on `:root` only when the `@theme` block uses `--color-*` names. If a custom token like `--brand-navy` doesn't appear, Phase 1's mapping must use a fallback declared in `globals.css`. Verify before moving on.

---

### 0.3 — Lock A2UI runtime decision (~2 h, was 1 h — expanded after spec discovery)

**Goal:** decide which A2UI runtime strategy to commit to. **Now a 3-way choice, not 2-way**, because the canonical spec + an official renderer both exist.

**Pre-req:** complete R1, R3, R5 from §1 above before reading this section. Without those, this comparison is fiction.

**The three options:**

| Axis | A. Adopt CopilotKit `@copilotkitnext/a2ui-renderer` | B. Roll our own, A2UI v0.8-compliant | C. Roll our own, A2UI-inspired (simplified) |
|---|---|---|---|
| Bundle size | +90–120 KB gz (renderer + react provider) | +15–25 KB gz | +5–10 KB gz |
| Spec compliance | full v0.8 (canonical) | full v0.8 | partial — `{name, props, children}` shape only |
| Streaming model | JSONL (canonical) | JSONL (canonical) | static or chunked, our shape |
| Data binding model | full `BoundValue` (path/literal) | full `BoundValue` | none — props are literals |
| Action dispatch | full A2UI actions | implement ourselves | our own callback prop |
| Time to first card on screen | ~1 d | ~3–5 d | ~2 d |
| LOC | ~150 (configuration only) | ~600 (parser + renderer + binding) | ~200 |
| Coupling to upstream churn | high (alpha) | medium (we own the impl) | low |
| Brand control over card anatomy (§12 N10) | needs theme overrides | full control | full control |
| Future-proofing for v0.9 / ecosystem | strong (CopilotKit tracks) | medium (we track manually) | weak (we drift) |
| Backend impact (per spine §1) | zero — we use the renderer client-side | zero | zero |
| Multi-framework portability (a2ui.org claim) | yes (irrelevant — we're React only) | yes if we keep the spec | no |
| Risk if A2UI v0.9 makes breaking changes | CopilotKit absorbs the churn for us | we re-implement | we don't care; we never claimed compliance |

**Decision criteria, weighted by §1 constraints + §12 UX principles:**

1. **No backend changes (spine §1):** all three options pass.
2. **Brand preservation + N10 anatomy invariant:** B and C win; A requires fighting CopilotKit's defaults.
3. **Bundle weight (§7 perf gate, TTI ≤ 2s):** C > B > A.
4. **Future ecosystem optionality:** A > B > C.
5. **Calendar (8–10 weeks total):** C > B ≈ A.
6. **Decision reversibility:** B is most reversible — we own the impl and the shape, can adopt CopilotKit later or drift simpler.

**Recommended: Option B — roll our own A2UI v0.8-compliant renderer.**

Rationale: we get the future-proofing of canonical compliance without the bundle and coupling costs of CopilotKit. We don't need their backend orchestration (we're frontend-only). The ~3-5 day cost is paid once; it makes Phase 11c (CopilotKit adoption) and Phase 11d (email canvas A2UI) trivial pivots later.

**Override conditions** (if any of these hold, reconsider):
- Team has already used CopilotKit and prefers it → switch to A
- Bundle budget is tight (mobile-heavy traffic) → switch to C
- A2UI v0.9 changes are imminent and dramatic → defer the spec lock until v0.9 stabilizes; build C in the meantime

**Steps:**

1. Read R1 (A2UI v0.8 spec) and R3 (CopilotKit blog) — required.
2. Run `npx create-ag-ui-app` in a scratch dir; eyeball the bundle output, the JSX touchpoints, the theme override surface (~30 min).
3. Sketch a 50-line proof-of-concept Option B renderer in `cms/apps/web/scratchpad/a2ui-poc.tsx` (do not commit) — confirm the v0.8 shape feels tractable to handcraft (~30 min).
4. Write the decision doc to `cms/apps/web/docs/decisions/D-002-a2ui-runtime.md` using the template below.
5. **If decision = A or C**, reopen spine §13 mapping and `02-a2ui-runtime.md` (when written) to reflect different deliverables.

**Decision doc template:**

```markdown
# D-002 · A2UI Runtime Choice

**Date:** 2026-MM-DD
**Author:** Linards
**Status:** Accepted

## Context
[1 paragraph: what we're picking, why now]

## Options considered
- Roll-our-own minimal A2UI runtime
- CopilotKit + AG-UI protocol package

## Decision
Roll-our-own.

## Why
- Bundle weight (5KB vs ~100KB) matters for workspace TTI ≤2s gate (§7)
- A2UI v1 is alpha; we want zero coupling to external churn
- We need full control over card anatomy to enforce §12 N10

## Trade-offs accepted
- We re-implement ~150 lines of spec interpreter
- We don't get free CopilotKit ecosystem cards (we wouldn't use them — brand)
- If CopilotKit matures, we can swap in Phase 11c

## Affects
- §4 Phase 2 deliverables stay as written
- spec.ts is hand-rolled, mirrors the Google A2UI shape
```

**Acceptance:** decision doc committed; Slack/issue posted summarising it; spine §10 D1 marked **locked**.

---

### 0.4 — Stand up module skeletons (~2 h)

**Goal:** create empty module structure so Phase 1+ can drop in code without bikeshedding paths.

**Create directories + index files:**

```
cms/apps/web/src/lib/
├── design-md/
│   ├── __fixtures__/      (already created in 0.2)
│   ├── index.ts           (re-exports)
│   ├── types.ts           (DesignMdDoc, etc.)
│   └── README.md          (what this module does)
├── a2ui/
│   ├── __fixtures__/      (already created in 0.1)
│   ├── components/        (empty for now)
│   ├── adapters/          (empty for now)
│   ├── index.ts
│   ├── spec.ts            (A2UISpec types stub)
│   └── README.md
├── ag-ui/
│   ├── adapters/          (empty)
│   ├── index.ts
│   ├── envelope.ts        (AgUiEvent discriminated union stub)
│   └── README.md
├── selection/
│   ├── index.ts
│   ├── types.ts           (SelectionState, SelectionSource)
│   ├── SelectionContext.tsx (React context skeleton)
│   └── README.md
└── agents/
    ├── index.ts
    ├── registry.ts        (9-agent constants stub)
    └── README.md
```

**File contents (minimal, just enough to compile):**

`lib/a2ui/spec.ts`:
```typescript
// Mirrors Google A2UI shape. Discriminated union over component name.
// Filled out in Phase 2.
export type A2UINode = {
  id: string;
  name: string;          // component vocabulary name, e.g. "BuildSummaryCard"
  props: Record<string, unknown>;
  children?: A2UINode[];
};

export type A2UISpec = A2UINode;
```

`lib/ag-ui/envelope.ts`:
```typescript
// Filled out in Phase 3.
export type AgUiEventBase = {
  ts: string;       // ISO timestamp
  runId: string;
  source: string;   // agent or pipeline name
};

export type AgUiEvent = AgUiEventBase & {
  type: string;     // "pipeline.start" | "level.complete" | ... — narrowed in Phase 3
  payload: unknown;
};
```

`lib/selection/types.ts`:
```typescript
// Section + agent attribution. The shared bus that ties workspace surfaces.
export type SelectionSource =
  | "canvas"
  | "crew"
  | "chat"
  | "qa"
  | "design-md"
  | "url";

export type SelectionState = {
  sectionId: string | null;       // email section id (e.g. "hero", "card-grid-1")
  agentIds: readonly string[];    // agents owning this section
  source: SelectionSource;        // who set the selection (for re-entrancy guards)
};

export const EMPTY_SELECTION: SelectionState = {
  sectionId: null,
  agentIds: [],
  source: "url",
};
```

`lib/selection/SelectionContext.tsx`:
```tsx
"use client";
// Filled out in Phase 5. Stub provides the API shape so Phase 1–4 can import.
import { createContext, useContext } from "react";
import { EMPTY_SELECTION, type SelectionState } from "./types";

type SelectionContextValue = {
  selection: SelectionState;
  select: (next: Partial<SelectionState> & { source: SelectionState["source"] }) => void;
  clear: () => void;
};

const Ctx = createContext<SelectionContextValue>({
  selection: EMPTY_SELECTION,
  select: () => {},
  clear: () => {},
});

export function useSelection() {
  return useContext(Ctx);
}

// Provider implementation lands in Phase 5.
export const SelectionContext = Ctx;
```

`lib/agents/registry.ts`:
```typescript
// Hardcoded 9-agent registry. Replaces dropdown source today.
// Phase 4 wires this into <AgentCrewPanel/>.
// If/when /api/v1/agents/registry exists (Phase 11b), this becomes a fallback.
export type AgentDef = {
  id: string;
  name: string;
  short: string;          // 2-letter avatar
  color: string;          // semantic token name, NOT a hex (§12 N3)
  role: string;           // 1-line description
  defaultLevel: 0 | 1 | 2 | 3;  // pipeline level this agent runs at
};

export const AGENTS: readonly AgentDef[] = [
  { id: "scaffolder",     name: "Scaffolder",     short: "SC", color: "primary",   role: "Build email layout from component manifest", defaultLevel: 1 },
  { id: "dark-mode",      name: "Dark Mode",      short: "DM", color: "info",      role: "Generate dark variant", defaultLevel: 2 },
  { id: "content",        name: "Content",        short: "CN", color: "warning",   role: "Draft and refine copy", defaultLevel: 2 },
  { id: "outlook-fixer",  name: "Outlook Fixer",  short: "OF", color: "secondary", role: "MSO ghost-table sweep + Outlook quirks", defaultLevel: 3 },
  { id: "accessibility",  name: "Accessibility",  short: "AX", color: "success",   role: "Alt-text, contrast, WCAG sweep", defaultLevel: 3 },
  { id: "personalisation",name: "Personalisation",short: "PR", color: "success",   role: "Liquid blocks + fallback chains", defaultLevel: 1 },
  { id: "code-reviewer",  name: "Code Reviewer",  short: "CR", color: "primary",   role: "Token drift, brand compliance, HITL gate", defaultLevel: 2 },
  { id: "knowledge",      name: "Knowledge",      short: "KN", color: "info",      role: "Inject proactive warnings from past failures", defaultLevel: 0 },
  { id: "innovation",     name: "Innovation",     short: "IN", color: "secondary", role: "Suggest novel layouts (opt-in)", defaultLevel: 0 },
] as const;

export const AGENT_BY_ID: Readonly<Record<string, AgentDef>> = Object.fromEntries(
  AGENTS.map((a) => [a.id, a]),
);
```

**README contents** (one per module): 1-paragraph purpose, link to spine + sub-plans, list of public exports, "filled out in phases X..Y" note.

**Acceptance:** `pnpm tsc --noEmit` passes; no new imports in app code yet (skeletons are dormant); `pnpm test` runs unchanged.

---

### 0.5 — UX kick-off note (~30 min)

**Goal:** lock the §12 UX principles in a separate doc so the team can review without re-reading the whole spine.

**Steps:**

1. Create `cms/apps/web/docs/agentic-ui/UX-PRINCIPLES.md`. Copy spine §12 verbatim.
2. Add a 1-paragraph preamble: "These rules govern every PR in 10.13.X. PRs that break a rule get blocked."
3. Link it from the project README + workspace CLAUDE.md.
4. (Optional, ~30 min) Set up a `pnpm lint:ux-principles` script that grep-checks for forbidden patterns: hex-coded statuses (rule N3), `<Dialog>` over canvas (S4 — heuristic), local `useState` for state owned by `SelectionContext`/`useAgUiStream`/`next-themes` (S7).

**Acceptance:** doc committed and linked; teammates know §12 exists as a separate readable file.

---

## 3 · Verification (gate to Phase 1)

Run all of these before declaring Phase 0 done. If any fail, do not proceed:

| # | Check | How |
|---|---|---|
| V1 | All 8+ real fixtures captured and committed | `ls cms/apps/web/src/lib/a2ui/__fixtures__/*.json` ≥ 8 |
| V2 | Token fixtures exist for both themes | `ls cms/apps/web/src/lib/design-md/__fixtures__/tokens-{light,dark}.json` |
| V3 | A2UI runtime decision recorded | `cat cms/apps/web/docs/decisions/D-002-a2ui-runtime.md` |
| V4 | Module skeletons compile | `cd cms/apps/web && pnpm tsc --noEmit` exits 0 |
| V5 | No production code imports from new modules yet | `git grep -E "from .+/lib/(a2ui\|ag-ui\|selection\|design-md)" cms/apps/web/src/app cms/apps/web/src/components` returns empty |
| V6 | Existing test suite untouched and passing | `pnpm test` → same pass count as before Phase 0 |
| V7 | UX principles doc reachable | docs link works |
| V8 | Backend untouched | `git diff main..HEAD -- app/ alembic/` is empty |

---

## 4 · Decisions to lock in this phase

These are the spine §10 decisions, brought forward to be answered HERE so Phase 1+ can move fast:

| ID | Question | Recommended | Lock by end of Phase 0 |
|---|---|---|---|
| D1 | Roll-our-own A2UI vs CopilotKit | Roll-our-own (see 0.3) | yes — written into D-002 |
| D2 | Add `/api/v1/agents/registry` BE endpoint | No — frontend constants for v1 | yes |
| D3 | Feature flag name | `WORKSPACE__AGENTIC_LAYOUT` | yes |
| D4 | DESIGN.md chip position in top bar | Right of breadcrumb, before user menu | yes |
| D5 | A2UI vocabulary cap for v1 | 12 cards | yes |
| D6 | AG-UI polling interval | 1000 ms visible / 5000 ms blurred | yes |
| D7 | (UX) Selection bus: Context vs. Zustand vs. Jotai | **React Context** (no new dep, simple, Phase 5 owner) | yes |
| D8 | (UX) Reduced-motion handling | Respect `prefers-reduced-motion`; ripples become single-frame opacity changes | yes |
| D9 | (UX) Onboarding tour persistence | localStorage flag, never re-show, scoped per user | yes |

Record all 9 in `docs/decisions/` (one short doc each, or batched into `D-003-10.13-locks.md`).

---

## 5 · Pitfalls (read before starting)

- **Don't generate fixtures.** Real responses only. The whole point is that downstream phases rely on actual shapes, not idealized ones. If the backend response has a quirk, we want to see it.
- **Don't import skeletons from app code yet.** The directories must stay dormant — V5 above. Otherwise Phase 1+ struggles to introduce real exports without triggering ripple changes.
- **Don't refactor existing types.** If `types/chat.ts` looks awkward, leave it. Phase 0 is observation only.
- **Don't add npm dependencies.** Specifically: do NOT install `@google/design.md` or `copilotkit` yet. Phase 1 (DESIGN.md) decides whether to install the lint package; Phase 2 confirmed in 0.3.
- **Don't write any styling.** No CSS in this phase. Skeletons ship with empty render bodies.
- **Don't touch the backend.** §1 spine forbids it. If a fixture seems missing because the BE doesn't expose it, raise a flag — do not stub.
- **Watch out for Tailwind 4 token resolution.** `@theme` directive emits `--color-*` only at root. If a custom token from `globals.css` `:root { ... }` overrides, Phase 1 mapping must read both. Test 0.2 catches this.

---

## 6 · Hand-off to Phase 1

When Phase 0 closes, the next agent picking up Phase 1 (DESIGN.md) reads:

1. The spine — `.agents/plans/10.13-agentic-ui-frontend-adoption.md`
2. This sub-plan's §3 Verification table (so they know what already passed)
3. `10.13/01-design-md.md`
4. The token fixtures from 0.2 (their main input)

They do NOT need to read 0.1 fixtures or the A2UI decision doc unless investigating. Sub-plan 01 is self-sufficient.

**End-state of Phase 0:** workspace looks identical to a user; under the hood, three module skeletons + selection context + agent registry are ready to receive code.