# Tech Debt 09a — `custom-icons.tsx` Monolith Split (F041)

**Source:** Carved out of `tech-debt-09-frontend-cleanup.md` Part A.
**Sibling plans:** `tech-debt-09c-ts-strict-tests.md` (Part C) — independent, can run in parallel.
**Prerequisite:** `tech-debt-09-frontend-cleanup.md` Parts B/D/E/F/G already landed on `refactor/tech-debt-09-frontend`. Branch off `main` after that PR merges, OR off the same branch if working in parallel.
**Scope:** Split the 9,882-LOC `custom-icons.tsx` into per-icon files. Confirm production bundle size does not regress.
**Goal:** `custom-icons.tsx` deleted; per-icon files exist under `components/icons/generated/`; barrel re-exports them; `next build` output size unchanged or smaller.
**Estimated effort:** Full session. May require revert if bundle regresses (see Risk).

## Risk warning (from parent plan)

> *"Verify production `next build` output before/after. If the new structure tree-shakes less efficiently, revert and just split the file (keep barrel pattern)."*

The whole point of splitting is to drop ~9.8k LOC out of TypeScript checking and to enable per-icon tree-shaking. If the per-file structure increases bundle size for any reason (worse Turbopack chunking, broken sideEffects flags, lazy-import overhead), the change is a net loss and must revert. **Measure before declaring done.**

## Pre-flight

```bash
git checkout -b refactor/tech-debt-09a-icons-split
cd cms && pnpm install

# Capture baseline bundle size
pnpm --filter web build 2>&1 | tee /tmp/build-before.log
du -sh apps/web/.next > /tmp/size-before.txt
ls -la apps/web/.next/static/chunks/*.js | awk '{print $5, $9}' | sort -rn > /tmp/chunks-before.txt
```

Keep these artefacts — they are the gate for the final verification step.

## Inventory

| File | LOC | Role |
|---|---|---|
| `cms/apps/web/scripts/generate-icons.mjs` | 995 | Generator. Currently writes ONE monolith. ICON_MAP defines ~330 icons. |
| `cms/apps/web/src/components/icons/custom-icons.tsx` | 9882 | Generated monolith — auto-output, do not hand-edit. |
| `cms/apps/web/src/components/icons/index.ts` | 453 | Barrel: re-exports custom icons + falls back to lucide-react for the rest. |
| `email-templates/Icons/**` | n/a | SVG sources used by the generator. |

Search for callers (verify before/after):

```bash
grep -rln "from [\"']@/components/icons" cms/apps/web/src | wc -l
# Expected: ~120-130 files
```

## A1. Generator rewrite

Rewrite the emit loop in `scripts/generate-icons.mjs` (currently around line 941: `for (const [name, config] of Object.entries(ICON_MAP))` and line 990: `writeFileSync(... "custom-icons.tsx", output)`) to:

1. **Emit one file per icon** at `cms/apps/web/src/components/icons/generated/{IconName}.tsx`.
   Each file should contain only the single component definition + its `export`. Keep the JSDoc generation banner (`Do not edit manually — regenerate with: node scripts/generate-icons.mjs`) on every output file so contributors don't try to edit by hand.

2. **Drop `forwardRef`** (parent plan F039 — but see audit step below before applying).
   React 19 doesn't need `forwardRef` for new components, and the per-icon files are new code. The icons currently render `<svg>` — the only legitimate reason to forwardRef is if a caller attaches a ref to a wrapper. Audit:
   ```bash
   grep -rnE "<[A-Z][A-Za-z0-9]+\s+[^>]*\bref=" cms/apps/web/src/**/*.{tsx,ts} \
     | grep -E "(Brain|Bot|Sparkles|<other icons>)"   # iterate per icon name
   ```
   If **any** caller passes a ref to an icon component, **keep `forwardRef`**. Don't risk breaking refs to save a wrapper.

3. **Generate the barrel** at `cms/apps/web/src/components/icons/index.ts` (regenerate, do not hand-edit). Two strategies — pick one based on the bundle measurement (A4):

   **Strategy 1 — Static re-exports (preferred — best tree-shaking):**
   ```typescript
   // ── Custom icons (332 — auto-generated) ──
   export { Brain } from "./generated/Brain";
   export { Bot } from "./generated/Bot";
   export { Sparkles } from "./generated/Sparkles";
   // ... one line per icon
   // ── lucide-react fallback (existing logic) ──
   export { ChevronUp, GripVertical, GripHorizontal, /* ... */ } from "lucide-react";
   ```
   Next 16 + Turbopack should tree-shake unused exports per file. This is the recommended starting point.

   **Strategy 2 — Dynamic imports (only if Strategy 1 regresses):**
   ```typescript
   // Each component is a React.lazy() wrapper around its file.
   // Adds runtime overhead but eliminates load-time cost for unused icons.
   ```
   Avoid unless Strategy 1 measurably regresses.

