# 10.13 / Phase 7 — Polish & ship

> Final phase. Audit, harden, doc, gate-test, and roll out behind the feature flag from 10% → 50% → 100%. The §12 UX principles get formal CI enforcement here. **No new functionality** — verify, polish, and gate.

**Spine:** §4 Phase 7, §7 (success criteria, especially gates 11–13), §12 (full UX principles).

| | |
|---|---|
| Calendar | 3–5 working days |
| LOC budget | ~600 (mostly tests, scripts, docs) |
| Dependencies | Phases 0–6 verification all green; cross-page consistency audit doc from Phase 6.7 |
| Outputs consumed by | the production user — this is the launch |
| Locked by spine | feature flag default (D3); 60-second cold-load gate (§7.13); 3-click rule (§7.12); 95% ⌘K coverage (§12 N1) |

---

## 1 · Inputs

### Local code

| What | File / Path | Why |
|---|---|---|
| Cross-page consistency audit | `docs/agentic-ui/CONSISTENCY-AUDIT.md` | Phase 6.7 — polish backlog |
| Feature flag system | `cms/apps/web/src/lib/feature-flags.ts` | Rollout |
| Existing Playwright e2e | `cms/apps/web/tests/e2e/` | Add new specs here |
| Existing CI | `.github/workflows/check-fe.yml` (or equivalent) | Wire new gates |
| Existing UX principles doc | `cms/apps/web/docs/agentic-ui/UX-PRINCIPLES.md` | Phase 0.5 — referenced by lints |
| All A2UI components | `cms/apps/web/src/lib/a2ui/components/` | Storybook coverage target |
| Selection bus | `cms/apps/web/src/lib/selection/` | Symbiotic test target |
| Workspace symbiotic e2e | `cms/apps/web/tests/e2e/workspace-symbiotic.spec.ts` | Phase 5.11 — extend |

---

## 2 · Tasks

### 7.1 — Accessibility audit (~1 day)

**Goal:** every new component + page passes axe with zero violations; manual keyboard pass; screen-reader pass.

**Tools:**

- `axe-playwright` for automated checks across all 9 routes + all 12 A2UI cards
- Manual pass with VoiceOver (macOS) and NVDA (Windows VM if available)
- Lighthouse a11y score ≥ 95 on every dashboard route

**Checklist per component:**

- Focus visible (semantic outline, not removed)
- Keyboard: Tab navigates, Enter/Space activates, Escape closes, Arrow keys for grouped controls
- ARIA: roles set correctly (`role="button"`, `role="dialog"`, etc.); `aria-live` for dynamic content (event log, status changes); `aria-label` for icon-only buttons
- Color contrast: ≥ 4.5:1 for body text, ≥ 3:1 for large text — even in dark mode; verified via `@google/design.md` lint
- Reduced-motion: every animation respects `prefers-reduced-motion`

**Output:**

- `docs/agentic-ui/A11Y-AUDIT.md` — page-by-page checklist with pass/fail
- Fix any violations before V1 gate

**Acceptance:** axe-clean across all routes; Lighthouse ≥ 95; one full keyboard-only pass through workspace blueprint flow recorded.

---

### 7.2 — Performance gates (~0.5 day)

**Goal:** TTI ≤ 2 s on cached load; AG-UI poll budget ≤ 1.5% CPU on idle tab; bundle size budgets per route.

**Measurements:**

| Gate | Tool | Threshold |
|---|---|---|
| Workspace TTI (cached) | Lighthouse CI | ≤ 2.0 s |
| Workspace TTI (cold) | Lighthouse CI | ≤ 4.0 s |
| Idle CPU when tab visible | DevTools Performance recording | ≤ 1.5% over 30 s |
| Idle CPU when tab blurred | DevTools Performance recording | ≤ 0.2% over 30 s |
| Workspace bundle delta vs main | `pnpm analyze` | ≤ 100 KB gz total across phases |
| Per-route bundle (intelligence, approvals, renderings) | `pnpm analyze` | ≤ 50 KB gz delta each |
| First contentful paint (FCP) | Lighthouse | ≤ 1.0 s |
| Cumulative layout shift (CLS) | Lighthouse | ≤ 0.05 |

