# 10.13 / Phase 6 — Adopt across QA / Approvals / Intelligence / Renderings

> Reuse the A2UI vocabulary across the four high-traffic non-workspace routes. Reduces visual fragmentation cited in the original audit (§4 spine) — currently every dashboard rolls its own card patterns. After this phase, the same `_BaseCard` anatomy and the same DESIGN.md chip work everywhere.

**Spine:** §4 Phase 6, §12 N3 (semantic colors), §12 N10 (card anatomy invariant), §1 (no backend changes).

| | |
|---|---|
| Calendar | 1 week |
| LOC budget | ~600 (mostly net deletions of ad-hoc components, replaced with A2UI calls) |
| Dependencies | Phases 1–5 verification all green; A2UI vocabulary, AG-UI envelope, DESIGN.md chip all live |
| Outputs consumed by | Phase 7 (polish does cross-page a11y + chromatic across the now-unified surface) |
| Locked by spine | No new BE endpoints (§1); no new vocabulary cards beyond v1's 12 (§10 D5); semantic colors only (§12 N3) |

---

## 1 · Inputs

### Local code

| What | File / Path | Why |
|---|---|---|
| Intelligence page | `cms/apps/web/src/app/(dashboard)/intelligence/page.tsx` | Refactor target |
| Approvals detail | `cms/apps/web/src/app/(dashboard)/approvals/[id]/page.tsx` | Refactor target |
| Approvals list | `cms/apps/web/src/app/(dashboard)/approvals/page.tsx` | Light updates only |
| Renderings page | `cms/apps/web/src/app/(dashboard)/renderings/page.tsx` | Refactor target |
| Failure pattern dashboard | `cms/apps/web/src/components/intelligence/top-failure-patterns-card.tsx` | Replace with A2UI `<KnowledgeHitsList/>` |
| Knowledge proactive warnings | `cms/apps/web/src/hooks/use-knowledge.ts` | Hooks already exist; we just route them through A2UI now |
| Existing intelligence stats hook | `cms/apps/web/src/hooks/use-intelligence-stats.ts` | Data source unchanged |
| A2UI catalog | `cms/apps/web/src/lib/a2ui/catalog.ts` (Phase 2) | Render target |
| A2UI adapters | `cms/apps/web/src/lib/a2ui/adapters/` (Phase 2) | Convert existing data shapes |
| `useAgUiStream` | Phase 3 | For live event feeds on Intelligence dashboard |
| `useDesignMdDoc` | Phase 1 | DESIGN.md chip already on every dashboard route |

---

## 2 · Tasks

### 6.1 — Intelligence dashboard refactor (~2 days)

**Goal:** replace ad-hoc bar charts and cards with A2UI rendering.

**File:** `cms/apps/web/src/app/(dashboard)/intelligence/page.tsx`

**Today:** custom DIV-based bar charts for agent performance + score trends; bespoke cards.

**After:**

```tsx
const { data: stats } = useIntelligenceStats();
const a2uiSpec = intelligenceStatsToA2UI(stats);   // adapter (~150 LOC)

return (
  <div className="grid grid-cols-12 gap-4">
    <div className="col-span-8">
      <A2UIRenderer messages={a2uiSpec.dashboard} catalog={EMAIL_HUB_CATALOG} />
    </div>
    <aside className="col-span-4">
      <A2UIRenderer messages={a2uiSpec.sidebar} catalog={EMAIL_HUB_CATALOG} />
    </aside>
  </div>
);
```

**Cards rendered:**

- `<InsightCard/>` × 4 — top stats (templates built, gate pass rate, eval pass rate, avg run time)
- `<AgentProposalCard/>` × 9 — per-agent performance summary (calibration TPR/TNR, last calibration delta)
- `<CalibrationDeltaCard/>` — global calibration trend
- `<KnowledgeHitsList/>` — top failure patterns of the last 7 days

**Adapter:** `cms/apps/web/src/lib/a2ui/adapters/intelligence.ts` — pure function `intelligenceStatsToA2UI(stats: IntelligenceStats): { dashboard: A2UIMessage[]; sidebar: A2UIMessage[] }`.

