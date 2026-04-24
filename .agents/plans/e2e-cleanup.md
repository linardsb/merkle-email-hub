# E2E Cleanup — Fix Remaining CI Failures

## Context

Recent commits `ff08ee9d`..`bf4fcb68` fixed a chain of CI issues (pgvector image, health-check path, webServer port, ESM seeding, auth-state path). Current CI run (`24882408344`) still fails at **E2E Smoke Tests → Run smoke E2E tests**:

```
ReferenceError: require is not defined in ES module scope, you can use import instead
   at import-fidelity.spec.ts:1
> 1 | import { test, expect } from "./fixtures";
```

## Root cause

`cms/apps/web/e2e/import-fidelity.spec.ts` still constructs `__dirname` from `import.meta.url`:

```ts
import { fileURLToPath } from "node:url";
const __dirname = dirname(fileURLToPath(import.meta.url));
```

`import.meta.url` forces Playwright's loader into ESM mode, but the transpiled `import { test, expect } from "./fixtures"` emits a `require` call, which blows up in ESM scope. Commit `bf4fcb68` removed the identical pattern from `fixtures/constants.ts` and switched to `process.cwd()`; `import-fidelity.spec.ts` was missed.

Test collection fails at load time, so **all** smoke specs abort — even those that don't import the bad file.

## Fix

Apply the same `process.cwd()` pattern to `import-fidelity.spec.ts`. Playwright runs from the package root (`cms/apps/web`), so `process.cwd() + "/e2e/fixtures"` is the correct anchor.

## Steps

1. **Edit `cms/apps/web/e2e/import-fidelity.spec.ts`**
   - Remove `fileURLToPath` import and the `import.meta.url`-derived `__dirname`.
   - Change `loadFixture` to resolve from `process.cwd()`: `resolve(process.cwd(), "e2e", "fixtures", name)`.

2. **Audit the rest of `cms/apps/web/e2e/` for the same pattern.**
   - `grep -rn "import.meta\|fileURLToPath" e2e/` — confirm nothing else relies on ESM-only identifiers.

3. **Commit** `test(e2e): drop import.meta.url from import-fidelity, resolve fixtures from cwd`.