**Wire-up:** add `pnpm perf-gate` script that runs all measurements and fails CI if any threshold missed.

**Acceptance:** all gates pass on a clean main branch + PR.

---

### 7.3 — Dark / light parity (~0.5 day)

**Goal:** every component renders cleanly in both themes; no contrast regressions.

**Tools:**

- Storybook Chromatic — every story snapshotted in both themes
- Manual pass: open every dashboard route, toggle theme, look for visual regressions (font weight shifts, color drift, contrast issues)
- DESIGN.md lint — run on the auto-generated DESIGN.md from both themes to catch contrast violations

**Output:** chromatic baselines updated; any regressions fixed.

**Acceptance:** zero new chromatic diffs flagged as bugs.

---

### 7.4 — Storybook coverage gate (~0.5 day)

**Goal:** 100% of new components have stories covering at least 3 variants (default, error, edge).

**Verify:**

- All 12 A2UI custom catalog cards: ≥ 3 stories each
- All 7 standard catalog cards: ≥ 2 stories each
- `<AgentCrewPanel/>`, `<AgentCrewCard/>`, `<PipelineHeader/>`: full state coverage
- `<DesignMdInspector/>`, `<DesignMdYamlView/>`, `<DesignMdLintList/>`: full state coverage
- `<StreamLog/>`: event-volume + filter variants
- `<HitlPauseCard/>` + `<TokenDriftCard/>`: error and recovery variants

**CI script:** `pnpm storybook:coverage` — fails if any new component lacks ≥ 3 stories.

**Acceptance:** script passes.

---

### 7.5 — Feature flag rollout (~0.5 day)

**Goal:** ship to 10% → monitor → 50% → monitor → 100%.

**Stages:**

| Stage | Cohort | Duration | Rollback if |
|---|---|---|---|
| Internal | Email Hub team only | 2 days | Any team report of split-view broken or symbiotic system not working |
| 10% | Random sample of users | 3 days | Sentry error rate > 0.5% OR P50 TTI regression > 200 ms OR support tickets mentioning "lost feature" |
| 50% | Random sample | 3 days | Same as 10% |
| 100% | Everyone | — | Same |

**Monitoring:**

- Sentry alerts on `WorkspaceGrid`, `A2UIRenderer`, `useAgUiStream`, `SelectionContext` errors
- Lighthouse CI runs on a sample of routes per cohort
- Custom telemetry: cold-load timing (per §7 gate 13), three-click audit metrics, ⌘K usage

**Rollback path:** `WORKSPACE__AGENTIC_LAYOUT` → false reverts to legacy workspace; no code revert needed.

**Acceptance:** internal stage starts; rollout schedule documented.

---

### 7.6 — Docs (~0.5 day)

**Goal:** `docs/agentic-ui/README.md` covers everything an engineer or designer needs.

**Sections:**

1. **What this is** — 1 paragraph, links to spine
2. **Architecture** — diagram (copy from spine §3 + augment with finished module map)
3. **DESIGN.md** — how to inspect, how to edit (per Phase 11e roadmap)
4. **A2UI vocabulary** — list all 12 cards with screenshots (chromatic links), props table, "view contract" workflow
5. **AG-UI events** — list all 17 events + the Email-Hub `CUSTOM` extensions; mapping to backend (§13 spine)
6. **Selection bus** — how to subscribe, the re-entrancy guard, the 5-surface ripple invariant
7. **UX principles** — link to `UX-PRINCIPLES.md`
8. **How to add a new A2UI card (post-v1)** — template + checklist
9. **How to add a new AG-UI custom event** — template + checklist
10. **Troubleshooting** — common issues (selection not propagating, stale tokens, etc.)
11. **References** — spine §13

**Plus:** update `cms/apps/web/CLAUDE.md` with a brief mention pointing to the new docs.

**Acceptance:** docs reviewed by 1 engineer + 1 designer; no broken links.

---

### 7.7 — Chat fallback test (~0.25 day)

**Goal:** existing chat (without `a2ui` payload on messages) renders identically to before. **Regression-protect Phase 2.10's "additive only" guarantee.**

