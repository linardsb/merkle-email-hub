# Tech Debt 00 — Status and Roadmap

**Source:** `TECH_DEBT_AUDIT.md` (2026-04-26, 70 findings F001–F070)
**Scope:** Reconcile audit doc with current `main`, sequence the open items into 21 executable sessions.
**Status:** Active — meta-plan; sub-plans referenced inline; new sub-plans created lazily.
**Generated:** 2026-05-04

## Decisions locked

1. **Audit refresh runs first as a doc-only PR (Session 0).** Folding into Session 1 hides the doc baseline behind a code review and forces every later session to re-verify status.
2. **RLS approach: option B** (repo-layer enforcement; retire RLS migrations). RLS as defense-in-depth is only valuable if live — currently it's a comment that doesn't compile. Faster to land, debuggable, fewer DB infra changes.
3. **F013 closure splits across 2 sessions ≥2 weeks apart.** The legacy `_convert_recursive` is a load-bearing fallback when MJML compile fails; removing without telemetry risks silent production breakage. Instrument first (Session 7), wait for Grafana confirmation, remove (Session 18).
4. **Plan 01 (quick wins) owns F027–F029.** Plan 02 already shipped its agent + MCP scope work; the JWT items in Plan 02 are reference, not execution scope. Single-source ownership prevents double-execute.
5. **Sequencing assumes 1 contributor.** Parallelism flagged in the table; a team of 2+ can fan out tracks 10–17 against 5–8 trivially.
6. **Tier-1 stop point after Session 4** = "minimum-viable-secure" milestone. Production deploys are safe past this point and unsafe before it. Tag a release here.
7. **Sub-plans for sessions 10–20 are written lazily**, one session before execution. Avoids ~3500 LOC of speculative plan content drifting against `main`.
8. **Snapshot regression is the safety net for converter refactor** (Sessions 5–6). `make rendering-regression` zero-diff is the gate, not unit tests. Per-branch unit tests (F065) come after, in Session 17.
9. **Two sweep PRs at the end, by review domain.** Backend sweep (Session 19) and frontend sweep (Session 20). Heterogeneous content is fine inside one review domain; mixing backend/frontend in a sweep is not.

## Phase 1 — Audit doc reconciliation (Session 0 deliverable)

### Findings to flip OPEN → RESOLVED (inline annotation)

