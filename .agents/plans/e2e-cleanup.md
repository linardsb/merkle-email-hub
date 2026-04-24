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