**File:** `cms/apps/web/tests/e2e/chat-fallback.spec.ts`

**Test:**

```typescript
test("chat without a2ui payload renders unchanged", async ({ page }) => {
  await page.goto("/projects/1/workspace");
  // Send a message that doesn't trigger structured output
  await page.fill('[data-testid="chat-input"]', "What is MJML?");
  await page.click('[data-testid="chat-send"]');
  // Expect plain text response, no A2UI card
  await expect(page.locator('[data-a2ui-rendered="true"]')).toHaveCount(0);
  await expect(page.locator('[data-testid="chat-message-text"]')).toBeVisible();
});
```

**Acceptance:** test passes; visual snapshot matches pre-Phase-2 baseline.

---

### 7.8 — E2E smoke test for full workflow (~0.5 day)

**Goal:** one end-to-end test that exercises the full agentic flow.

**File:** `cms/apps/web/tests/e2e/workspace-agentic-smoke.spec.ts`

**Scenario:**

1. Cold-load workspace (start Playwright timer)
2. Within ≤ 60 s, verify all 9 agents visible in crew rail (§7.13)
3. Press ⌘⇧G to start blueprint run
4. Verify stream events arrive in Event Log within 1.5 s of backend events
5. Wait for HITL pause card (or skip if not triggered in test data)
6. If HITL: click "Resume" → verify pipeline continues
7. Wait for run completion
8. Verify QA gate populates with check results
9. Click a section on canvas → verify 5-surface ripple
10. Press ⌘K → verify command palette has ≥ 95% of actions
11. Three-click audit: count clicks needed to reach Approval submit from cold-load

**Acceptance:** test passes in CI; runs in ≤ 90 s.

---

### 7.9 — Navigability gates (~0.5 day)

**Goal:** §7 gates 11–13 + §12 navigability rules — all enforced in CI.

**Gates:**

| Gate | Spec | Check | CI |
|---|---|---|---|
| Section selection ripples to 5 surfaces in 1 frame | §7.11, §12 S1 | Phase 5.11 e2e | yes |
| Three-click rule | §7.12, §12 N11 | `scripts/audit-three-click.ts` walks the route graph, fails if any action > 3 clicks (excluding ⌘K) | yes |
| 60-second cold-load to "see all 9 agents working" | §7.13 | Phase 7.8 e2e | yes |
| ⌘K coverage ≥ 95% of actions | §12 N1 | `scripts/audit-command-palette.ts` cross-references action registry vs palette entries | yes |
| Reduced-motion respected | §12.4 | `scripts/audit-reduced-motion.ts` checks all CSS animations + Framer-Motion variants | yes |
| Semantic colors only (no hex in components) | §12 N3 | ESLint rule `no-hardcoded-status-colors` | yes |
| Card anatomy invariant | §12 N10 | structural snapshot test on `_BaseCard` usage | yes |
| No `<Dialog>` over canvas | §12 S4 | code grep + manual review | manual |

**Acceptance:** all gates pass; failing PRs blocked.

---

### 7.10 — Final consistency review (~0.5 day)

**Goal:** one last visual + UX review across the whole product.

**Checklist:**

- DESIGN.md chip on every dashboard route
- Crew rail accessible via workspace
- All A2UI cards consistent in anatomy
- Status colors consistent
- Loading skeletons everywhere
- Empty states have CTAs
- Error states have recovery
- Hover/focus visible
- Three-click rule passes
- ⌘K covers the surface
- Onboarding tour shows once for new users
- Existing functionality intact

**Output:** `docs/agentic-ui/SHIP-REVIEW.md` — final sign-off doc.

**Acceptance:** signed off by 2 reviewers.

---

## 3 · Verification gates (the §7 success criteria, restated)

