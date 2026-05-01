# 10.13 / Phase 5 — Workspace re-layout (the symbiotic phase)

> Restructure the workspace shell to host all the new agentic surfaces while **preserving the design ↔ code split view** (user-locked requirement). Implement the **SelectionContext Provider** that turns five panels into one organism (§12 S1). Add section anchors on canvas, token overlay tied to DESIGN.md, keyboard shortcuts, feature-flag rollout, and a one-time onboarding tour.

**Spine:** §4 Phase 5, §12 (all UX principles), §1 (split view locked), §10 (D3, D7).

| | |
|---|---|
| Calendar | 1.5 weeks |
| LOC budget | ~1500 (split across files; this plan orchestrates) |
| Dependencies | Phases 1–4 verification all green; tokens fixtures, A2UI vocabulary, AG-UI events, Crew rail all ready |
| Outputs consumed by | Phase 6 (other pages adopt the same chrome patterns), Phase 7 (polish + e2e gates) |
| Locked by spine | Split view preserved (§1, §7 gate 3); SelectionContext as Context not Zustand (D7); feature flag `WORKSPACE__AGENTIC_LAYOUT` (D3); reduced-motion respected (D8); onboarding tour one-time (D9) |

---

## 1 · Inputs

### Local code (read first)

| What | File / Path | Why |
|---|---|---|
| Workspace page | `cms/apps/web/src/app/projects/[id]/workspace/page.tsx` | Main refactor target |
| Workspace layout | `cms/apps/web/src/app/projects/[id]/workspace/layout.tsx` | Routing layout |
| Existing Editor + Preview | `cms/apps/web/src/components/workspace/{editor-panel,preview-panel}.tsx` | Preserved; mounted in split mode |
| View switcher | `cms/apps/web/src/components/workspace/view-switcher.tsx` | Locked: code/builder/split modes preserved |
| Existing chat panel | `cms/apps/web/src/components/workspace/chat-panel.tsx` | Re-mounted in right zone (existing tabs preserved + new tabs from Phase 3) |
| Existing bottom panel | `cms/apps/web/src/components/workspace/bottom-panel.tsx` | Re-mounted with new tabs |
| `react-resizable-panels` | already in deps | Grid foundation |
| Selection skeleton | `cms/apps/web/src/lib/selection/SelectionContext.tsx` | Provider implementation lands here |
| Workspace shortcuts | `cms/apps/web/src/hooks/use-workspace-shortcuts.ts` | Extend with new shortcuts |
| Section detection | `cms/apps/web/src/components/workspace/builder/section-wrapper.tsx` | Extend with anchor pattern |
| Builder hook | `cms/apps/web/src/hooks/use-builder.ts` | For section IDs + agent attribution |
| `<AgentCrewPanel/>` | from Phase 4 | Mounts in left zone |
| `useDesignMdDoc` | from Phase 1 | Token overlay reads from this |
| `useAgUiStream` | from Phase 3 | Drives ripple cues |
| Feature flag system | `cms/apps/web/src/lib/feature-flags.ts` | Existing pattern |

---

## 2 · Tasks

### 5.1 — `<WorkspaceGrid />` 5-zone shell (~6 h)

**Goal:** the new grid using `react-resizable-panels`. Five zones: rail (slim icon nav, existing) / crew (Phase 4) / canvas (preserves split) / convo (chat with new tabs) / bottom (QA + new tabs).

**File:** `cms/apps/web/src/components/workspace/workspace-grid.tsx`