4. **Push and watch CI.** If the smoke job advances past collection and hits real test failures, triage them as a follow-up (out of scope for this cleanup — we're unblocking the pipeline first).

## Verification

- `grep -rn "import.meta\|fileURLToPath\|__dirname" cms/apps/web/e2e/` returns no matches inside `e2e/` source.
- CI run on the new commit reaches the "Running N tests using 1 worker" line (past the collection error).

## Non-goals

- Fixing any individual failing smoke test that only surfaces after collection succeeds — triaged separately once we can see them.
- Migrating the package to `"type": "module"` — scope creep.

---

## Phase 2 — NextAuth missing `AUTH_SECRET` in CI

### Symptom (CI run `24883498651`)

Collection passed (`Running 8 tests using 1 worker`), but the Next.js dev server flooded with:

```
[auth][error] MissingSecret: Please define a `secret`.
```

Every login attempt returned 500; all auth-dependent smoke tests stalled in `waitForURL` until the 10-minute job timeout cancelled the run.

### Root cause

`cms/apps/web/auth.ts` calls `NextAuth({...})` with no explicit `secret`. NextAuth v5 reads `AUTH_SECRET` from env at boot. The `e2e-smoke` job's env block set `AUTH__JWT_SECRET_KEY` (backend) but not `AUTH_SECRET` (frontend).

### Fix

Add `AUTH_SECRET: test-secret-for-ci` to the `e2e-smoke` job env block in `.github/workflows/ci.yml`.

### Verification

- CI re-run reaches per-test results (pass or fail) instead of the `MissingSecret` flood.
- No `MissingSecret` in the `[WebServer]` lines.

---

## Phase 3 — Visibility for hanging tests

### Symptom (CI run `24884087946`)

With `AUTH_SECRET` in place, no more `MissingSecret`. Playwright printed `Running 8 tests using 1 worker` at `10:14:12`, then produced **zero output** for 9 minutes until the job hit `timeout-minutes: 10` and was cancelled. `if: failure()` artifact step did not fire on cancellation, so no traces.

### Root cause

Only reporter configured was `html`, which writes nothing to stdout during the run. A hang is indistinguishable from slow progress. Workflow timeout of 10 min is tighter than the worst-case budget (setup + 8 tests × 3 retries × 30s).

### Fix

1. `playwright.config.ts`: in CI use both `list` (stdout progress) and `html` (trace/report) reporters.
2. `.github/workflows/ci.yml`: bump e2e-smoke `timeout-minutes` 10 → 20; change artifact upload condition to `if: ${{ failure() || cancelled() }}` so we always get traces.

### Verification

- Next CI run prints per-test `[n/8] ✓ ...` or `✘ ...` lines.
- If it hangs again, artifacts download and the trace viewer shows the hang location.

---

## Phase 4 — `waitForURL` regex matches full URL, not pathname

### Symptom (CI run `24884775604`)

With the `list` reporter we finally see every smoke test timing out at 30s × 3 retries. Every failure stack is identical:

```
Error: page.waitForURL: Test timeout of 30000ms exceeded.
  waiting for navigation until "load"
    navigated to "http://localhost:3100/"
> 11 | await page.waitForURL(/^\/$|\/projects|\/dashboard/);
```

Login succeeds, the app navigates to `http://localhost:3100/`, yet Playwright keeps waiting.

### Root cause

`page.waitForURL(regex)` matches against the full URL, not the pathname. The intended anchor `^\/$` never matches a full URL (which starts with `http`). Post-login lands at `/` (homepage) — the regex has no alternative that matches the root, so it waits forever.

### Fix

Replace with `/\/(projects|dashboard)?$/` in three places:
- `cms/apps/web/e2e/fixtures/auth.ts:38` (powers every `authenticatedPage` fixture)
- `cms/apps/web/e2e/auth.spec.ts:11`
- `cms/apps/web/e2e/collaboration.spec.ts:32`

The new regex matches URLs ending with `/`, `/projects`, or `/dashboard` — covers all three valid post-login landing states.

`auth.spec.ts:28`'s `/\/login/` is already a substring match and needs no change.

### Verification

- `auth.spec.ts "login with valid credentials"` passes.
- All `authenticatedPage`-dependent smoke tests can at least reach their first `page.goto` after login.

---

## Phase 5 — global-setup sends stale schema; "create project" uses stale IDs

### Symptom (CI run `24885565892`)

After Phase 4 the `list` reporter is finally honest:

```
✓  1 auth.spec.ts  login with valid credentials
✓  5 dashboard.spec.ts  dashboard loads with navigation
✘  2 builder, 9 export, 12–15 workspace  → "Shared test project was not created in global-setup"
✘  6–8 dashboard "create a new project" → locator.fill timeout on #name
```

### Root cause

1. **global-setup.ts** POSTs `{ name, description, category, target_esp }` to `/api/v1/projects`. The current `ProjectCreate` schema (app/projects/schemas.py:36) requires `client_org_id`; `category` and `target_esp` are **not fields on the schema at all**. The 422 was silently swallowed by `if (projectRes.ok)`, so `projectId` was written as `null`. Every test that used `authenticatedPage` → `getSharedProjectId()` threw at constants.ts:26.

2. **dashboard.spec.ts "create a new project"** fills `#name` and `#description`, but the current dialog uses `#project-name` / `#project-description` (cms/apps/web/src/components/dashboard/create-project-dialog.tsx). The client-org dropdown auto-selects when exactly one org exists, so once global-setup seeds one, the test doesn't need to touch `#project-org`.

3. **fixtures/api.ts ApiHelper.createProject()** has the same stale schema as (1).

### Fix

- `global-setup.ts`: list orgs, create one if zero, then create the project with `client_org_id`. Throw loudly on any non-2xx with response body included. Persist `clientOrgId` into auth-state for future use.
- `fixtures/api.ts` `createProject`: query orgs first, include `client_org_id`, drop `category`/`target_esp`.
- `dashboard.spec.ts`: `#name` → `#project-name`, `#description` → `#project-description`. The org dropdown auto-selects since global-setup created exactly one org.

### Verification

- All `Shared test project was not created` errors disappear.
- `dashboard.spec.ts "create a new project"` gets past form fill.
- Any remaining failures reveal their own root causes without the noise.