| # | Spine reference | Check | Pass criteria |
|---|---|---|---|
| V1 | §7.1 | Visual diff every existing page vs. pre-plan | Zero unintended palette/typography changes |
| V2 | §7.2 | Storybook chromatic both themes | All stories pass |
| V3 | §7.3 | Split view preserved | Phase 5.2 e2e passes |
| V4 | §7.4 | Backend untouched | `git diff main..HEAD -- app/ alembic/` empty |
| V5 | §7.5 | DESIGN.md chip live | Manual + e2e |
| V6 | §7.6 | 9 agents in crew rail | Manual + e2e |
| V7 | §7.7 | A2UI cards in chat | Manual; ≥ 5 of 12 observed |
| V8 | §7.8 | AG-UI event log visible during runs | ≥ 10 events captured per run |
| V9 | §7.9 | HITL works | Phase 7.8 e2e |
| V10 | §7.10 | No new BE endpoints | Network audit during e2e |
| V11 | §7.11 | Section selection ripples to 5 surfaces in 1 frame | Phase 5.11 e2e |
| V12 | §7.12 | Three-click rule + ⌘K ≥ 95% + axe clean | Phase 7.9 audits |
| V13 | §7.13 | 60-second cold-load → 9 agents | Phase 7.8 e2e |
| V14 | §12.1 S5 | Reduced-motion respected | Phase 7.9 audit |
| V15 | §12 N3 | Semantic colors only | ESLint rule |
| V16 | §12 N10 | A2UI anatomy invariant | structural snapshot |
| V17 | §7.2 perf | TTI ≤ 2 s, idle CPU ≤ 1.5% | Lighthouse CI |
| V18 | — | All previous phase verification gates green | review |

---

## 4 · Decisions to lock in this phase

| ID | Question | Default |
|---|---|---|
| D7.1 | Rollout cohort sizes | **10% → 50% → 100%** with 3-day soak between |
| D7.2 | Rollback trigger thresholds | Sentry error > 0.5%, P50 TTI regression > 200 ms |
| D7.3 | Internal-only stage duration | **2 days** |
| D7.4 | Old layout retirement | **Phase 11f** — separate PR after 2 weeks at 100% |
| D7.5 | New A2UI card requests during rollout | **Hold for v1.1** unless severity = blocker |
| D7.6 | Three-click audit script ownership | `scripts/audit-three-click.ts` — maintained by infra rotation |

Record in `docs/decisions/D-010-ship-locks.md`.

---

## 5 · Pitfalls

- **Don't ship at 100% on day 1.** Cohort rollout is non-negotiable. Symbiotic-system bugs are subtle; users will catch what synthetic tests miss.
- **Don't merge feature-flag-on changes during rollout.** Lock layout-related PRs once 10% is live; only land critical fixes.
- **Don't skip the consistency audit.** It catches the small things that erode trust (one page using hex, another using token; one with sheet, another with dialog).
- **Don't rely on smoke test alone.** Run a manual blueprint flow on each cohort stage start.
- **Don't retire the old layout in this phase.** Keep `LegacyWorkspace` mountable for 2 weeks at 100%; emergency rollback should be a flag flip, not a deploy.
- **Don't relax UX gates under deadline pressure.** A2UI anatomy invariant, semantic-colors-only, and reduced-motion respect are *features*, not formalities.
- **Don't ship docs as a stub.** `docs/agentic-ui/README.md` must be readable end-to-end for someone unfamiliar with the project.
- **Don't over-instrument.** Telemetry should answer specific rollback questions (TTI, error rate, click-depth). Avoid event soup.

---

## 6 · Hand-off (post-launch)

After 7.10 sign-off and 100% rollout:

- File Phase 11f issue: "Retire `LegacyWorkspace`" with 14-day delay
- Open the v1.1 vocabulary backlog: any new A2UI cards held during rollout (§D7.5)
- Open the Phase 11a issue: "Server-pushed AG-UI via SSE" — `useAgUiStream` is the seam
- Open the Phase 11b issue: "Add `/api/v1/agents/registry`"
- Open the Phase 11e issue: "DESIGN.md round-trip from inspector"
- Update `docs/TODO-completed.md` with the 10.13 phase summary

**End-state:** all 9 dashboard routes use the unified agentic chrome; selecting a section ripples through five surfaces; agents are first-class citizens; DESIGN.md is the readable brand source; backend untouched; ≥ 1000 LOC of ad-hoc components retired.

The system is one symbiotic organism. The user wins.