**Layout:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ TOP BAR (existing dashboard layout — DESIGN.md chip from Phase 1)  │
├─────┬──────────┬──────────────────────────────┬─────────────────────┤
│ R   │ Crew     │ Canvas                       │ Convo               │
│ a   │ (Phase 4)│  ┌────────────────────────┐  │ Conversation        │
│ i   │  ┌──────┐│  │ Preview / Builder /    │  │ Event Log (Ph 3)    │
│ l   │  │SC ●  ││  │ Code  / SPLIT          │  │ Eval Trace          │
│     │  │DM ●  ││  │                        │  │ History             │
│     │  │ ...  ││  │  (existing components, │  │                     │
│ existing  │  └──────┘│  │   NO CHANGES to split  │  │ A2UI cards inline   │
│ ToolSidebar│ Pipeline ││  │   view behavior)       │  │ Stream             │
│ stays     │  header  ││  │                        │  │ Chat input          │
│ inside    │          ││  │                        │  │                     │
│ rail      │          ││  └────────────────────────┘  │                     │
├─────┴──────────┴──────────────────────────────┴─────────────────────┤
│ BOTTOM PANEL — QA Gate · Rendering · Approval · Eval Trace · ...   │
└─────────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```tsx
import { Group, Panel, Separator } from "react-resizable-panels";

export function WorkspaceGrid() {
  return (
    <Group direction="vertical" className="h-screen">
      <Panel defaultSize={70} minSize={45}>
        <Group direction="horizontal">
          <Panel defaultSize={5} minSize={4} maxSize={6}>
            <ExistingToolSidebar />     {/* preserved */}
          </Panel>
          <Separator />
          <Panel defaultSize={20} minSize={12} collapsible>
            <AgentCrewPanel />          {/* Phase 4 */}
          </Panel>
          <Separator />
          <Panel defaultSize={50} minSize={30}>
            <CanvasZone />              {/* preserves split mode */}
          </Panel>
          <Separator />
          <Panel defaultSize={25} minSize={18} collapsible>
            <ConvoZone />               {/* chat + Stream + Eval Trace + History */}
          </Panel>
        </Group>
      </Panel>
      <Separator />
      <Panel defaultSize={30} minSize={15} collapsible>
        <BottomPanelZone />             {/* QA + Rendering + Approval + Eval Trace + Knowledge Hits */}
      </Panel>
    </Group>
  );
}
```

**Sizes persisted:** `cms/apps/web/src/hooks/use-workspace-layout.ts` — read/write to `localStorage` keyed per user.

**Acceptance:** grid renders; resizing works; sizes persist across reloads; collapsed panel can be reopened.

---

### 5.2 — Preserve split view (CRITICAL — user requirement) (~4 h)

**Goal:** split mode in CanvasZone shows Editor + Preview side-by-side **unchanged from current behavior**. This is a regression test, not a new feature.

**File:** `cms/apps/web/src/components/workspace/CanvasZone.tsx`

**Behavior:**

```tsx
const { viewMode } = useViewMode();    // existing hook

return (
  <>
    <CanvasToolbar />
    {viewMode === "code"   && <EditorPanel  />}
    {viewMode === "builder"&& <BuilderPanel />}
    {viewMode === "split"  && (
      <Group direction="horizontal">
        <Panel defaultSize={50}><EditorPanel  /></Panel>
        <Separator />
        <Panel defaultSize={50}><PreviewPanel /></Panel>
      </Group>
    )}
  </>
);
```

**Regression test (Playwright):**

```typescript
// cms/apps/web/tests/e2e/workspace-split-view.spec.ts
test("split view shows Editor + Preview side-by-side (locked behavior)", async ({ page }) => {
  await page.goto("/projects/1/workspace?view=split");
  await expect(page.locator('[data-testid="editor-panel"]')).toBeVisible();
  await expect(page.locator('[data-testid="preview-panel"]')).toBeVisible();
  // Both panels are siblings horizontally
  const editorBox = await page.locator('[data-testid="editor-panel"]').boundingBox();
  const previewBox = await page.locator('[data-testid="preview-panel"]').boundingBox();
  expect(editorBox!.x).toBeLessThan(previewBox!.x);
  expect(Math.abs(editorBox!.y - previewBox!.y)).toBeLessThan(5);  // same row
});
```

**Acceptance:** Playwright passes against the new layout in both feature-flag states (on/off).

---

### 5.3 — `<SelectionContext />` Provider — the symbiotic backbone (~6 h)