| ID | Evidence on disk | Closure ref |
|---|---|---|
| F006 | `app/streaming/{manager,subscriber,routes}.py` gone; `/ws/stream` mount removed from `app/main.py` | `eddcd1ac` (#40) |
| F007 | `app/example/` gone; `/api/v1/items` removed from `app/main.py` | `eddcd1ac` (#40) |
| F015 | `mjml_generator.py` + `penpot/converter.py` shim deleted; `DESIGN_SYNC__PENPOT_CONVERTER_ENABLED` flag removed | `eddcd1ac` |
| F018 | `app/qa_engine/custom_checks/` package, 11 files (a11y, brand, css, dark_mode, file_size, html, image, link, mso, personalisation, spam) | landed Apr 27 |
| F019 | `app/qa_engine/checks/_factory.py` exists | landed Apr 27 |
| F032 | `app/core/config/` is now a 14-file package (8999-LOC `__init__.py` is the re-export aggregator) | landed Apr 28 |
| F041 | already inline in audit; 332 per-icon files under `cms/apps/web/src/components/icons/generated/` | Plan 09a (#48) |
| F044 | `cms/apps/web/src/hooks/use-builder.ts` 215 LOC; `cms/apps/web/src/lib/builder/html-assembler.ts` exists with tests | landed |
| F048 | collaboration WS JWT wired | landed |
| F064 | hardcoded `linardsberzins@gmail.com` moved to `settings.auth.demo_user_email` | `eddcd1ac` |

### Fudge / partial items resolved to explicit status

| ID | New status | Closes when |
|---|---|---|
| F035 | OPEN — count refreshed | Audit refresh records the actual count (currently 67 `DESIGN_SYNC__*` entries in `.env.example`, up from the 47 stated in the audit). Cull session is out of scope here; goal: ≤30 active flags. |
| F043 | OPEN — PARTIAL (corrected from user-table claim) | 2026-05-04 verification: `grep -rl '@ts-nocheck' cms/apps/web/src` returns 10 files (down from the audit's 12). Closes when count reaches 0; tracked by Session 16 (`tech-debt-09c-ts-strict-tests.md`). |
| F063 | OPEN — partial | `.gitignore` covers `*.zip`, `=2.0`, `e2e-screenshots/`, and per-output `data/debug/*/{actual.html,rendered.png,raw_figma.json,structure.json,tokens.json,report.json,...}`. Curated committed fixtures: `expected.html`, `manifest.yaml`, `vlm_classifications.json`, `actual-tree-with-fixes.html`, `actual-with-fixes.html`. Closes when EITHER (a) flip to blanket-ignore + `!` exceptions for the 5 curated types; OR (b) update line-113 comment to declare current pattern the final design and F063 closes as-designed. **Session 0 deferred the .gitignore flip** — it conflicts with a deliberate maintainer comment and warrants a discrete decision. |

### Findings that stay OPEN

F001, F002, F003, F010, F011, F013, F014, F025, F026, F027, F028, F029, F030, F031, F036, F037, F038, F039, F040, F042, F043, F045, F046, F047, F049, F050, F051, F052, F053, F054, F055, F056, F057, F058, F059, F060, F061, F062, F065, F066, F067, F068, F070.

### Sections to refresh

- **Top 5 — Fix These First:** items 3 (Phase 48) and 5 (dead code) drop out — shipped. Replace with F010/F011 (converter god funcs) and F052/F053 (Knowledge split).
- **Quick Wins checkboxes:** tick F050, F064; mark F063 as partial.
- **Open Questions:** Q2 → "RESOLVED — Phase 48 parked under `prototypes/ai-pipeline/`, see Plan 05B"; Q3 → "RESOLVED — `app/example/` deleted, `eddcd1ac`"; Q4 → "RESOLVED — `/ws/stream` deleted, `eddcd1ac`". Q1 collapses after Session 2 lands.
- **"Things That Look Bad But Are Actually Fine":** stale paths — `app/core/config.py` → now a package; `app/qa_engine/custom_checks.py` → now a package. Sweep refresh, no logic changes.

## Phase 2 — 21-session execution table

### Critical path (sessions 0–4, serial — Tier 1)

| # | Title | Findings | Plan ref | Verify | Effort |
|---|---|---|---|---|---|
| 0 | Audit refresh (doc-only) | F035 count, F042 size, F043 PARTIAL correction, F063 partial close, RESOLVED annotations on 10 findings | (this file, Phase 1) | doc PR review; `git status` clean; pre-commit passes | 30–60m |
| 1 | Multi-tenant repo scoping | F002, F003 | `tech-debt-03-multi-tenant-isolation.md` §A | new `tests/test_cross_tenant_leak.py` parametrized over 8 repos; `make check-full` | 1 session |
| 2 | RLS retirement + env doc | F001 | `tech-debt-03-multi-tenant-isolation.md` §B | `alembic upgrade head` clean; grep zero `BYPASSRLS` references; CLAUDE.md updated | 1 session |
| 3 | Frontend proxy + token security | F045, F046, F047 | `tech-debt-01-quick-wins.md` (frontend subset) | `make check-fe` + new proxy header tests + 401 invalidation test | 1 session |
| 4 | Auth cluster — JWT + lockout + revocation | F027, F028, F029, F031 | `tech-debt-01-quick-wins.md` (auth subset) | `make check` + token edge-case tests | 1 session |

**Tier-1 stop point.** Tag release here. Production deploys are safe past this line; before it they expose cross-tenant data and accept malformed JWTs.

### God-function decomposition (sessions 5–9)

| # | Title | Findings | Plan ref | Notes |
|---|---|---|---|---|
| 5 | RenderContext extraction | F010 | `tech-debt-08-converter-god-functions.md` (split as 08a) | **Pre-step:** capture `make rendering-regression` baselines. **Post-step:** zero-diff assertion. |
| 6 | `_convert_with_components` phase split | F011 | `tech-debt-08-converter-god-functions.md` §B | Split into `MatchPhase` / `RenderPhase` / `VerifyPhase` frozen dataclasses. Snapshot equivalence. |
| 7 | Legacy shim instrumentation | F013 (instrument only) | `tech-debt-08-converter-god-functions.md` §C1 (split as 08c) | structlog event + Prometheus counter at the 2 shim entry points + `DeprecationWarning`. **Starts the 2-week telemetry clock.** |
| 8 | DesignSyncService facade deletion | F012 closure | `tech-debt-08b-design-sync-service-deletion.md` | Delete the 1729-LOC delegating facade; rewrite ~30 caller imports. Mechanical. |
| 9 | `workspace/page.tsx` decomposition | F042 | `tech-debt-09-frontend-cleanup.md` §A | Extract `useWorkspaceTemplate`/`useWorkspaceDialogs`/`useWorkspaceFollowMode`/`useAgentMode`. **Parallel-safe with 5–8** (no shared files). |

### Parallel tracks (sessions 10–17 — fan out)

Six independent backend tracks (10–15) + two frontend/test tracks (16, 17). Schedule in any order once Tier-1 is green. Each is 1 session.

| # | Title | Findings | Plan ref | New plan? |
|---|---|---|---|---|
| 10 | Resilience cluster | F036, F037, F038, F040, F055 | `tech-debt-10-config-and-observability.md` (extend) | Extend Plan 10 |
| 11 | `/bootstrap` hardening | F030 | `tech-debt-12-auth-bootstrap.md` | New (lazy) |
| 12 | LLM adapter base class | F026 | `tech-debt-13-llm-adapter-base.md` | New (lazy) |
| 13 | Eval runner registry | F025 | `tech-debt-13b-eval-runner-registry.md` | New (lazy) |
| 14 | KnowledgeService split + RRF extract | F052, F053, F054 | `tech-debt-11-knowledge-split.md` | New (lazy) |
| 15 | Figma typed boundaries | F014 | `tech-debt-15-figma-typed-boundaries.md` | New (lazy) |
| 16 | Frontend test types + middleware default-deny | F051, F068 (F043 verify-only) | `tech-debt-09c-ts-strict-tests.md` (extend) | Extend |
| 17 | Connector + QA test gaps | F065, F066, F067 | Extends `tech-debt-04-connector-dedup.md` + `tech-debt-06-custom-checks-split.md` | Extend |

**Parallelism map (file disjointness verified):**
- 10 → `app/core/database.py`, `app/email_engine/service.py`, `app/scheduling/engine.py`, `app/notifications/emitter.py`, `app/qa_engine/repair/pipeline.py`
- 11 → `app/auth/routes.py`, `app/auth/service.py`
- 12 → `app/ai/adapters/{base,anthropic,openai_compat}.py`
- 13 → `app/ai/agents/evals/runner.py`
- 14 → `app/knowledge/{service,fusion,repository}.py`
- 15 → `app/design_sync/figma/{service,raw_types}.py`
- 16, 17 → `cms/` and `tests/` only

Six-way backend parallelism is safe. Track 16 + 17 add 2 more frontend/test contributors.

### Telemetry-gated closure (Session 18)

| # | Title | Findings | Plan ref | Trigger |
|---|---|---|---|---|
| 18 | Legacy shim removal | F013 closure | `tech-debt-08-converter-god-functions.md` §C2 | ≥2 weeks since Session 7 + Grafana shows zero hits at the 2 shim entry points. If non-zero hits → converts to caller-migration session, not removal. |

### Long tail — sweep PRs (sessions 19–20)

| # | Title | Findings | Plan ref |
|---|---|---|---|
| 19 | Backend sweep | F049 (SDK CI gate), F056, F057, F058, F059, F060, F061, F062, F070 | `tech-debt-19-backend-sweep.md` (lazy) |
| 20 | Frontend / repo sweep | F050, F063 closure | `tech-debt-20-frontend-sweep.md` (lazy) |

## Plan dependency graph

```
0 (audit refresh)
  └─ 1 (multi-tenant scoping) ── 2 (RLS retirement)
       └─ 3 (proxy security)
            └─ 4 (auth cluster)         ← TIER-1 STOP POINT (tag release)
                 └─ 5 (RenderContext)
                      └─ 6 (_convert_with_components)
                           └─ 7 (instrument shims) ─ ─ 2 weeks ─ ─ 18 (remove shims)
                                └─ 8 (facade deletion)
                                     └─ 9 (workspace decomposition)
                                          └─ 10–17 (fan out, parallel-safe)
                                               └─ 19, 20 (sweep)
```

## Verification protocol per session

Every session ends with:
1. `make check-full` (backend) or `make check-fe` (frontend) green
2. New regression test asserting the finding-specific behavior
3. PR description references the F00N IDs closed
4. Inline `**RESOLVED** (<commit>, <plan ref>)` annotation in `TECH_DEBT_AUDIT.md`, in the same PR
5. Sessions 5–8 also require `make rendering-regression` zero-diff against pre-session baseline

## Sub-plan creation rule

Lazy. New sub-plans (sessions 11, 12, 13, 14, 15, 19, 20) are written one session before their execution, not preemptively. The meta-plan is the index; each sub-plan inherits scope from the row above. Reasons:

- Plan stubs drift; better to write fresh against current `main` at execution time.
- 7 new plan files would add ~3500 LOC of speculative content before any code lands.
- Per project rule: plans cap at 700 LOC each; this meta-plan is the routing layer.

## Out of scope

- Decisions in "Things That Look Bad But Are Actually Fine" — the audit already justified each.
- `.agents/deferred-items.json` Phase 50.7 LEGO entries — different lineage from F00N findings, tracked separately under `.claude/rules/deferred-items.md`.
- Repo housekeeping beyond F063 (rotating `TODO-completed.md`, archiving plans older than the active phase).
- F018 / F019 verification beyond confirming the files exist on disk (already done in Phase 1 evidence column).

## Hand-off

**Next session: 1** (Multi-tenant repo scoping). Session 0 ran on 2026-05-04: `TECH_DEBT_AUDIT.md` doc refresh landed; `.gitignore` flip for F063 closure deferred to a future micro-session pending maintainer affirmation of approach (a) vs. (b).