**Net deletion:** the old `<ScoreOverviewCards/>`, `<CheckPerformanceChart/>`, `<ScoreTrendBars/>`, `<AgentPerformanceChart/>` components are replaced. ~600 LOC removed; ~150 LOC added (adapter).

**Acceptance:** intelligence page visually consistent with workspace; all data sources unchanged; backend untouched; chromatic both themes.

---

### 6.2 — Approvals detail refactor (~1.5 days)

**Goal:** approval detail page uses A2UI vocabulary throughout. Audit timeline becomes a list of A2UI cards.

**File:** `cms/apps/web/src/app/(dashboard)/approvals/[id]/page.tsx`

**Mapping:**

| Today | After |
|---|---|
| Custom approval status header | `<InsightCard/>` with status, requester, age |
| Decision bar (approve/reject buttons) | preserved (unique action surface, OK to keep custom — it's not card-shaped) |
| Audit timeline | list of `<AgentProposalCard/>` and `<EvalVerdictCard/>` instances, ordered by timestamp |
| Rejection feedback | `<HitlPauseCard/>` rendering the rejection reason as a paused state |
| Version compare | preserved |

**Adapter:** `cms/apps/web/src/lib/a2ui/adapters/approval.ts` — `approvalToA2UI(approval): A2UIMessage[]`.

**Net deletion:** ~300 LOC of custom timeline code. Replaced with ~120 LOC adapter.

**Acceptance:** approval detail visually unified with workspace cards; existing approve/reject flow unchanged; chromatic both themes.

---

### 6.3 — Renderings page refactor (~1 day)

**Goal:** the per-client gate panel becomes `<RenderingMatrixCard/>`. Confidence summary becomes `<InsightCard/>`s.

**File:** `cms/apps/web/src/app/(dashboard)/renderings/page.tsx`

**Mapping:**

| Today | After |
|---|---|
| 14-client preview grid | `<RenderingMatrixCard/>` (single A2UI card per template) |
| Confidence summary | `<InsightCard/>` × 3 |
| Calibration health panel | `<CalibrationDeltaCard/>` |
| Gate-blocking client list | `<KnowledgeHitsList/>` with severity coloring |

**Adapter:** `cms/apps/web/src/lib/a2ui/adapters/renderings.ts` — `renderingsToA2UI(matrix): A2UIMessage[]`.

**Acceptance:** rendering page visually consistent; per-client thumbnails render correctly inside the matrix card; preview iframes work as before.

---

### 6.4 — Failure pattern dashboard (~0.5 day)

**Goal:** the existing failure-pattern card becomes a thin A2UI wrapper.

**File:** `cms/apps/web/src/components/intelligence/top-failure-patterns-card.tsx`

**Replace** the entire component with:

```tsx
export function TopFailurePatternsCard() {
  const { data } = useFailurePatterns();
  const spec = failurePatternsToA2UI(data ?? []);
  return <A2UIRenderer messages={spec} catalog={EMAIL_HUB_CATALOG} />;
}
```

Adapter exists from Phase 2.9 (`failurePatternsToA2UI`).

**Net deletion:** ~150 LOC.

**Acceptance:** identical data displayed; A2UI card rendered.

---

### 6.5 — Knowledge proactive warnings inline (~0.5 day)

**Goal:** when starting a workspace blueprint run, render proactive warnings inline in chat as A2UI cards.

**Wired in Phase 3.8 already** — this task confirms the integration works on adopted pages.

**Verify:**

- Intelligence page shows recent proactive warnings if any
- Workspace chat at run start shows warnings before agent runs (already wired)
- No double-rendering between Intelligence and workspace

**Acceptance:** warnings appear once, not duplicated; visual consistency.

---

### 6.6 — Approval list page light updates (~0.5 day)

**Goal:** the approval *list* page (vs. detail) gets minor consistency updates only — same DESIGN.md chip, same status-color semantics.

**File:** `cms/apps/web/src/app/(dashboard)/approvals/page.tsx`

**Changes:**

- Status badges use semantic tokens (`pass`/`warn`/`fail`/`info`) per N3
- Empty state copy + CTA per N4
- Three-click rule audited

**Net change:** small tweaks; ~50 LOC modified.

**Acceptance:** semantic tokens used; no hex; existing behavior unchanged.

---

### 6.7 — Cross-page consistency audit (~0.5 day)

**Goal:** verify the four refactored pages + workspace + 4 unchanged pages all look like one product.

**Checklist:**

- DESIGN.md chip appears on all
- Color semantics consistent
- Empty states have CTAs
- Loading states use skeletons
- Error states have recovery actions
- Hover/focus visible everywhere
- ⌘K command palette includes navigations to all pages

**Output:** `docs/agentic-ui/CONSISTENCY-AUDIT.md` — checklist with screenshots, pass/fail per page.

**Acceptance:** all 9 routes pass; gaps documented as Phase 7 polish items.

---

## 3 · Verification gates

| # | Check | How |
|---|---|---|
| V1 | Intelligence page uses A2UI for ≥80% of cards | code grep + visual |
| V2 | Approvals detail uses A2UI for timeline + status | manual |
| V3 | Renderings page uses `<RenderingMatrixCard/>` | manual |
| V4 | Failure pattern card replaced | code grep |
| V5 | Existing data flows untouched (no new API calls) | network audit |
| V6 | Chromatic shows both themes for all refactored pages | CI |
| V7 | Net LOC reduction: ≥1000 LOC removed; ≤400 LOC added | `git diff --stat` |
| V8 | Cross-page consistency audit doc complete | review |
| V9 | A11y: all four pages axe-clean | CI |
| V10 | Backend untouched | `git diff` |
| V11 | `pnpm tsc && pnpm test` clean | CI |

---

## 4 · Decisions to lock in this phase

| ID | Question | Default |
|---|---|---|
| D6.1 | Aggressive replacement vs. incremental | **Aggressive** for Intelligence + Approvals; **incremental** for Renderings (preview iframes are touchy) |
| D6.2 | Keep version-compare custom or A2UI-ify | **Keep custom**; it has unique diff-rendering needs out of scope for v1 |
| D6.3 | Approve/reject buttons in approvals detail | **Keep custom**; not card-shaped |
| D6.4 | New A2UI cards needed? | **No** — stay within the 12-card v1 cap (§10 D5) |
| D6.5 | If a page needs a card we don't have | **Use `<InsightCard/>` generic** + log requirement for v1.1 |

Record in `docs/decisions/D-009-page-adoption-locks.md`.

---

## 5 · Pitfalls

- **Don't add new card types.** §10 D5 caps v1 at 12. Pressure to add will arise during this phase. Resist; use `<InsightCard/>` generic and log gaps.
- **Don't break existing data flows.** All hooks/types stay; we change rendering, not fetching.
- **Don't over-style adapter output.** Adapters produce A2UI specs; cards do the styling. Adapters never inject CSS.
- **Don't refactor the email-canvas builder.** §9 spine non-goal. Stay above the canvas.
- **Don't lose feature parity.** Every action available pre-refactor must be available post-refactor. If something gets removed accidentally, file an immediate fix.
- **Don't ship A2UI for the renderings preview iframes.** Iframes are special; they render real ESP HTML. Wrap them in cards but don't put the iframe content through A2UI.
- **Don't forget loading states.** Skeletons match the A2UI card shape (use `_BaseCard` skeleton variant).
- **Don't break URL deep links.** `/approvals/123` and `/intelligence?tab=patterns` etc. must keep working.

---

## 6 · Hand-off to Phase 7

Phase 7 (polish + ship) consumes:

- The cross-page consistency audit doc as polish backlog
- All four refactored pages as scope for chromatic + a11y + perf gates
- The unified A2UI surface as a single thing to test for the §12 navigability gates

When Phase 6 closes, the next agent reads:

1. Spine §7 (success criteria, especially gates 11–13)
2. Phase 6 V1–V11 verification table
3. `10.13/07-polish-ship.md`
4. The consistency audit doc

**End-state of Phase 6:** four routes refactored; visual consistency across the dashboard; net LOC reduced; backend untouched; ready for the polish + ship phase.