**Goal:** implement the Provider that ties canvas/crew/chat/QA/DESIGN.md into one organism per §12 S1. **The single most important task in this phase.**

**File:** `cms/apps/web/src/lib/selection/SelectionContext.tsx` (replace skeleton with real Provider)

**API:**

```typescript
type SelectionState = {
  sectionId: string | null;        // e.g. "hero", "card-grid-1"
  agentIds: readonly string[];     // agents owning this section (from builder annotations)
  source: "canvas" | "crew" | "chat" | "qa" | "design-md" | "url";
};

type SelectionContextValue = {
  selection: SelectionState;
  select: (next: Partial<SelectionState> & { source: SelectionState["source"] }) => void;
  clear: () => void;
};
```

**Provider:**

```tsx
export function SelectionProvider({ children }: { children: React.ReactNode }) {
  const [selection, setSelection] = useState<SelectionState>(EMPTY_SELECTION);
  const reentrancyGuard = useRef<string | null>(null);    // prevents A→B→A loops

  const select = useCallback((next: Partial<SelectionState> & { source: SelectionState["source"] }) => {
    if (reentrancyGuard.current === next.source) return;
    reentrancyGuard.current = next.source;
    setSelection((prev) => ({
      ...prev,
      ...next,
      // resolve agentIds from sectionId if not provided
      agentIds: next.agentIds ?? deriveAgentIdsForSection(next.sectionId ?? prev.sectionId),
    }));
    queueMicrotask(() => { reentrancyGuard.current = null; });
  }, []);

  const clear = useCallback(() => setSelection(EMPTY_SELECTION), []);

  return <SelectionContext.Provider value={{ selection, select, clear }}>
    {children}
  </SelectionContext.Provider>;
}
```

**Subscribers (the 5 surfaces):**

| Surface | Behavior on selection |
|---|---|
| Canvas (Phase 5.4) | Outline the selected section; show `<TokenOverlay/>` |
| Crew rail (Phase 4) | Highlight `selection.agentIds` with gold ring |
| Chat panel | Filter conversation to messages whose `meta.sectionId === selection.sectionId` |
| QA gate (bottom panel) | Filter checks to those scoped to the section |
| DESIGN.md inspector (Phase 1) | Show which tokens the section uses |

**Re-entrancy:** the `source` field prevents loops. If chat updates selection (`source: "chat"`), and crew fires another update reacting to that, the guard short-circuits.

**Acceptance:** unit test demonstrating 5 subscribers all update from a single `select()` call within one frame; re-entrancy guard prevents loops; clear works.

---

### 5.4 — Section anchors + agent attribution on canvas (~5 h)

**Goal:** hovering a section reveals "Ask agent" tooltip; clicking selects (drives SelectionContext); hovered section also pulses (S5) on agent activity.

**File:** `cms/apps/web/src/components/workspace/builder/section-wrapper.tsx` (extend)

**Anchor anatomy:**

```
┌──────────────────────────────────────┐
│  HERO · Scaffolder + Content [tag]   │  ← visible on hover/select
│                                      │
│  ┌────────────────────────────────┐  │
│  │  [actual section content]      │  │
│  │                                │  │
│  └────────────────────────────────┘  │
│  [Ask agent] [Outlook Fixer] [⚙]     │  ← actions on select only
└──────────────────────────────────────┘
```

**Hover tag:** small chip top-left showing section type + owning agents. Reads from existing builder annotations.

**Select actions (visible only when selected):**
- "Ask agent…" → opens chat with `@agent: this section's …` prefilled
- Per-agent quick fix buttons (e.g. "Outlook Fixer" → triggers a focused fix call)
- Settings cog → opens section properties sheet

**Selection wiring:**

```tsx
const { selection, select } = useSelection();
const isSelected = selection.sectionId === section.id;
return (
  <div
    data-section-id={section.id}
    onClick={() => select({ sectionId: section.id, source: "canvas" })}
    className={isSelected ? "outline-2 outline-warning" : ""}
  >
    {isSelected && <SectionTag agents={section.agentIds} />}
    {children}
    {isSelected && <SectionActions section={section} />}
  </div>
);
```