4. Mark `cms/packages/sdk/package.json` and any icons-package equivalent with `"sideEffects": false` if not already set. The generated files must be pure (no side effects) so bundlers can drop unused ones.

## A2. Generate

```bash
cd cms/apps/web
node scripts/generate-icons.mjs
```

Verify output:
- `ls components/icons/generated/ | wc -l` matches `ICON_MAP` size (≈ 330)
- Each file ≤ 50 LOC
- Barrel `index.ts` ≤ 600 LOC and references every generated file

## A3. Migrate (if needed)

Existing imports already use the barrel (`@/components/icons`), so callsites should not need changes. Verify:

```bash
# Direct imports of custom-icons.tsx — should now be zero (or only inside the barrel)
grep -rln "from [\"']@/components/icons/custom-icons[\"']" cms/apps/web/src
```

If any direct imports exist, rewrite them to use the barrel:

```typescript
// before
import { Brain, Bot } from "@/components/icons/custom-icons";
// after
import { Brain, Bot } from "@/components/icons";
```

## A4. Bundle size verification (gate)

```bash
pnpm --filter web build 2>&1 | tee /tmp/build-after.log
du -sh apps/web/.next > /tmp/size-after.txt
ls -la apps/web/.next/static/chunks/*.js | awk '{print $5, $9}' | sort -rn > /tmp/chunks-after.txt

echo "Before:"; cat /tmp/size-before.txt
echo "After: "; cat /tmp/size-after.txt
diff /tmp/chunks-before.txt /tmp/chunks-after.txt | head -40
```

**Pass criteria:**
- `.next` total size: ≤ baseline + 1% (essentially equal)
- The largest client chunk: ≤ baseline (icons should not bloat any single chunk)
- Initial page chunks (e.g. workspace, dashboard): no new "icons-megachunk" pattern

**If size regressed:**
- First, verify `sideEffects: false` is set everywhere in the icons package path
- If still regressed, abandon Strategy 1 and revert to a single-file split (just delete `custom-icons.tsx` after regenerating into the barrel directly — no `generated/` directory). This still removes the 9.8k-LOC type-check cost without changing the export topology.
- Document the regression in the PR description so reviewers see the constraint.

## A5. Delete the monolith

After A4 passes:

```bash
rm cms/apps/web/src/components/icons/custom-icons.tsx
```

Update the generator's output path comments and the JSDoc banner accordingly.

## A6. Final checks

```bash
cd cms
pnpm --filter web type-check    # zero errors (and ~9.8k fewer LOC checked)
pnpm --filter web test           # all tests green
pnpm --filter web lint           # clean
pnpm --filter web e2e:smoke      # ensure no runtime icon import failures
```

## Done when

- [ ] `cms/apps/web/src/components/icons/custom-icons.tsx` deleted.
- [ ] `cms/apps/web/src/components/icons/generated/*.tsx` exists, one file per icon in `ICON_MAP`.
- [ ] `cms/apps/web/scripts/generate-icons.mjs` rewritten and the barrel regenerated.
- [ ] `next build` total size and largest chunk ≤ baseline (within 1%).
- [ ] `pnpm --filter web type-check` green; LOC checked drops by ~9,800.
- [ ] `pnpm --filter web test` and `e2e:smoke` green.
- [ ] PR title: `refactor(cms): split custom-icons.tsx monolith into per-icon files (F041)`.
- [ ] PR description includes the before/after bundle size numbers.
- [ ] Mark **F041 as RESOLVED** in `TECH_DEBT_AUDIT.md`.

## Rollback

This change touches:
- `scripts/generate-icons.mjs` (rewritten)
- `src/components/icons/index.ts` (regenerated)
- `src/components/icons/custom-icons.tsx` (deleted)
- `src/components/icons/generated/*.tsx` (created)

Rollback = revert the single PR commit. Re-run `node scripts/generate-icons.mjs` from the previous generator HEAD if you need the old monolith back during a hotfix window.

## Notes for the agent

- The generator already exists and writes to `OUTPUT_DIR`. Read its current emit loop carefully before rewriting — it has accumulated SVG-cleanup rules (color stripping, currentColor mapping) that the new emit must preserve verbatim.
- Each generated file should be a React function component that returns `<svg>` directly — no wrapper div, no className-merge logic that wasn't in the original. The emit loop's job is mechanical.
- Do **not** mix Strategy 1 and Strategy 2 (`React.lazy` for some icons, static for others). Be consistent so the bundle behaviour is predictable.
- The lucide-react fallback section of the barrel must continue to work — that path provides ~50 icons not in `ICON_MAP`.
- Verify with `pnpm --filter web e2e:smoke` before declaring done — there have been past incidents where icon imports break only at runtime when the chunk graph changes.
- Do **not** run `pnpm --filter web lint:fix` over the whole project — it has been observed to mangle JSX `eslint-disable-next-line` comments into empty `{}` expressions. Run targeted: `pnpm exec eslint <files> --fix` from `cms/apps/web/`.