**Live ripple (S5):** when `useAgUiStream` emits an event mentioning this section (e.g. `TOOL_CALL_RESULT.content.sectionId === section.id`), the section briefly pulses with a 200 ms tint. Respects `prefers-reduced-motion`.

**Acceptance:** hover reveals tag; click selects; selection drives crew/chat/QA filters; ripple pulses tastefully.

---

### 5.5 — Token overlay tied to DESIGN.md (~3 h)

**Goal:** when a section is selected, show a small overlay listing which DESIGN.md tokens that section's CSS uses.

**File:** `cms/apps/web/src/components/workspace/builder/TokenOverlay.tsx`

**Visual:**

```
┌─────────────────────────────────────────┐
│ bg = {colors.tertiary}                  │
│ text = {colors.on-tertiary}             │
│ rounded = {rounded.sm}                  │
└─────────────────────────────────────────┘
```

**Computation:** read the section's resolved styles via `getComputedStyle(sectionEl)`, match each property value against the current `useDesignMdDoc()` token map, render the matched token names.

**Position:** absolute, top-left of selected section, just below the SectionTag. ~10 px font, mono.

**Acceptance:** every selected section shows tokens; off-token values shown in danger color (with click-to-open `<TokenDriftCard />`).

---

### 5.6 — Bottom panel new tabs (~3 h)

**Goal:** add `Eval Trace` and `Knowledge Hits` tabs to the existing bottom panel. Existing tabs (QA, Rendering, Approval) preserved.

**File:** `cms/apps/web/src/components/workspace/bottom-panel.tsx` (extend)

**New tabs:**

- **Eval Trace** — renders A2UI `<EvalVerdictCard/>` + `<CalibrationDeltaCard/>` from `useAgUiStream` events filtered by `eval.verdict` + `calibration.delta`
- **Knowledge Hits** — renders A2UI `<KnowledgeHitsList/>` from `knowledge.warnings` + the existing failure-pattern API

Tab counts (live) reflect event counts.

**Acceptance:** all five tabs work; existing tabs visually unchanged; A2UI cards render correctly in new tabs.

---

### 5.7 — Keyboard shortcuts (~2 h)

**Goal:** extend the existing shortcut registry. Every new surface gets a shortcut. `?` cheat-sheet auto-derives.

**File:** `cms/apps/web/src/hooks/use-workspace-shortcuts.ts` (extend)

**New shortcuts:**

| Shortcut | Action |
|---|---|
| `⌘\` | toggle crew rail |
| `⌘.` | open contract inspector (from Phase 2) |
| `⌘L` | open Event Log tab |
| `⌘B` | toggle bottom panel |
| `⌘⇧A` | focus Agent Crew (Tab cycles cards) |
| `⌘⇧S` | focus selection (from URL ?sectionId) |
| `?` | open cheat sheet |
| `Esc` | clear selection |

**Existing shortcuts preserved:**

- `⌘S` save, `⌘⇧G` generate, `⌘⇧Q` run QA, `⌘K` command palette

**Acceptance:** all shortcuts fire; cheat sheet shows them all; conflicts with system shortcuts checked.

---

### 5.8 — Feature flag rollout (~2 h)

**Goal:** new layout opt-in via `WORKSPACE__AGENTIC_LAYOUT`. Old layout reachable via flag-off. Lets us 10 → 50 → 100% rollout.

**Files:**

- `cms/apps/web/src/lib/feature-flags.ts` (extend with new flag)
- `cms/apps/web/src/app/projects/[id]/workspace/page.tsx` (gate)

**Implementation:**

```tsx
const useNewLayout = useFeatureFlag("WORKSPACE__AGENTIC_LAYOUT");

return useNewLayout ? <WorkspaceGrid /> : <LegacyWorkspace />;
```

**Acceptance:** flag off = old workspace untouched; flag on = new grid; rollout cohorts work.

---

### 5.9 — Onboarding tour (one-time, dismissible) (~4 h)

**Goal:** §12 N5 — first-visit overlay highlights (1) crew rail, (2) event log, (3) DESIGN.md chip with one-line captions. localStorage flag persists dismissal (D9).

**File:** `cms/apps/web/src/components/onboarding/AgenticTour.tsx`

**Flow:**

1. On first visit (per user), check `localStorage.getItem("agentic-tour-dismissed-v1")`
2. If null, show overlay: 3 numbered hotspots with arrows + captions, "Got it" dismisses
3. Sets the flag; never shows again (D9)
4. Manual replay: ⌘⇧? → "Replay tour"

**Captions (locked to S2/S5/S8 spirit + §1.6 user-facing naming policy — no protocol names):**

1. **Agent panel** (left rail) — "Your 9 AI agents. Click any to focus the chat. They light up when working."
2. **Live activity** (right tab) — "See exactly what each agent is doing in real time."
3. **Brand** (top-bar chip) — "Your project's brand, in one place. Click to inspect colors and typography."

These caption strings are user-visible — pass through ESLint `no-protocol-names-in-ui` rule.

**Acceptance:** first-time user sees tour; click "Got it" dismisses; reload → no tour; replay shortcut works.

---

### 5.10 — Wire SelectionProvider at workspace root (~1 h)

**Goal:** mount the Provider above all 5 zones so subscribers can read.

**File:** `cms/apps/web/src/app/projects/[id]/workspace/page.tsx` (modify)

```tsx
return (
  <SelectionProvider>
    <FeatureFlagGate flag="WORKSPACE__AGENTIC_LAYOUT">
      <WorkspaceGrid />
    </FeatureFlagGate>
  </SelectionProvider>
);
```

URL → selection sync (optional v1.5): `?sectionId=hero` updates the selection on first paint with `source: "url"`.

**Acceptance:** Provider visible to all zones; selection persists across panel resizes.

---

### 5.11 — Storybook + Playwright for symbiotic system (~5 h)

**Goal:** the §12 S1 ripple test. Click a section, assert 5 surfaces respond.

**File:** `cms/apps/web/tests/e2e/workspace-symbiotic.spec.ts`

**Test:**

```typescript
test("selecting a section ripples to crew, chat, QA, design-md, canvas in one frame", async ({ page }) => {
  await page.goto("/projects/1/workspace");
  await page.waitForSelector('[data-section-id="hero"]');
  const t0 = Date.now();
  await page.click('[data-section-id="hero"]');

  // Within 1 frame (~16 ms), all surfaces respond:
  await Promise.all([
    page.waitForSelector('[data-section-id="hero"][data-selected="true"]'),         // canvas
    page.waitForSelector('[data-agent-id="scaffolder"][data-highlighted="true"]'),  // crew
    page.waitForSelector('[data-chat-filter="hero"]'),                              // chat
    page.waitForSelector('[data-qa-filter="hero"]'),                                // QA
    page.waitForSelector('[data-design-md-section="hero"]'),                        // design-md
  ]);
  const elapsed = Date.now() - t0;
  expect(elapsed).toBeLessThan(80);    // 5 frames at 60fps = ~83 ms; allow some slack
});
```

**Acceptance:** test passes in CI; regression-protects S1.

---

## 3 · Verification gates

| # | Check | How |
|---|---|---|
| V1 | Grid renders all 5 zones; sizes persist | manual + e2e |
| V2 | Split view (`?view=split`) shows Editor + Preview side-by-side | Playwright (5.2) |
| V3 | SelectionContext propagates to all 5 surfaces in one frame | Playwright symbiotic test (5.11) |
| V4 | Section click selects; tag, actions, token overlay appear | manual + e2e |
| V5 | Live ripple cue pulses on agent activity; respects reduced-motion | manual with system pref |
| V6 | Bottom panel: existing 3 tabs + 2 new tabs all functional | snapshot + manual |
| V7 | All keyboard shortcuts fire; ? cheat sheet up-to-date | e2e |
| V8 | Feature flag off → old workspace pixel-identical | visual diff |
| V9 | Feature flag on → new layout, all subsystems integrated | manual |
| V10 | Onboarding tour: shows once, dismisses, replay works | manual |
| V11 | Three-click rule: any action ≤3 clicks (excluding ⌘K) | audit script |
| V12 | 60-second cold-load → "see all 9 agents working" | Playwright timing test |
| V13 | A11y: keyboard nav across whole grid; screen reader | axe |
| V14 | Bundle size delta ≤ 24 KB gz on workspace route | `pnpm analyze` |
| V15 | Backend untouched | `git diff` |
| V16 | `pnpm tsc && pnpm test && pnpm storybook:build && pnpm test:e2e` clean | CI |

---

## 4 · Decisions to lock in this phase

| ID | Question | Default |
|---|---|---|
| D5.1 | Resizable layout sizes default | rail 5 / crew 20 / canvas 50 / convo 25; bottom 30 vertical |
| D5.2 | localStorage key naming | `email-hub:workspace-layout:v1` |
| D5.3 | Split-view inner ratio | **50 / 50**; user-resizable |
| D5.4 | Onboarding flag key | `agentic-tour-dismissed-v1` |
| D5.5 | URL-driven selection? | **v1.5 — defer**; only implement section-click path now |
| D5.6 | Ripple animation duration | **200 ms** ease-out; 0 ms with `prefers-reduced-motion` |
| D5.7 | Re-entrancy guard scope | per-source; cleared in microtask |
| D5.8 | "Ask agent" affordance default agent | **Scaffolder** if section has no owners; else first owner |

Record in `docs/decisions/D-008-workspace-layout-locks.md`.

---

## 5 · Pitfalls

- **DO NOT break split view.** This is the most important regression to avoid. Run the Playwright test from 5.2 *before* and *after* every PR in this phase.
- **DO NOT lose persistence.** localStorage layout sizes have to survive layout changes. Migrate gracefully if keys change.
- **DO NOT make the SelectionContext re-render-y.** Subscribers should `useSelection()` selectively (e.g. with a `useSelectionAgentIds` hook that returns only the slice they need) to avoid full-tree re-renders on every click.
- **DO NOT swallow URL changes.** If the user navigates away mid-selection, restore selection on back-button if possible.
- **DO NOT block on reduced-motion.** Even with `prefers-reduced-motion`, selections must visibly succeed (border change is fine; pulse is removed).
- **DO NOT make the tour modal.** §12 S4. Use a non-blocking overlay with click-through dimming.
- **DO NOT show the tour to existing users automatically.** localStorage flag *defaults to dismissed* on the first deploy day to avoid disrupting active users; consider migration script that sets the flag for users with > N session count.
- **DO NOT change the existing dropdown shortcut for agent selection.** Keep keyboard parity.
- **DO NOT block the canvas with overlays.** Token overlay positions absolutely above section; never wider than section.
- **DO NOT couple the Crew rail directly to canvas DOM.** Crew reads via SelectionContext only — never querySelector across panels.

---

## 6 · Hand-off to Phase 6

Phase 6 (page adoption) consumes:

- The chrome patterns established here (Sheet, ⌘L Event Log, semantic tokens, A2UI inline rendering)
- `useSelection` is *not* exported from workspace globally — pages outside workspace get their own SelectionProvider scoped per page if needed
- Onboarding tour pattern can be reused per-page (different localStorage keys)

When Phase 5 closes, the next agent reads:

1. Spine §12 (UX principles, especially §12.2 Intuitive navigability)
2. Phase 5 V1–V16 verification table
3. `10.13/06-page-adoption.md`

**End-state of Phase 5:** workspace shipped behind feature flag; split view preserved; selecting a section ripples to 5 surfaces in one frame; backend untouched; bundle delta ≤ 24 KB.
